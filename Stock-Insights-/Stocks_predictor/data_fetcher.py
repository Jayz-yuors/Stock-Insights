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

# Helper function to extract scalar from Series or just return the value
def safe_scalar(val):
    if isinstance(val, pd.Series):
        return val.iloc[0]
    return val

def insert_prices(data, ticker_symbol, source='yfinance'):
    db = create_connection()
    count = 0
    for idx, row in data.iterrows():
        if source == 'yfinance':
            open_price = float(safe_scalar(row.get('Open', 0)))
            high_price = float(safe_scalar(row.get('High', 0)))
            low_price = float(safe_scalar(row.get('Low', 0)))
            close_price = float(safe_scalar(row.get('Close', 0)))
            volume_val = safe_scalar(row.get('Volume', 0))
            volume = int(volume_val) if pd.notna(volume_val) else 0
        else:
            open_price = float(safe_scalar(row.get('1. open', 0)))
            high_price = float(safe_scalar(row.get('2. high', 0)))
            low_price = float(safe_scalar(row.get('3. low', 0)))
            close_price = float(safe_scalar(row.get('4. close', 0)))
            volume_val = safe_scalar(row.get('5. volume', 0))
            volume = int(volume_val) if pd.notna(volume_val) else 0

        doc = {
            "ticker_symbol": ticker_symbol,
            "trade_date": idx.strftime('%Y-%m-%d'),
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "close_price": close_price,
            "volume": volume,
            "source": source
        }
        # Upsert to avoid duplicates
        db.stock_prices.update_one(
            {"ticker_symbol": ticker_symbol, "trade_date": doc["trade_date"]},
            {"$set": doc},
            upsert=True
        )
        count += 1
    print(f"{count} rows inserted/updated for company {ticker_symbol} using source: {source}")

def get_company_list():
    db = create_connection()
    companies = list(db.companies.find({}))
    print("Companies found:", companies)   # Debug print
    return [c["ticker_symbol"] for c in companies]

def run_fetching():
    print(f"Fetching data started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    companies = get_company_list()
    for ticker in companies:
        print(f"Fetching and inserting for {ticker}")
        data = fetch_alpha_vantage(ticker)
        if data is not None and not data.empty:
            insert_prices(data, ticker, source='alpha_vantage')
        else:
            print("Alpha Vantage failed, trying yfinance.")
            data = fetch_yfinance(ticker)
            if data is not None and not data.empty:
                insert_prices(data, ticker, source='yfinance')
            else:
                print(f"No data found for {ticker}.")
    print(f"Fetching data completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
