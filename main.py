#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch create Octo Browser profiles:
  • proxies from proxies.csv
  • optional cookies from cookies.json
  • Octo auto-generates fingerprint from stub
  • Number of profiles controlled via PROFILE_COUNT env (default: number of proxies)
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import itertools

import requests
from dotenv import load_dotenv

# ──────────────────────────── CONFIG ─────────────────────────────
API_BASE      = "https://app.octobrowser.net/api/v2/automation"
REQ_TIMEOUT   = 30       # сек
PAUSE         = 0.5      # сек
DEFAULT_FP    = {"os": "win", "screen": "1920x1080"}

BASE_DIR      = Path(__file__).parent.resolve()
load_dotenv()  # загружаем .env

TOKEN         = os.getenv("OCTO_API_TOKEN", "")
if not TOKEN:
    sys.exit("🛑 Specify OCTO_API_TOKEN in .env")
HEADERS       = {"X-Octo-Api-Token": TOKEN}

PROXY_CSV     = BASE_DIR / os.getenv("PROXY_FILE", "proxies.csv")
COOKIE_JSON   = BASE_DIR / os.getenv("COOKIE_FILE", "cookies.json")
PROFILE_COUNT = int(os.getenv("PROFILE_COUNT", "0"))  # 0 = use len(proxies)

# ────────────────────────────── UTILITIES ─────────────────────────

def sniff(path: Path) -> csv.Dialect:
    sample = path.read_text(encoding="utf-8")[:1024]
    return csv.Sniffer().sniff(sample, delimiters=",;\t ")


def load_proxies(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        sys.exit(f"🛑 Proxies file not found: {path}")
    dialect = sniff(path)
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, dialect=dialect)
        proxies = []
        for row in reader:
            p = {k.strip(): v.strip() for k, v in row.items() if v and k}
            try:
                p["port"] = int(p["port"])
            except:
                sys.exit(f"🛑 Invalid proxy row: {row}")
            proxies.append(p)
    if not proxies:
        sys.exit("🛑 No proxies loaded")
    return proxies


def load_cookies(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit("🛑 cookies.json must be a JSON object")
    return data


def api_post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=REQ_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["data"]

# ─────────────────────────────── MAIN ──────────────────────────────

def main():
    proxies = load_proxies(PROXY_CSV)
    cookies_map = load_cookies(COOKIE_JSON)

    # determine how many profiles to create
    total = PROFILE_COUNT if PROFILE_COUNT > 0 else len(proxies)
    proxy_cycle = itertools.cycle(proxies)

    for idx in range(1, total + 1):
        proxy = next(proxy_cycle)
        title = f"BatchProfile_{idx}"
        cookies = cookies_map.get(str(idx-1))

        payload = {"title": title, "proxy": proxy, "fingerprint": DEFAULT_FP}
        if cookies:
            payload["cookies"] = cookies

        try:
            data = api_post("profiles", payload)
            print(f"✅ Profile #{idx} created → UUID {data['uuid']}")
        except requests.HTTPError as e:
            print(f"❌ HTTP error for profile #{idx}: {e}")
            print("   Server response:", e.response.text)
        time.sleep(PAUSE)

if __name__ == "__main__":
    main()
