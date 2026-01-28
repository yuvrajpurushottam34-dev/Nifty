import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Nifty Sentiment Auto", page_icon="🤖", layout="wide")

# --- NAVIGATION ---
page = st.sidebar.radio("Go to", ["Live Dashboard", "Logic & Explanation"])

# --- FUNCTION 1: SCRAPE GIFT NIFTY (WITH FALLBACK) ---
@st.cache_data(ttl=300)
def scrape_gift_nifty():
    # Attempt 1: MoneyControl with Browser Headers
    url = "https://www.moneycontrol.com/markets/global-indices/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Look for table rows containing "GIFT Nifty"
            for row in soup.find_all("tr"):
                if "GIFT Nifty" in row.text:
                    cells = row.find_all("td")
                    # Usually the price is in the 2nd cell (index 1)
                    for cell in cells:
                        try:
                            # Clean text (remove commas, spaces)
                            clean_text = cell.text.replace(",", "").strip()
                            price = float(clean_text)
                            if price > 10000: # Valid price check
                                return price
                        except ValueError:
                            continue
    except:
        pass # If scraping fails, just return None silently
    
    return None

# --- FUNCTION 2: FETCH MARKET DATA ---
@st.cache_data(ttl=300)
def get_market_data():
    # Added "GC=F" (Gold) just for reference if needed, mainly using CL=F (Oil)
    tickers = ["INDA", "EWW", "HDB", "IBN", "INFY", "^NSEI", "CL=F", "^TNX", "DX-Y.NYB", "QQQ"]
    try:
        data = yf.download(tickers, period="7d", progress=False)
        
        # Handle MultiIndex if strictly needed
        if 'Close' in data:
            close_data = data['Close']
        else:
            close_data = data
            
        changes = {}
        last_prices = {}
        
        for ticker in tickers:
            try:
                # Get series and drop NaNs to find valid trading days
                series = close_data[ticker].dropna()
                if len(series) >= 2:
                    curr = series.iloc[-1]
                    prev = series.iloc[-2]
                    change = ((curr - prev) / prev) * 100
                    
                    changes[ticker] = round(change, 2)
                    last_prices[ticker] = round(curr, 2)
                else:
                    changes[ticker] = 0.0
                    last_prices[ticker] = 0.0
            except:
                changes[ticker] = 0.0
                last_prices[ticker] = 0.0
                
        return changes, last_prices
    except:
        return {}, {}

# --- PAGE 1: LIVE DASHBOARD ---
if page == "Live Dashboard":
    st.title("🤖 Nifty Sentiment (Auto-Safe Mode)")
    st.markdown("Analyzing Global Cues & GIFT Nifty.")

    with st.spinner("Fetching Data..."):
        # 1. Fetch Market Data first
        changes, prices = get_market_data()
        
        # 2. Try Scraping GIFT Nifty
        scraped_price = scrape_gift_nifty()
        
        # 3. SMART FALLBACK LOGIC
        # Get the actual Nifty 50 Close from Yahoo
        nifty_last_close = prices.get("^NSEI", 24000.0)
        
        if scraped_price:
            # If scraping succeeded, use it
            auto_price = scraped_price
            status_msg = f"✅ Auto-Detected GIFT Nifty: {auto_price}"
            status_color = "green"
        else:
            # If scraping FAILED, use Nifty Close (So Gap = 0)
            auto_price = nifty_last_close
            status_msg = "⚠️ Scraping blocked. Defaulting to Nifty Close (Flat)."
            status_color = "orange"

    # --- SIDEBAR CONTROLS ---
    st.sidebar.header("Settings")
    st.sidebar.markdown(f":{status_color}[{status_msg}]")
    
    # The input box defaults to 'auto_price'. 
    # If scraping failed, it defaults to Nifty Close, so Gap is 0.0 (No Crash).
    manual_gift = st.sidebar.number_input(
        "GIFT Nifty Price:", 
        value=float(auto_price),
        step=10.0
    )

    # --- ANALYSIS ENGINE ---
    if changes:
        # Calculate Gap based on Manual Input (which might be the auto-filled value)
        gap_points = manual_gift - nifty_last_close
        gap_pct = (gap_points / nifty_last_close) * 100

        # Logic Rules
        sentiment = "NEUTRAL"
        color = "gray"
        reason = "Signals are mixed or flat."
        
        # Rule 1: Macro Killers (Oil & Yields)
        if changes.get("CL=F", 0) > 2.0:
            sentiment = "NEGATIVE (Oil Spike)"
            color = "red"
            reason = "Crude Oil is up > 2%. Inflationary pressure."
        elif changes.get("^TNX", 0) > 3.0: 
            sentiment = "CAUTION (Yields Rising)"
            color = "orange"
            reason = "US 10Y Yields are spiking significantly."
            
        # Rule 2: Risk Off
        elif changes.get("EWW", 0) < -1.5:
            sentiment = "BEARISH (Risk Off)"
            color = "red"
            reason = "Mexico ETF (EWW) crashed. Global sentiment is weak."
            
        # Rule 3: Bank Weakness
        elif changes.get("HDB", 0) < -1.5:
            sentiment = "WEAK OPEN (Bank Drag)"
            color = "orange"
            reason = "HDFC Bank ADR is down > 1.5%."
            
        # Rule 4: Strong Buy
        elif changes.get("INDA", 0) > 0.5 and changes.get("CL=F", 0) < 0 and gap_points > 40:
            sentiment = "STRONG BUY"
            color = "green"
            reason = "US bought India (INDA) + Oil cooling + Gap Up."

        # Rule 5: Gap Logic
        elif gap_points > 50:
            sentiment = "POSITIVE GAP UP"
            color = "green"
            reason = f"GIFT Nifty indicates a {int(gap_points)} pt Gap Up."
        elif gap_points < -50:
            sentiment = "NEGATIVE GAP DOWN"
            color = "red"
            reason = f"GIFT Nifty indicates a {int(gap_points)} pt Gap Down."
        elif abs(gap_points) <= 50:
            sentiment = "FLAT / RANGEBOUND"
            color = "gray"
            reason = "Gap is small (< 50 pts). Expect a flat start."

        # --- DISPLAY VERDICT ---
        st.header(f"Verdict: :{color}[{sentiment}]")
        st.write(f"**Reason:** {reason}")
        st.divider()

        # --- METRICS GRID ---
        def safe_metric(label, value, change, invert=False):
            delta_color = "inverse" if invert else "normal"
            st.metric(label, value, f"{change}%", delta_color=delta_color)

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("GIFT Nifty", f"{manual_gift}", f"{round(gap_points, 1)} pts")
        with c2: safe_metric("Crude Oil", f"${prices.get('CL=F',0)}", changes.get('CL=F',0), invert=True)
        with c3: safe_metric("US 10Y Yield", f"{prices.get('^TNX',0)}%", changes.get('^TNX',0), invert=True)

        c4, c5, c6 = st.columns(3)
        with c4: safe_metric("INDA (US ETF)", f"${prices.get('INDA',0)}", changes.get('INDA',0))
        with c5: safe_metric("Mexico (Risk)", f"${prices.get('EWW',0)}", changes.get('EWW',0))
        with c6: safe_metric("HDFC Bank ADR", f"${prices.get('HDB',0)}", changes.get('HDB',0))

# --- PAGE 2: LOGIC ---
elif page == "Logic & Explanation":
    st.title("How the 'Safe Mode' Works")
    st.info("""
    **Why did the 'Crash' error happen before?**
    When scraping failed, the app thought GIFT Nifty was **0**. 
    So it calculated: `0 - 24000 = -24000 Gap` (Huge Crash).
    
    **How we fixed it:**
    If scraping fails now, the app automatically assumes the price is **Equal to Nifty Close**.
    * **Result:** Gap = 0 (Flat).
    * **Action:** You simply update the real price in the sidebar manually.
    """)