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


def lees_body(pad: Path, max_tekens: int = 400) -> str:
    """Lees de bodytekst van een wet (na de frontmatter)."""
    try:
        inhoud = pad.read_text(encoding="utf-8", errors="replace")
        einde = inhoud.find("\n---", 3)
        if einde < 0:
            return ""
        body = inhoud[einde + 4:].strip()
        # Verwijder Markdown-opmaak
        body = re.sub(r"^#{1,6}\s+", "", body, flags=re.MULTILINE)
        body = re.sub(r"\n+", " ", body)
        body = re.sub(r"\s+", " ", body)
        return body[:max_tekens].strip()
    except Exception:
        return ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wetten",  default="wetten/")
    p.add_argument("--output",  default="index.json")
    p.add_argument("--zoekindex", default="zoekindex.json")
    p.add_argument("--verwijzingen", default="verwijzingen.json")
    args = p.parse_args()

    wetten_dir = Path(args.wetten)
    index = []
    zoekindex = []

    bestanden = sorted(wetten_dir.rglob("*.md"))
    print(f"{len(bestanden)} bestanden verwerken...")

    for i, bestand in enumerate(bestanden):
        meta = lees_frontmatter(bestand)
        if not meta:
            continue

        rel_pad = str(bestand).replace("\\", "/")

        index.append({
            "titel":      meta.get("title", bestand.stem),
            "identifier": meta.get("identifier", ""),
            "categorie":  meta.get("categorie", "Overig"),
            "datum":      meta.get("laatste_update", meta.get("publicatiedatum", "")),
            "status":     meta.get("status", "geldig"),
            "pad":        rel_pad,
        })

        # Zoekindex: id verwijst naar positie in index
        body = lees_body(bestand)
        zoekindex.append({"i": i, "b": body})

    # Sorteer beide op titel
    gesorteerd = sorted(range(len(index)), key=lambda x: index[x]["titel"].lower())
    index = [index[i] for i in gesorteerd]
    zoekindex_gesorteerd = {gesorteerd[i]: zoekindex[i] for i in range(len(gesorteerd))}
    zoekindex_lijst = [zoekindex_gesorteerd[i] for i in range(len(index))]

    output_pad = Path(args.output)
    output_pad.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    print(f"index.json: {len(index)} wetten ({output_pad.stat().st_size/1024/1024:.1f} MB)")

    zoek_pad = Path(args.zoekindex)
    zoek_pad.write_text(
        json.dumps(zoekindex_lijst, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    print(f"zoekindex.json: {zoek_pad.stat().st_size/1024/1024:.1f} MB")

    # Genereer verwijzingen.json
    bwbr_pat = re.compile(r'BWBR\d{7}')
    bwbr_naar_idx = {w['identifier']: i for i, w in enumerate(index) if w.get('identifier')}
    verwijzingen = {}
    for i, item in enumerate(zoekindex_lijst):
        body = item.get('b', '')
        eigen_id = index[i].get('identifier', '') if i < len(index) else ''
        if not eigen_id:
            continue
        refs = set(bwbr_pat.findall(body))
        refs.discard(eigen_id)
        refs = [r for r in refs if r in bwbr_naar_idx]
        if refs:
            verwijzingen[eigen_id] = refs
    verw_pad = Path(args.verwijzingen)
    verw_pad.write_text(json.dumps(verwijzingen, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"verwijzingen.json: {verw_pad.stat().st_size/1024:.0f} KB ({len(verwijzingen)} wetten)")


if __name__ == "__main__":
    main()
