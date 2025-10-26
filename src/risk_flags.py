# risk_flags.py
# Add safety-ish context to each pool:
# - audit_status  (from known protocol mappings and optional external audit table)
# - red_flag      (simple rules)

import pandas as pd
from . import config
from .fetch_audit import get_external_audit_table

def apply_risk_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Bring in external audit/exploit info if available
    audit_df = get_external_audit_table()
    if not audit_df.empty:
        df = df.merge(
            audit_df,
            how="left",
            left_on="project",
            right_on="project",
            suffixes=("", "_audit")
        )
    else:
        # ensure columns exist
        df["external_audit_score"] = None
        df["exploited_recently"] = False

    # audit_status from config.PROTOCOL_SAFETY or fallback to external info
    def get_audit_status(row):
        proj = row.get("project", "")
        base_status = config.PROTOCOL_SAFETY.get(proj, "Unknown")

        # If we merged external data and it's bad, override
        if row.get("exploited_recently", False):
            return "Exploit History"
        if base_status != "Unknown":
            return base_status

        # If we have an external score, reflect it
        score = row.get("external_audit_score")
        if score not in [None, ""]:
            return f"Score {score}"

        return base_status  # probably "Unknown"

    df["audit_status"] = df.apply(get_audit_status, axis=1)

    # red_flag:
    def is_red_flag(row):
        # Rule 1: tiny TVL + expensive chain
        tvl = row.get("tvlUsd", 0) or 0
        chain = row.get("chain", "")
        if (chain in config.EXPENSIVE_GAS_CHAINS) and (tvl < config.RED_FLAG_TVL_ETH_THRESHOLD):
            return "⚠"

        # Rule 2: exploited recently
        if row.get("exploited_recently", False):
            return "⚠"

        # Rule 3: IL High AND basically all APY is reward
        if row.get("il_risk") == "High":
            fee_apy = row.get("fee_apy", 0) or 0
            reward_apy = row.get("reward_apy", 0) or 0
            if fee_apy < 2 and reward_apy > 15:
                return "⚠"

        # Rule 4: unknown audit status but reward APY is crazy
        if row.get("audit_status") == "Unknown":
            reward_apy = row.get("reward_apy", 0) or 0
            if reward_apy >= 20:
                return "⚠"

        return ""

    df["red_flag"] = df.apply(is_red_flag, axis=1)

    return df
