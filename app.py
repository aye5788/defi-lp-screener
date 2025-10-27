import streamlit as st
import pandas as pd

from src.fetch_llama import get_yield_data
from src.enrich_metrics import add_basic_columns, add_trend_columns_and_snapshot
from src.risk_flags import apply_risk_flags
from src.formatting import format_for_display
from src import config
from src.fetch_gas import get_eth_gas_gwei


st.set_page_config(
    page_title="DeFi Liquidity Pool Screener",
    layout="wide"
)

st.title("DeFi Liquidity Pool Screener")
st.caption("Not financial advice. Yield != safety. High APY often means high risk or short-term incentives.")

# Optional: show live gas so you understand 'Net Yield After Gas'
gas_now = get_eth_gas_gwei()
if gas_now is not None:
    st.write(f"🧮 Current Ethereum gas: {gas_now:.1f} gwei")
else:
    st.write("🧮 Current Ethereum gas: (unavailable)")

# 1. Fetch raw data
df_raw = get_yield_data()

if df_raw is None or df_raw.empty:
    st.warning("⚠️ No data loaded from DeFiLlama (API may be rate-limited or temporarily unavailable). Showing empty table.")
else:
    st.success(f"✅ Loaded {len(df_raw)} pools from DeFiLlama.")

# 2. Derive metrics (total_apy, il_risk, gas_context, etc.)
df_enriched = add_basic_columns(df_raw)
df_enriched = add_trend_columns_and_snapshot(df_enriched)

# 3. Add audit_status + red_flag
df_scored = apply_risk_flags(df_enriched)

# 4. Safety: ensure expected columns exist even if something upstream was missing
expected_cols = [
    "chain",
    "project",
    "symbol",
    "tvlUsd",
    "fee_apy",
    "reward_apy",
    "total_apy",
    "il_risk",
    "audit_status",
    "gas_context",
    "net_yield_after_gas",
    "tvl_trend_7d",
    "red_flag",
    "pool_name",
    "volume_24h_usd",
    "vol_to_tvl",
]
for col in expected_cols:
    if col not in df_scored.columns:
        df_scored[col] = None

# -------------------------
# UI CONTROLS / FILTERS
# -------------------------

st.sidebar.header("Filters")

# Chain filter (robust even if we have no data)
if "chain" in df_scored.columns and not df_scored["chain"].dropna().empty:
    all_chains = sorted(df_scored["chain"].dropna().unique().tolist())
else:
    all_chains = []

chains_selected = st.sidebar.multiselect(
    "Chains to include",
    options=all_chains,
    default=all_chains,
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
    help="Impermanent loss = if tokens move apart in price, you might bleed vs just holding them."
)
def il_allowed(il_value: str) -> bool:
    if il_filter_choice == "Show all":
        return True
    if il_filter_choice == "Low + Medium":
        return il_value in ["Low", "Medium"]
    if il_filter_choice == "Low only":
        return il_value == "Low"
    return True

# Hide risky pools
hide_red_flag = st.sidebar.checkbox(
    "Hide ⚠ risky pools",
    value=True,
    help="⚠ = tiny TVL on an expensive chain, unaudited + huge reward APY, recent exploit, etc."
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
    help="What matters most to you right now?"
)

# -------------------------
# APPLY FILTERS
# -------------------------

df_filtered = df_scored.copy()

# filter by chain
if "chain" in df_filtered.columns and chains_selected:
    df_filtered = df_filtered[df_filtered["chain"].isin(chains_selected)]

# filter by min TVL
if "tvlUsd" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["tvlUsd"].fillna(0) >= float(min_tvl)]

# filter by IL risk
if "il_risk" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["il_risk"].apply(il_allowed)]

# filter by red flag
if "red_flag" in df_filtered.columns and hide_red_flag:
    df_filtered = df_filtered[df_filtered["red_flag"].fillna("") == ""]

# -------------------------
# RENAME COLUMNS FOR DISPLAY
# -------------------------

display_cols_raw = [
    "pool_name",            # <symbol> | <project> | <chain>
    "tvlUsd",               # TVL
    "volume_24h_usd",       # from Uniswap subgraph for some pools
    "vol_to_tvl",           # volume / TVL efficiency
    "fee_apy",              # from apyBase
    "reward_apy",           # from apyReward
    "total_apy",            # fee_apy + reward_apy
    "il_risk",              # Low / Medium / High
    "audit_status",         # from risk_flags (includes exploit info if available)
    "gas_context",          # Cheap gas / High gas
    "net_yield_after_gas",  # heuristic, adjusted by live gas where possible
    "tvl_trend_7d",         # ▲/▼ once we have ~7d snapshots
    "red_flag",             # ⚠ if sketch
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

# keep only columns that actually exist
existing_display_cols = [c for c in display_cols_raw if c in df_filtered.columns]

df_display = df_filtered[existing_display_cols].rename(columns=nice_names)

# -------------------------
# SORT
# -------------------------

sort_map = {
    "Net Yield After Gas (%)": "Net Yield After Gas (%)",
    "TVL ($)": "TVL ($)",
    "Fee APY (%)": "Fee APY (%)",
    "Total APY (%)": "Total APY (%)",
}

# we need to map pretty names back to the internal names we just renamed to
inverse_name_map = {v: k for k, v in nice_names.items()}

sort_col_pretty = sort_map[sort_choice]  # e.g. "Net Yield After Gas (%)"
sort_col_internal = inverse_name_map.get(sort_col_pretty, None)

df_display_for_sort = df_display.copy()

if sort_col_internal and sort_col_internal in df_filtered.columns:
    # Use the numeric source column from df_filtered for sorting
    numeric_series = pd.to_numeric(df_filtered[sort_col_internal], errors="coerce")
    df_display_for_sort["_sort_helper"] = numeric_series.values
else:
    # Fallback: try to sort on the pretty column directly
    df_display_for_sort["_sort_helper"] = pd.to_numeric(
        df_display_for_sort.get(sort_col_pretty, pd.Series(dtype=float)),
        errors="coerce"
    )

df_display_for_sort = df_display_for_sort.sort_values(
    "_sort_helper", ascending=False, na_position="last"
).drop(columns=["_sort_helper"], errors="ignore")

# -------------------------
# FORMAT FOR DISPLAY
# -------------------------

# After sorting, pretty-print dollar amounts, % values, arrows, etc.
df_display_pretty = format_for_display(df_display_for_sort)

# Drop columns that are completely empty / None across all rows (pure cleanup)
df_display_pretty = df_display_pretty.dropna(axis=1, how="all")

# -------------------------
# RENDER
# -------------------------

st.subheader("Leaderboard")

st.write(
    "Filter by chain, hide tiny TVL, remove high IL pools, then sort by Net Yield After Gas. "
    "Green-looking pools with no ⚠ and healthy TVL are usually safer starting points."
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

- **Vol 24h ($) / Vol/TVL (24h)**  
  How actively this pool is trading. Higher Vol/TVL means your liquidity gets used, so fee income is more “real,” not just bribed.

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
  “High gas” (Ethereum mainnet) is expensive to get in/out unless you're depositing size. “Cheap gas” (Arbitrum, Base, etc.) is friendlier for smaller deposits.

- **Net Yield After Gas (%)**  
  Our rough “is this even worth it for a normal wallet” estimate, not just the pretty headline APY. This now adapts based on live Ethereum gas.

- **TVL Trend (7d)**  
  Will show ▲ or ▼ once your snapshots have ~1 week of history. Up means money is flowing in (confidence). Down means people are leaving.

- **Red Flag**  
  ⚠ means slow down: maybe tiny TVL on an expensive chain, maybe yield is 100% bribes, maybe audit is unknown or exploit history.
""")
