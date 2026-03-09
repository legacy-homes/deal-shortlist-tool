#!/usr/bin/env python3
"""
Parser Health Check — Scheduled Rightmove Structure Validator
==============================================================

Run this every 2-3 days (via Windows Task Scheduler) to detect if Rightmove
has changed their website structure and the parser is silently returning 0 results.

Exit codes:
  0 — all checks passed
  1 — one or more checks failed (parser needs investigation)

Log file: logs/parser_healthcheck.log  (auto-created next to this script)

Usage:
  python scripts/parser_healthcheck.py

Windows Task Scheduler setup (run once in an admin terminal):
  schtasks /Create /SC DAILY /MO 3 /TN "DealFinder\\ParserHealthCheck" \
    /TR "C:\\personal\\deal-shortlist-tool\\.venv\\Scripts\\python.exe C:\\personal\\deal-shortlist-tool\\scripts\\parser_healthcheck.py" \
    /ST 08:00 /RL HIGHEST /F
"""

import sys
import os
import requests
import time
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
ROOT_DIR     = SCRIPT_DIR.parent
LOG_DIR      = ROOT_DIR / 'logs'
LOG_FILE     = LOG_DIR / 'parser_healthcheck.log'
STATUS_FILE  = LOG_DIR / 'parser_status.txt'   # last result for quick checks

sys.path.insert(0, str(ROOT_DIR / 'shared'))
from rightmove_parsers import extract_sold_properties_from_html, get_parser_info

# ── Test URLs — these should always have sold results ─────────────────────────
# Use high-volume areas so empty results always indicate a parser problem.
TEST_CASES = [
    {
        'label': 'Manchester — unfiltered, 1 mile radius',
        'url':   'https://www.rightmove.co.uk/house-prices/manchester.html?soldIn=2&radius=1.0',
        'min_expected': 10,
    },
    {
        'label': 'CV10 0NB — filtered, 0.25 mile, terraced freehold',
        'url':   'https://www.rightmove.co.uk/house-prices/cv10-0nb.html?soldIn=2&radius=0.25&propertyType=TERRACED&tenure=FREEHOLD',
        'min_expected': 1,    # small area — just needs to return something
    },
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def log(msg: str, also_print: bool = True):
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    if also_print:
        print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def run_checks() -> bool:
    """Run all test cases. Returns True if all pass."""
    info = get_parser_info()
    log("=" * 70)
    log(f"Parser Health Check — v{info['parser_version']} (last verified: {info['last_verified']})")
    log("=" * 70)

    all_passed = True

    for tc in TEST_CASES:
        label = tc['label']
        url   = tc['url']
        min_expected = tc['min_expected']

        log(f"\nChecking: {label}")
        log(f"  URL: {url}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log(f"  ✗ FAIL — HTTP request failed: {e}")
            all_passed = False
            continue

        try:
            props = extract_sold_properties_from_html(resp.text)
        except Exception as e:
            log(f"  ✗ FAIL — Parser exception: {e}")
            all_passed = False
            continue

        if len(props) < min_expected:
            log(f"  ✗ FAIL — Got {len(props)} properties, expected >= {min_expected}")
            log(f"           Rightmove may have changed their page structure.")
            all_passed = False
            continue

        # Spot-check first property has required fields
        p = props[0]
        missing = [f for f in ('address', 'sold_date', 'sold_price', 'link') if not p.get(f)]
        if missing:
            log(f"  ✗ FAIL — First property missing fields: {missing}")
            log(f"           Sample: {p}")
            all_passed = False
            continue

        # Check links start with expected prefix
        bad_links = [p2.get('link','') for p2 in props
                     if p2.get('link') and not p2['link'].startswith('https://www.rightmove.co.uk/house-prices/details/')]
        if bad_links:
            log(f"  ✗ FAIL — {len(bad_links)} links have unexpected format: {bad_links[0][:80]}")
            all_passed = False
            continue

        log(f"  ✓ PASS — {len(props)} properties extracted")
        log(f"           Sample: {p['address'][:50]} | {p['sold_date']} | £{p.get('sold_price','?'):,}")

        time.sleep(1)  # polite delay between requests

    return all_passed


def main():
    LOG_DIR.mkdir(exist_ok=True)
    passed = run_checks()

    log("\n" + "=" * 70)
    if passed:
        status = "PASS"
        log("✓ ALL CHECKS PASSED — parser is working correctly")
    else:
        status = "FAIL"
        log("✗ ONE OR MORE CHECKS FAILED — investigate parser")
        log(f"  Log file: {LOG_FILE}")
        log(f"  Run full test suite: python test_suite/test_parsing.py --verbose")
    log("=" * 70 + "\n")

    # Write a simple status file for quick external checks
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        f.write(f"{status}\n{datetime.now().isoformat()}\n")

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
