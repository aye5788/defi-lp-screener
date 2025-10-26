# enrich_metrics.py
# Turn raw DeFiLlama data into the columns we actually want to display.

import pandas as pd
from . import config

def add_basic_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create core derived columns:
    - total_apy
    - gas_context
    - net_yield_after_gas (placeholder heuristic)
    - il_risk (placeholder)
    - audit_status (placeholder; full logic in risk_flags.py later)
    - pool_name (formatted label)
    """
    # total_apy = fee APY + reward APY
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

    # net_yield_after_gas (first pass heuristic)
    def est_net_yield(row):
        total = row["total_apy"]
        if row["gas_context"] == "High gas" and total < 8:
            # if gas is expensive and APY is meh, just treat it as basically not worth it
            return 0.5
        return total
    df["net_yield_after_gas"] = df.apply(est_net_yield, axis=1)

    # il_risk placeholder:
    # We'll refine this. First pass:
    # - If symbol looks like "TOKEN-STABLE" -> Medium
    # - If it's stable-stable or stakedETH/ETH -> Low
    # - Else -> High
    def guess_il(symbol: str):
        if not isinstance(symbol, str):
            return "Unknown"

        sym_upper = symbol.upper()

        # very rough heuristics:
        stable_words = ["USDC", "USDT", "DAI", "USD", "USDe", "FRAX"]
        if any(s in sym_upper for s in stable_words) and "ETH" in sym_upper:
            return "Medium"
        if all(s in sym_upper for s in ["USDC", "USDT"]) or "DAI" in sym_upper:
            return "Low"
        if "STETH" in sym_upper and "ETH" in sym_upper:
            return "Low"
        return "High"
    df["il_risk"] = df["symbol"].apply(guess_il)

    # pool_name: "<symbol> | <project> | <chain>"
    def make_pool_name(row):
        sym = row.get("symbol", "<?>")
        proj = row.get("project", "<?>")
        chain = row.get("chain", "<?>")
        return f"{sym} | {proj} | {chain}"
    df["pool_name"] = df.apply(make_pool_name, axis=1)

    return df

def add_placeholder_trend_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Later we'll calculate 7d TVL changes using the /data/snapshots/ files.
    For now, we just stub the columns so Streamlit table won't explode.
    """
    df["tvl_trend_7d"] = "—"
    return df
