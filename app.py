import streamlit as st
import pandas as pd

from src.fetch_llama import get_yield_data
from src.enrich_metrics import add_basic_columns, add_trend_columns_and_snapshot
from src.risk_flags import apply_risk_flags
from src.formatting import format_for_display
from src import config
from src.fetch_gas import get_eth_gas_gwei


# -------------------------
# PAGE SETUP
# -------------------------

st.set_page_config(
    page_title="DeFi Liquidity Pool Screener",
    layout="wide"
)

st.title("DeFi Liquidity Pool Screener")
st.caption("Not financial advice. Yield != safety. High APY often means high risk or short-term incentives.")

# Show live gas so you understand why Net Yield After Gas moves
gas_now = get_eth_gas_gwei()
if gas_now is not None:
    st.write(f"📊 Current Ethereum gas: {gas_now:.1f} gwei")
else:
    st.write("📊 Current Ethereum gas: (unavailable)")

# -------------------------
# LOAD + ENRICH DATA
# -------------------------

# 1. Fetch raw data
df_raw = get_yield_data()

if df_raw is None or df_raw.empty:
    st.warning("⚠️ No data loaded from DeFiLlama (API may be rate-limited or temporarily unavailable). Showing empty table.")
else:
    st.success(f"✅ Loaded {len(df_raw)} pools from DeFiLlama.")

# 2. Derive metrics (total_apy, il_risk, gas_context, etc.)
df_enriched = add_basic_columns(df_raw)

# 3. Add TVL trend and snapshot (best-effort, won't crash on failure)
df_enriched = add_trend_columns_and_snapshot(df_enriched)

# 4. Add audit_status + red_flag, and other safety logic
df_scored = apply_risk_flags(df_enriched)

# 5. Safety: ensure expected columns always exist so downstream code doesn't KeyError
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
# SIDEBAR FILTERS
# -------------------------

st.sidebar.header("Filters")

# Chain filter (robust even if data is missing)
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

# Minimum TVL filter
min_tvl = st.sidebar.number_input(
    "Minimum TVL ($)",
    min_value=0,
    value=config.MIN_TVL_DEFAULT,
    step=50000,
    help="Hide tiny pools below this size. Bigger TVL is usually safer / less ruggy."
)

# IL risk tolerance
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

# Hide obvious sketch
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
# APPLY FILTER LOGIC
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

# filter by red flag (defensive: only if column exists)
if hide_red_flag and "red_flag" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["red_flag"].fillna("") == ""]

# -------------------------
# PREP COLUMNS FOR DISPLAY
# -------------------------

display_cols_raw = [
    "pool_name",            # <symbol> | <project> | <chain>
    "tvlUsd",               # TVL
    "volume_24h_usd",       # 24h volume (Uniswap v3 pools only right now)
    "vol_to_tvl",           # capital efficiency
    "fee_apy",              # fee APY
    "reward_apy",           # incentive APY
    "total_apy",            # fee + reward
    "il_risk",              # Low / Medium / High
    "audit_status",         # includes exploit info where known
    "gas_context",          # Cheap gas / High gas
    "net_yield_after_gas",  # APY after gas penalty
    "tvl_trend_7d",         # ▲ or ▼ once snapshot history accumulates
    "red_flag",             # ⚠ marker
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

# Only keep columns that actually exist in df_filtered
existing_display_cols = [c for c in display_cols_raw if c in df_filtered.columns]

# Build df_display with nice names
df_display = df_filtered[existing_display_cols].rename(columns=nice_names)

# -------------------------
# SORT ROWS
# -------------------------

# Mapping from UI sort label -> pretty column name in df_display
sort_map = {
    "Net Yield After Gas (%)": "Net Yield After Gas (%)",
    "TVL ($)": "TVL ($)",
    "Fee APY (%)": "Fee APY (%)",
    "Total APY (%)": "Total APY (%)",
}

sort_col_pretty = sort_map[sort_choice]  # e.g. "Net Yield After Gas (%)"

df_display_for_sort = df_display.copy()

# Create a numeric helper column for sorting
if sort_col_pretty in df_display_for_sort.columns:
    df_display_for_sort["_sort_helper"] = pd.to_numeric(
        df_display_for_sort[sort_col_pretty].str.replace("%", "", regex=False)
        if df_display_for_sort[sort_col_pretty].dtype == object
        else df_display_for_sort[sort_col_pretty],
        errors="coerce"
    )
else:
    # fallback if somehow missing
    df_display_for_sort["_sort_helper"] = pd.Series(dtype=float)

df_display_for_sort = df_display_for_sort.sort_values(
    "_sort_helper",
    ascending=False,
    na_position="last"
).drop(columns=["_sort_helper"], errors="ignore")

# -------------------------
# HUMAN-FRIENDLY FORMATTING
# -------------------------

df_display_pretty = format_for_display(df_display_for_sort)

# Drop columns that are 100% empty/null after formatting
df_display_pretty = df_display_pretty.dropna(axis=1, how="all")

# -------------------------
# RENDER TABLE + EXPLANATION
# -------------------------

st.subheader("Leaderboard")

st.write(
    "Filter by chain, hide tiny TVL, remove high IL pools, then sort by Net Yield After Gas. "
    "Green-looking pools with no ⚠ and healthy TVL are usually safer starting points."
)

st.dataframe(
    df_display_pretty,
    width="stretch",
    hide_index=True
)

st.markdown("---")
st.markdown("""
**Column guide (why you should care):**

- **TVL ($)**  
  How much money is sitting in the pool. Bigger = more established, less likely to just vanish.

- **Vol 24h ($) / Vol/TVL (24h)**  
  How actively this pool is trading. Higher Vol/TVL means your liquidity is used, so fee income is “real,” not just bribes.

- **Fee APY (%)**  
  Yield from actual swap fees. This is the sustainable part.

- **Reward APY (%)**  
  Extra incentives the protocol is throwing at LPs. Can disappear fast.

- **Total APY (%)**  
  Fee APY + Reward APY. This is the headline number, but it can be fake-looking if it's all rewards.

- **IL Risk**  
  Impermanent loss danger. High IL means if the tokens move apart in price, you might bleed vs just holding them.

- **Audit / Exploit Status**  
  Rough safety snapshot. “Unknown” doesn’t mean scam, but it means slow down and actually read.

- **Gas Context**  
  “High gas” (Ethereum mainnet) is expensive to get in/out unless you're depositing size. “Cheap gas” (Arbitrum, Base, etc.) is friendlier for smaller deposits.

- **Net Yield After Gas (%)**  
  Our rough “is this even worth it for a normal wallet” estimate, not just the pretty headline APY. This now adapts based on live Ethereum gas.

- **TVL Trend (7d)**  
  Will show ▲ or ▼ once your snapshots have ~1 week of history. Up = money flowing in (confidence). Down = people leaving.

- **Red Flag**  
  ⚠ means slow down: maybe tiny TVL on an expensive chain, maybe yield is 100% bribed, maybe audit is unknown or exploit history.
""")
