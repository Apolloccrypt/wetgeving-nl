#!/usr/bin/env python3
"""
koppel_kamerstukken.py — Koppel Kamerstukken aan Nederlandse wetten
via de rijksoverheid.nl open data API.

Gebruik:
    python scripts/koppel_kamerstukken.py --index index.json --limit 100
    python scripts/koppel_kamerstukken.py --index index.json
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import requests

DELAY   = 0.3
API_URL = "https://opendata.rijksoverheid.nl/v1/documents"


def fetch(url: str, params: dict = None) -> Optional[requests.Response]:
    for i in range(3):
        try:
            r = requests.get(url, params=params, timeout=20)
            r.raise_for_status()
            time.sleep(DELAY)
            return r
        except requests.RequestException:
            time.sleep(2 ** i)
    return None


def haal_kamerstukken_op(titel: str, identifier: str) -> list[dict]:
    """Zoek Kamerstukken via de rijksoverheid.nl API op wet-titel."""
    # Gebruik citeertitel (korter en preciezer)
    zoekterm = titel[:60] if len(titel) > 60 else titel

    params = {
        "type": "parliamentarydocument",
        "q":    zoekterm,
        "rows": 3,
    }
    r = fetch(API_URL, params=params)
    if not r:
        return []

    try:
        root = ET.fromstring(r.text)
        resultaten = []
        for doc in root.findall("document"):
            titel_el  = doc.find("title")
            url_el    = doc.find("canonical")
            datum_el  = doc.find("available")
            intro_el  = doc.find("introduction")

            if titel_el is None:
                continue

            # Strip HTML uit introduction
            intro = ""
            if intro_el is not None and intro_el.text:
                intro = re.sub(r"<[^>]+>", "", intro_el.text).strip()[:200]

            datum = ""
            if datum_el is not None and datum_el.text:
                datum = datum_el.text[:10]

            resultaten.append({
                "titel": (titel_el.text or "").strip()[:120],
                "url":   (url_el.text or "").strip() if url_el is not None else "",
                "datum": datum,
                "intro": intro,
            })

        return resultaten
    except Exception:
        return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index",  default="index.json")
    p.add_argument("--output", default="index.json")
    p.add_argument("--limit",  type=int, default=0)
    args = p.parse_args()

    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    te_verwerken = index[:args.limit] if args.limit else index

    print(f"{len(te_verwerken)} wetten verwerken...")
    gevonden = 0

    for i, wet in enumerate(te_verwerken):
        titel = wet.get("titel", "")
        ident = wet.get("identifier", "")
        if not titel:
            continue

        kamerstukken = haal_kamerstukken_op(titel, ident)
        if kamerstukken:
            wet["kamerstukken"] = kamerstukken
            gevonden += 1

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(te_verwerken)} ({gevonden} met Kamerstukken)")

    print(f"\nKlaar: {gevonden}/{len(te_verwerken)} wetten hebben Kamerstukken")

    Path(args.output).write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    print(f"Opgeslagen: {args.output}")


if __name__ == "__main__":
    main()
