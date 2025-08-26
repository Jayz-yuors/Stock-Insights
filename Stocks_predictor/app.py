import streamlit as st
from analysis import (
    fetch_prices, fetch_current_price, fetch_company_info,
    compute_sma, compute_ema, detect_abrupt_changes,
    volatility_and_risk, correlation_analysis,
    compare_companies, plot_correlation,
    best_time_to_invest, plot_prices
)
from data_fetcher import get_company_list, run_fetching
from datetime import datetime

st.set_page_config(page_title="Stocks Predictor Dashboard", layout="wide")

@st.cache_data(ttl=24*60*60)
def update_stock_data():
    run_fetching()

# Optional: call update_stock_data() manually if you want to avoid data fetching on every app launch
# update_stock_data()

# Theme selection
theme = st.sidebar.selectbox("Select Theme", options=["Light", "Dark"])
if theme == "Dark":
    st.markdown("""
    <style>
    .stApp {
        background-color: #181a1b;
        color: #eee;
    }
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp {
        background-color: #f8fbff;
        color: #000;
    }
    </style>""", unsafe_allow_html=True)

st.title("📈 Stocks Insights ")
st.markdown("Explore and analyze Nifty50 stocks with analytics & interactive charts.")

company_tickers = get_company_list()
company_dict = {ticker: ticker for ticker in company_tickers}
company_names = list(company_dict.keys())

st.sidebar.header("Choose One or More Companies")
selected_companies = st.sidebar.multiselect("Select Company Tickers", company_names, default=company_names[:1])
selected_tickers = [company_dict[ticker] for ticker in selected_companies]

st.sidebar.header("Date Range (Optional)")
start_date = st.sidebar.date_input("Start date", value=None)
end_date = st.sidebar.date_input("End date", value=None, max_value=datetime.today())

dynamic_end_date = datetime.today().date()

if start_date and end_date:
    if start_date >= end_date:
        st.sidebar.error("Start date must be *less* than end date.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Price & Trends",
    "🔍 Abrupt Changes",
    "🤖 ML & Volatility",
    "📚 Compare & Correlate",
    "⚙️ Export & Info"
])

with tab1:
    st.subheader("View Full Historical Price Data & Chart")
    for ticker in selected_companies:
        info = fetch_company_info(ticker)
        company_name_display = info.get('company_name') if info else ticker
        st.markdown(f"### {company_name_display} ({ticker})")
        df = fetch_prices(ticker, start_date=start_date if start_date else None, end_date=end_date if end_date else dynamic_end_date)
        if df is not None and not df.empty:
            df = compute_sma(df)
            df = compute_ema(df)
            current = fetch_current_price(ticker)
            st.metric(label="Current Price", value=current['close_price'] if current is not None else "N/A")
            st.line_chart(df.set_index('trade_date')[['close_price', 'SMA', 'EMA']])
            with st.expander("Show Full Historical Data Table (Expandable)"):
                st.dataframe(df, use_container_width=True)
            st.markdown("---")
        else:
            st.warning("No price data for selected company.")

with tab2:
    st.subheader("Abrupt Price Changes Detection")
    threshold = st.slider("Set threshold for abrupt change (%)", 1, 20, value=5) / 100.0
    for ticker in selected_companies:
        info = fetch_company_info(ticker)
        if info is None:
            st.warning(f"No info found for ticker {ticker}")
            continue
        company_name_display = info.get('company_name', ticker)
        st.markdown(f"### {company_name_display} ({ticker})")
        df = fetch_prices(ticker, start_date=start_date if start_date else None, end_date=end_date if end_date else dynamic_end_date)
        if df is not None and not df.empty:
            abrupt = detect_abrupt_changes(df, threshold=threshold)
            st.dataframe(abrupt)
        else:
            st.warning("No data to analyze.")
    st.markdown("---")

with tab3:
    st.subheader("ML & Volatility / Risk Analysis")
    window = st.slider("SMA/Volatility Window (days)", 5, 50, value=20)
    for ticker in selected_companies:
        info = fetch_company_info(ticker)
        if info is None:
            st.warning(f"No info found for ticker {ticker}")
            continue
        company_name_display = info.get('company_name', ticker)
        st.markdown(f"### {company_name_display} ({ticker})")
        df = fetch_prices(ticker, start_date=start_date if start_date else None, end_date=end_date if end_date else dynamic_end_date)
        if df is not None and not df.empty:
            df = compute_sma(df, window=window)
            vr_df = volatility_and_risk(df, window=window)
            st.line_chart(vr_df.set_index('trade_date')[['volatility', 'risk']])
        else:
            st.warning("No price data available for volatility analysis.")
    st.markdown("---")

with tab4:
    st.subheader("Compare Multiple Companies & Correlation Analysis")
    if len(selected_tickers) > 1:
        merged = compare_companies(selected_tickers, start_date if start_date else None, end_date if end_date else dynamic_end_date)
        st.line_chart(merged)
        corr = correlation_analysis(selected_tickers)
        st.write("Correlation Matrix of Selected Companies:")
        st.dataframe(corr)
        plot_correlation(corr)
    else:
        st.info("Select two or more companies to compare/correlate.")

with tab5:
    st.subheader("Export Data & Company Info")
    for ticker in selected_companies:
        info = fetch_company_info(ticker)
        if info is None:
            st.warning(f"No info found for ticker {ticker}")
            continue
        st.markdown(f"### {info.get('company_name', ticker)} ({ticker}) Info")
        st.json(info)
        df = fetch_prices(ticker, start_date if start_date else None, end_date if end_date else dynamic_end_date)
        if df is not None and not df.empty:
            filename = f"{ticker}_price_data.csv"
            st.download_button("Export Data as CSV", data=df.to_csv(index=False), file_name=filename)
        st.markdown("---")

# Developer credit watermark
st.markdown("""
<style>
.watermark-box {
    position: fixed;
    right: 20px;
    bottom: 20px;
    background: linear-gradient(90deg, #a7e9edcc 10%, #eeaeca33 100%);
    border-radius: 24px;
    padding: 10px 25px 10px 17px;
    color: #222;
    font-size: 18px;
    font-weight: 500;
    box-shadow: 2px 4px 24px rgba(103,90,150,0.05);
    z-index: 1100;
    font-family: 'Montserrat', 'Roboto', sans-serif;
    display: flex;
    align-items: center;
    transition: background 0.5s;
    animation: slide-in 1.25s cubic-bezier(.25,.42,.44,1.15);
}
.watermark-box:hover {
    background: linear-gradient(85deg, #eeaeca99 40%, #a7e9edcc 80%);
    color: #3066be;
}
.watermark-emoji {
    font-size: 26px;
    margin-right: 12px;
    animation: bounce 1.5s infinite;
}
@keyframes bounce {
    0%, 100% { transform: translateY(0px);}
    50%      { transform: translateY(-5px);}
}
@keyframes slide-in {
    0% { opacity:0; left:-160px;}
    100% { opacity:1; left:20px;}
}
</style>
<div class="watermark-box">
<span class="watermark-emoji">🚀</span>
Developed By &nbsp;&nbsp : &nbsp;&nbsp <b><a href="https://www.linkedin.com/in/jay-keluskar-b17601358" target="_blank" style="color: inherit; text-decoration: none;">Jay Keluskar</a></b>
</div>
""", unsafe_allow_html=True)

st.sidebar.info("Made with ❤️ using Streamlit, AlphaVantage, and yfinance APIs.")
