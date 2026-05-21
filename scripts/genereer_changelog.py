#!/usr/bin/env python3
"""
genereer_changelog.py — Bouw changelog.json voor de wet-radar op de homepage.

Leest de Git-historie van wetten/ en koppelt gewijzigde bestanden via index.json
aan wet-titels. Geeft tellingen (vandaag / deze week / deze maand) en een lijst
van recent nieuwe of gewijzigde wetten.

Gebruik (vanuit de repo-root):
    python scripts/genereer_changelog.py --index index.json --output changelog.json --dagen 60
"""

import argparse
import json
import subprocess
from datetime import date, timedelta
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index",  default="index.json")
    p.add_argument("--output", default="changelog.json")
    p.add_argument("--dagen",  type=int, default=60)
    p.add_argument("--max",    type=int, default=60)
    p.add_argument("--repo",   default=".")
    args = p.parse_args()

    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    pad2wet = {w["pad"]: w for w in index}

    sinds = (date.today() - timedelta(days=args.dagen)).isoformat()
    log = subprocess.run(
        ["git", "log", f"--since={sinds}", "--name-status", "--date=short",
         "--pretty=format:C|%ad", "--", "wetten/"],
        capture_output=True, text=True, cwd=args.repo,
    ).stdout

    huidige = None
    gezien = {}  # identifier -> record (eerste voorkomen = meest recent)
    for regel in log.splitlines():
        if regel.startswith("C|"):
            huidige = regel[2:].strip()
        elif regel and regel[0] in "AMRD":
            velden = regel.split("\t")
            status, pad = velden[0], velden[-1].strip()
            if status.startswith("D"):
                continue
            w = pad2wet.get(pad)
            if not w or not w.get("identifier"):
                continue
            bid = w["identifier"]
            if bid in gezien:
                continue
            gezien[bid] = {
                "identifier": bid,
                "titel": w.get("titel", ""),
                "type": w.get("type", ""),
                "categorie": w.get("categorie", ""),
                "datum": huidige,
                "actie": "nieuw" if status.startswith("A") else "gewijzigd",
            }

    recent = list(gezien.values())  # git log is al nieuw->oud
    vandaag = date.today()

    def binnen(n):
        c = 0
        for x in recent:
            try:
                if (vandaag - date.fromisoformat(x["datum"])).days < n:
                    c += 1
            except ValueError:
                pass
        return c

    changelog = {
        "gegenereerd": vandaag.isoformat(),
        "vandaag":    binnen(1),
        "deze_week":  binnen(7),
        "deze_maand": binnen(30),
        "totaal_periode": len(recent),
        "recent": recent[: args.max],
    }
    Path(args.output).write_text(json.dumps(changelog, ensure_ascii=False), encoding="utf-8")
    print(f"changelog.json: vandaag={changelog['vandaag']} week={changelog['deze_week']} "
          f"maand={changelog['deze_maand']} (lijst {len(changelog['recent'])})")


if __name__ == "__main__":
    main()
