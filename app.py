import streamlit as st
import pandas as pd

from src.fetch_llama import get_yield_data
from src.enrich_metrics import add_basic_columns, add_trend_columns_and_snapshot
from src.risk_flags import apply_risk_flags
from src.formatting import format_for_display
from src import config

st.set_page_config(
    page_title="DeFi Liquidity Pool Screener",
    layout="wide"
)

st.title("DeFi Liquidity Pool Screener")
st.caption("Not financial advice. Yield != safety. High APY often means high risk or short-term incentives.")

# 1. Fetch raw data
df_raw = get_yield_data()

if df_raw is None or df_raw.empty:
    st.error("No data returned from DeFiLlama.")
    st.stop()

# 2. Derive metrics (total_apy, il_risk, gas_context, etc.)
df_enriched = add_basic_columns(df_raw)
df_enriched = add_trend_columns_and_snapshot(df_enriched)


# 3. Add audit_status + red_flag
df_scored = apply_risk_flags(df_enriched)

# -------------------------
# UI CONTROLS / FILTERS
# -------------------------

st.sidebar.header("Filters")

# Chain filter
all_chains = sorted(df_scored["chain"].dropna().unique().tolist())
default_chains = all_chains  # start with everything selected
chains_selected = st.sidebar.multiselect(
    "Chains to include",
    options=all_chains,
    default=default_chains,
    help="Only show pools on these networks."
)

# Minimum TVL
min_tvl = st.sidebar.number_input(
    "Minimum TVL ($)",
    min_value=0,
    value=config.MIN_TVL_DEFAULT,
    step=50000,
    help="Hide tiny pools below this size. Bigger TVL is usually safer / less ruggy."
)

# IL risk filter
il_filter_choice = st.sidebar.selectbox(
    "Max IL Risk allowed",
    options=["Low only", "Low + Medium", "Show all"],
    index=1,
    help="Impermanent loss (IL) is when token prices move apart and you lose value vs just holding them."
)
def il_allowed(il_value: str) -> bool:
    if il_filter_choice == "Show all":
        return True
    if il_filter_choice == "Low + Medium":
        return il_value in ["Low", "Medium"]
    if il_filter_choice == "Low only":
        return il_value == "Low"
    return True  # fallback

# Hide red-flag pools
hide_red_flag = st.sidebar.checkbox(
    "Hide ⚠ risky pools",
    value=True,
    help="Red flag triggers include tiny TVL on expensive chains, unaudited + high incentive APY, etc."
)

# Sort choice
sort_choice = st.sidebar.selectbox(
    "Sort by",
    options=[
        "Net Yield After Gas (%)",
        "TVL ($)",
        "Fee APY (%)",
        "Total APY (%)",
    ],
    index=0,
    help="What do you care about most right now?"
)

# -------------------------
# APPLY FILTERS
# -------------------------

df_filtered = df_scored.copy()

# filter by chain
df_filtered = df_filtered[df_filtered["chain"].isin(chains_selected)]

# filter by min TVL
df_filtered = df_filtered[df_filtered["tvlUsd"] >= float(min_tvl)]

# filter by IL risk
df_filtered = df_filtered[df_filtered["il_risk"].apply(il_allowed)]

# filter by red flag
if hide_red_flag:
    df_filtered = df_filtered[df_filtered["red_flag"] == ""]

# -------------------------
# RENAME COLUMNS FOR DISPLAY
# -------------------------

display_cols_raw = [
    "pool_name",            # <symbol> | <project> | <chain>
    "tvlUsd",               # TVL
    "volume_24h_usd",       # NEW: only populated for some pools (Uniswap v3 for now)
    "vol_to_tvl",           # NEW: capital efficiency
    "fee_apy",              # from apyBase
    "reward_apy",           # from apyReward
    "total_apy",            # fee_apy + reward_apy
    "il_risk",              # Low / Medium / High
    "audit_status",         # from risk_flags
    "gas_context",          # Cheap gas / High gas
    "net_yield_after_gas",  # heuristic
    "tvl_trend_7d",         # placeholder for now
    "red_flag",             # ⚠ or ""
]


nice_names = {
    "pool_name": "Pool",
    "tvlUsd": "TVL ($)",
    "volume_24h_usd": "Vol 24h ($)",
    "vol_to_tvl": "Vol/TVL (24h)",
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

df_display = df_filtered[display_cols_raw].rename(columns=nice_names)

# -------------------------
# SORT
# -------------------------

# Map sort choice (UI label) back to df_display column
sort_map = {
    "Net Yield After Gas (%)": "Net Yield After Gas (%)",
    "TVL ($)": "TVL ($)",
    "Fee APY (%)": "Fee APY (%)",
    "Total APY (%)": "Total APY (%)",
}

sort_col = sort_map[sort_choice]

# numeric-ish sorting: try to convert column to numeric where possible
def _to_numeric_safe(series: pd.Series):
    # we'll try float; if it fails (like "⚠"), set NaN
    return pd.to_numeric(series, errors="coerce")

df_display = df_display.copy()
df_display["_sort_helper"] = _to_numeric_safe(df_display[sort_col])
df_display = df_display.sort_values("_sort_helper", ascending=False, na_position="last").drop(columns=["_sort_helper"])

# -------------------------
# FORMAT FOR DISPLAY
# -------------------------

df_display_pretty = format_for_display(df_display)

# -------------------------
# RENDER
# -------------------------

st.subheader("Leaderboard")

st.write(
    "Filter by chain, hide tiny TVL, remove high IL pools, then sort by Net Yield After Gas.\n"
    "Green-looking pools with no ⚠ and healthy TVL are usually safer starting points.\n"
)

st.dataframe(
    df_display_pretty,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")
st.markdown("""
**Column guide (why you should care):**

- **TVL ($)**  
  How much money is sitting in the pool. Bigger = more established, less likely to just vanish.

- **Fee APY (%)**  
  Yield from actual trading fees. This is the “real business model” income.

- **Reward APY (%)**  
  Extra incentives the protocol is throwing at LPs. This can vanish fast.

- **Total APY (%)**  
  Fee APY + Reward APY. Headline number, can be misleading if it's all rewards.

- **IL Risk**  
  Impermanent loss danger. High IL means if the tokens move apart in price, you might bleed value vs just holding them.

- **Audit / Exploit Status**  
  Very rough safety read. “Unknown” doesn’t mean scam, but you should slow down.

- **Gas Context**  
  “High gas” (Ethereum mainnet) is expensive to get in/out unless you’re depositing size. “Cheap gas” (Arbitrum, Polygon, etc.) is friendlier for smaller deposits.

- **Net Yield After Gas (%)**  
  Our rough “is this even worth it for a normal wallet” estimate, not just the pretty headline APY.

- **TVL Trend (7d)**  
  Will show ▲ or ▼ once we start logging snapshots. Up means money is flowing in (confidence). Down means people are leaving.

- **Red Flag**  
  ⚠ means slow down: maybe tiny TVL on an expensive chain, maybe yield is 100% bribes, maybe audit is unknown.
""")
