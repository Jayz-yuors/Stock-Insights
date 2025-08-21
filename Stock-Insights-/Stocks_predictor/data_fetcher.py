from db_config import create_connection, close_connection
from alpha_vantage.timeseries import TimeSeries
import yfinance as yf
from datetime import datetime
import pandas as pd

ALPHA_VANTAGE_API_KEY = 'H13FNA09HVUDWWKU'

def fetch_alpha_vantage(ticker):
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        data, _ = ts.get_daily(symbol=ticker, outputsize='full')  # full for max data through current date
        return data
    except Exception as e:
        print(f"Alpha Vantage error for {ticker}: {e}")
        return None

def fetch_yfinance(ticker):
    try:
        # Fetch data up to today's date dynamically
        data = yf.download(ticker, period="max", interval="1d", auto_adjust=True)
        if data.empty:
            print(f"YFinance data empty for {ticker}")
            return None
        return data
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None

def insert_prices(data, company_id, source='yfinance'):
    conn = create_connection()
    if conn is None:
        print("Failed to connect to the database:")
        return
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO stock_prices (company_id, trade_date, open_price, high_price, low_price, close_price, volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (company_id, trade_date) DO NOTHING;
    """
    count = 0
    try:
        for idx, row in data.iterrows():
            if source == "yfinance":
                trade_date = idx.date() if isinstance(idx, pd.Timestamp) else idx
                open_p = float(row['Open'])
                high_p = float(row['High'])
                low_p = float(row['Low'])
                close_p = float(row['Close'])
                volume = int(row['Volume']) if not pd.isna(row['Volume']) else 0
            else:
                trade_date = idx.date()
                open_p = float(row['1. open'])
                high_p = float(row['2. high'])
                low_p = float(row['3. low'])
                close_p = float(row['4. close'])
                volume = int(row['5. volume'])
            cursor.execute(insert_query, (company_id, trade_date, open_p, high_p, low_p, close_p, volume))
            count += cursor.rowcount
        conn.commit()
        print(f"{count} rows inserted for company {company_id} using source: {source}")
    except Exception as e:
        conn.rollback()
        print(f"Insert error: {e}")
    finally:
        cursor.close()
        close_connection(conn)

def get_company_list():
    conn = create_connection()
    if conn is None:
        print("Failed to connect to the database.")
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT company_id, ticker_symbol FROM companies;")
        result = cursor.fetchall()
        return result
    except Exception as e:
        print(f"Database query error: {e}")
        return []
    finally:
        if conn:
            cursor.close()
            close_connection(conn)


if __name__ == "__main__":
    companies = get_company_list()
    for company_id, ticker in companies:
        print(f"Fetching and inserting for {ticker}")
        data = fetch_alpha_vantage(ticker)
        if data is not None and not data.empty:
            insert_prices(data, company_id, source='alpha_vantage')
        else:
            print("AlphaVantage failed, trying yfinance.")
            data = fetch_yfinance(ticker)
            if data is not None and not data.empty:
                insert_prices(data, company_id, source='yfinance')
            else:
                print(f"No data found for {ticker}.")

