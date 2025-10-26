# fetch_gas.py
# Pulls live Ethereum gas price data using Etherscan.
# Now uses Streamlit secrets for secure key storage.

import streamlit as st
import requests

ETHERSCAN_URL = "https://api.etherscan.io/api"

def get_eth_gas_gwei():
    """
    Returns current gas price (Gwei) from Etherscan Gas Oracle API.
    Falls back to None if API is unavailable or key missing.
    """
    try:
        api_key = st.secrets["general"]["ETHERSCAN_API_KEY"]
    except Exception:
        return None

    try:
        response = requests.get(
            ETHERSCAN_URL,
            params={
                "module": "gastracker",
                "action": "gasoracle",
                "apikey": api_key,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        result = data.get("result", {})
        gwei = result.get("ProposeGasPrice")
        if gwei:
            return float(gwei)
        return None
    except Exception:
        return None
