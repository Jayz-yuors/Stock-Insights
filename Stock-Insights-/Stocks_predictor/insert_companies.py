
from db_config import create_connection, close_connection

def insert_companies(companies):
    conn = create_connection()
    if conn is None:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor()
    insert_query = """
    INSERT INTO companies (company_name, ticker_symbol)
    VALUES (%s, %s)
    ON CONFLICT (ticker_symbol) DO NOTHING; -- Avoid duplicates
    """

    try:
        count = 0
        for company in companies:
            cursor.execute(insert_query, company)
            count += cursor.rowcount  # Increment inserted rows count
        conn.commit()  # Commit once after all inserts
        print(f"Inserted {count} records successfully.")
    except Exception as e:
        conn.rollback()  # Rollback transaction on error
        print(f"Error inserting companies: {e}")
    finally:
        cursor.close()
        close_connection(conn)

if __name__ == "__main__":
    companies_list = [
        ("Reliance Industries", "RELIANCE.NS"),
        ("HDFC Bank", "HDFCBANK.NS"),
        ("Tata Consultancy Services", "TCS.NS"),
        ("Bharti Airtel", "BHARTIARTL.NS"),
        ("ICICI Bank", "ICICIBANK.NS"),
        ("State Bank of India", "SBIN.NS"),
        ("Infosys", "INFY.NS"),
        ("Hindustan Unilever", "HINDUNILVR.NS"),
        ("Life Insurance Corporation of India", "LICI.NS"),
        ("Bajaj Finance", "BAJFINANCE.NS"),
        ("ITC", "ITC.NS"),
        ("Larsen & Toubro", "LT.NS"),
        ("Maruti Suzuki India", "MARUTI.NS"),
        ("HCL Technologies", "HCLTECH.NS"),
        ("Sun Pharmaceutical", "SUNPHARMA.NS"),
        ("Kotak Mahindra Bank", "KOTAKBANK.NS"),
        ("Mahindra & Mahindra", "M&M.NS"),
        ("UltraTech Cement", "ULTRACEMCO.NS"),
        ("Axis Bank", "AXISBANK.NS"),
        ("NTPC Limited", "NTPC.NS"),
        ("Titan Company", "TITAN.NS"),
        ("Bajaj Finserv", "BAJAJFINSV.NS"),
        ("Hindustan Aeronautics", "HAL.NS"),
        ("Oil & Natural Gas", "ONGC.NS"),
        ("Adani Ports & SEZ", "ADANIPORTS.NS"),
        ("Bharat Electronics", "BEL.NS"),
        ("Wipro", "WIPRO.NS"),
        ("JSW Steel", "JSWSTEEL.NS"),
        ("Tata Motors", "TATAMOTORS.NS"),
        ("Asian Paints", "ASIANPAINT.NS"),
        ("Coal India", "COALINDIA.NS"),
        ("Nestlé India", "NESTLEIND.NS"),
        ("Grasim Industries", "GRASIM.NS"),
        ("Hindalco Industries", "HINDALCO.NS"),
    ]

    insert_companies(companies_list)


from db_config import create_connection ,close_connection
def insert_companies(companies):
    conn = create_connection()
    if conn is None :
        print("Failed to connect to the database.")
        return 
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO companies (company_name, ticker_symbol)
    VALUES (%s, %s)
    ON CONFLICT (ticker_symbol) DO NOTHING;  -- Avoid duplicates"""
    try:
        count = 0
        for company in companies:
            cursor.execute(insert_query, company)
            count += cursor.rowcount  # Increment inserted rows count
        conn.commit()  # Commit once after all inserts
        print(f"Inserted {count} records successfully.")
    except Exception as e:
        conn.rollback()  # Rollback transaction on error
        print(f"Error inserting companies: {e}")
    finally:
        cursor.close()
        close_connection(conn)
if __name__ == "__main__":
    companies_list = [
        ("Reliance Industries", "RELIANCE.NS"),
        ("HDFC Bank", "HDFCBANK.NS"),
        ("Tata Consultancy Services", "TCS.NS"),
        ("Bharti Airtel", "BHARTIARTL.NS"),
        ("ICICI Bank", "ICICIBANK.NS"),
        ("State Bank of India", "SBIN.NS"),
        ("Infosys", "INFY.NS"),
        ("Hindustan Unilever", "HINDUNILVR.NS"),
        ("Life Insurance Corporation of India", "LICI.NS"), 
        ("Bajaj Finance", "BAJFINANCE.NS"),
        ("ITC", "ITC.NS"),
        ("Larsen & Toubro", "LT.NS"),
        ("Maruti Suzuki India", "MARUTI.NS"),
        ("HCL Technologies", "HCLTECH.NS"),
        ("Sun Pharmaceutical", "SUNPHARMA.NS"),
        ("Kotak Mahindra Bank", "KOTAKBANK.NS"),
        ("Mahindra & Mahindra", "M&M.NS"),
        ("UltraTech Cement", "ULTRACEMCO.NS"),
        ("Axis Bank", "AXISBANK.NS"),
        ("NTPC Limited", "NTPC.NS"),
        ("Titan Company", "TITAN.NS"),
        ("Bajaj Finserv", "BAJAJFINSV.NS"),
        ("Hindustan Aeronautics", "HAL.NS"),
        ("Oil & Natural Gas", "ONGC.NS"),
        ("Adani Ports & SEZ", "ADANIPORTS.NS"),
        ("Bharat Electronics", "BEL.NS"),
        ("Wipro", "WIPRO.NS"),
        ("JSW Steel", "JSWSTEEL.NS"),
        ("Tata Motors", "TATAMOTORS.NS"),
        ("Asian Paints", "ASIANPAINT.NS"),
        ("Coal India", "COALINDIA.NS"),
        ("Nestlé India", "NESTLEIND.NS"),
        ("Grasim Industries", "GRASIM.NS"),
        ("Hindalco Industries", "HINDALCO.NS")
    ]
    insert_companies(companies_list) 

