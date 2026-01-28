import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import numpy as np

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Nifty Master 4.0", page_icon="📈", layout="wide")

# --- NAVIGATION ---
page = st.sidebar.radio("Go to", ["Live Dashboard", "Technical Health 🛠️", "Logic & Explanation"])

# --- FUNCTION 1: SCRAPE GIFT NIFTY (ROBUST) ---
@st.cache_data(ttl=300)
def scrape_gift_nifty():
    url = "https://www.moneycontrol.com/markets/global-indices/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for row in soup.find_all("tr"):
                if "GIFT Nifty" in row.text:
                    for cell in row.find_all("td"):
                        try:
                            price = float(cell.text.replace(",", "").strip())
                            if price > 10000: return price
                        except: continue
    except: pass
    return None

# --- FUNCTION 2: FETCH DATA & CALCULATE TECHNICALS ---
@st.cache_data(ttl=300)
def get_market_data():
    # Added ^INDIAVIX for fear gauge
    tickers = ["INDA", "EWW", "HDB", "IBN", "INFY", "^NSEI", "CL=F", "^TNX", "^INDIAVIX"]
    
    # We need 250 days for 200 SMA
    data = yf.download(tickers, period="1y", progress=False)
    
    if 'Close' in data:
        close_data = data['Close']
    else:
        close_data = data
        
    changes = {}
    last_prices = {}
    technicals = {}

    for ticker in tickers:
        try:
            series = close_data[ticker].dropna()
            if len(series) >= 2:
                curr = series.iloc[-1]
                prev = series.iloc[-2]
                change = ((curr - prev) / prev) * 100
                changes[ticker] = round(change, 2)
                last_prices[ticker] = round(curr, 2)
                
                # --- CALCULATE RSI (14 Days) ---
                delta = series.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                technicals[f"{ticker}_RSI"] = round(rsi.iloc[-1], 2)
                
                # --- CALCULATE SMA (Moving Averages) ---
                technicals[f"{ticker}_SMA50"] = round(series.rolling(window=50).mean().iloc[-1], 2)
                technicals[f"{ticker}_SMA200"] = round(series.rolling(window=200).mean().iloc[-1], 2)

            else:
                changes[ticker] = 0.0
        except:
            changes[ticker] = 0.0

    return changes, last_prices, technicals, close_data

# --- PAGE 1: LIVE DASHBOARD ---
if page == "Live Dashboard":
    st.title("🚀 Nifty Master 4.0")
    
    with st.spinner("Analyzing Market Internals..."):
        changes, prices, technicals, _ = get_market_data()
        scraped_price = scrape_gift_nifty()
        
        # Fallback Logic
        nifty_last = prices.get("^NSEI", 24000.0)
        auto_price = scraped_price if scraped_price else nifty_last
        status_msg = "✅ Auto-Detected" if scraped_price else "⚠️ Scraping Failed (Using Last Close)"

    # Sidebar
    st.sidebar.markdown(f"**Status:** {status_msg}")
    manual_gift = st.sidebar.number_input("GIFT Nifty:", value=float(auto_price))
    
    # Logic
    gap_points = manual_gift - nifty_last
    vix = prices.get("^INDIAVIX", 0)
    
    # --- VERDICT ENGINE 4.0 ---
    sentiment = "NEUTRAL"
    color = "gray"
    reason = "Mixed Signals."
    
    # Rule 1: VIX Panic (New!)
    if vix > 16.0 and changes.get("^INDIAVIX", 0) > 5.0:
        sentiment = "EXTREME CAUTION (Fear High)"
        color = "red"
        reason = f"India VIX spiked to {vix}. Fear is high, market may crash."
    
    # Rule 2: Macro Killers
    elif changes.get("CL=F", 0) > 2.0:
        sentiment = "NEGATIVE (Oil Spike)"
        color = "red"
        reason = "Crude Oil surged > 2%."
    elif changes.get("^TNX", 0) > 3.0: 
        sentiment = "BEARISH (Yields)"
        color = "orange"
        reason = "US Yields spiking."
        
    # Rule 3: Strong Buy
    elif changes.get("INDA", 0) > 0.5 and vix < 13.0 and gap_points > 40:
        sentiment = "STRONG BUY"
        color = "green"
        reason = "Low Fear (VIX < 13) + Strong Global Cues."

    # Rule 4: Gaps
    elif gap_points > 50:
        sentiment = "POSITIVE GAP UP"
        color = "green"
        reason = f"{int(gap_points)} pt Gap Up."
    elif gap_points < -50:
        sentiment = "NEGATIVE GAP DOWN"
        color = "red"
        reason = f"{int(gap_points)} pt Gap Down."

    # Display
    st.header(f"Verdict: :{color}[{sentiment}]")
    st.write(f"**Reason:** {reason}")
    st.divider()
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("GIFT Nifty", f"{manual_gift}", f"{int(gap_points)} pts")
    c2.metric("India VIX (Fear)", f"{vix}", f"{changes.get('^INDIAVIX',0)}%", delta_color="inverse")
    c3.metric("Crude Oil", f"${prices.get('CL=F',0)}", f"{changes.get('CL=F',0)}%", delta_color="inverse")
    
    c4, c5, c6 = st.columns(3)
    c4.metric("US 10Y Yield", f"{prices.get('^TNX',0)}%", f"{changes.get('^TNX',0)}%", delta_color="inverse")
    c5.metric("HDFC Bank ADR", f"${prices.get('HDB',0)}", f"{changes.get('HDB',0)}%")
    c6.metric("Nifty Last Close", f"{nifty_last}", f"{changes.get('^NSEI',0)}%")

# --- PAGE 2: TECHNICAL HEALTH (NEW) ---
elif page == "Technical Health 🛠️":
    st.title("🛠️ Nifty Internal Health")
    st.write("Is the market Overbought or Oversold?")
    
    with st.spinner("Calculating RSI & Moving Averages..."):
        changes, prices, technicals, history = get_market_data()
        
        rsi = technicals.get("^NSEI_RSI", 50)
        sma200 = technicals.get("^NSEI_SMA200", 0)
        curr_price = prices.get("^NSEI", 0)
        
        # RSI Gauge
        st.subheader("1. RSI Meter (Relative Strength)")
        st.progress(int(rsi))
        if rsi > 70:
            st.error(f"RSI is {rsi} (OVERBOUGHT) - High risk of profit booking.")
        elif rsi < 30:
            st.success(f"RSI is {rsi} (OVERSOLD) - Good time to buy.")
        else:
            st.info(f"RSI is {rsi} (Neutral).")
            
        st.divider()
        
        # SMA Trend
        st.subheader("2. Long Term Trend (200 SMA)")
        col1, col2 = st.columns(2)
        col1.metric("Current Nifty", curr_price)
        col2.metric("200 Day Average", sma200)
        
        if curr_price > sma200:
            st.success("✅ Market is in a BULL TREND (Above 200 SMA).")
        else:
            st.error("❌ Market is in a BEAR TREND (Below 200 SMA).")
            
        # Chart
        st.subheader("3. 1-Year Trend Chart")
        if "^NSEI" in history:
            st.line_chart(history["^NSEI"])

# --- PAGE 3: LOGIC ---
elif page == "Logic & Explanation":
    st.title("🧠 The New Indicators")
    st.markdown("""
    **1. India VIX (The Fear Gauge)**
    * **Normal Range:** 10-15.
    * **Danger Zone:** > 16. If VIX shoots up, Nifty usually crashes.
    
    **2. RSI (Relative Strength Index)**
    * Scores momentum from 0 to 100.
    * **> 70:** Market is tired (Overbought). Don't buy aggressively.
    * **< 30:** Market is beaten down (Oversold). Look for bounces.
    
    **3. 200 Day Moving Average (SMA)**
    * The most important line for big investors.
    * If Nifty is **above** this line, buy-on-dip works.
    * If **below**, sell-on-rise works.
    """)