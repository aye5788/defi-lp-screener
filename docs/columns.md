# Column Definitions (Leaderboard Screener)

This file defines every column in the dashboard table. For each column:
- what it means in plain English
- how we get it
- why it matters when deciding if a pool is worth entering

## pool_name
- Display: `TOKEN_PAIR | DEX | CHAIN` (e.g. `USDC-WETH | Uniswap v3 | Arbitrum`)
- Source: DeFiLlama `/yields` (`symbol`, `project`, `chain`)
- Why: Tells you exactly what you're providing liquidity for, where, and on what network.

## tvl_usd
- Display: `TVL ($)`
- Meaning: Total value locked in the pool right now (USD).
- Source: `tvlUsd` from DeFiLlama `/yields`.
- Why: Higher TVL usually means deeper, more trusted liquidity. Tiny TVL can be toxic.

## vol_24h_usd
- Display: `24h Volume ($)`
- Meaning: How much trading went through this pool in the last 24 hours.
- Source: DEX-specific data (Uniswap subgraph, Bitquery) or left blank at first if not yet integrated.
- Why: No volume = no fees. High volume = active pool earning fees.

## vol_to_tvl
- Display: `Vol/TVL (24h)`
- Formula: `vol_24h_usd / tvl_usd`
- Meaning: How hard each dollar in the pool is being "worked" by traders.
- Why: Higher is better. This is capital efficiency.

## fee_apy
- Display: `Fee APY (%)`
- Meaning: Estimated annualized return from swap fees only.
- Source: `apyBase` from DeFiLlama `/yields`.
- Why: This is the organic yield. If this is decent, pool is naturally productive.

## reward_apy
- Display: `Reward APY (%)`
- Meaning: Extra APY from incentives / emissions / bribes.
- Source: `apyReward` from DeFiLlama `/yields`.
- Why: High reward APY can disappear fast. It's the "this is hot right now" boost.

## total_apy
- Display: `Total APY (%)`
- Formula: `fee_apy + reward_apy`
- Meaning: Gross projected APY if you just look at headline yield.
- Why: Quick "is this even interesting" number.

## il_risk
- Display: `IL Risk`
- Meaning: Impermanent loss risk bucket: Low / Medium / High.
- Source: Either a flag from the data or rule-based on pair type:
  - Stable/stable or stakedAsset/asset → Low
  - Blue-chip vs stable → Medium
  - Volatile alt vs stable → High
- Why: IL is where you silently lose money if tokens move apart in price.

## audit_status
- Display: `Audit / Exploit Status`
- Meaning: Trust/safety label like:
  - "Audited / Clean"
  - "Exploit History"
  - "Unknown"
- Source: Map protocol name to status in code (config.PROTOCOL_SAFETY). Later can be enriched with hack data.
- Why: A huge APY is useless if the contract just got rugged.

## gas_context
- Display: `Gas Context`
- Meaning: "Cheap gas" (L2 / sidechain) vs "High gas (mainnet)" style label.
- Source: Infer from chain name (Arbitrum, Polygon, Base → cheap; Ethereum → high).
- Why: If gas is expensive and you're only putting in a few hundred bucks, yield might get eaten by fees.

## net_yield_after_gas
- Display: `Net Yield After Gas (%)`
- Meaning: Your realistic take-home yield after accounting for gas pain.
- Heuristic rule:
  - On cheap-gas chains: basically `total_apy`.
  - On Ethereum mainnet with low total_apy: treat as near 0 for small deposits.
- Why: Helps you avoid pools that are unprofitable at your size even if they look good on paper.

## tvl_trend_7d
- Display: `TVL Trend (7d)`
- Meaning: % change in TVL over the last 7 days, shown with ▲ / ▼.
- Source: Compare current `tvlUsd` vs stored snapshot from 7 days ago (`/data/snapshots/tvl_history.csv`).
- Why: If liquidity is fleeing fast, that's a warning. If it's climbing, that’s confidence.

## red_flag
- Display: `Red Flag`
- Meaning: "⚠" if this pool triggers one of the danger rules:
  - Exploit / unaudited
  - High IL + only-reward APY
  - Very tiny TVL on a high-gas chain
  - TVL dumping fast
- Source: logic in `risk_flags.py`.
- Why: This is your pause button. If ⚠ shows up, don't ape without reading details.
