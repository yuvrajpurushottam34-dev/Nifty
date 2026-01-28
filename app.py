import streamlit as st
import yfinance as yf
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Nifty Sentiment Tracker", page_icon="📈")

# --- TITLE & HEADER ---
st.title("🇮🇳 Nifty Sentiment Mirror")
st.write("Analyze US market cues to predict Nifty's opening.")

# --- SIDEBAR: MANUAL INPUT ---
st.sidebar.header("Step 1: Input Live Data")
gift_nifty_input = st.sidebar.number_input(
    "Enter Current GIFT Nifty Level:", 
    min_value=10000.0, 
    max_value=30000.0, 
    value=24000.0,
    step=10.0
)

# --- FUNCTION TO FETCH DATA ---
def get_market_data():
    tickers = ["INDA", "EWW", "HDB", "IBN", "INFY", "^NSEI"]
    
    # FIX 1: Increased period to "5d" to ensure we handle weekends/holidays safely
    try:
        data = yf.download(tickers, period="5d", progress=False)
        
        # Check if data is empty
        if data.empty:
            st.error("⚠️ Error: No data received from Yahoo Finance. Check your internet.")
            return {}, {}

        # Handle yfinance structure (Access 'Close' price)
        # If multiple tickers, yf returns a MultiIndex. We try to access 'Close' safely.
        if 'Close' in data:
            close_data = data['Close']
        else:
            close_data = data # Fallback if structure is different
            
        # Get the latest available closing prices
        changes = {}
        last_prices = {}

        for ticker in tickers:
            try:
                # Drop empty rows (NaNs) for this specific ticker to find real data
                ticker_series = close_data[ticker].dropna()
                
                if len(ticker_series) >= 2:
                    curr_close = ticker_series.iloc[-1]
                    prev_close = ticker_series.iloc[-2]
                    pct_change = ((curr_close - prev_close) / prev_close) * 100
                    
                    changes[ticker] = round(pct_change, 2)
                    last_prices[ticker] = round(curr_close, 2)
                else:
                    # Not enough data points
                    changes[ticker] = 0.0
                    last_prices[ticker] = 0.0
            except KeyError:
                # Ticker not found in data
                changes[ticker] = 0.0
                last_prices[ticker] = 0.0
                
        return changes, last_prices

    except Exception as e:
        st.error(f"⚠️ specific error: {e}")
        return {}, {}

# --- MAIN LOGIC ---
if st.button("Analyze Sentiment"):
    with st.spinner("Fetching US Market Data..."):
        changes, prices = get_market_data()
        
        if not changes: # Stop if data fetch failed
            st.stop()
        
        # Calculate Nifty Implied Gap
        nifty_prev_close = prices.get("^NSEI", 24000)
        if nifty_prev_close == 0: nifty_prev_close = 24000 
        
        gap_points = gift_nifty_input - nifty_prev_close
        gap_pct = (gap_points / nifty_prev_close) * 100

        # --- RULES ---
        sentiment = "NEUTRAL"
        color = "gray"
        reason = "Data inconclusive."
        
        # Rule 1: The "Mexico" Warning
        if changes.get("EWW", 0) < -1.0:
            sentiment = "BEARISH / CAUTION"
            color = "red"
            reason = f"Mexico (EWW) crashed {changes['EWW']}%. Global Risk-Off sentiment."
        
        # Rule 2: Bank Nifty Drag
        elif changes.get("HDB", 0) < -1.5 or changes.get("IBN", 0) < -1.5:
            sentiment = "WEAK OPEN (Bank Drag)"
            color = "orange"
            reason = "Heavy selling in HDFC/ICICI ADRs in the US."

        # Rule 3: Strong Bullish
        elif changes.get("INDA", 0) > 0.5 and changes.get("EWW", 0) > -0.5 and gap_points > 50:
            sentiment = "BULLISH"
            color = "green"
            reason = "US bought India (INDA Green) & Global sentiment is stable."

        # Rule 4: The Fake Out
        elif gap_points > 40 and changes.get("INDA", 0) < -0.2:
            sentiment = "FAKE OUT RISK"
            color = "orange"
            reason = "GIFT Nifty is up, but US investors SOLD India (INDA Red)."
            
        # Rule 5: Standard Gap
        elif gap_points > 30:
            sentiment = "MILD POSITIVE"
            color = "green" # Changed from lightgreen to green
            reason = "GIFT Nifty indicates a gap up, US cues neutral."
        elif gap_points < -30:
            sentiment = "NEGATIVE"
            color = "red"
            reason = "GIFT Nifty indicates a gap down."
            
        # --- DISPLAY RESULTS ---
        # Fixed color formatting syntax
        st.header(f"Verdict: :{color}[{sentiment}]")
        st.write(f"**Reason:** {reason}")
        
        st.divider()
        
        # --- METRICS DASHBOARD ---
        col1, col2, col3 = st.columns(3)
        col1.metric("GIFT Nifty Gap", f"{round(gap_points, 1)} pts", f"{round(gap_pct, 2)}%")
        col2.metric("INDA (US Sentiment)", f"${prices.get('INDA', 0)}", f"{changes.get('INDA', 0)}%")
        col3.metric("Mexico (Risk Check)", f"${prices.get('EWW', 0)}", f"{changes.get('EWW', 0)}%")
        
        col4, col5, col6 = st.columns(3)
        col4.metric("HDFC Bank ADR", f"${prices.get('HDB', 0)}", f"{changes.get('HDB', 0)}%")
        col5.metric("ICICI Bank ADR", f"${prices.get('IBN', 0)}", f"{changes.get('IBN', 0)}%")
        col6.metric("Infosys ADR", f"${prices.get('INFY', 0)}", f"{changes.get('INFY', 0)}%")

else:
    st.info("Enter the current GIFT Nifty price in the sidebar and click 'Analyze'.")