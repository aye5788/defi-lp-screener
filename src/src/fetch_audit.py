# fetch_audit.py
# OPTIONAL: pull external safety/audit context.
# Different sources have different formats.
# We'll design this so that if the fetch fails,
# we just fall back to config.PROTOCOL_SAFETY.

import requests
import pandas as pd

# This is a placeholder. In practice you'd adapt to whichever audit source you trust.
# Many audit trackers expose protocol name + score or "exploited recently" yes/no.

def get_external_audit_table():
    """
    Return a DataFrame with columns:
    - project (string, e.g. "uniswap-v3", "curve")
    - external_audit_score (0-100 or text)
    - exploited_recently (True/False)

    If we can't fetch anything, return empty DataFrame.
    """
    try:
        # This is a stub. Replace URL with a real JSON source you trust.
        # For example: a curated GitHub gist you maintain, or a service like DeFiSafety.
        # We'll just return empty for now.
        return pd.DataFrame(columns=["project", "external_audit_score", "exploited_recently"])
    except Exception:
        return pd.DataFrame(columns=["project", "external_audit_score", "exploited_recently"])
