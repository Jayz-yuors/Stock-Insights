# Stocks Insights

## Installation

To use this project, you'll need to have the following dependencies installed:

- Python 3.7 or higher
- Pandas
- Matplotlib
- Streamlit
- Alpha Vantage API key
- PostgreSQL database connection details

You can install the required Python packages using pip:

```
pip install -r requirements.txt
```

## Usage

The main entry point for the application is the `app.py` file. You can run the Streamlit app using the following command:

```
streamlit run app.py
```

This will launch the Stocks Insights dashboard in your default web browser.

The dashboard allows you to:

- View historical stock prices and charts for selected companies
- Detect abrupt price changes
- Analyze volatility and risk
- Compare and correlate stock prices of multiple companies
- Export stock data as CSV files
- View company information

## API

The project uses the following APIs and data sources:

- Yfinance library for fetching historical stock prices
- Alpha Vantage API as a fallback for fetching stock data
- PostgreSQL database for storing and retrieving stock price data

The `data_fetcher.py` module handles the data fetching and insertion into the database.

## Contributing

If you'd like to contribute to this project, please follow these steps:

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes and commit them
4. Push your branch to your forked repository
5. Submit a pull request to the main repository

## License

This project is licensed under the [MIT License](LICENSE).

## Testing

The project does not currently have any automated tests. However, you can manually test the functionality by running the Streamlit app and interacting with the different features.
