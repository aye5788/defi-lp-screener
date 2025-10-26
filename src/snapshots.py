# snapshots.py
# Handle writing and reading historical snapshots so we can compute TVL trend.

import os
import pandas as pd
from datetime import datetime, timedelta

SNAPSHOT_DIR = "data/snapshots"

def save_today_snapshot(df_current: pd.DataFrame):
    """
    Save today's tvlUsd snapshot per pool into data/snapshots/YYYY-MM-DD.csv
    We keep: date, pool_name-ish identifiers, and tvlUsd.
    """
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    cols_to_keep = ["project", "chain", "symbol", "tvlUsd"]
    snap_df = df_current[cols_to_keep].copy()
    snap_df.insert(0, "timestamp_utc", datetime.utcnow().isoformat() + "Z")

    out_path = os.path.join(SNAPSHOT_DIR, f"{today_str}.csv")
    snap_df.to_csv(out_path, index=False)

def load_recent_snapshots(days=7):
    """
    Load last `days` worth of snapshots from data/snapshots/*.csv
    Returns a single DataFrame with columns:
    - snapshot_date (YYYY-MM-DD)
    - project, chain, symbol
    - tvlUsd
    """
    rows = []
    cutoff = datetime.utcnow() - timedelta(days=days+1)

    if not os.path.isdir(SNAPSHOT_DIR):
        return pd.DataFrame()

    for fname in os.listdir(SNAPSHOT_DIR):
        if not fname.endswith(".csv"):
            continue
        # Expect YYYY-MM-DD.csv
        snapshot_date = fname.replace(".csv", "")
        try:
            snap_dt = datetime.strptime(snapshot_date, "%Y-%m-%d")
        except ValueError:
            continue
        if snap_dt < cutoff:
            continue

        full_path = os.path.join(SNAPSHOT_DIR, fname)
        tmp = pd.read_csv(full_path)
        tmp["snapshot_date"] = snapshot_date
        rows.append(tmp)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)

def compute_tvl_trend_7d(df_current: pd.DataFrame) -> pd.DataFrame:
    """
    For each (project, chain, symbol) in df_current,
    look up what tvlUsd was ~7 days ago in snapshots,
    compute % change, and attach as 'tvl_trend_7d'.
    If we can't compute it, use '—'.
    """
    df_current = df_current.copy()
    hist = load_recent_snapshots(days=7)
    if hist.empty:
        df_current["tvl_trend_7d"] = "—"
        return df_current

    # pick oldest snapshot in the window for baseline
    # (not perfect but simple)
    oldest_per_pool = (
        hist.sort_values("snapshot_date")
            .groupby(["project", "chain", "symbol"], as_index=False)
            .first()[["project", "chain", "symbol", "tvlUsd"]]
            .rename(columns={"tvlUsd": "tvlUsd_7d_ago"})
    )

    merged = df_current.merge(
        oldest_per_pool,
        on=["project", "chain", "symbol"],
        how="left"
    )

    def pct_change(now, then):
        try:
            now_f = float(now)
            then_f = float(then)
            if then_f == 0:
                return None
            return ((now_f - then_f) / then_f) * 100.0
        except (TypeError, ValueError):
            return None

    merged["tvl_trend_7d"] = merged.apply(
        lambda r: pct_change(r.get("tvlUsd"), r.get("tvlUsd_7d_ago")),
        axis=1
    )

    # If None, fallback "—"
    def fmt(v):
        if v is None:
            return "—"
        return v  # we'll pretty-format later in formatting.py

    merged["tvl_trend_7d"] = merged["tvl_trend_7d"].apply(fmt)

    return merged
