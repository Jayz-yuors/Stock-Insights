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

# ============================================================
# DWM SYLLABUS ANALYTICS
# Data exploration, preprocessing, classification, regression,
# clustering, association rules, and OLAP-style aggregation.
# ============================================================

def prepare_dwm_dataset(df):
    """Clean OHLCV data and derive DWM-friendly mining features.

    Keeps the original columns, sorts by date, removes duplicate dates,
    imputes missing numeric values with the column median, and adds returns,
    moving averages, volatility, and next-day direction target.
    """
    if df is None or df.empty:
        raise ValueError("No stock observations are available for preprocessing.")

    data = df.copy()
    if "trade_date" in data.columns:
        data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce")
        data = data.dropna(subset=["trade_date"]).sort_values("trade_date")
        data = data.drop_duplicates(subset=["trade_date"], keep="last")

    for col in ["open", "high", "low", "close", "volume"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    close_col = get_close_price_column(data)
    data = data.dropna(subset=[close_col])
    if data.empty:
        raise ValueError("No valid closing prices remain after cleaning.")

    data["daily_return"] = data[close_col].pct_change()
    data["return_pct"] = data["daily_return"] * 100
    data["SMA_20"] = data[close_col].rolling(20, min_periods=1).mean()
    data["EMA_20"] = data[close_col].ewm(span=20, adjust=False).mean()
    data["rolling_volatility"] = data["daily_return"].rolling(20, min_periods=2).std()
    if "volume" in data.columns:
        data["volume_change_pct"] = data["volume"].pct_change() * 100
    else:
        data["volume"] = np.nan
        data["volume_change_pct"] = np.nan

    # The target is shifted from the future; never use it as a predictor.
    data["next_close"] = data[close_col].shift(-1)
    data["next_day_direction"] = np.where(
        data["next_close"].isna(), np.nan,
        (data["next_close"] > data[close_col]).astype(float)
    )
    data["market_direction"] = np.where(
        data["daily_return"] > 0, "Up",
        np.where(data["daily_return"] < 0, "Down", "Flat")
    )

    numeric = data.select_dtypes(include=[np.number]).columns
    target_columns = {"next_close", "next_day_direction"}
    for col in numeric:
        data[col] = data[col].replace([np.inf, -np.inf], np.nan)
        # Never impute future targets: the final row has no known next-day label.
        if col not in target_columns and data[col].notna().any():
            data[col] = data[col].fillna(data[col].median())
    return data.reset_index(drop=True)


def summarize_dwm_dataset(df):
    """Return dataset quality, descriptive statistics, and attribute types."""
    if df is None or df.empty:
        return {"overview": pd.DataFrame(), "statistics": pd.DataFrame(), "missing": pd.DataFrame()}
    overview = pd.DataFrame({
        "Measure": ["Rows", "Columns", "Duplicate rows", "Missing cells", "Memory (KB)"],
        "Value": [
            int(len(df)), int(df.shape[1]), int(df.duplicated().sum()),
            int(df.isna().sum().sum()), round(df.memory_usage(deep=True).sum() / 1024, 2)
        ]
    })
    statistics = df.select_dtypes(include=[np.number]).describe().transpose().reset_index().rename(columns={"index": "Attribute"})
    missing = pd.DataFrame({
        "Attribute": df.columns,
        "Data Type": [str(df[c].dtype) for c in df.columns],
        "Missing Count": [int(df[c].isna().sum()) for c in df.columns],
        "Missing %": [round(float(df[c].isna().mean() * 100), 2) for c in df.columns],
        "Unique Values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    }).sort_values(["Missing %", "Attribute"], ascending=[False, True])
    return {"overview": overview, "statistics": statistics, "missing": missing}


def run_dwm_supervised_analysis(df, test_fraction=0.2):
    """Evaluate a simple/multiple linear regression and DT/Naive Bayes classifiers.

    Chronological split is used for time-series data. Predictors are current-day
    OHLCV and engineered features; targets are next day's close and direction.
    """
    if df is None or len(df) < 60:
        raise ValueError("At least 60 observations are recommended for DWM model evaluation.")
    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.naive_bayes import GaussianNB
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, precision_score, recall_score, f1_score
    except ImportError as exc:
        raise ImportError("Install scikit-learn to run regression and classification.") from exc

    data = prepare_dwm_dataset(df)
    close = get_close_price_column(data)
    feature_candidates = ["open", "high", "low", close, "volume", "daily_return", "SMA_20", "EMA_20", "rolling_volatility", "volume_change_pct"]
    features = [c for c in feature_candidates if c in data.columns]
    model_data = data[features + ["next_close", "next_day_direction"]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(model_data) < 40:
        raise ValueError("Not enough complete rows remain for model evaluation.")

    split = int(len(model_data) * (1 - test_fraction))
    split = min(max(split, 1), len(model_data) - 1)
    train, test = model_data.iloc[:split], model_data.iloc[split:]
    X_train, X_test = train[features], test[features]

    # Simple linear regression: today's close -> next day's close.
    simple_regression = LinearRegression().fit(X_train[[close]], train["next_close"])
    simple_pred = simple_regression.predict(X_test[[close]])

    # Multiple linear regression: several OHLCV/derived predictors -> next close.
    regression = LinearRegression().fit(X_train, train["next_close"])
    reg_pred = regression.predict(X_test)

    regression_rows = []
    for name, predictions in [
        ("Simple Linear Regression", simple_pred),
        ("Multiple Linear Regression", reg_pred),
    ]:
        regression_rows.append({
            "Model": name,
            "MAE": float(mean_absolute_error(test["next_close"], predictions)),
            "RMSE": float(np.sqrt(mean_squared_error(test["next_close"], predictions))),
            "R²": float(r2_score(test["next_close"], predictions)) if len(test) > 1 else np.nan,
            "Train Rows": int(len(train)), "Test Rows": int(len(test))
        })
    regression_metrics = pd.DataFrame(regression_rows)
    regression_predictions = pd.DataFrame({
        "trade_date": data.loc[test.index, "trade_date"].values if "trade_date" in data else test.index,
        "Actual Next Close": test["next_close"].values,
        "Simple Regression Prediction": simple_pred,
        "Multiple Regression Prediction": reg_pred,
    })

    # Classification target: next day's direction (up/down).
    y_train = train["next_day_direction"].astype(int)
    y_test = test["next_day_direction"].astype(int)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    classifiers = {
        "Decision Tree (ID3-style)": DecisionTreeClassifier(criterion="entropy", max_depth=5, min_samples_leaf=3, random_state=42),
        "Naive Bayes": GaussianNB(),
    }
    rows = []
    for name, model in classifiers.items():
        if name == "Naive Bayes":
            model.fit(X_train_scaled, y_train)
            pred = model.predict(X_test_scaled)
        else:
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
        rows.append({
            "Model": name,
            "Accuracy": float(accuracy_score(y_test, pred)),
            "Precision": float(precision_score(y_test, pred, zero_division=0)),
            "Recall": float(recall_score(y_test, pred, zero_division=0)),
            "F1 Score": float(f1_score(y_test, pred, zero_division=0)),
        })
    classification_metrics = pd.DataFrame(rows).sort_values("F1 Score", ascending=False)
    return {
        "regression_metrics": regression_metrics,
        "regression_predictions": regression_predictions,
        "classification_metrics": classification_metrics,
        "feature_columns": features,
        "train_rows": int(len(train)), "test_rows": int(len(test)),
    }


def build_stock_profiles(history_by_ticker):
    """Aggregate selected OHLCV histories into one row per ticker for clustering."""
    rows = []
    for ticker, raw in history_by_ticker.items():
        if raw is None or raw.empty:
            continue
        df = prepare_dwm_dataset(raw)
        close = get_close_price_column(df)
        returns = pd.to_numeric(df[close], errors="coerce").pct_change().dropna()
        prices = pd.to_numeric(df[close], errors="coerce").dropna()
        volume = pd.to_numeric(df.get("volume", pd.Series(dtype=float)), errors="coerce").dropna()
        if prices.empty:
            continue
        rows.append({
            "Ticker": ticker,
            "Average Daily Return %": float(returns.mean() * 100) if not returns.empty else 0.0,
            "Return Volatility %": float(returns.std() * 100) if len(returns) > 1 else 0.0,
            "Total Return %": float((prices.iloc[-1] / prices.iloc[0] - 1) * 100) if prices.iloc[0] else 0.0,
            "Average Volume": float(volume.mean()) if not volume.empty else 0.0,
            "Price Range %": float((prices.max() - prices.min()) / prices.iloc[0] * 100) if prices.iloc[0] else 0.0,
        })
    return pd.DataFrame(rows)


def cluster_stock_profiles(profiles, n_clusters=3, method="K-Means"):
    """Cluster ticker profiles with K-Means or agglomerative hierarchical clustering."""
    if profiles is None or profiles.empty:
        raise ValueError("No stock profiles are available for clustering.")
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans, AgglomerativeClustering
    except ImportError as exc:
        raise ImportError("Install scikit-learn to run clustering.") from exc
    features = [c for c in profiles.columns if c != "Ticker"]
    values = profiles[features].replace([np.inf, -np.inf], np.nan)
    values = values.fillna(values.median()).fillna(0)
    if len(profiles) < 2:
        raise ValueError("Select at least two tickers to compare clusters.")
    k = min(max(2, int(n_clusters)), len(profiles))
    scaled = StandardScaler().fit_transform(values)
    if method == "Hierarchical (Agglomerative)":
        labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(scaled)
    else:
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(scaled)
    result = profiles.copy()
    result["Cluster"] = labels.astype(int) + 1
    return result.sort_values(["Cluster", "Ticker"]).reset_index(drop=True)


def build_market_transactions(history_by_ticker):
    """Turn daily price/volume states into transactions for Apriori-style mining."""
    date_baskets = {}
    for ticker, raw in history_by_ticker.items():
        if raw is None or raw.empty:
            continue
        df = prepare_dwm_dataset(raw)
        close = get_close_price_column(df)
        df["daily_return"] = pd.to_numeric(df[close], errors="coerce").pct_change()
        volume_median = df["volume"].median() if "volume" in df else np.nan
        vol_median = df["daily_return"].abs().median()
        for _, row in df.iterrows():
            if pd.isna(row.get("trade_date")):
                continue
            day = pd.Timestamp(row["trade_date"]).date().isoformat()
            items = date_baskets.setdefault(day, set())
            ret = row.get("daily_return", 0)
            if pd.isna(ret):
                continue
            items.add(f"{ticker}:{'UP' if ret > 0 else 'DOWN' if ret < 0 else 'FLAT'}")
            if "volume" in df.columns and pd.notna(row.get("volume")) and pd.notna(volume_median):
                items.add(f"{ticker}:{'HIGH_VOLUME' if row['volume'] >= volume_median else 'LOW_VOLUME'}")
            if pd.notna(vol_median):
                items.add(f"{ticker}:{'HIGH_MOVE' if abs(ret) >= vol_median else 'LOW_MOVE'}")
    return [(day, sorted(items)) for day, items in sorted(date_baskets.items()) if items]


def mine_association_rules(transactions, min_support=0.1, min_confidence=0.5, max_itemset_size=3):
    """Small, dependency-free Apriori implementation for DWM practicals.

    Returns frequent itemsets and rules with support, confidence, and lift.
    Intended for modest interactive selections, not very large transaction sets.
    """
    baskets = [set(items) for _, items in transactions] if transactions and isinstance(transactions[0], tuple) else [set(items) for items in transactions]
    baskets = [b for b in baskets if b]
    if not baskets:
        return pd.DataFrame(), pd.DataFrame()
    n = len(baskets)
    min_count = max(1, int(np.ceil(float(min_support) * n)))
    item_counts = {}
    for basket in baskets:
        for item in basket:
            item_counts[frozenset([item])] = item_counts.get(frozenset([item]), 0) + 1
    frequent = {items: count for items, count in item_counts.items() if count >= min_count}
    all_frequent = dict(frequent)
    k = 2
    while frequent and k <= max_itemset_size:
        prev_sets = list(frequent.keys())
        candidates = set()
        for i in range(len(prev_sets)):
            for j in range(i + 1, len(prev_sets)):
                union = prev_sets[i] | prev_sets[j]
                if len(union) == k and all(frozenset(sub) in frequent for sub in __import__('itertools').combinations(union, k - 1)):
                    candidates.add(union)
        counts = {candidate: sum(candidate.issubset(b) for b in baskets) for candidate in candidates}
        frequent = {items: count for items, count in counts.items() if count >= min_count}
        all_frequent.update(frequent)
        k += 1
    itemset_rows = [{"Itemset": " + ".join(sorted(items)), "Length": len(items), "Support": count / n, "Count": count} for items, count in all_frequent.items()]
    rules = []
    for itemset, joint_count in all_frequent.items():
        if len(itemset) < 2:
            continue
        for size in range(1, len(itemset)):
            for antecedent_tuple in __import__('itertools').combinations(itemset, size):
                antecedent = frozenset(antecedent_tuple)
                consequent = itemset - antecedent
                ant_count = sum(antecedent.issubset(b) for b in baskets)
                cons_count = sum(consequent.issubset(b) for b in baskets)
                if not ant_count or not cons_count:
                    continue
                support = joint_count / n
                confidence = joint_count / ant_count
                lift = confidence / (cons_count / n)
                if confidence >= min_confidence:
                    rules.append({
                        "Antecedent": " + ".join(sorted(antecedent)),
                        "Consequent": " + ".join(sorted(consequent)),
                        "Support": support, "Confidence": confidence, "Lift": lift,
                    })
    itemsets_df = pd.DataFrame(itemset_rows).sort_values(["Length", "Support"], ascending=[True, False]) if itemset_rows else pd.DataFrame()
    rules_df = pd.DataFrame(rules).sort_values(["Lift", "Confidence"], ascending=False) if rules else pd.DataFrame(columns=["Antecedent", "Consequent", "Support", "Confidence", "Lift"])
    return itemsets_df.reset_index(drop=True), rules_df.reset_index(drop=True)


def build_olap_fact_table(history_by_ticker):
    """Combine histories into a tidy fact-like table for OLAP slice/dice/roll-up."""
    frames = []
    for ticker, raw in history_by_ticker.items():
        if raw is None or raw.empty:
            continue
        df = raw.copy()
        if "trade_date" not in df.columns:
            continue
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
        close = get_close_price_column(df)
        df[close] = pd.to_numeric(df[close], errors="coerce")
        df = df.dropna(subset=["trade_date", close]).sort_values("trade_date")
        if df.empty:
            continue
        df["Ticker"] = ticker
        df["Year"] = df["trade_date"].dt.year
        df["Month"] = df["trade_date"].dt.month
        df["Quarter"] = "Q" + df["trade_date"].dt.quarter.astype(str)
        df["Daily Return %"] = df[close].pct_change() * 100
        df["Direction"] = np.where(df["Daily Return %"] > 0, "Up", np.where(df["Daily Return %"] < 0, "Down", "Flat"))
        df["Close Value"] = df[close]
        frames.append(df[["Ticker", "trade_date", "Year", "Quarter", "Month", "Direction", "Close Value", "Daily Return %"]])
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def olap_aggregate(fact_table, level="Monthly", selected_tickers=None, direction="All"):
    """Perform OLAP slice/dice and roll-up at yearly, quarterly, or monthly level."""
    if fact_table is None or fact_table.empty:
        return pd.DataFrame()
    data = fact_table.copy()
    if selected_tickers:
        data = data[data["Ticker"].isin(selected_tickers)]
    if direction != "All":
        data = data[data["Direction"] == direction]
    if data.empty:
        return pd.DataFrame()
    if level == "Yearly":
        group_cols = ["Year", "Ticker"]
    elif level == "Quarterly":
        group_cols = ["Year", "Quarter", "Ticker"]
    else:
        group_cols = ["Year", "Month", "Ticker"]
    result = data.groupby(group_cols, dropna=False).agg(
        Trading_Days=("Close Value", "count"),
        Average_Close=("Close Value", "mean"),
        Min_Close=("Close Value", "min"),
        Max_Close=("Close Value", "max"),
        Average_Daily_Return_Pct=("Daily Return %", "mean"),
        Up_Days=("Direction", lambda s: int((s == "Up").sum())),
        Down_Days=("Direction", lambda s: int((s == "Down").sum())),
    ).reset_index()
    return result.round(4)
