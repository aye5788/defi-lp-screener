# fetch_gas.py
# Pulls gas price info so we can estimate cost to LP.
# NOTE: You'll need to provide ETHERSCAN_API_KEY via env or streamlit secrets
# before this will return real data.

import os
import requests

ETHERSCAN_URL = "https://api.etherscan.io/api"

def get_eth_gas_gwei():
    """
    Returns average gas price (gwei) from Etherscan.
    If no API key or call fails, returns None.
    """
    api_key = os.getenv("ETHERSCAN_API_KEY")
    if not api_key:
        # We'll just gracefully degrade
        return None

    try:
        resp = requests.get(
            ETHERSCAN_URL,
            params={
                "module": "gastracker",
                "action": "gasoracle",
                "apikey": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        # 'ProposeGasPrice' is in gwei
        gwei = result.get("ProposeGasPrice")
        if gwei is None:
            return None
        return float(gwei)
    except Exception:
        return None
