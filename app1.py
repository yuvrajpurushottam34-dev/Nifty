import streamlit as st
import yfinance as yf
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Nifty Sentiment Pro", page_icon="📈", layout="wide")

# --- NAVIGATION ---
page = st.sidebar.radio("Go to", ["Live Dashboard", "Logic & Explanation"])

# --- FUNCTION TO SAFE FETCH DATA ---
@st.cache_data(ttl=300) # Cache data for 5 mins to prevent constant reloading
def get_market_data():
    # Added "CL=F" (Crude Oil) instead of BZ=F which is sometimes delayed
    tickers = ["INDA", "EWW", "HDB", "IBN", "INFY", "^NSEI", "CL=F", "^TNX", "DX-Y.NYB", "QQQ"]
    
    try:
        # Fetch 7 days to ensure we definitely find valid trading days
        data = yf.download(tickers, period="7d", progress=False)
        
        if 'Close' in data:
            close_data = data['Close']
        else:
            close_data = data
            
        changes = {}
        last_prices = {}
        history = {} # Store history for the second page

        for ticker in tickers:
            try:
                # Get valid data points (drop NaNs)
                series = close_data[ticker].dropna()
                
                # We need at least 2 days of data to calculate change
                if len(series) >= 2:
                    curr = series.iloc[-1]
                    prev = series.iloc[-2]
                    change = ((curr - prev) / prev) * 100
                    
                    changes[ticker] = round(change, 2)
                    last_prices[ticker] = round(curr, 2)
                    history[ticker] = series.tail(5) # Save last 5 days for the "Why" page
                else:
                    # If not enough data, set to 0 to avoid "NaN" error
                    changes[ticker] = 0.0
                    last_prices[ticker] = 0.0
                    history[ticker] = None
            except:
                changes[ticker] = 0.0
                last_prices[ticker] = 0.0
                history[ticker] = None
                
        return changes, last_prices, history

    except Exception as e:
        return {}, {}, {}

# --- PAGE 1: LIVE DASHBOARD ---
if page == "Live Dashboard":
    st.title("🇮🇳 Nifty Sentiment Predictor")
    st.markdown("Real-time cues from Global Markets.")

    # Sidebar Input
    st.sidebar.header("Step 1: Input Data")
    gift_nifty_input = st.sidebar.number_input(
        "Enter Current GIFT Nifty Level:", 
        value=24000.0, step=10.0
    )

    if st.button("Run Analysis 🚀"):
        with st.spinner("Fetching global data..."):
            changes, prices, history = get_market_data()
            
            if not changes:
                st.error("⚠️ Could not fetch data. Please check your internet connection.")
                st.stop()
            
            # Calculations
            nifty_prev_close = prices.get("^NSEI", 24000)
            if nifty_prev_close == 0: nifty_prev_close = 24000
            
            gap_points = gift_nifty_input - nifty_prev_close
            gap_pct = (gap_points / nifty_prev_close) * 100

            # --- LOGIC ENGINE ---
            sentiment = "NEUTRAL"
            color = "gray"
            reason = "Market signals are mixed."
            
            # Rule 1: Macro Danger (Yields & Oil)
            # Use .get() with default 0.0 to prevent errors
            if changes.get("CL=F", 0) > 2.5:
                sentiment = "NEGATIVE (Oil Spike)"
                color = "red"
                reason = "Crude Oil surged > 2.5%. This increases inflation risk for India."
            elif changes.get("^TNX", 0) > 3.0: 
                sentiment = "CAUTION (Yields Rising)"
                color = "orange"
                reason = "US Bond Yields are spiking. FIIs often sell Emerging Markets."
            
            # Rule 2: Global Risk Off
            elif changes.get("EWW", 0) < -1.5:
                sentiment = "BEARISH (Risk Off)"
                color = "red"
                reason = "Mexico (EWW) crashed. Global funds are exiting risky assets."

            # Rule 3: Bank Drag
            elif changes.get("HDB", 0) < -1.5:
                sentiment = "WEAK OPEN (Bank Drag)"
                color = "orange"
                reason = "HDFC Bank ADR is down significantly in the US."

            # Rule 4: Strong Buy
            elif changes.get("INDA", 0) > 0.5 and changes.get("CL=F", 0) < 0 and gap_points > 40:
                sentiment = "STRONG BUY"
                color = "green"
                reason = "US bought India (INDA) + Oil is cooling + GIFT Nifty is Up."

            # Rule 5: Standard Gaps
            elif gap_points > 40:
                sentiment = "POSITIVE GAP UP"
                color = "green"
                reason = f"GIFT Nifty indicates a {round(gap_points)} pt gap up."
            elif gap_points < -40:
                sentiment = "NEGATIVE GAP DOWN"
                color = "red"
                reason = f"GIFT Nifty indicates a {round(gap_points)} pt gap down."

            # --- DISPLAY ---
            st.header(f"Verdict: :{color}[{sentiment}]")
            st.write(f"**Reason:** {reason}")
            st.divider()

            # Dashboard Rows
            # Helper function to ensure we never display "nan%"
            def safe_metric(label, value, change, invert_color=False):
                if change is None: change = 0.0
                delta_color = "inverse" if invert_color else "normal"
                st.metric(label, value, f"{change}%", delta_color=delta_color)

            st.subheader("1. 🌍 Macro Killers (Inverse Logic)")
            st.caption("If these go UP (Red), it is BAD for Nifty.")
            c1, c2, c3 = st.columns(3)
            with c1: safe_metric("Crude Oil", f"${prices.get('CL=F',0)}", changes.get('CL=F',0), invert_color=True)
            with c2: safe_metric("US 10Y Yield", f"{prices.get('^TNX',0)}%", changes.get('^TNX',0), invert_color=True)
            with c3: safe_metric("Dollar Index", f"{prices.get('DX-Y.NYB',0)}", changes.get('DX-Y.NYB',0), invert_color=True)

            st.subheader("2. 🇮🇳 India Sentiment")
            st.caption("If these go UP (Green), it is GOOD for Nifty.")
            c4, c5, c6 = st.columns(3)
            with c4: safe_metric("GIFT Gap", f"{round(gap_points,1)} pts", round(gap_pct,2))
            with c5: safe_metric("INDA (US ETF)", f"${prices.get('INDA',0)}", changes.get('INDA',0))
            with c6: safe_metric("Mexico (Risk)", f"${prices.get('EWW',0)}", changes.get('EWW',0))

            st.subheader("3. 🏢 Key Stocks")
            c7, c8, c9 = st.columns(3)
            with c7: safe_metric("HDFC Bank ADR", f"${prices.get('HDB',0)}", changes.get('HDB',0))
            with c8: safe_metric("ICICI Bank ADR", f"${prices.get('IBN',0)}", changes.get('IBN',0))
            with c9: safe_metric("Infosys ADR", f"${prices.get('INFY',0)}", changes.get('INFY',0))

    else:
        st.info("👈 Enter GIFT Nifty price in the sidebar and click 'Run Analysis'.")

# --- PAGE 2: LOGIC & HISTORY ---
elif page == "Logic & Explanation":
    st.title("🧠 Understanding the Logic")
    
    st.markdown("""
    ### Why do we track these?
    
    **1. Why is Oil (CL=F) Red when it goes UP?**
    * India imports **85%** of its Crude Oil.
    * **High Oil Prices** = Higher Petrol prices = Higher Inflation.
    * Higher Inflation = RBI cannot cut interest rates.
    * **Result:** Stock Market falls.
    
    **2. Why the US 10-Year Yield (^TNX)?**
    * This is the "Safe Interest Rate" of the world.
    * If US Yields go **UP** (e.g., from 4.0% to 4.2%), US investors sell risky assets (like Indian Stocks) and put money in US Bonds for safety.
    * **Result:** FII Selling in Nifty.
    
    **3. Why Mexico (EWW)?**
    * Mexico is India's "sibling" in the Emerging Markets basket.
    * Global algorithms trade them together. If Mexico crashes overnight, it means the "Risk Off" button has been pressed globally.
    """)
    
    st.divider()
    
    st.subheader("📊 Data Validation (Last 5 Days)")
    st.write("Check the recent trend to see if the logic holds true.")
    
    if st.button("Load History"):
        with st.spinner("Loading history..."):
            _, _, history = get_market_data()
            
            if history:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Crude Oil Trend**")
                    if history.get('CL=F') is not None:
                        st.line_chart(history['CL=F'])
                    else:
                        st.warning("No Oil data available.")
                        
                with col2:
                    st.write("**US 10Y Yield Trend**")
                    if history.get('^TNX') is not None:
                        st.line_chart(history['^TNX'])
                    else:
                        st.warning("No Yield data available.")
                        
                st.write("**INDA (India ETF) Trend**")
                if history.get('INDA') is not None:
                    st.line_chart(history['INDA'])
            else:
                st.error("Could not load history.")