#!/usr/bin/env python3
"""
dekking.py — houdt de site naast de officiele BWB-lijst en meldt het verschil.

Dit ontbrak, en daardoor kon de vulling maandenlang stilvallen zonder dat
iemand het zag: de dagelijkse run committeerde alleen bij een wijziging in
wetten/, dus "geen wijzigingen" en "de bron is dood" zien er hetzelfde uit.

Levert dekking.json:
    {
      "gegenereerd": "2026-07-29",
      "bwb_geldend": 18549,          # regelingen die vandaag gelden volgens BWB
      "site_totaal": 19631,          # wetten in index.json
      "site_geldend": 17158,
      "dekkingsgraad": 0.925,        # geldende regelingen die de site heeft
      "ontbrekend": [...],           # geldend bij BWB, niet op de site
      "ten_onrechte_geldig": [...],  # op de site als geldig, vervallen bij BWB
      "onbekend": [...]              # op de site, niet in de BWB-lijst
    }

Exit 1 als de dekkingsgraad onder --faal-onder zakt of als de bron onbereikbaar
is. Dat laatste is met opzet: een stille bron is de fout die dit project al
eerder heeft gemaakt.

Gebruik:
    python scripts/dekking.py --index index.json --output dekking.json
    python scripts/dekking.py --faal-onder 0.98 --verifieer
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bwb_bron  # noqa: E402

log = logging.getLogger("dekking")

# Regelingsoorten die de site bewust niet spiegelt. Leeg houden betekent:
# alles wat BWB geldend noemt hoort erbij.
UITGESLOTEN_SOORTEN: set[str] = set()


def lees_index(pad: Path) -> list[dict]:
    with pad.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    p = argparse.ArgumentParser(description="Dekking van de site tegen de BWB-lijst")
    p.add_argument("--index", default="index.json")
    p.add_argument("--output", default="dekking.json")
    p.add_argument("--peildatum", help="Standaard vandaag")
    p.add_argument("--faal-onder", type=float, default=0.0,
                   help="Exit 1 als de dekkingsgraad hieronder zakt (bijv. 0.98)")
    p.add_argument("--verifieer", action="store_true",
                   help="Verschilverzameling tegen het manifest per regeling controleren "
                        "(trager, maar het manifest is de zwaarste bron)")
    p.add_argument("--verifieer-max", type=int, default=4000,
                   help="Maximaal aantal regelingen dat tegen het manifest gaat")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
    peildatum = args.peildatum or date.today().isoformat()

    try:
        regelingen = bwb_bron.alle_regelingen(peildatum)
    except bwb_bron.BronFout as e:
        log.error("BWB-bron onbereikbaar: %s", e)
        return 1
    if len(regelingen) < 30_000:
        log.error("BWB-lijst verdacht klein (%d regelingen) — bron waarschijnlijk stuk",
                  len(regelingen))
        return 1

    index = lees_index(Path(args.index))
    site = {w.get("identifier", ""): w for w in index if w.get("identifier")}
    site_ids = set(site)

    geldend = {i for i, r in regelingen.items()
               if r["geldend"] and r.get("type") not in UITGESLOTEN_SOORTEN}

    ontbrekend = sorted(geldend - site_ids)
    verdacht_vervallen = sorted(site_ids & set(regelingen) - geldend)
    onbekend = sorted(site_ids - set(regelingen))

    # De zoekservice geeft niet elke toestand terug; het manifest per regeling
    # wel. Alleen het verschil verifieren houdt dat betaalbaar.
    if args.verifieer:
        teverifieren = (ontbrekend + verdacht_vervallen + onbekend)[:args.verifieer_max]
        log.info("Manifest-controle op %d regelingen...", len(teverifieren))
        manifesten = bwb_bron.manifesten(teverifieren, peildatum)
        ontbrekend = [i for i in ontbrekend if manifesten.get(i, {}).get("geldend", True)]
        verdacht_vervallen = [i for i in verdacht_vervallen
                              if i in manifesten and not manifesten[i]["geldend"]]
        onbekend = [i for i in onbekend if i not in manifesten or not manifesten[i]["geldend"]]
        geldend = (geldend - set(t for t in teverifieren if t in manifesten
                                 and not manifesten[t]["geldend"]))
        geldend |= {t for t in teverifieren if manifesten.get(t, {}).get("geldend")}

    site_geldend = len(geldend & site_ids)
    graad = site_geldend / len(geldend) if geldend else 0.0

    rapport = {
        "gegenereerd": peildatum,
        # De zoekservice geeft niet elke toestand terug: in een steekproef van
        # 498 wetten die zij "vervallen" noemde, was 64% volgens het manifest
        # gewoon geldig. Zonder verificatie mag dit rapport dus nooit gebruikt
        # worden om status te overschrijven — zie vul_aan.py.
        "geverifieerd": bool(args.verifieer),
        "bwb_regelingen": len(regelingen),
        "bwb_geldend": len(geldend),
        "site_totaal": len(site_ids),
        "site_geldend": site_geldend,
        "dekkingsgraad": round(graad, 4),
        "aantal_ontbrekend": len(ontbrekend),
        "aantal_ten_onrechte_geldig": len(verdacht_vervallen),
        "aantal_onbekend": len(onbekend),
        "ontbrekend": [{"id": i,
                        "titel": regelingen[i]["titel"],
                        "type": regelingen[i]["type"]} for i in ontbrekend],
        "ten_onrechte_geldig": [{"id": i, "titel": site[i].get("titel", "")}
                                for i in verdacht_vervallen],
        "onbekend": [{"id": i, "titel": site[i].get("titel", "")} for i in onbekend],
    }

    Path(args.output).write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")

    log.info("BWB geldend: %d | site: %d | dekking: %.2f%%",
             len(geldend), len(site_ids), graad * 100)
    log.info("Ontbrekend: %d | ten onrechte geldig: %d | onbekend bij BWB: %d",
             len(ontbrekend), len(verdacht_vervallen), len(onbekend))

    if args.faal_onder and graad < args.faal_onder:
        log.error("Dekking %.4f ligt onder de drempel %.4f", graad, args.faal_onder)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
