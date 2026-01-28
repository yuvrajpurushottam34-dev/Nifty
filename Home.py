import streamlit as st

st.set_page_config(
    page_title="Nifty App Collection",
    page_icon="👋",
)

st.write("# Welcome to your Nifty Algo App! 👋")

st.markdown(
    """
    This app contains the entire history of our development.
    Select a version from the **sidebar** to run it.

    ### 👈 Select a Version from the Sidebar
    
    * **1_Basic_Version:** The first simple mirror (INDA vs Nifty).
    * **2_Pro_Version:** Added Oil, Yields, and 'Inverse Logic'.
    * **3_Auto_Bot:** Added the Web Scraper to fetch GIFT Nifty automatically.
    * **4_Master_Version:** The final robust version with VIX, RSI, and SMA.
    """
)