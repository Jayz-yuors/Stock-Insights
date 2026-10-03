from db_config import create_connection

import pandas as pd
import numpy as np

# ============================================================
# OPTIONAL ML DEPENDENCIES
# ============================================================

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
    )

    ML_AVAILABLE = True

except ImportError:
    ML_AVAILABLE = False


# ============================================================
# UTILITY: CORRECT CLOSE PRICE COLUMN
# ============================================================

def get_close_price_column(df):
    """
    Return the name of the close-price column.

    Checks for 'close' case-insensitively.
    """
    for col in df.columns:
        if col.lower() == "close":
            return col

    raise KeyError("Close price column not found!")


# ============================================================
# FETCH PRICE HISTORY
# ============================================================

def fetch_prices(ticker_symbol, start_date=None, end_date=None):
    """
    Fetch OHLCV history from PostgreSQL.
    """

    conn = create_connection()

    sql = """
        SELECT sp.trade_date,
               sp.open_price  AS open,
               sp.high_price  AS high,
               sp.low_price   AS low,
               sp.close_price AS close,
               sp.volume
        FROM stock_prices sp
        JOIN companies c
          ON sp.company_id = c.company_id
        WHERE c.ticker_symbol = %s
          AND sp.close_price IS NOT NULL
    """

    params = [ticker_symbol]

    if start_date and end_date:

        sql += " AND sp.trade_date BETWEEN %s AND %s"
        params += [start_date, end_date]

    elif start_date:

        sql += " AND sp.trade_date >= %s"
        params.append(start_date)

    elif end_date:

        sql += " AND sp.trade_date <= %s"
        params.append(end_date)

    sql += " ORDER BY sp.trade_date ASC"

    df = pd.read_sql(sql, conn, params=params)

    conn.close()

    if df.empty:
        return None

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    for column in ["open", "high", "low", "close", "volume"]:

        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    df = df.dropna(subset=["close"])

    if df.empty:
        return None

    return df


# ============================================================
# CURRENT PRICE
# ============================================================

def fetch_current_price(ticker_symbol):

    conn = create_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT sp.close_price
            FROM stock_prices sp
            JOIN companies c
              ON sp.company_id = c.company_id
            WHERE c.ticker_symbol = %s
              AND sp.close_price IS NOT NULL
            ORDER BY sp.trade_date DESC
            LIMIT 1;
            """,
            (ticker_symbol,),
        )

        row = cur.fetchone()

    conn.close()

    return float(row[0]) if row else None


# ============================================================
# COMPANY INFORMATION
# ============================================================

def fetch_company_info(ticker):

    conn = create_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT company_name, ticker_symbol
            FROM companies
            WHERE ticker_symbol = %s;
            """,
            (ticker,),
        )

        row = cur.fetchone()

    conn.close()

    if not row:
        return None

    return {
        "company_name": row[0],
        "ticker_symbol": row[1],
    }


# ============================================================
# PRICE INDICATORS
# ============================================================

def compute_sma(df, window=20):

    col = get_close_price_column(df)

    df = df.copy()

    df["SMA"] = (
        df[col]
        .rolling(window, min_periods=1)
        .mean()
    )

    return df


def compute_ema(df, window=20):

    col = get_close_price_column(df)

    df = df.copy()

    df["EMA"] = (
        df[col]
        .ewm(span=window, adjust=False)
        .mean()
    )

    return df


def detect_abrupt_changes(df, threshold=0.05):

    col = get_close_price_column(df)

    df = df.copy()

    df["pct_change"] = df[col].pct_change()

    return df[
        abs(df["pct_change"]) > threshold
    ]


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def add_technical_indicators(df):
    """
    Add technical indicators used by the ML pipeline.

    Indicators:
        SMA_20
        SMA_50
        SMA_200
        EMA_20
        EMA_50
        RSI_14
        MACD
        MACD_signal
        MACD_hist
        Golden_Cross
    """

    if df is None or df.empty:
        return df

    df = df.copy()

    col = get_close_price_column(df)

    close = pd.to_numeric(
        df[col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Moving averages
    # --------------------------------------------------------

    df["SMA_20"] = (
        close
        .rolling(20, min_periods=1)
        .mean()
    )

    df["SMA_50"] = (
        close
        .rolling(50, min_periods=1)
        .mean()
    )

    df["SMA_200"] = (
        close
        .rolling(200, min_periods=1)
        .mean()
    )

    df["EMA_20"] = (
        close
        .ewm(span=20, adjust=False)
        .mean()
    )

    df["EMA_50"] = (
        close
        .ewm(span=50, adjust=False)
        .mean()
    )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = close.diff()

    gain = delta.where(
        delta > 0,
        0.0
    )

    loss = -delta.where(
        delta < 0,
        0.0
    )

    avg_gain = (
        gain
        .rolling(14, min_periods=14)
        .mean()
    )

    avg_loss = (
        loss
        .rolling(14, min_periods=14)
        .mean()
    )

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    df["RSI_14"] = rsi.fillna(50)

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    ema_12 = (
        close
        .ewm(span=12, adjust=False)
        .mean()
    )

    ema_26 = (
        close
        .ewm(span=26, adjust=False)
        .mean()
    )

    macd = ema_12 - ema_26

    macd_signal = (
        macd
        .ewm(span=9, adjust=False)
        .mean()
    )

    df["MACD"] = macd

    df["MACD_signal"] = macd_signal

    df["MACD_hist"] = (
        macd - macd_signal
    )

    # --------------------------------------------------------
    # Golden Cross
    # --------------------------------------------------------

    df["Golden_Cross"] = (
        (
            df["SMA_50"]
            > df["SMA_200"]
        )
        .astype(int)
    )

    return df


# ============================================================
# VOLATILITY & RISK
# ============================================================

def volatility_and_risk(df, window=20):

    col = get_close_price_column(df)

    df = df.copy()

    df["volatility"] = (
        df[col]
        .rolling(window)
        .std()
    )

    df["risk"] = (
        df["volatility"]
        / df[col]
    )

    return df


# ============================================================
# CORRELATION
# ============================================================

def correlation_analysis(tickers):

    series_list = []

    for ticker in tickers:

        df = fetch_prices(ticker)

        if df is None:
            continue

        col = get_close_price_column(df)

        series_list.append(
            df.set_index("trade_date")[col]
            .rename(ticker)
        )

    if not series_list:
        return pd.DataFrame()

    merged = pd.concat(
        series_list,
        axis=1,
        join="inner"
    )

    return merged.corr()


# ============================================================
# COMPANY COMPARISON
# ============================================================

def compare_companies(
    tickers,
    start_date=None,
    end_date=None
):

    series_list = []

    for ticker in tickers:

        df = fetch_prices(
            ticker,
            start_date,
            end_date
        )

        if df is None:
            continue

        col = get_close_price_column(df)

        series_list.append(
            df.set_index("trade_date")[col]
            .rename(ticker)
        )

    if not series_list:
        return pd.DataFrame()

    return pd.concat(
        series_list,
        axis=1,
        join="inner"
    )


# ============================================================
# INVESTMENT STRATEGY
# ============================================================

def best_time_to_invest(df):

    col = get_close_price_column(df)

    if "SMA" not in df.columns:
        df = compute_sma(df)

    return df[
        df[col] > df["SMA"]
    ][
        ["trade_date", col]
    ]


# ============================================================
# ML FEATURE ENGINEERING
# ============================================================

def create_ml_features(df):
    """
    Create features for next-day stock-direction prediction.

    The target is:

        1 -> next day's closing price is higher
        0 -> next day's closing price is lower/equal
    """

    if df is None or df.empty:
        raise ValueError(
            "DataFrame cannot be empty."
        )

    df = df.copy()

    if "SMA_20" not in df.columns:
        df = add_technical_indicators(df)

    close = get_close_price_column(df)

    # --------------------------------------------------------
    # Price-based features
    # --------------------------------------------------------

    df["daily_return"] = (
        df[close].pct_change()
    )

    df["return_5d"] = (
        df[close].pct_change(5)
    )

    df["return_20d"] = (
        df[close].pct_change(20)
    )

    df["high_low_ratio"] = (
        df["high"] - df["low"]
    ) / df[close].replace(
        0,
        np.nan
    )

    df["open_close_ratio"] = (
        df["close"] - df["open"]
    ) / df["open"].replace(
        0,
        np.nan
    )

    df["volume_change"] = (
        df["volume"].pct_change()
    )

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    df["volatility_10"] = (
        df["daily_return"]
        .rolling(10)
        .std()
    )

    df["volatility_20"] = (
        df["daily_return"]
        .rolling(20)
        .std()
    )

    # --------------------------------------------------------
    # Target
    #
    # Shift(-1) means the model learns today's features
    # against tomorrow's direction.
    # --------------------------------------------------------

    df["target"] = (
        df[close].shift(-1)
        > df[close]
    ).astype(int)

    return df


# ============================================================
# ML MODEL FEATURES
# ============================================================

ML_FEATURE_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "SMA_20",
    "SMA_50",
    "SMA_200",
    "EMA_20",
    "EMA_50",
    "RSI_14",
    "MACD",
    "MACD_signal",
    "MACD_hist",
    "Golden_Cross",
    "daily_return",
    "return_5d",
    "return_20d",
    "high_low_ratio",
    "open_close_ratio",
    "volume_change",
    "volatility_10",
    "volatility_20",
]


# ============================================================
# MARKET REGIME CLUSTERING
# ============================================================

def detect_market_regimes(
    df,
    n_clusters=3
):
    """
    Detect market regimes using K-Means.

    Regimes are learned from:
        return
        volatility
        RSI
        MACD
    """

    if not ML_AVAILABLE:
        raise ImportError(
            "scikit-learn is required for ML functionality."
        )

    df = df.copy()

    regime_features = [
        "daily_return",
        "volatility_20",
        "RSI_14",
        "MACD",
    ]

    available = [
        c for c in regime_features
        if c in df.columns
    ]

    regime_data = (
        df[available]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )

    if len(regime_data) < n_clusters:
        df["market_regime"] = 0
        return df

    scaler = StandardScaler()

    scaled = scaler.fit_transform(
        regime_data
    )

    model = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    clusters = model.fit_predict(
        scaled
    )

    df["market_regime"] = np.nan

    df.loc[
        regime_data.index,
        "market_regime"
    ] = clusters

    df["market_regime"] = (
        df["market_regime"]
        .fillna(method="ffill")
        .fillna(0)
        .astype(int)
    )

    return df


# ============================================================
# MODEL EVALUATION
# ============================================================

def _evaluate_model(
    model,
    X_train,
    y_train,
    X_test,
    y_test
):

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    return {
        "model": model,
        "accuracy": float(
            accuracy_score(
                y_test,
                predictions
            )
        ),
        "precision": float(
            precision_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "f1": float(
            f1_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
    }


# ============================================================
# ML STOCK DIRECTION PREDICTION
# ============================================================

def predict_stock_direction(
    df,
    test_size=0.2
):
    """
    Train multiple ML models to predict next-day
    stock direction.

    Models:
        Logistic Regression
        Decision Tree
        Random Forest
        Gradient Boosting

    K-Means is used separately for market-regime
    clustering.

    A chronological train/test split is used to
    reduce future-data leakage.
    """

    if not ML_AVAILABLE:
        raise ImportError(
            "Install scikit-learn before using "
            "predict_stock_direction()."
        )

    if df is None or df.empty:
        raise ValueError(
            "Input DataFrame cannot be empty."
        )

    data = create_ml_features(df)

    data = detect_market_regimes(
        data
    )

    available_features = [
        feature
        for feature in ML_FEATURE_COLUMNS
        if feature in data.columns
    ]

    model_data = data[
        available_features
        + ["target"]
    ].replace(
        [np.inf, -np.inf],
        np.nan
    ).dropna()

    if len(model_data) < 100:
        raise ValueError(
            "At least 100 valid observations "
            "are recommended for ML prediction."
        )

    X = model_data[
        available_features
    ]

    y = model_data["target"]

    split_index = int(
        len(model_data)
        * (1 - test_size)
    )

    if split_index <= 0 or split_index >= len(model_data):
        raise ValueError(
            "Invalid chronological train/test split."
        )

    X_train = X.iloc[:split_index]

    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]

    y_test = y.iloc[split_index:]

    # --------------------------------------------------------
    # Scaling for Logistic Regression
    # --------------------------------------------------------

    scaler = StandardScaler()

    X_train_scaled = (
        scaler.fit_transform(X_train)
    )

    X_test_scaled = (
        scaler.transform(X_test)
    )

    # --------------------------------------------------------
    # Models
    # --------------------------------------------------------

    models = {
        "Logistic Regression":
            LogisticRegression(
                max_iter=1000,
                random_state=42
            ),

        "Decision Tree":
            DecisionTreeClassifier(
                max_depth=6,
                min_samples_leaf=5,
                random_state=42
            ),

        "Random Forest":
            RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_leaf=3,
                random_state=42,
                n_jobs=-1
            ),

        "Gradient Boosting":
            GradientBoostingClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=3,
                random_state=42
            ),
    }

    results = {}

    fitted_models = {}

    # --------------------------------------------------------
    # Logistic Regression
    # --------------------------------------------------------

    logistic_result = _evaluate_model(
        models["Logistic Regression"],
        X_train_scaled,
        y_train,
        X_test_scaled,
        y_test
    )

    results[
        "Logistic Regression"
    ] = {
        key: value
        for key, value in logistic_result.items()
        if key != "model"
    }

    fitted_models[
        "Logistic Regression"
    ] = logistic_result["model"]

    # --------------------------------------------------------
    # Tree-based models
    # --------------------------------------------------------

    for name in [
        "Decision Tree",
        "Random Forest",
        "Gradient Boosting",
    ]:

        result = _evaluate_model(
            models[name],
            X_train,
            y_train,
            X_test,
            y_test
        )

        results[name] = {
            key: value
            for key, value in result.items()
            if key != "model"
        }

        fitted_models[name] = result["model"]

    # --------------------------------------------------------
    # Select best model using F1 score
    # --------------------------------------------------------

    best_model_name = max(
        results,
        key=lambda name:
            results[name]["f1"]
    )

    best_model = fitted_models[
        best_model_name
    ]

    # --------------------------------------------------------
    # Latest prediction
    # --------------------------------------------------------

    latest_features = (
        data[
            available_features
        ]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .dropna()
    )

    if latest_features.empty:
        raise ValueError(
            "Unable to construct latest ML features."
        )

    latest_row = latest_features.iloc[
        [-1]
    ]

    if best_model_name == "Logistic Regression":

        latest_input = (
            scaler.transform(
                latest_row
            )
        )

    else:

        latest_input = latest_row

    prediction = int(
        best_model.predict(
            latest_input
        )[0]
    )

    if hasattr(
        best_model,
        "predict_proba"
    ):

        probabilities = (
            best_model
            .predict_proba(
                latest_input
            )[0]
        )

        probability = float(
            probabilities[prediction]
        )

    else:

        probability = None

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    feature_importance = {}

    if hasattr(
        best_model,
        "feature_importances_"
    ):

        feature_importance = {
            feature: float(importance)
            for feature, importance
            in zip(
                available_features,
                best_model.feature_importances_
            )
        }

    elif hasattr(
        best_model,
        "coef_"
    ):

        coefficients = (
            best_model.coef_[0]
        )

        feature_importance = {
            feature: float(abs(value))
            for feature, value
            in zip(
                available_features,
                coefficients
            )
        }

    # --------------------------------------------------------
    # Current market regime
    # --------------------------------------------------------

    current_regime = int(
        data["market_regime"]
        .iloc[-1]
    )

    return {
        "prediction": (
            "UP"
            if prediction == 1
            else "DOWN"
        ),
        "prediction_class": prediction,
        "probability": probability,
        "best_model": best_model_name,
        "market_regime": current_regime,
        "model_metrics": results,
        "feature_importance": feature_importance,
        "training_samples": int(
            len(X_train)
        ),
        "testing_samples": int(
            len(X_test)
        ),
        "features_used": available_features,
    }


# ============================================================
# SIMPLE ML TEST
# ============================================================

def test_ml_engine():
    """
    Lightweight synthetic test.

    This does NOT require PostgreSQL.
    """

    if not ML_AVAILABLE:
        raise ImportError(
            "scikit-learn is not installed."
        )

    np.random.seed(42)

    rows = 250

    dates = pd.date_range(
        start="2020-01-01",
        periods=rows,
        freq="D"
    )

    returns = np.random.normal(
        0.001,
        0.02,
        rows
    )

    close = (
        100
        * np.exp(
            np.cumsum(returns)
        )
    )

    synthetic = pd.DataFrame({

        "trade_date": dates,

        "open": close
        * np.random.uniform(
            0.99,
            1.01,
            rows
        ),

        "high": close
        * np.random.uniform(
            1.00,
            1.02,
            rows
        ),

        "low": close
        * np.random.uniform(
            0.98,
            1.00,
            rows
        ),

        "close": close,

        "volume": np.random.randint(
            100000,
            1000000,
            rows
        ),
    })

    result = predict_stock_direction(
        synthetic
    )

    assert result["prediction"] in {
        "UP",
        "DOWN"
    }

    assert result["best_model"] in {
        "Logistic Regression",
        "Decision Tree",
        "Random Forest",
        "Gradient Boosting",
    }

    assert "KMeans" not in result["best_model"]

    assert len(
        result["model_metrics"]
    ) == 4

    assert (
        result["market_regime"]
        >= 0
    )

    print(
        "ML ENGINE TEST PASSED"
    )

    print(
        "Best model:",
        result["best_model"]
    )

    print(
        "Prediction:",
        result["prediction"]
    )

    print(
        "Probability:",
        result["probability"]
    )

    print(
        "Market regime:",
        result["market_regime"]
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":
    test_ml_engine()