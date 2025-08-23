
import matplotlib.pyplot as plt
import pandas as pd
from db_config import create_connection, close_connection

def fetch_prices(company_id, start_date=None, end_date=None):
    db = create_connection()
    query = {"ticker_symbol": ticker_symbol}
    if start_date and end_date:
        query["trade_date"] = {"$gte": str(start_date), "$lte": str(end_date)}
    elif start_date:
        query["trade_date"] = {"$gte": str(start_date)}
    elif end_date:
        query["trade_date"] = {"$lte": str(end_date)}
    cursor = db.stock_prices.find(query).sort("trade_date", 1)
    df = pd.DataFrame(list(cursor))
    if not df.empty:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df if not df.empty else None

def fetch_current_price(company_id):
    conn = create_connection()
    query = """
    SELECT trade_date, close_price
    FROM stock_prices
    WHERE company_id = %s
    ORDER BY trade_date DESC
    LIMIT 1
    """
    try:
        df = pd.read_sql(query, conn, params=(company_id,))
        if not df.empty:
            return df.iloc[0]
        else:
            return None
    except Exception as e:
        print(f"Error fetching current price: {e}")
        return None
    finally:
        close_connection(conn)

def fetch_company_info(company_id):
    db = create_connection()
    return db.companies.find_one({"ticker_symbol": ticker_symbol})

# --- ANALYTICS ---

def compute_sma(df, window=20):
    df['SMA'] = df['close_price'].rolling(window=window).mean()
    return df

def compute_ema(df, window=20):
    df['EMA'] = df['close_price'].ewm(span=window, adjust=False).mean()
    return df

def detect_abrupt_changes(df, threshold=0.05):
    df['pct_change'] = df['close_price'].pct_change()
    abrupt = df[abs(df['pct_change']) > threshold]
    return abrupt[['trade_date', 'close_price', 'pct_change']]

def volatility_and_risk(df, window=20):
    df['volatility'] = df['close_price'].rolling(window=window).std()
    df['risk'] = df['volatility'] / df['close_price']
    return df[['trade_date', 'close_price', 'volatility', 'risk']]

def correlation_analysis(company_ids):
    conn = create_connection()
    dfs = []
    names = []
    for cid in company_ids:
        query = """
        SELECT trade_date, close_price FROM stock_prices WHERE company_id = %s"""
        df = pd.read_sql(query, conn, params=(cid,))
        info = fetch_company_info(cid)
        name = info['company_name'] if info is not None else f"company_{cid}"
        names.append(name)
        df = df.rename(columns={'close_price': name})
        dfs.append(df.set_index('trade_date'))
    close_connection(conn)
    merged = pd.concat(dfs, axis=1, join='inner')
    corr = merged.corr()
    corr.index = names
    corr.columns = names
    return corr

def compare_companies(company_ids, start_date=None, end_date=None):
    conn = create_connection()
    dfs = []
    for cid in company_ids:
        query = """
        SELECT trade_date, close_price
        FROM stock_prices
        WHERE company_id = %s
        """
        params = [cid]
        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)
        df = pd.read_sql(query + " ORDER BY trade_date", conn, params=tuple(params))
        info = fetch_company_info(cid)
        name = info['company_name'] if info is not None else f"company_{cid}"
        df = df.rename(columns={'close_price': name})
        dfs.append(df.set_index('trade_date'))
    close_connection(conn)
    merged = pd.concat(dfs, axis=1, join='inner')
    return merged

# --- VISUALS ---

def plot_prices(df, company_name):
    plt.figure(figsize=(12, 5))
    plt.plot(df['trade_date'], df['close_price'], label='Close Price')
    if 'SMA' in df:
        plt.plot(df['trade_date'], df['SMA'], label='SMA')
    if 'EMA' in df:
        plt.plot(df['trade_date'], df['EMA'], label='EMA')
    plt.title(f"{company_name} Stock Price")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_correlation(corr_matrix):
    plt.figure(figsize=(8, 6))
    plt.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
    plt.colorbar(label='Correlation')
    plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=45)
    plt.yticks(range(len(corr_matrix.index)), corr_matrix.index)
    plt.title("Stock Price Correlation Matrix")
    plt.tight_layout()
    plt.show()

# --- DATA EXPORT ---

def export_data(df, filename):
    df.to_csv(filename, index=False)
    print(f"Data exported to {filename}")

# Pseudo ML: Best Time to Invest (existing logic)

def best_time_to_invest(df):
    if 'SMA' not in df:
        df = compute_sma(df)
    return df[df['close_price'] > df['SMA']]['trade_date']
import matplotlib.pyplot as plt
import pandas as pd
from db_config import create_connection, close_connection

def fetch_prices(company_id, start_date=None, end_date=None):
    conn = create_connection()
    if conn is None:
        print("Failed to connect to Database:")
        return None
    query = """
    SELECT trade_date, close_price
    FROM stock_prices
    WHERE company_id = %s
    """
    params = [company_id]
    if start_date:
        query += " AND trade_date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND trade_date <= %s"
        params.append(end_date)
    query += " ORDER BY trade_date"
    try:
        df = pd.read_sql(query, conn, params=tuple(params))
        df['trade_date'] = pd.to_datetime(df['trade_date'])
    except Exception as e:
        print(f"Error fetching prices: {e}")
        df = None
    finally:
        close_connection(conn)
    return df

def fetch_current_price(company_id):
    conn = create_connection()
    query = """
    SELECT trade_date, close_price
    FROM stock_prices
    WHERE company_id = %s
    ORDER BY trade_date DESC
    LIMIT 1
    """
    try:
        df = pd.read_sql(query, conn, params=(company_id,))
        if not df.empty:
            return df.iloc[0]
        else:
            return None
    except Exception as e:
        print(f"Error fetching current price: {e}")
        return None
    finally:
        close_connection(conn)

def fetch_company_info(company_id):
    conn = create_connection()
    query = "SELECT * FROM companies WHERE company_id = %s"
    try:
        df = pd.read_sql(query, conn, params=(company_id,))
        if not df.empty:
            return df.iloc[0]
        else:
            return None
    except Exception as e:
        print(f"Error fetching company info: {e}")
        return None
    finally:
        close_connection(conn)

# --- ANALYTICS ---

def compute_sma(df, window=20):
    df['SMA'] = df['close_price'].rolling(window=window).mean()
    return df

def compute_ema(df, window=20):
    df['EMA'] = df['close_price'].ewm(span=window, adjust=False).mean()
    return df

def detect_abrupt_changes(df, threshold=0.05):
    df['pct_change'] = df['close_price'].pct_change()
    abrupt = df[abs(df['pct_change']) > threshold]
    return abrupt[['trade_date', 'close_price', 'pct_change']]

def volatility_and_risk(df, window=20):
    df['volatility'] = df['close_price'].rolling(window=window).std()
    df['risk'] = df['volatility'] / df['close_price']
    return df[['trade_date', 'close_price', 'volatility', 'risk']]

def correlation_analysis(company_ids):
    conn = create_connection()
    dfs = []
    names = []
    for cid in company_ids:
        query = """
        SELECT trade_date, close_price FROM stock_prices WHERE company_id = %s"""
        df = pd.read_sql(query, conn, params=(cid,))
        df = df.rename(columns={'close_price': f'company_{cid}'})
        dfs.append(df.set_index('trade_date'))
        info = fetch_company_info(cid)
        name = info['company_name'] if info is not None else f"company_{cid}"
        names.append(name)
    close_connection(conn)
    merged = pd.concat(dfs, axis=1, join='inner')
    corr = merged.corr()
    corr.index = names
    corr.columns = names
    return corr

def compare_companies(company_ids, start_date=None, end_date=None):
    conn = create_connection()
    dfs = []
    for cid in company_ids:
        query = """
        SELECT trade_date, close_price
        FROM stock_prices
        WHERE company_id = %s
        """
        params = [cid]
        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)
        df = pd.read_sql(query + " ORDER BY trade_date", conn, params=tuple(params))
        df = df.rename(columns={'close_price': f'company_{cid}'})
        dfs.append(df.set_index('trade_date'))
    close_connection(conn)
    merged = pd.concat(dfs, axis=1, join='inner')
    return merged

# --- VISUALS ---

def plot_prices(df, company_name):
    plt.figure(figsize=(12, 5))
    plt.plot(df['trade_date'], df['close_price'], label='Close Price')
    if 'SMA' in df:
        plt.plot(df['trade_date'], df['SMA'], label='SMA')
    if 'EMA' in df:
        plt.plot(df['trade_date'], df['EMA'], label='EMA')
    plt.title(f"{company_name} Stock Price")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_correlation(corr_matrix):
    plt.figure(figsize=(8, 6))
    plt.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
    plt.colorbar(label='Correlation')
    plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=45)
    plt.yticks(range(len(corr_matrix.index)), corr_matrix.index)
    plt.title("Stock Price Correlation Matrix")
    plt.tight_layout()
    plt.show()

# --- DATA EXPORT ---

def export_data(df, filename):
    df.to_csv(filename, index=False)
    print(f"Data exported to {filename}")

# Pseudo ML: Best Time to Invest (existing logic)
def best_time_to_invest(df):
    if 'SMA' not in df:
        df = compute_sma(df)
    return df[df['close_price'] > df['SMA']]['trade_date']

