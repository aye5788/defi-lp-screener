# fetch_llama.py
# Responsible for talking to external APIs (starting with DeFiLlama)
# and returning raw data as a pandas DataFrame.

import requests
import pandas as pd

LLAMA_YIELDS_URL = "https://yields.llama.fi/pools"  # DeFiLlama yields endpoint

def get_yield_data():
    """
    Fetch pool/yield data from DeFiLlama and return as a pandas DataFrame.

    Columns we care about (not exhaustive):
    - project (DEX/protocol name)
    - chain
    - symbol (token pair, ex: "USDC-WETH")
    - tvlUsd
    - apyBase  (fee APY)
    - apyReward (reward/incentive APY)
    - rewardTokens (what's paying incentives)
    - pool (unique pool id string)
    """
    try:
        resp = requests.get(LLAMA_YIELDS_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pools = data.get("data", [])
        df = pd.DataFrame(pools)
    except Exception as e:
        # Fallback on any network / parsing issue: return empty but valid frame
        print(f"[fetch_llama] Error fetching data: {e}")
        df = pd.DataFrame([], columns=[
            "project",
            "chain",
            "symbol",
            "tvlUsd",
            "apyBase",
            "apyReward",
            "rewardTokens",
            "pool",
        ])

    # Guarantee we return a DataFrame, never None
    return df
