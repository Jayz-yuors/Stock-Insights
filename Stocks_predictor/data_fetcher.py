from db_config import create_connection
from alpha_vantage.timeseries import TimeSeries
import yfinance as yf  # YahooFinance
from datetime import datetime
import pandas as pd
import logging

# Setup basic logging to file + console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data_fetch_log.txt"),
        logging.StreamHandler()
    ]
)

ALPHA_VANTAGE_API_KEY = 'H13FNA09HVUDWWKU'


def fetch_alpha_vantage(ticker):
    """Fetch data from Alpha Vantage API."""
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        data, _ = ts.get_daily(symbol=ticker, outputsize='full')
        return data
    except Exception as e:
        logging.warning(f"Alpha Vantage error for {ticker}: {e}")
        return None


def fetch_yfinance(ticker):
    """Fetch data from Yahoo Finance as a fallback."""
    try:
        data = yf.download(ticker, period="max", interval="1d", auto_adjust=True, progress=False)
        if data.empty:
            logging.warning(f"YFinance returned empty data for {ticker}")
            return None
        return data
    except Exception as e:
        logging.error(f"YFinance error for {ticker}: {e}")
        return None


def safe_scalar(val):
    """Safely extract scalar from Series if needed."""
    if isinstance(val, pd.Series):
        return val.iloc[0]
    return val


def get_company_list():
    """Fetch list of all tickers from database."""
    conn = create_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT ticker_symbol FROM companies ORDER BY company_name;")
        companies = cur.fetchall()
    conn.close()
    return [c[0] for c in companies]


def get_company_id(conn, ticker_symbol):
    """Return company_id from ticker symbol."""
    with conn.cursor() as cur:
        cur.execute("SELECT company_id FROM companies WHERE ticker_symbol = %s;", (ticker_symbol,))
        result = cur.fetchone()
    return result[0] if result else None


def get_latest_date(conn, company_id):
    """Return the latest date already stored for this company."""
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(trade_date) FROM stock_prices WHERE company_id = %s;", (company_id,))
        result = cur.fetchone()
    return result[0] if result and result[0] else None


def insert_prices(df, ticker_symbol):
    """Insert or update stock prices efficiently, avoiding duplicates."""
    # Only keep data after 2015
    df = df[df.index >= '2015-01-01']
    if df.empty:
        logging.info(f"No price data from 2015 onwards for {ticker_symbol}")
        return 0

    conn = create_connection()
    company_id = get_company_id(conn, ticker_symbol)
    if not company_id:
        logging.warning(f"Company not found for ticker {ticker_symbol}")
        conn.close()
        return 0

    latest_date = get_latest_date(conn, company_id)

    # Filter only new data (after the last stored date)
    if latest_date:
        df = df[df.index > pd.to_datetime(latest_date)]

    if df.empty:
        conn.close()
        return 0  # Already up-to-date

    # Detect column naming pattern
    price_cols_candidates = [
        ('Open', 'High', 'Low', 'Close', 'Volume'),  # yfinance
        ('1. open', '2. high', '3. low', '4. close', '5. volume')  # AlphaVantage
    ]
    for cols in price_cols_candidates:
        if all(col in df.columns for col in cols):
            open_col, high_col, low_col, close_col, vol_col = cols
            break
    else:
        logging.warning(f"Price columns not found for {ticker_symbol}: {df.columns.tolist()}")
        conn.close()
        return 0

    inserted_count = 0

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
                    (company_id, idx.strftime('%Y-%m-%d'),
                     open_price, high_price, low_price, close_price, volume)
                )
                inserted_count += 1
            except Exception as e:
                logging.error(f"Error inserting row for {ticker_symbol} on {idx}: {e}")

    conn.commit()
    conn.close()

    logging.info(f"Inserted/updated {inserted_count} records for {ticker_symbol}")
    return inserted_count


def run_fetching():
    """Main process: fetch & insert data for all companies."""
    start_time = datetime.now()
    tickers = get_company_list()
    total = len(tickers)
    success_count = 0
    fail_count = 0
    total_new_rows = 0

    print(f"\n=== Fetch started for {total} companies at {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    for idx, ticker in enumerate(tickers, start=1):
        print(f"[{idx}/{total}] {ticker}", end=" ", flush=True)

        data = fetch_alpha_vantage(ticker)
        if data is None or data.empty:
            data = fetch_yfinance(ticker)

        if data is not None and not data.empty:
            inserted = insert_prices(data, ticker)
            if inserted > 0:
                success_count += 1
                total_new_rows += inserted
                print(f"-> {inserted} new rows")
            else:
                print("-> up to date")
        else:
            fail_count += 1
            print("-> no data")

    end_time = datetime.now()
    duration = end_time - start_time

    summary = (f"\n=== Completed: total={total}, success_updates={success_count}, "
               f"failures={fail_count}, new_rows={total_new_rows}, time_taken={duration} ===")
    print(summary)
    logging.info(summary)


if __name__ == "__main__":
    run_fetching()
