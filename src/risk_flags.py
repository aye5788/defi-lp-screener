# risk_flags.py
# Add safety-ish context to each pool:
# - audit_status  (from known protocol mappings)
# - red_flag      (simple rules)

import pandas as pd
from . import config

def apply_risk_flags(df: pd.DataFrame) -> pd.DataFrame:
    # audit_status from config.PROTOCOL_SAFETY
    def get_audit_status(project: str):
        if project in config.PROTOCOL_SAFETY:
            return config.PROTOCOL_SAFETY[project]
        return "Unknown"
    df["audit_status"] = df["project"].apply(get_audit_status)

    # red_flag:
    # We'll mark pools that look sketchy for small LPs.
    def is_red_flag(row):
        # Rule 1: tiny TVL on expensive chain
        tvl = row.get("tvlUsd", 0) or 0
        chain = row.get("chain", "")
        if (chain in config.EXPENSIVE_GAS_CHAINS) and (tvl < config.RED_FLAG_TVL_ETH_THRESHOLD):
            return "⚠"

        # Rule 2: audit unknown
        if row.get("audit_status", "Unknown") == "Unknown":
            # unknown isn't automatically ⚠, but we CAN warn if APY is huge/bribey
            # if it's paying huge reward_apy and no audit, call ⚠
            reward_apy = row.get("reward_apy", 0) or 0
            if reward_apy >= 20:  # arbitrary early threshold
                return "⚠"

        # Rule 3: IL risk High + reward-driven APY
        if row.get("il_risk") == "High":
            fee_apy = row.get("fee_apy", 0) or 0
            reward_apy = row.get("reward_apy", 0) or 0
            if fee_apy < 2 and reward_apy > 15:
                return "⚠"

        return ""

    df["red_flag"] = df.apply(is_red_flag, axis=1)

    return df
