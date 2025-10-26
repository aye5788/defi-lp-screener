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
    resp = requests.get(LLAMA_YIELDS_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # DeFiLlama returns { "status": "...", "data": [ {...}, {...} ] }
    pools = data.get("data", [])

    df = pd.DataFrame(pools)

    # Some cleaning / renaming we'll likely want later:
    # We'll do most enrichment in enrich_metrics.py, not here.
    return df
