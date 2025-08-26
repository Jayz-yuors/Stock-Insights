import matplotlib.pyplot as plt
import pandas as pd
from db_config import create_connection

def fetch_prices(ticker_symbol, start_date='2015-01-01', end_date=None):
    conn = create_connection()
    query = """
        SELECT sp.trade_date, sp.open_price, sp.high_price, sp.low_price,
               sp.close_price, sp.volume
        FROM stock_prices sp
        JOIN companies c ON sp.company_id = c.company_id
        WHERE c.ticker_symbol = %s
    """
    params = [ticker_symbol]
    if start_date and end_date:
        query += " AND sp.trade_date BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    elif start_date:
        query += " AND sp.trade_date >= %s"
        params.append(start_date)
    elif end_date:
        query += " AND sp.trade_date <= %s"
        params.append(end_date)
    query += " ORDER BY sp.trade_date ASC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    if not df.empty:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df if not df.empty else None

def fetch_current_price(ticker_symbol):
    conn = create_connection()
    query = """
        SELECT sp.close_price, sp.trade_date
        FROM stock_prices sp
        JOIN companies c ON sp.company_id = c.company_id
        WHERE c.ticker_symbol = %s
        ORDER BY sp.trade_date DESC
        LIMIT 1
    """
    df = pd.read_sql(query, conn, params=[ticker_symbol])
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None

def fetch_company_info(ticker_symbol):
    conn = create_connection()
    query = """
        SELECT company_name, ticker_symbol
        FROM companies
        WHERE ticker_symbol = %s
    """
    df = pd.read_sql(query, conn, params=[ticker_symbol])
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None

# --- ANALYTICS ---

def compute_sma(df, window=20):
    df['SMA'] = df['close_price'].rolling(window=window).mean()
    return df

def compute_ema(df, window=20):
    df['EMA'] = df['close_price'].ewm(span=window, adjust=False).mean()
    return df

def detect_abrupt_changes(df, threshold=0.05):
    df['pct_change'] = df['close_price'].pct_change()
    abrupt = df[abs(df['pct_change']) > threshold].copy()
    return abrupt[['trade_date', 'close_price', 'pct_change']]

def volatility_and_risk(df, window=20):
    df['volatility'] = df['close_price'].rolling(window=window).std()
    df['risk'] = df['volatility'] / df['close_price']
    return df[['trade_date', 'close_price', 'volatility', 'risk']]

def correlation_analysis(ticker_symbols):
    dfs = []
    company_names = []
    for ticker in ticker_symbols:
        df = fetch_prices(ticker)
        if df is None or df.empty:
            continue
        name = fetch_company_info(ticker)['company_name']
        company_names.append(name)
        df = df.rename(columns={'close_price': name})
        dfs.append(df.set_index('trade_date')[name])
    if not dfs:
        return pd.DataFrame()
    merged = pd.concat(dfs, axis=1, join='inner')
    corr = merged.corr()
    corr.index = company_names
    corr.columns = company_names
    return corr

def compare_companies(ticker_symbols, start_date=None, end_date=None):
    dfs = []
    for ticker in ticker_symbols:
        df = fetch_prices(ticker, start_date, end_date)
        if df is None or df.empty:
            continue
        name = fetch_company_info(ticker)['company_name']
        df = df.rename(columns={'close_price': name})
        dfs.append(df.set_index('trade_date')[name])
    if not dfs:
        return pd.DataFrame()
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
