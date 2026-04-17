#!/usr/bin/env python3
"""
genereer_index.py — Genereer een JSON index van alle wetten voor de website.

Leest alle .md bestanden in wetten/, pakt de YAML-frontmatter eruit,
en schrijft een index.json die de website kan laden.

Gebruik:
    python scripts/genereer_index.py --wetten wetten/ --output index.json
"""

import argparse
import json
import re
from pathlib import Path


def lees_frontmatter(pad: Path) -> dict:
    """Lees YAML-frontmatter uit een Markdown-bestand."""
    try:
        inhoud = pad.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    if not inhoud.startswith("---"):
        return {}

    einde = inhoud.find("\n---", 3)
    if einde == -1:
        return {}

    meta = {}
    for regel in inhoud[3:einde].split("\n"):
        if ":" in regel:
            sleutel, _, waarde = regel.partition(":")
            meta[sleutel.strip()] = waarde.strip().strip('"')

    return meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wetten",  default="wetten/")
    p.add_argument("--output",  default="index.json")
    args = p.parse_args()

    wetten_dir = Path(args.wetten)
    index = []

    bestanden = sorted(wetten_dir.rglob("*.md"))
    print(f"{len(bestanden)} bestanden verwerken...")

    for bestand in bestanden:
        meta = lees_frontmatter(bestand)
        if not meta:
            continue

        # Relatief pad voor GitHub URL
        rel_pad = str(bestand).replace("\\", "/")

        index.append({
            "titel":      meta.get("title", bestand.stem),
            "identifier": meta.get("identifier", ""),
            "categorie":  meta.get("categorie", "Overig"),
            "datum":      meta.get("laatste_update", meta.get("publicatiedatum", "")),
            "status":     meta.get("status", "geldig"),
            "pad":        rel_pad,
        })

    # Sorteer op titel
    index.sort(key=lambda w: w["titel"].lower())

    output_pad = Path(args.output)
    output_pad.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )

    print(f"Index geschreven: {len(index)} wetten → {output_pad}")
    print(f"Bestandsgrootte: {output_pad.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
