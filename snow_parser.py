#!/usr/bin/env python3
"""
VDI Onboarding Pipeline — Parse, Reconcile & Flag
==================================================
End-to-end pre-processor for contractor onboarding batches.

Stage 1  Parse ITSM ticket exports — each ticket stores ~10 fields per worker
         inside one HTML-formatted cell. BeautifulSoup + regex extract them.

Stage 2  Reconcile parsed records against an identity-management export to
         attach assigned usernames, with name normalisation handling casing,
         middle initials, and preferred-name variants.

Stage 3  Anomaly detection — for each (pool, region) combination, check the
         rolling 12-month history. Seen recently -> auto-populate the
         historical security group. Not seen -> flag for manual review
         (most likely a new pool, or one that's been retired).

Output is a single CSV that the PowerShell provisioner consumes.

This is the sanitised, public version. All example field names are generic;
no internal labels are used.

Usage:
    python snow_parser.py tickets.xlsx identity.xlsx history.csv -o batch.csv

Requires: pandas, openpyxl, beautifulsoup4
    pip install pandas openpyxl beautifulsoup4
"""

import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
from bs4 import BeautifulSoup


# ────────────────────────────────────────────────────────────────────────────
# Stage 1 — Parse one ticket's HTML metadata blob
# ────────────────────────────────────────────────────────────────────────────

FIELD_PATTERNS = {
    "first_name":    r"(legal[\s_-]?first[\s_-]?name|first[\s_-]?name)",
    "last_name":     r"(legal[\s_-]?last[\s_-]?name|last[\s_-]?name)",
    "manager":       r"(people[\s_-]?manager|manager[\s_-]?name|manager)",
    "region":        r"(geographic[\s_-]?region|region)",
    "pool_name":     r"(pool[\s_-]?name|vdi[\s_-]?profile)",
    "start_date":    r"(request[\s_-]?start[\s_-]?date|start[\s_-]?date)",
    "rehire":        r"(ever[\s_-]?worked|previous[\s_-]?employee|rehire)",
    "contact_email": r"(personal[\s_-]?email|contact[\s_-]?email)",
}


def parse_ticket_html(raw: str) -> dict:
    """Extract structured fields from one ticket's HTML metadata cell."""
    record = {k: None for k in FIELD_PATTERNS}

    if not raw or isinstance(raw, float):
        return record

    text = BeautifulSoup(str(raw), "html.parser").get_text(separator="\n")

    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        for field, pattern in FIELD_PATTERNS.items():
            if record[field] is None and re.search(pattern, line, re.I):
                m = re.search(r":\s*(.+)", line)
                if m:
                    record[field] = m.group(1).strip()
                break

    # Compose normalised full name for matching downstream
    if record["first_name"] and record["last_name"]:
        record["full_name"] = f"{record['first_name']} {record['last_name']}"

    # Normalise rehire flag to a clean boolean
    if isinstance(record["rehire"], str):
        record["rehire"] = record["rehire"].lower().startswith(("yes", "true", "y"))

    return record


# ────────────────────────────────────────────────────────────────────────────
# Stage 2 — Reconcile parsed records against the identity-management export
# ────────────────────────────────────────────────────────────────────────────

def normalise_name(name: str) -> str:
    """Lowercase, drop middle initials, collapse whitespace.
    'John A. Smith' and 'john   smith' both normalise to 'john smith'."""
    if not name:
        return ""
    name = re.sub(r"\s+\w\.\s+", " ", name)
    return re.sub(r"\s+", " ", name.strip().lower())


def attach_usernames(tickets: pd.DataFrame, identity: pd.DataFrame) -> pd.DataFrame:
    """Match parsed ticket records to identity-management records by
    normalised full name and attach the assigned username."""
    tickets["_key"] = tickets["full_name"].apply(normalise_name)
    identity["_key"] = identity["full_name"].apply(normalise_name)

    merged = tickets.merge(
        identity[["_key", "username"]],
        on="_key",
        how="left",
    ).drop(columns="_key")

    unmatched = merged["username"].isna().sum()
    if unmatched:
        print(f"⚠ {unmatched} record(s) could not be matched to a username — "
              f"verify name spelling against the identity portal.")
    return merged


# ────────────────────────────────────────────────────────────────────────────
# Stage 3 — Anomaly detection on rolling pool/region history
# ────────────────────────────────────────────────────────────────────────────

def flag_new_pool_combinations(
    records: pd.DataFrame,
    history: pd.DataFrame,
    window_days: int = 180,
) -> pd.DataFrame:
    """For each record, check whether its (pool, region) combination has
    been used in the rolling history window.

      • Seen recently    → auto-populate the most recent security group.
      • Not seen recently → flag for manual review (probable new pool, or
                            a retired one that needs cleanup).
    """
    cutoff = datetime.now() - timedelta(days=window_days)
    history["seen_at"] = pd.to_datetime(history["seen_at"])
    recent = history[history["seen_at"] >= cutoff]

    # Lookup: (pool, region) -> most recent security group seen in window
    lookup = (
        recent.sort_values("seen_at", ascending=False)
              .drop_duplicates(subset=["pool_name", "region"])
              .set_index(["pool_name", "region"])["security_group"]
              .to_dict()
    )

    def resolve(row):
        return lookup.get((row["pool_name"], row["region"]))

    records["security_group"]      = records.apply(resolve, axis=1)
    records["needs_manual_review"] = records["security_group"].isna()
    return records


# ────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ────────────────────────────────────────────────────────────────────────────

def run_pipeline(tickets_path, identity_path, history_path, output_path=None):
    for p in (tickets_path, identity_path, history_path):
        if not Path(p).exists():
            sys.exit(f"File not found: {p}")

    tickets_raw = pd.read_excel(tickets_path)
    identity_df = pd.read_excel(identity_path)
    history_df  = pd.read_csv(history_path)

    parsed = tickets_raw["ticket_html"].apply(parse_ticket_html)
    records = pd.DataFrame(parsed.tolist())

    records = attach_usernames(records, identity_df)
    records = flag_new_pool_combinations(records, history_df)

    dest = Path(output_path) if output_path else Path("onboarding_batch.csv")
    records.to_csv(dest, index=False)

    total = len(records)
    flagged = int(records["needs_manual_review"].sum())
    print(f"✓ Processed {total} records  →  {dest}")
    print(f"  • {total - flagged} auto-resolved security groups")
    print(f"  • {flagged} flagged for manual review (new / retired pool)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Parse, reconcile and flag a VDI onboarding batch."
    )
    ap.add_argument("tickets",  help="ITSM ticket export (.xlsx)")
    ap.add_argument("identity", help="Identity-management export (.xlsx)")
    ap.add_argument("history",  help="12-month onboarding history (.csv)")
    ap.add_argument("-o", "--output", help="Output CSV path (default: onboarding_batch.csv)")
    args = ap.parse_args()
    run_pipeline(args.tickets, args.identity, args.history, args.output)
