import streamlit as st
import pandas as pd

from src.fetch_llama import get_yield_data
from src.enrich_metrics import add_basic_columns, add_placeholder_trend_columns
from src.risk_flags import apply_risk_flags

st.set_page_config(
    page_title="DeFi LP Screener",
    layout="wide"
)

st.title("DeFi Liquidity Pool Screener (Prototype)")
st.caption("Not financial advice. High yield almost always means high risk. Be careful.")

# 1. Fetch raw data
st.subheader("Fetching data…")
df_raw = get_yield_data()

if df_raw is None or df_raw.empty:
    st.error("No data returned from DeFiLlama.")
    st.stop()

# 2. Enrich with our derived columns
df_enriched = add_basic_columns(df_raw)
df_enriched = add_placeholder_trend_columns(df_enriched)

# 3. Risk flags (audit status, red flag logic)
df_scored = apply_risk_flags(df_enriched)

# 4. Choose the columns we actually want to show in the leaderboard table
display_cols = [
    "pool_name",            # <symbol> | <project> | <chain>
    "tvlUsd",               # raw from llama
    "fee_apy",              # derived from apyBase
    "reward_apy",           # derived from apyReward
    "total_apy",            # fee_apy + reward_apy
    "il_risk",              # low/med/high
    "audit_status",         # safety-ish label
    "gas_context",          # cheap gas vs high gas
    "net_yield_after_gas",  # heuristic
    "tvl_trend_7d",         # placeholder now
    "red_flag",             # ⚠ if sketch
]

# Rename columns to nicer headers for the UI
nice_names = {
    "pool_name": "Pool",
    "tvlUsd": "TVL ($)",
    "fee_apy": "Fee APY (%)",
    "reward_apy": "Reward APY (%)",
    "total_apy": "Total APY (%)",
    "il_risk": "IL Risk",
    "audit_status": "Audit / Exploit Status",
    "gas_context": "Gas Context",
    "net_yield_after_gas": "Net Yield After Gas (%)",
    "tvl_trend_7d": "TVL Trend (7d)",
    "red_flag": "Red Flag",
}

df_display = df_scored[display_cols].copy()
df_display = df_display.rename(columns=nice_names)

st.subheader("Leaderboard")
st.write(
    "Higher TVL and decent Fee APY usually = healthier. "
    "High Reward APY with red flags usually = farm-and-dump or risk."
)

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")
st.caption("""
Column notes:
- TVL ($): Total value locked. Bigger = more established.
- Fee APY: Organic yield from trading fees.
- Reward APY: Extra incentive/bribe tokens. Can disappear suddenly.
- IL Risk: Impermanent loss danger if token prices move apart.
- Audit / Exploit Status: Has this protocol been audited / rugged.
- Gas Context: Mainnet gas can kill small positions.
- Net Yield After Gas: Rough 'is this worth it for a normal wallet'.
- Red Flag: ⚠ means slow down and inspect before you touch it.
""")

