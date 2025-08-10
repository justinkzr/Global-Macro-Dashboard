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
from fredapi import Fred

fred = Fred(api_key=st.secrets["FRED_API_KEY"])



# INSERT YOUR ALPHA VANTAGE API KEY
API_KEY = st.secrets["ALPHA_VANTAGE_API"]


st.set_page_config(page_title="Global Macro Dashboard", layout="wide")
st.sidebar.title("JK Capital")
page = st.sidebar.selectbox("Select Page", [
    "Market Monitor", "US Macro", "Eurozone Macro", "China Macro",
    "Market Commentary", "Trade Ideas",
    "Sentiment & Positioning", "Yield Curve",
    "Economic Calendar", "Macro Regime", "Backtesting"
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
    cpi = fred.get_series("CPIAUCSL")
    cpi = cpi.resample("M").last()
    cpi_yoy = cpi.pct_change(12) * 100
    cpi_yoy = cpi_yoy.dropna().to_frame(name="CPI_YoY")
    return cpi_yoy


@st.cache_data(ttl=3600)
def load_us_unemp():
    unemp = fred.get_series("UNRATE")
    unemp = unemp.to_frame(name="Unemployment")
    return unemp


@st.cache_data(ttl=3600)
def load_us_gdp():
    gdp = fred.get_series("GDPC1")
    gdp = gdp.resample("Q").last()
    gdp_yoy = gdp.pct_change(4) * 100
    gdp_yoy = gdp_yoy.dropna().to_frame(name="GDP_YoY")
    return gdp_yoy


@st.cache_data(ttl=3600)
def load_us_nfp():
    nfp = fred.get_series("PAYEMS")
    nfp = nfp.to_frame(name="Non-Farm Payrolls")
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
    series = {
        "3M": "DTB3",
        "2Y": "GS2",
        "10Y": "GS10",
        "30Y": "GS30"
    }
    df = pd.DataFrame({label: fred.get_series(code) for label, code in series.items()})
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
            df[name] = yf.download(ticker, start="2016-01-01")["Close"]
        except Exception as e:
            st.warning(f"⚠️ Failed to load {name}: {e}")
    return df
    



# --------------------
# Market Monitor

if page == "Market Monitor":
    st.title("🌍 Global Markets Monitor")

    
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

    file_path = "china.md"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            commentary_text = f.read()
    else:
        commentary_text = """
        
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


    st.markdown("### 🧾 Commentary")
    st.markdown(commentary_text)


    # --------------------
# Trade Ideas

if page == "Sentiment & Positioning":

    pass  # TODO: fill in later


# Yield Curve page


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

    yields = load_us_yields()

    spread_2s10s = yields['10Y'] - yields['2Y']
    spread_3m10y = yields['10Y'] - yields['3M']

    st.title("📊 Yield Curve Spreads Over Time")
    
    # 2s10s Spread Chart
    fig_2s10s = go.Figure()
    fig_2s10s.add_trace(go.Scatter(x=spread_2s10s.index, y=spread_2s10s, name="2s10s Spread"))
    fig_2s10s.add_hline(y=0, line_dash="dash", line_color="red")
    fig_2s10s.update_layout(title="2s10s Spread (10Y - 2Y)", xaxis_title="Date", yaxis_title="Spread (%)")
    st.plotly_chart(fig_2s10s, use_container_width=True)
    
    # 3M10Y Spread Chart
    fig_3m10y = go.Figure()
    fig_3m10y.add_trace(go.Scatter(x=spread_3m10y.index, y=spread_3m10y, name="3M10Y Spread"))
    fig_3m10y.add_hline(y=0, line_dash="dash", line_color="red")
    fig_3m10y.update_layout(title="3M10Y Spread (10Y - 3M)", xaxis_title="Date", yaxis_title="Spread (%)")
    st.plotly_chart(fig_3m10y, use_container_width=True)


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
    st.title("📅 Economic Calendar")


    sample_events = [
        {"title": "🇺🇸 ISM Manufacturing PMI", "start": "2025-08-1"},
        {"title": "🇺🇸 NFP", "start": "2025-08-1"},
        {"title": "🇺🇸 CPI", "start": "2025-08-12"},
        {"title": "🇺🇸 PPI", "start": "2025-08-14"},
        {"title": "🇺🇸 Retail Sales", "start": "2025-08-15"},
        {"title": "🇺🇸 Unemployment Rate", "start": "2025-08-1"},
        {"title": "🇺🇸 Unemployment Claims", "start": "2025-08-7"},
        {"title": "🇺🇸 FOMC", "start": "2025-07-31"},
        {"title": "🇺🇸 Core PCE", "start": "2025-08-29"},
        {"title": "🇯🇵 BoJ Policy Rate", "start": "2025-07-31"},
        {"title": "🇬🇧 BoE Policy Rate", "start": "2025-08-7"},
        {"title": "🇦🇺 RBA Cash Rate", "start": "2025-08-12"},
    ]

    calendar(
    sample_events,
    options={
        "initialView": "dayGridMonth",
        "validRange": {
            "start": "2024-01-01"  # or an earlier date if needed
        }
    }
)

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


if page == "Backtesting":
    st.title("🧪 Backtesting Results")

