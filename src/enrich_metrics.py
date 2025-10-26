# enrich_metrics.py
# Turn raw DeFiLlama data into the columns we actually want to display.

import pandas as pd
from . import config
from .fetch_uniswap import get_uniswap_pools


def add_basic_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create core derived columns:
    - fee_apy (from apyBase)
    - reward_apy (from apyReward)
    - total_apy
    - gas_context
    - net_yield_after_gas (heuristic)
    - il_risk (heuristic)
    - pool_name ("<symbol> | <project> | <chain>")
    Also attach Uniswap-specific volume (+ vol_to_tvl) if we can match.
    """
    df = df.copy()

    # base APYs
    df["fee_apy"] = df.get("apyBase", 0).fillna(0)
    df["reward_apy"] = df.get("apyReward", 0).fillna(0)
    df["total_apy"] = df["fee_apy"] + df["reward_apy"]

    # gas_context: cheap vs expensive based on chain
    def classify_gas(chain):
        if chain in config.CHEAP_GAS_CHAINS:
            return "Cheap gas"
        if chain in config.EXPENSIVE_GAS_CHAINS:
            return "High gas"
        return "Unknown"
    df["gas_context"] = df["chain"].apply(classify_gas)

    from .fetch_gas import get_eth_gas_gwei

def est_net_yield(row):
    total = row["total_apy"] or 0
    gas_context = row.get("gas_context", "")
    gas_gwei = get_eth_gas_gwei()

    # Default heuristic if no live data
    if gas_gwei is None:
        if gas_context == "High gas" and total < 8:
            return 0.5
        return total

    # Use live gas
    if gas_context == "High gas":
        # adjust yield penalty based on gas range
        if gas_gwei > 100:
            penalty = 0.9
        elif gas_gwei > 50:
            penalty = 0.6
        elif gas_gwei > 25:
            penalty = 0.3
        else:
            penalty = 0.15
        return max(total - penalty * total, 0.2)

    # cheaper chains - minimal penalty
    return total


    # il_risk heuristic
    def guess_il(symbol: str):
        if not isinstance(symbol, str):
            return "Unknown"

        sym_upper = symbol.upper()

        stable_words = ["USDC", "USDT", "DAI", "USD", "USDE", "FRAX"]
        # stable-stable or stake-derivative pairs = Low
        if ("STETH" in sym_upper and "ETH" in sym_upper):
            return "Low"
        if any(s in sym_upper for s in stable_words) and all(st in sym_upper for st in ["USDC","USDT","DAI","USD","FRAX"]):
            # super stable-ish basket
            return "Low"
        # blue chip vs stable = Medium
        if any(s in sym_upper for s in stable_words) and "ETH" in sym_upper:
            return "Medium"
        # else assume High
        return "High"
    df["il_risk"] = df["symbol"].apply(guess_il)

    # pool_name for display
    def make_pool_name(row):
        sym = row.get("symbol", "<?>")
        proj = row.get("project", "<?>")
        chain = row.get("chain", "<?>")
        return f"{sym} | {proj} | {chain}"
    df["pool_name"] = df.apply(make_pool_name, axis=1)

    # --- NEW: Uniswap metrics merge ---
    # Get top Uniswap pools and merge on symbol if project is uniswap-v3
    try:
        df_uni = get_uniswap_pools(limit=50)
    except Exception:
        df_uni = pd.DataFrame()

    # We'll only merge where project == "uniswap-v3"
    if not df_uni.empty:
        df_uni_subset = df_uni[["symbol", "volume_24h_usd", "tvl_uniswap_usd", "vol_to_tvl", "feeTier"]].copy()

        df = df.merge(
            df_uni_subset,
            on="symbol",
            how="left",
            suffixes=("", "_uniswap")
        )

    # If we got Uniswap data, great. If not, fill safe defaults.
    for col in ["volume_24h_usd", "tvl_uniswap_usd", "vol_to_tvl", "feeTier"]:
        if col not in df.columns:
            df[col] = None

    return df


from .snapshots import compute_tvl_trend_7d, save_today_snapshot
import pandas as pd

def add_trend_columns_and_snapshot(df) -> pd.DataFrame:
    """
    - Ensure df is a DataFrame
    - Save today's snapshot to data/snapshots/YYYY-MM-DD.csv
    - Compute tvl_trend_7d using recent snapshots
    - Always return a DataFrame with a tvl_trend_7d column
    """
    # Guard: if upstream gave us None, make an empty frame
    if df is None or not isinstance(df, pd.DataFrame):
        safe_df = pd.DataFrame()
        safe_df["tvl_trend_7d"] = "—"
        return safe_df

    # Try to save a snapshot (best effort)
    try:
        save_today_snapshot(df)
    except Exception as e:
        print(f"[trend] snapshot save failed: {e}")

    # Try to compute 7d trend (best effort)
    try:
        df_with_trend = compute_tvl_trend_7d(df)
        # compute_tvl_trend_7d returns a copy, so just return that
        return df_with_trend
    except Exception as e:
        print(f"[trend] compute_tvl_trend_7d failed: {e}")
        df = df.copy()
        df["tvl_trend_7d"] = "—"
        return df

