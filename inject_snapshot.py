#!/usr/bin/env python3
"""
inject_snapshot.py
──────────────────
Run by the GitHub Action at build time.
Reads the latest CSVs from sibling repos (alpha-core, live-trading-alpha,
ml-portfolio-optimizer) and patches index.html with pre-rendered values so
that:
  - crawlers and preview tools see real numbers without JS
  - page ships with valid data even if JS fetch later fails (stale beats blank)

Usage (from quant-dashboard/ root):
    python3 inject_snapshot.py [--html index.html] [--data-root ../]
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List, Dict


# ── helpers ─────────────────────────────────────────────────────────────────
def read_csv_last(path: Path) -> Optional[Dict]:
    """Return the last non-empty row of a CSV file, or None."""
    try:
        with path.open(newline="") as f:
            rows = [r for r in csv.DictReader(f) if any(v.strip() for v in r.values())]
        return rows[-1] if rows else None
    except Exception as e:
        print(f"  WARN: cannot read {path}: {e}", file=sys.stderr)
        return None


def read_csv_all(path: Path) -> List[Dict]:
    """Return all rows of a CSV."""
    try:
        with path.open(newline="") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"  WARN: cannot read {path}: {e}", file=sys.stderr)
        return []


def patch(html: str, element_id: str, new_text: str, attr: str = "data-snapshot") -> str:
    """
    Replace both the text content AND data-snapshot attribute of an element.
    Works on single-line elements; safe for multi-line if id is unique.
    """
    # Update data-snapshot attribute value
    html = re.sub(
        rf'(id="{element_id}"[^>]*){attr}="[^"]*"',
        rf'\g<1>{attr}="{new_text}"',
        html,
    )
    # Replace inner text between > and < (greedy-safe: first occurrence after id)
    # We find the tag, then replace text content
    pattern = rf'(<[^>]+id="{element_id}"[^>]*>)[^<]*(<)'
    html = re.sub(pattern, rf'\g<1>{new_text}\g<2>', html)
    return html


# ── main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html",      default="index.html")
    parser.add_argument("--data-root", default="..")
    args = parser.parse_args()

    html_path = Path(args.html)
    root      = Path(args.data_root)

    # ── data paths ──────────────────────────────────────────────────────────
    journal_path  = root / "live-trading-alpha"  / "alpaca_journal.csv"
    regime_path   = root / "alpha-core"          / "data" / "regime_labels.csv"
    rolling_path  = root / "alpha-core"          / "data" / "rolling_ic.csv"

    # ── read latest values ──────────────────────────────────────────────────
    journal_last = read_csv_last(journal_path)
    regime_last  = read_csv_last(regime_path)
    rolling_last = read_csv_last(rolling_path)

    nav      = float(journal_last.get("Portfolio_Value", 100000) or 100000) if journal_last else 100000
    pnl      = nav - 100000
    pnl_pct  = pnl / 100000 * 100
    sessions = len(read_csv_all(journal_path))
    data_date = (journal_last.get("Date") or journal_last.get("Day") or str(date.today())) if journal_last else str(date.today())

    regime  = (regime_last.get("regime_name") or regime_last.get("regime") or "BULL").upper() if regime_last else "BULL"

    avg_ic  = float(rolling_last.get("mean_ic") or rolling_last.get("ic") or 0.071) if rolling_last else 0.071

    # ── format values ───────────────────────────────────────────────────────
    nav_fmt     = f"${nav:,.2f}"
    pnl_sign    = "+" if pnl >= 0 else ""
    pnl_fmt     = f"{pnl_sign}${abs(pnl):,.2f}"
    ret_fmt     = f"{pnl_sign}{pnl_pct:.2f}%"
    ic_fmt      = f"{avg_ic:.3f}"
    build_ts    = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    print(f"  NAV:      {nav_fmt}")
    print(f"  P&L:      {pnl_fmt}  ({ret_fmt})")
    print(f"  Sessions: {sessions}")
    print(f"  Date:     {data_date}")
    print(f"  Regime:   {regime}")
    print(f"  Avg IC:   {ic_fmt}")
    print(f"  Build:    {build_ts}")

    # ── patch HTML ──────────────────────────────────────────────────────────
    html = html_path.read_text(encoding="utf-8")

    # Item 3: pre-render NAV into #alpaca-nav
    html = patch(html, "alpaca-nav",  nav_fmt,      "data-snapshot")
    html = patch(html, "donut-nav",   nav_fmt,      "data-snapshot")
    html = patch(html, "dataAsOf",    data_date,    "data-snapshot")
    html = patch(html, "aps-ret",     ret_fmt,      "data-snapshot")
    html = patch(html, "aps-sess",    str(sessions),"data-snapshot")
    html = patch(html, "hdr-ic",      ic_fmt,       "data-snapshot")

    # Also stamp a build comment at the top of <body>
    build_comment = f"\n<!-- snapshot: {nav_fmt} · {data_date} · built {build_ts} -->"
    html = html.replace("<body>", f"<body>{build_comment}", 1)

    html_path.write_text(html, encoding="utf-8")
    print(f"\n✅  Patched {html_path}  ({html_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
