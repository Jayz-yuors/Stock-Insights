# 📈 Stock Insights Dashboard

## Project Overview

The **Stock Insights Dashboard** is a web-based application built with **Streamlit** that provides comprehensive historical analysis for a predefined list of stocks (primarily Nifty50 stocks). The project follows a robust ETL (Extract, Transform, Load) pipeline, fetching data from external financial APIs, storing it in a PostgreSQL database, and performing various technical and statistical analyses to offer actionable insights.

## Features

* **Robust Data Pipeline:** Efficiently fetches and updates historical data using a custom-built pipeline that checks the database for the last update date (`MAX(trade_date)`) to minimize redundant API calls.
* **Database Management:** Stores data persistently in a PostgreSQL database, ensuring data integrity using `ON CONFLICT DO UPDATE` and `ON DELETE CASCADE` foreign key constraints.
* **Technical Analysis:** Calculates and visualizes popular indicators like **Simple Moving Average (SMA)** and **Exponential Moving Average (EMA)**.
* **Risk Analysis:** Computes and charts **Volatility (Rolling Standard Deviation)** and a derived **Risk** metric.
* **Comparative Analysis:** Allows users to select multiple stocks to compare price trends and compute the **Correlation Matrix** for portfolio diversification insights.
* **Interactive UI:** A responsive dashboard built with Streamlit featuring dynamic filters for date range and analysis parameters (e.g., threshold for abrupt changes).
* **Data Export:** Allows users to download the raw historical data for any selected stock as a CSV file.

## Technologies Used

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend/App** | Python, Streamlit | Creating the interactive web dashboard. |
| **Backend/DB** | PostgreSQL, Psycopg2 | Persistent data storage and database connectivity. |
| **Data Processing** | Python, Pandas | Data cleaning, manipulation, and statistical analysis. |
| **Data Source** | `yfinance`, Alpha Vantage | Fetching historical stock price data. |
| **Visualization** | Matplotlib, Streamlit's built-in charts | Generating line graphs, heatmaps, and data tables. |

## Installation and Setup

### Prerequisites

1.  **Python 3.8+**
2.  **PostgreSQL Server:** Ensure a running PostgreSQL instance (with host, port, user, and password ready).

### Steps

1.  **Clone the Repository:**
    ```bash
    # Assuming you have cloned or downloaded the project files
    cd stock-insights-dashboard
    ```

2.  **Create and Activate Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    # Install all required Python packages
    pip install psycopg2-binary streamlit pandas yfinance matplotlib alpha_vantage
    ```

4.  **Configure Database Connection:**
    * Open `db_config.py` and modify the connection details to match your PostgreSQL setup:
        ```python
        # db_config.py
        PG_HOST = "localhost"
        PG_PORT = 5432
        PG_DB   = "DemoDb"
        PG_USER = "your_postgres_user"      # <-- CHANGE THIS
        PG_PASS = "your_strong_password"  # <-- CHANGE THIS
        ```

5.  **Initialize the Database Schema:**
    * Run the `schema.sql` script in your PostgreSQL client (e.g., pgAdmin or psql) to create the `companies` and `stock_prices` tables.
    ```bash
    # Example using psql
    psql -h localhost -d DemoDb -U postgres -f schema.sql
    ```

6.  **Populate Companies List:**
    * Run the insertion script to populate the `companies` reference table.
    ```bash
    python insert_companies.py
    ```

7.  **Fetch Initial Stock Price Data:**
    * Run the data fetcher script once to populate the historical price data. This may take several minutes depending on the number of stocks.
    ```bash
    python data_fetcher.py
    ```
    *(Note: Check `data_fetch_log.txt` for status and any errors.)*

## Running the Dashboard

Start the Streamlit application from your terminal:

```bash
streamlit run app.py
