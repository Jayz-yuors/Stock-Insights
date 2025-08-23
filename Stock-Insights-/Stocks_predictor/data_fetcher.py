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
        data = yf.download(ticker, period="max", interval="1d", auto_adjust=True)
        if data.empty:
            print(f"YFinance data empty for {ticker}")
            return None
        return data
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None


def insert_prices(data, ticker_symbol, source='yfinance'):
    db = create_connection()
    count = 0
    for idx, row in data.iterrows():
        doc = {
            "ticker_symbol": ticker_symbol,
            "trade_date": idx.strftime('%Y-%m-%d'),
            "open_price": float(row['Open']) if source == 'yfinance' else float(row['1. open']),
            "high_price": float(row['High']) if source == 'yfinance' else float(row['2. high']),
            "low_price": float(row['Low']) if source == 'yfinance' else float(row['3. low']),
            "close_price": float(row['Close']) if source == 'yfinance' else float(row['4. close']),
            "volume": int(row['Volume']) if source == 'yfinance' and not pd.isna(row['Volume']) else (int(row['5. volume']) if source != 'yfinance' else 0),
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
    companies = db.companies.find({})
    # Return list of ticker_symbols
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
