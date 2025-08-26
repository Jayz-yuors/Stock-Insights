from db_config import create_connection
from alpha_vantage.timeseries import TimeSeries
import yfinance as yf
from datetime import datetime
import pandas as pd

ALPHA_VANTAGE_API_KEY = 'H13FNA09HVUDWWKU'

def fetch_alpha_vantage(ticker):
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        data, _ = ts.get_daily(symbol=ticker, outputsize='full')
        return data
    except Exception as e:
        print(f"Alpha Vantage error for {ticker}: {e}")
        return None

def fetch_yfinance(ticker):
    try:
        data = yf.download(ticker, period="max", interval="1d", auto_adjust=True)
        if data.empty:
            print(f"YFinance data empty for {ticker}")
            return None
        return data
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None

def safe_scalar(val):
    if isinstance(val, pd.Series):
        return val.iloc[0]
    return val

def get_company_list():
    conn = create_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT ticker_symbol FROM companies ORDER BY company_name;")
        companies = cur.fetchall()
    conn.close()
    return [c[0] for c in companies]

def get_company_id(conn, ticker_symbol):
    with conn.cursor() as cur:
        cur.execute("SELECT company_id FROM companies WHERE ticker_symbol = %s;", (ticker_symbol,))
        result = cur.fetchone()
    return result[0] if result else None

def insert_prices(df, ticker_symbol):
    # Filter for data from 2010-01-01 onwards
    df = df[df.index >= '2015-01-01']
    if df.empty:
        print(f"No price data from 2010 onwards for {ticker_symbol}")
        return
    
    conn = create_connection()
    company_id = get_company_id(conn, ticker_symbol)
    if not company_id:
        print(f"Company not found for ticker {ticker_symbol}")
        conn.close()
        return

    # Identify which API column format is present
    price_cols_candidates = [
        ('Open', 'High', 'Low', 'Close', 'Volume'),          # yfinance
        ('1. open', '2. high', '3. low', '4. close', '5. volume')  # AlphaVantage
    ]
    for cols in price_cols_candidates:
        if all(col in df.columns for col in cols):
            open_col, high_col, low_col, close_col, vol_col = cols
            break
    else:
        print(f"Price columns not found for {ticker_symbol}, columns present: {df.columns.tolist()}")
        conn.close()
        return

    with conn.cursor() as cur:
        for idx, row in df.iterrows():
            try:
                open_price = float(safe_scalar(row.get(open_col, 0)))
                high_price = float(safe_scalar(row.get(high_col, 0)))
                low_price = float(safe_scalar(row.get(low_col, 0)))
                close_price = float(safe_scalar(row.get(close_col, 0)))
                volume_val = safe_scalar(row.get(vol_col, 0))
                volume = int(volume_val) if pd.notna(volume_val) else 0

                cur.execute(
                    """
                    INSERT INTO stock_prices (company_id, trade_date, open_price, high_price, low_price, close_price, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, trade_date) DO UPDATE SET
                        open_price=EXCLUDED.open_price,
                        high_price=EXCLUDED.high_price,
                        low_price=EXCLUDED.low_price,
                        close_price=EXCLUDED.close_price,
                        volume=EXCLUDED.volume;
                    """,
                    (company_id, idx.strftime('%Y-%m-%d'), open_price, high_price, low_price, close_price, volume)
                )
            except Exception as e:
                print(f"Error inserting row for {ticker_symbol} on {idx}: {e}")
    conn.commit()
    conn.close()
    print(f"Inserted/updated stock prices for {ticker_symbol}")

def run_fetching():
    print(f"Fetching data started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tickers = get_company_list()
    for ticker in tickers:
        print(f"Fetching and inserting for {ticker}")
        data = fetch_alpha_vantage(ticker)
        if data is not None and not data.empty:
            insert_prices(data, ticker)
        else:
            print("Alpha Vantage failed, trying yfinance.")
            data = fetch_yfinance(ticker)
            if data is not None and not data.empty:
                insert_prices(data, ticker)
            else:
                print(f"No data found for {ticker}.")
    print(f"Fetching data completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_ticker = "RELIANCE.NS"
    print(f"Testing fetch for {test_ticker}")
    data = fetch_alpha_vantage(test_ticker)
    if data is not None and not data.empty:
        print("Alpha Vantage data fetched. Insert now...")
        insert_prices(data, test_ticker)
    else:
        print("Alpha Vantage failed, trying yfinance.")
        data = fetch_yfinance(test_ticker)
        if data is not None and not data.empty:
            insert_prices(data, test_ticker)
        else:
            print(f"No data found for {test_ticker}.")
