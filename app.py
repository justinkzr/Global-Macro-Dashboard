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


# INSERT YOUR ALPHA VANTAGE API KEY
API_KEY = st.secrets["ALPHA_VANTAGE_API"]


st.set_page_config(page_title="Global Macro Dashboard", layout="wide")
st.sidebar.title("JK Capital")
page = st.sidebar.selectbox("Select Page", [
    "Market Monitor", "US Macro", "Eurozone Macro", "China Macro",
    "Market Commentary", "Trade Ideas",
    "Sentiment & Positioning", "Yield Curve", "Recession Risk",
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
def load_us_nfp():
    nfp = web.DataReader('PAYEMS', 'fred', start='2010-01-01')  # Total Nonfarm Payrolls
    nfp.rename(columns={'PAYEMS': 'Non-Farm Payrolls'}, inplace=True)
    return nfp

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
    tickers = ['DTB3', 'GS2', 'GS5', 'GS10', 'GS30']
    data = {t: web.DataReader(t, 'fred', start='2023-01-01') for t in tickers}
    df = pd.concat(data.values(), axis=1)
    df.columns = ['3M', '2Y', '5Y', '10Y', '30Y']
    return df


@st.cache_data(ttl=3600)
def load_market_assets():
    import yfinance as yf
    tickers = {
        "US500": "^GSPC",             # S&P 500
        "US100": "^NDX",              # Nasdaq 100
        "Dow Jones": "^DJI",          # Dow Jones
        "Russell 2000": "^RUT",       # Russell 2000
        "FTSE 100": "^FTSE",          # FTSE 100
        "Hang Seng": "^HSI",          # Hang Seng Index
        "Gold": "GC=F",               # Gold Futures
        "US 10Y Yield": "^TNX",       # 10-Year Yield
        "VIX": "^VIX",                # Volatility Index
        "Crude Oil": "CL=F"           # Crude Oil Futures
    }

    df = pd.DataFrame()
    for name, ticker in tickers.items():
        try:
            df[name] = yf.download(ticker, start="2023-01-01")["Close"]
        except Exception as e:
            st.warning(f"⚠️ Failed to load {name}: {e}")
    return df






# --------------------
# Market Monitor

if page == "Market Monitor":
    st.title("🌍 Global Market Monitor")

    
    df = load_market_assets()
    if df.empty:
        st.error("Market data could not be loaded")
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    tickers = df.columns.tolist()
    num_cols = 3

    for i in range(0, len(tickers), num_cols):
        cols = st.columns(num_cols)
        for j, col in enumerate(cols):
            if i + j >= len(tickers):
                break

            ticker = tickers[i + j]
            price = latest[ticker]
            delta = price - prev[ticker]
            pct = (delta / prev[ticker]) * 100

            with col:
                st.metric(
                    label=ticker,
                    value=f"{price:,.2f}",
                    delta=f"{delta:+.2f} ({pct:+.2f}%)"
                )
                st.line_chart(df[ticker], use_container_width=True)




# --------------------
# US Macro
if page == "US Macro":
    st.title("🇺🇸 US Macro Dashboard")

    st.subheader("Key Economic Indicators (FRED)")

    gdp = load_us_gdp()
    cpi = load_us_cpi()
    unemp = load_us_unemp()
    nfp = load_us_nfp()


    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Real GDP YoY", f"{gdp.iloc[-1, 0]:.2f}%")
    col2.metric("CPI YoY", f"{cpi.iloc[-1, 0]:.2f}%")
    col3.metric("Unemployment", f"{unemp.iloc[-1, 0]:.2f}%")
    col4.metric("NFP (Thousands)", f"{nfp.iloc[-1, 0]:,.0f}")

    st.line_chart(gdp.rename(columns={gdp.columns[0]: "Real GDP YoY"}))
    st.line_chart(cpi.rename(columns={cpi.columns[0]: "CPI YoY"}))
    st.line_chart(unemp.rename(columns={unemp.columns[0]: "Unemployment Rate"}))

    st.subheader("📈 Non-Farm Payrolls (NFP)")
    st.line_chart(nfp)

    st.subheader("📋 PMI (Manual Entry)")
    st.info("S&P Global PMI data is not free via API. You can manually update it below.")

    st.write("**Latest PMI (Manufacturing)**: 51.3")
    st.write("**Latest PMI (Services)**: 52.8")
    st.caption("Source: S&P Global, manually updated.")


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

# --------------------
# Market Commentary

if page == "Market Commentary":
    st.title("📘 Market Commentary")

    file_path = "commentary.md"

    # Load saved commentary if exists
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            commentary_text = f.read()
    else:
        commentary_text = """
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

    st.markdown("### 🧾 Commentary")
    st.markdown(commentary_text)


    # --------------------
# Trade Ideas

if page == "Sentiment & Positioning":
    st.title("🧠 Sentiment & Positioning")
    st.metric("Equity Sentiment", "+0.34 (Bullish)")
    st.metric("FX Sentiment", "-0.20 (Bearish)")
    st.markdown("Sentiment signals coming from placeholder. Integrate FinBERT or Marketaux for live sentiment.")

if page == "Yield Curve":
    st.title("📈 US Yield Curve")

    yields = load_us_yields()
    latest = yields.dropna().iloc[-1]

    # Calculate spreads
    spread_2s10s = latest["10Y"] - latest["2Y"]
    spread_3m10y = latest["10Y"] - latest["3M"]

    # Show warnings
    if spread_2s10s < 0:
        st.warning(f"2s10s spread inverted: {spread_2s10s:.2f}%")
    else:
        st.success(f"2s10s spread: {spread_2s10s:.2f}%")

    if spread_3m10y < 0:
        st.warning(f"3M10Y spread inverted: {spread_3m10y:.2f}%")
    else:
        st.success(f"3M10Y spread: {spread_3m10y:.2f}%")

    # Display yield curve
    fig = go.Figure(go.Scatter(
        x=latest.index,
        y=latest.values,
        mode='lines+markers',
        name='Yield Curve'
    ))
    fig.update_layout(title="Latest US Yield Curve", xaxis_title="Maturity", yaxis_title="Yield (%)")
    st.plotly_chart(fig)

    # --- Time-Series Plots for Spreads ---

    st.subheader("📊 Yield Curve Spreads Over Time")

    spread_2s10s_series = yields["10Y"] - yields["2Y"]
    spread_3m10y_series = yields["10Y"] - yields["3M"]

    fig_2s10s = go.Figure()
    fig_2s10s.add_trace(go.Scatter(x=spread_2s10s_series.index, y=spread_2s10s_series, mode='lines', name='2s10s Spread'))
    fig_2s10s.add_hline(y=0, line=dict(color='red', dash='dash'))
    fig_2s10s.update_layout(title="2s10s Spread (10Y - 2Y)", xaxis_title="Date", yaxis_title="Spread (%)")

    fig_3m10y = go.Figure()
    fig_3m10y.add_trace(go.Scatter(x=spread_3m10y_series.index, y=spread_3m10y_series, mode='lines', name='3M10Y Spread'))
    fig_3m10y.add_hline(y=0, line=dict(color='red', dash='dash'))
    fig_3m10y.update_layout(title="3M10Y Spread (10Y - 3M)", xaxis_title="Date", yaxis_title="Spread (%)")

    st.plotly_chart(fig_2s10s, use_container_width=True)
    st.plotly_chart(fig_3m10y, use_container_width=True)




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

