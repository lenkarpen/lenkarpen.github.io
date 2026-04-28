#!/usr/bin/env python3
"""
ServiceNow Ticket Parser
Extracts structured user data (full name, pool, username) from
HTML-formatted columns in ServiceNow Excel exports.

Usage:
    python snow_parser.py tickets.xlsx
    python snow_parser.py tickets.xlsx -o output.csv
    python snow_parser.py tickets.xlsx -c caller_info -o output.csv

Requires: pandas, openpyxl, beautifulsoup4
    pip install pandas openpyxl beautifulsoup4
"""

import sys
import re
import argparse
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


def parse_user_info(raw: str) -> dict:
    """Parse one HTML-formatted cell from a ServiceNow export column."""
    fields = {"full_name": None, "pool_name": None, "username": None}

    if not raw or isinstance(raw, float):
        return fields

    text = BeautifulSoup(str(raw), "html.parser").get_text(separator="\n")

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if re.search(r"(full[\s_-]?name|display[\s_-]?name)", line, re.I):
            m = re.search(r":\s*(.+)", line)
            if m:
                fields["full_name"] = m.group(1).strip()

        elif re.search(r"(pool|desktop[\s_-]?pool|vdi[\s_-]?pool)", line, re.I):
            m = re.search(r":\s*(.+)", line)
            if m:
                fields["pool_name"] = m.group(1).strip()

        elif re.search(r"(user[\s_-]?name|login[\s_-]?id|sam[\s_-]?account)", line, re.I):
            m = re.search(r":\s*(\S+)", line)
            if m:
                fields["username"] = m.group(1).strip()

    return fields


def process_export(
    input_path: str,
    output_path: str | None = None,
    column: str = "user_info",
) -> pd.DataFrame:
    """
    Read a ServiceNow Excel export and produce a clean CSV with parsed user fields.

    Args:
        input_path:  Path to the .xlsx export file
        output_path: Destination CSV path (defaults to <input_stem>_parsed.csv)
        column:      Name of the column containing raw HTML user data

    Returns:
        DataFrame with extracted full_name, pool_name, username columns
    """
    src = Path(input_path)
    if not src.exists():
        sys.exit(f"File not found: {src}")

    print(f"Reading {src.name} ...")
    df = pd.read_excel(src)

    if column not in df.columns:
        available = ", ".join(df.columns.tolist())
        sys.exit(f"Column '{column}' not found.\nAvailable columns: {available}")

    parsed = df[column].apply(parse_user_info)
    df["full_name"] = [r["full_name"] for r in parsed]
    df["pool_name"] = [r["pool_name"] for r in parsed]
    df["username"]  = [r["username"]  for r in parsed]

    missing = df["full_name"].isna().sum()
    total = len(df)

    dest = Path(output_path) if output_path else src.with_name(f"{src.stem}_parsed.csv")
    df[["full_name", "pool_name", "username"]].to_csv(dest, index=False)

    print(f"Parsed {total - missing}/{total} rows successfully -> {dest}")
    if missing:
        print(f"Warning: {missing} rows could not be parsed — verify column format.")

    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Parse HTML user info from ServiceNow Excel exports"
    )
    ap.add_argument("input", help="Path to .xlsx export file")
    ap.add_argument("-o", "--output", help="Output CSV path (optional)")
    ap.add_argument(
        "-c", "--column",
        default="user_info",
        help="Column name containing HTML data (default: user_info)",
    )
    args = ap.parse_args()
    process_export(args.input, args.output, args.column)
