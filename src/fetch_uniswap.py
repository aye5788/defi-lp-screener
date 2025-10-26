# fetch_uniswap.py
# Pulls Uniswap v3 pool data (public subgraph, no API key).
# We'll grab a few high-volume pools and map them back into our main table.

import requests
import pandas as pd

UNISWAP_V3_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"

def _run_query(query: str):
    resp = requests.post(UNISWAP_V3_SUBGRAPH, json={"query": query}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["data"]

def get_uniswap_pools(limit=50):
    """
    Returns a DataFrame of top Uniswap v3 pools (by volumeUSD).
    Columns:
    - id (pool address)
    - token0.symbol
    - token1.symbol
    - volumeUSD (24h-ish window from poolDayData[0])
    - totalValueLockedUSD
    - feeTier
    """
    # We'll grab poolDayData for recent volume. We take most recent day per pool.
    query = f"""
    {{
      pools(first: {limit}, orderBy: volumeUSD, orderDirection: desc) {{
        id
        feeTier
        totalValueLockedUSD
        token0 {{ symbol }}
        token1 {{ symbol }}
        poolDayData(first: 1, orderBy: date, orderDirection: desc) {{
          volumeUSD
        }}
      }}
    }}
    """

    data = _run_query(query)
    pools = data["pools"]

    rows = []
    for p in pools:
        vol_list = p.get("poolDayData", [])
        volume_24h = float(vol_list[0]["volumeUSD"]) if vol_list else 0.0

        rows.append({
            "uniswap_pool_id": p["id"],
            "symbol": f'{p["token0"]["symbol"]}-{p["token1"]["symbol"]}',
            "volume_24h_usd": float(volume_24h),
            "tvl_uniswap_usd": float(p["totalValueLockedUSD"]) if p["totalValueLockedUSD"] else 0.0,
            "feeTier": float(p["feeTier"]) / 1e4,  # 500 -> 0.05%, 3000 -> 0.3%, etc.
        })

    df_uni = pd.DataFrame(rows)

    # Add vol_to_tvl for these pools
    def _safe_div(a, b):
        if b and b != 0:
            return a / b
        return 0.0
    df_uni["vol_to_tvl"] = df_uni.apply(
        lambda r: _safe_div(r["volume_24h_usd"], r["tvl_uniswap_usd"]),
        axis=1
    )

    return df_uni
