import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pandas_datareader.data as web
import wbdata
import os
from io import BytesIO
from datetime import datetime
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from streamlit_calendar import calendar
import requests
from streamlit_calendar import calendar
import matplotlib.pyplot as plt


TE_API_KEY = st.secrets["TRADING_ECON_API"] 

# INSERT YOUR ALPHA VANTAGE API KEY
API_KEY = st.secrets["ALPHA_VANTAGE_API"]


st.set_page_config(page_title="Global Macro Dashboard", layout="wide")
st.sidebar.title("Global Macro Dashboard")
page = st.sidebar.selectbox("Select Page", [
    "Market Monitor", "US Macro", "Eurozone Macro", "China Macro",
    "Market Commentary", "Trade Ideas",
    "Market Sentiment", "Yield Curve", "Recession Risk",
    "Economic Calendar", "Correlation Matrix", "Macro Regime"
])



# --------------------
# Alpha Vantage Functions

@st.cache_data(ttl=1800)
def get_spy_data():
    ts = TimeSeries(key=API_KEY, output_format='pandas')
    data, meta_data = ts.get_daily(symbol='SPY', outputsize='compact')
    data.index = pd.to_datetime(data.index)
    data.sort_index(inplace=True)
    return data

@st.cache_data(ttl=1800)
def get_fx_data(from_symbol, to_symbol):
    fx = ForeignExchange(key=API_KEY, output_format='pandas')
    data, meta_data = fx.get_currency_exchange_daily(from_symbol=from_symbol, to_symbol=to_symbol)
    data.index = pd.to_datetime(data.index)
    data.sort_index(inplace=True)
    return data

# --------------------
# Macro Data (FRED & WB)

@st.cache_data(ttl=3600)
def load_us_cpi():
    cpi = web.DataReader('CPIAUCSL', 'fred', start='2010-01-01')
    cpi_yoy = cpi.pct_change(12) * 100
    cpi_yoy.dropna(inplace=True)
    cpi_yoy.rename(columns={'CPIAUCSL': 'CPI_YoY'}, inplace=True)
    return cpi_yoy

@st.cache_data(ttl=3600)
def load_us_unemp():
    unemp = web.DataReader('UNRATE', 'fred', start='2010-01-01')
    unemp.rename(columns={'UNRATE': 'Unemployment'}, inplace=True)
    return unemp

@st.cache_data(ttl=3600)
def load_us_gdp():
    gdp = web.DataReader('GDPC1', 'fred', start='2010-01-01')
    gdp_yoy = gdp.pct_change(4) * 100
    gdp_yoy.dropna(inplace=True)
    gdp_yoy.rename(columns={'GDPC1': 'GDP_YoY'}, inplace=True)
    return gdp_yoy

@st.cache_data(ttl=3600)
def load_euro_cpi():
    euro_cpi = web.DataReader('IRLTLT01EZM156N', 'fred', start='2010-01-01')
    euro_cpi.rename(columns={'IRLTLT01EZM156N': 'Euro_CPI'}, inplace=True)
    return euro_cpi

@st.cache_data(ttl=3600)
def load_euro_unemp():
    euro_unemp = web.DataReader('LRHUTTTTEZM156S', 'fred', start='2010-01-01')
    euro_unemp.rename(columns={'LRHUTTTTEZM156S': 'Euro_Unemp'}, inplace=True)
    return euro_unemp

@st.cache_data(ttl=3600)
def load_china_gdp():
    indicator = {"NY.GDP.MKTP.KD.ZG": "China_GDP"}
    data = wbdata.get_dataframe(indicator, country="CN")
    data.index = pd.to_datetime(data.index)
    data.sort_index(inplace=True)
    data = data[data.index >= pd.Timestamp("2010-01-01")]
    return data

@st.cache_data(ttl=3600)
def load_us_yields():
    tickers = ['DTB3', 'GS2', 'GS10', 'GS30']
    data = {t: web.DataReader(t, 'fred', start='2023-01-01') for t in tickers}
    df = pd.concat(data.values(), axis=1)
    df.columns = ['3M', '2Y', '10Y', '30Y']
    return df

@st.cache_data(ttl=3600)
def load_market_assets():
    import yfinance as yf
    assets = {
        "SPY": "SPY",
        "EURUSD": "EURUSD=X",
        "USDJPY": "JPY=X",
        "Gold": "GC=F",
        "Crude": "CL=F",
        "VIX": "^VIX"
    }
    df = pd.DataFrame()
    for name, ticker in assets.items():
        df[name] = yf.download(ticker, start="2023-01-01")["Close"]
    return df


# --------------------
# Market Monitor

if page == "Market Monitor":
    st.title("Global Market Monitor")

    # SPY data
    try:
        spy_data = get_spy_data()
        st.write("S&P 500 (SPY):", round(spy_data['4. close'].iloc[-1], 2))
        fig_spy = go.Figure()
        fig_spy.add_trace(go.Scatter(x=spy_data.index, y=spy_data['4. close'], mode='lines', name='SPY'))
        fig_spy.update_layout(title="S&P 500 (SPY)", xaxis_title="Date", yaxis_title="Price")
        st.plotly_chart(fig_spy, key="spy_chart")
    except:
        st.warning("Failed to load SPY data.")

    # EUR/USD
    try:
        eurusd = get_fx_data('EUR', 'USD')
        st.write("EUR/USD:", round(eurusd['4. close'].iloc[-1], 4))
    except:
        st.warning("Failed to load EUR/USD data.")

    # USD/JPY with inversion logic
    try:
        usdjpy_raw = get_fx_data('JPY', 'USD')
        usdjpy_raw['USDJPY'] = 1 / usdjpy_raw['4. close']
        st.write("USD/JPY:", round(usdjpy_raw['USDJPY'].iloc[-1], 2))
        fig_usdjpy = go.Figure()
        fig_usdjpy.add_trace(go.Scatter(x=usdjpy_raw.index, y=usdjpy_raw['USDJPY'], mode='lines', name='USD/JPY'))
        fig_usdjpy.update_layout(title="USD/JPY", xaxis_title="Date", yaxis_title="Exchange Rate")
        st.plotly_chart(fig_usdjpy)
    except:
        st.warning("Failed to load USD/JPY data.")

# --------------------
# US Macro
if page == "US Macro":

    st.title("🇺🇸 US Macro Dashboard")
    st.write("Visualize key US economic indicators from TradingEconomics API.")

    api_key = TE_API_KEY

    indicators = {
        "GDP QoQ": "GDP Growth Rate",
        "GDP YoY": "GDP Annual Growth Rate",
        "Inflation CPI": "Inflation Rate",
        "Inflation Core PCE": "Core Inflation Rate",
        "Unemployment": "Unemployment Rate",
        "PMI Manufacturing": "Manufacturing PMI",
        "PMI Services": "Services PMI",
        "Consumer Sentiment": "Consumer Confidence",
        "Industrial Production": "Industrial Production"
}

    if api_key:
        data_dict = {}

        for label, indicator in indicators.items():
            url = f"https://api.tradingeconomics.com/historical/country/united states/indicator/{indicator}?c={api_key}&f=json"
            response = requests.get(url)

            if response.status_code == 200:
                df = pd.DataFrame(response.json())
                df = df[["date", "value"]]
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
                df = df.sort_index()
                data_dict[label] = df.rename(columns={"value": label})
            else:
                st.warning(f"❌ Failed to load {label}")

        combined_df = pd.concat(data_dict.values(), axis=1)

        st.subheader("📊 Combined Data Table")
        st.dataframe(combined_df.tail(), use_container_width=True)

        st.subheader("📈 Indicator Charts")
        for label in indicators:
            if label in data_dict and not data_dict[label].empty:
                st.line_chart(data_dict[label], use_container_width=True)
    else:
        st.info("Please input your TradingEconomics API key to begin.")

# --------------------
# Eurozone Macro

if page == "Eurozone Macro":
    st.title("Eurozone Macro Dashboard")
    euro_cpi = load_euro_cpi()
    euro_unemp = load_euro_unemp()

    st.subheader("Latest Eurozone Data:")
    st.write(f"Inflation: {round(euro_cpi.iloc[-1, 0], 2)}%")
    st.write(f"Unemployment Rate: {round(euro_unemp.iloc[-1, 0], 2)}%")

    fig_cpi = go.Figure()
    fig_cpi.add_trace(go.Scatter(x=euro_cpi.index, y=euro_cpi.iloc[:, 0], mode='lines'))
    fig_cpi.update_layout(title="Eurozone Inflation (%)", xaxis_title="Date", yaxis_title="Inflation")
    st.plotly_chart(fig_cpi)

# --------------------
# China Macro

if page == "China Macro":
    st.title("China Macro Dashboard")
    china_gdp = load_china_gdp()

    st.subheader("Latest China GDP:")
    st.write(f"GDP YoY Growth: {round(china_gdp.iloc[-1, 0], 2)}%")

    fig_gdp = go.Figure()
    fig_gdp.add_trace(go.Scatter(x=china_gdp.index, y=china_gdp.iloc[:, 0], mode='lines'))
    fig_gdp.update_layout(title="China GDP YoY Growth (%)", xaxis_title="Date", yaxis_title="GDP YoY")
    st.plotly_chart(fig_gdp)

# --------------------
# Market Commentary

if page == "Market Commentary":
    st.title("📘 Market Commentary")

    file_path = "commentary.md"

    # Load saved commentary if exists
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            default_text = f.read()
    else:
        default_text = """
📅 Date: 
🌎 Macro Environment Summary:
- US:
- Eurozone:
- China:
- Other:

📊 Market Drivers:
- Rates:
- Commodities:
- FX:
- Equities:

📌 Positioning / Sentiment:
🧠 Personal Takeaways:
        """

    notes = st.text_area("Write your macro thoughts here:", default_text, height=500)
    if st.button("💾 Save Commentary"):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(notes)
        st.success("Commentary saved!")

    st.markdown("### 🧾 Preview")
    st.markdown(notes)

    # --------------------
# Trade Ideas

if page == "Market Sentiment":
    st.title("🧠 Market Sentiment")
    st.metric("Equity Sentiment", "+0.34 (Bullish)")
    st.metric("FX Sentiment", "-0.20 (Bearish)")
    st.markdown("Sentiment signals coming from placeholder. Integrate FinBERT or Marketaux for live sentiment.")

if page == "Yield Curve":
    st.title("📈 US Yield Curve")
    yields = load_us_yields()
    latest = yields.iloc[-1]
    fig = go.Figure(go.Scatter(x=latest.index, y=latest.values, mode='lines+markers'))
    fig.update_layout(title="Latest US Yield Curve", xaxis_title="Maturity", yaxis_title="Yield (%)")
    st.plotly_chart(fig)

if page == "Recession Risk":
    st.title("⚠️ Recession Risk Indicator")
    yields = load_us_yields()
    unemp = load_us_unemp()
    slope = yields['10Y'] - yields['2Y']
    recent_slope = slope.iloc[-1]
    unemp_rate = unemp.iloc[-1, 0]
    risk = "High" if recent_slope < 0 and unemp_rate > 4 else "Moderate"
    st.metric("Recession Risk", risk)
    st.write(f"2s10s Slope: {recent_slope:.2f}")
    st.write(f"Unemployment Rate: {unemp_rate:.2f}%")

@st.cache_data(ttl=3600)
def load_macro_events():
    API_KEY = st.secrets["TRADING_ECON_API"]
    url = f"https://api.tradingeconomics.com/calendar?country=United States&importance=2,3&c={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"API call failed with status {response.status_code}")
        return []

    data = response.json()
    events = []
    for event in data:
        if 'date' in event and 'event' in event:
            events.append({
                "title": f"🇺🇸 {event['event']}",
                "start": event["date"]
            })
    return events

# 📅 Economic Calendar page
if page == "Economic Calendar":
    st.title("📅 U.S. Economic Calendar")

    try:
        events = load_macro_events()
        if events:
            calendar(events, options={"initialView": "dayGridMonth"})
        else:
            raise ValueError("Empty event list")
    except:
        st.warning("⚠️ Failed to load real-time data. Showing sample events instead.")

        sample_events = [
            {"title": "🇺🇸 CPI Report", "start": "2025-06-27"},
            {"title": "🇺🇸 FOMC Meeting", "start": "2025-07-17"},
            {"title": "🇺🇸 ECB Rate Decision", "start": "2025-07-25"},
            {"title": "🇺🇸 NFP Report", "start": "2025-08-02"},
            {"title": "🇺🇸 ISM Manufacturing PMI", "start": "2025-07-01"},
        ]

        calendar(sample_events, options={"initialView": "dayGridMonth"})



if page == "Correlation Matrix":
    st.title("📊 Asset Correlation Matrix")
    df = load_market_assets()
    corr = df.corr()
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale='RdBu',
        zmin=-1,
        zmax=1
    ))
    st.plotly_chart(fig)

if page == "Macro Regime":
    st.title("🔍 Macro Regime Classifier")
    gdp = load_us_gdp().iloc[-1, 0]
    cpi = load_us_cpi().iloc[-1, 0]
    if gdp > 0 and cpi > 2:
        regime = "Reflation 🚀"
    elif gdp < 0 and cpi > 2:
        regime = "Stagflation ⚠️"
    elif gdp < 0 and cpi < 2:
        regime = "Deflation 🧊"
    elif gdp > 0 and cpi < 2:
        regime = "Goldilocks 🌞"
    else:
        regime = "Unclear ❓"
    st.metric("Current Regime", regime)
    st.write(f"GDP YoY: {gdp:.2f}%, CPI YoY: {cpi:.2f}%")


if page == "Trade Ideas":
    st.title("📑 Trade Ideas Tracker")

    trade_file = "trade_ideas.csv"

    # Load existing trade ideas
    if os.path.exists(trade_file):
        df = pd.read_csv(trade_file)
    else:
        df = pd.DataFrame({
            "Date": [""],
            "Asset": [""],
            "Direction": [""],
            "Entry Price": [""],
            "Stop Loss": [""],
            "Take Profit": [""],
            "Conviction (1–5)": [""],
            "Time Horizon": [""],
            "Macro Thesis": [""],
            "Current Status": [""],
        })

    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    # Save updated trade ideas
    if st.button("💾 Save Trade Ideas"):
        edited_df.to_csv(trade_file, index=False)
        st.success("Trade ideas saved!")

    # Download as CSV
    csv_buffer = BytesIO()
    edited_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="⬇️ Download Trade Ideas CSV",
        data=csv_buffer.getvalue(),
        file_name="trade_ideas.csv",
        mime="text/csv"
    )

    st.markdown("📋 Tip: Use this table to track your trade ideas, review setups, and evaluate performance.")

