#!/usr/bin/env python3
"""
genereer_feeds.py — Atom-feeds van recente wetswijzigingen.

Schrijft feed.xml (alle wijzigingen) en feed/<rechtsgebied>.xml per categorie,
op basis van changelog.json. Geen externe afhankelijkheden.

Gebruik:
    python scripts/genereer_feeds.py --changelog changelog.json --output-dir .
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path

BASIS = "https://vrijewetgeving.nl"


def x(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "overig"


def feed(titel, self_url, items):
    bijgewerkt = (items[0]["datum"] if items else date.today().isoformat()) + "T00:00:00Z"
    regels = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"<title>{x(titel)}</title>",
        f'<link href="{BASIS}/"/>',
        f'<link rel="self" href="{x(self_url)}"/>',
        f"<id>{x(self_url)}</id>",
        f"<updated>{bijgewerkt}</updated>",
        "<author><name>vrijewetgeving.nl</name></author>",
    ]
    for w in items:
        url = f"{BASIS}/wet.html?id={w['identifier']}"
        regels += [
            "<entry>",
            f"<title>[{w['actie']}] {x(w['titel'])}</title>",
            f'<link href="{url}"/>',
            f"<id>{url}#{w['datum']}</id>",
            f"<updated>{w['datum']}T00:00:00Z</updated>",
            f'<category term="{x(w.get("categorie",""))}"/>',
            f"<summary>{x(w['type'])} — {w['actie']} op {w['datum']}</summary>",
            "</entry>",
        ]
    regels.append("</feed>")
    return "\n".join(regels)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--changelog", default="changelog.json")
    p.add_argument("--output-dir", default=".")
    args = p.parse_args()

    cl = json.loads(Path(args.changelog).read_text(encoding="utf-8"))
    items = cl.get("recent", [])
    uit = Path(args.output_dir)

    (uit / "feed.xml").write_text(
        feed("vrijewetgeving.nl — recente wetswijzigingen", f"{BASIS}/feed.xml", items),
        encoding="utf-8")

    feeddir = uit / "feed"
    feeddir.mkdir(exist_ok=True)
    per_cat = {}
    for w in items:
        per_cat.setdefault(w.get("categorie", "Overig"), []).append(w)
    for cat, ws in per_cat.items():
        s = slug(cat)
        (feeddir / f"{s}.xml").write_text(
            feed(f"vrijewetgeving.nl — {cat}", f"{BASIS}/feed/{s}.xml", ws),
            encoding="utf-8")

    print(f"feed.xml ({len(items)} items) + {len(per_cat)} categorie-feeds")


if __name__ == "__main__":
    main()
