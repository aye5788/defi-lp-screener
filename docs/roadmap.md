# Roadmap / Build Phases

This file tracks the evolution plan for the DeFi LP Screener.

## Phase 0: Define columns (DONE)
- Lock in which columns we show in the leaderboard table.
- Document what each column means (columns.md).
- Decide what counts as a "red flag."

Output of this phase:
- docs/columns.md
- This roadmap file

## Phase 1: Data ingestion
Goal:
- Pull raw pool data from DeFiLlama `/yields`.

Tasks:
- Create `src/fetch_llama.py`
  - `get_yield_data()` → returns a pandas DataFrame with:
    - project (DEX name)
    - chain
    - symbol (token pair)
    - tvlUsd
    - apyBase
    - apyReward
    - etc.

- Add `requirements.txt` with:
  - streamlit
  - pandas
  - requests
  - python-dateutil

## Phase 2: Derived metrics
Goal:
- Turn raw data into the final columns we care about.

Tasks:
- Create `src/enrich_metrics.py` with helpers that add:
  - total_apy = fee_apy + reward_apy
  - il_risk (rule-based on pair type)
  - gas_context (L2 vs Ethereum mainnet)
  - net_yield_after_gas (cheap chain vs high gas chain heuristic)
  - (later) vol_to_tvl and tvl_trend_7d if available

- Create `src/risk_flags.py`:
  - Adds `audit_status`
  - Adds `red_flag` using rules (exploit, tiny TVL, etc).

- Create `src/config.py`:
  - CHEAP_GAS_CHAINS
  - EXPENSIVE_GAS_CHAINS
  - thresholds for red flags
  - protocol audit mappings

## Phase 3: Streamlit UI (MVP)
Goal:
- Actually see this in a browser.

Tasks:
- Create `app.py`:
  - Call `get_yield_data()`
  - Run through `enrich_metrics` and `risk_flags`
  - Apply filters:
    - chain filter
    - min TVL slider
    - IL risk allowed
    - sort by (default: net_yield_after_gas)
  - Show table with the final columns.

- Add row expanders:
  - Human explanation for the pool:
    - Why yield exists (fees vs incentives)
    - IL risk meaning
    - Gas context
    - Any red flags

## Phase 4: Persistence / trend
Goal:
- Add time awareness.

Tasks:
- Add `/data/snapshots/tvl_history.csv`
  - Append daily snapshots of pool TVL and APY.
  - Use that to calculate `tvl_trend_7d`.

- Update `enrich_metrics.py` to merge in trend columns.

- Update table to show ▲ / ▼ next to TVL Trend.

## Phase 5: Safety polish
Goal:
- Help avoid obvious traps.

Tasks:
- Expand `risk_flags.py`:
  - Mark pools with recent exploit history or unaudited status.
  - Mark pools where almost all APY is from `reward_apy` and it's collapsing.
  - Hide these by default (Streamlit checkbox "Show risky pools").

- Add a "Red Flag" column with ⚠ in the main table.
- Add optional filter "Hide ⚠ pools".

This is enough to use the app like a daily scanner for LP opportunities.
