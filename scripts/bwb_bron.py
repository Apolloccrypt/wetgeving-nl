#!/usr/bin/env python3
"""
bwb_bron.py — de officiele BWB-bron, in een module.

Twee routes die de rest van de pijplijn gebruikte zijn stilzwijgend dood:

  1. https://repository.officiele-overheidspublicaties.nl/bwb/BWBIDLIST.zip
     (bron voor "alle regelingen" in seed_wetten.py fase 3) -> HTTP 204, leeg.
  2. .../BWB/<id>/xml/<id>_xml.zip
     (bron voor de wettekst in dagelijkse_update.py)        -> HTTP 204, leeg.

Allebei geven 204 No Content in plaats van een fout, dus geen enkele
retry-lus merkte het. De update viel daardoor elke dag terug op legalize-nl,
een repo van een derde partij, en de volledige vulling heeft nooit gedraaid.

Dit zijn de routes die wel werken:

  * SRU-zoekservice          -> alle regelingen met hun toestanden
  * .../bwb/<id>/            -> manifest per regeling (toestanden + XML-paden)
  * .../bwb/<id>/<toestand>/xml/<id>_<toestand>.xml -> de wettekst zelf

Gebruik als CLI:
    python scripts/bwb_bron.py --lijst bwb_regelingen.json
    python scripts/bwb_bron.py --manifest BWBR0001840
    python scripts/bwb_bron.py --tekst BWBR0001840 > grondwet.xml
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Iterable, Optional

import requests

log = logging.getLogger("bwb_bron")

SRU_URL = "https://zoekservice.overheid.nl/sru/Search"
REPO_BASE = "https://repository.officiele-overheidspublicaties.nl/bwb"

SRU_BATCH = 1000          # maximum dat de dienst per verzoek teruggeeft
SRU_WERKERS = 6           # gelijktijdige SRU-verzoeken
REPO_WERKERS = 12         # gelijktijdige manifest-verzoeken
TIMEOUT = 60

_EXPRESSIE = re.compile(r'<expression label="([^"]+)"><metadata>(.*?)</metadata>', re.S)
_RECORD = re.compile(r"<record>(.*?)</record>", re.S)


class BronFout(RuntimeError):
    """De officiele bron gaf geen bruikbaar antwoord."""


def _haal(url: str, params: Optional[dict] = None, pogingen: int = 4) -> Optional[requests.Response]:
    """Haal een URL op met retry. Behandelt 204 (leeg) expliciet als mislukking,
    want dat is precies hoe de oude bronnen stilletjes stierven."""
    for poging in range(pogingen):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 204 or not r.content:
                log.debug("Leeg antwoord (204) van %s", url)
                return None
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if poging == pogingen - 1:
                log.debug("Mislukt na %d pogingen: %s (%s)", pogingen, url, e)
            time.sleep(2 ** poging)
    return None


def _veld(blok: str, tag: str) -> str:
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", blok)
    return m.group(1).strip() if m else ""


# ── 1. De volledige regelingenlijst via SRU ──────────────────────────────────

def sru_aantal() -> int:
    """Hoeveel toestanden kent de BWB-zoekservice op dit moment?"""
    r = _haal(SRU_URL, {
        "x-connection": "BWB", "operation": "searchRetrieve", "version": "1.2",
        "query": "cql.allRecords=1", "maximumRecords": 1,
    })
    if not r:
        raise BronFout("SRU-zoekservice gaf geen antwoord")
    m = re.search(r"numberOfRecords>(\d+)", r.text)
    if not m:
        raise BronFout("SRU-antwoord zonder numberOfRecords")
    return int(m.group(1))


def _sru_pagina(start: int) -> list[dict]:
    r = _haal(SRU_URL, {
        "x-connection": "BWB", "operation": "searchRetrieve", "version": "1.2",
        "query": "cql.allRecords=1", "maximumRecords": SRU_BATCH, "startRecord": start,
    })
    if not r:
        return []
    rijen = []
    for blok in _RECORD.findall(r.text):
        ident = _veld(blok, "dcterms:identifier")
        if not ident.startswith("BWB"):
            continue
        rijen.append({
            "id": ident,
            "titel": _veld(blok, "dcterms:title"),
            "type": _veld(blok, "dcterms:type"),
            "gezag": _veld(blok, "overheid:authority"),
            "start": _veld(blok, "overheidbwb:geldigheidsperiode_startdatum"),
            "eind": _veld(blok, "overheidbwb:geldigheidsperiode_einddatum"),
            "gewijzigd": _veld(blok, "dcterms:modified"),
        })
    return rijen


def alle_regelingen(peildatum: Optional[str] = None) -> dict[str, dict]:
    """Alle BWB-regelingen met hun laatst bekende toestand.

    Geeft {identifier: {titel, type, gezag, start, eind, geldend}}.
    De zoekservice levert toestanden (een regeling heeft er vele); die worden
    hier tot een kaart per regeling samengevouwen.
    """
    peildatum = peildatum or date.today().isoformat()
    totaal = sru_aantal()
    starts = list(range(1, totaal + 1, SRU_BATCH))
    log.info("SRU: %d toestanden in %d pagina's ophalen...", totaal, len(starts))

    regelingen: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=SRU_WERKERS) as ex:
        for rijen in ex.map(_sru_pagina, starts):
            for rij in rijen:
                huidig = regelingen.get(rij["id"])
                # bewaar de toestand met de laatste startdatum die al is ingegaan
                if huidig is None or (rij["start"] or "") > (huidig["start"] or ""):
                    if rij["start"] and rij["start"] > peildatum and huidig is not None:
                        continue  # toekomstige toestand telt niet als de actuele
                    regelingen[rij["id"]] = rij

    for rij in regelingen.values():
        eind = rij.get("eind") or ""
        rij["geldend"] = eind in ("", "9999-12-31") or eind >= peildatum

    log.info("SRU: %d unieke regelingen, %d geldend op %s",
             len(regelingen), sum(1 for r in regelingen.values() if r["geldend"]), peildatum)
    return regelingen


# ── 2. Het manifest per regeling ─────────────────────────────────────────────

def manifest(identifier: str, peildatum: Optional[str] = None) -> Optional[dict]:
    """De actuele toestand van een regeling volgens haar eigen manifest.

    Dit is de zwaarste bron van waarheid die er is: het manifest komt van de
    uitgever zelf en noemt elke toestand met inwerkingtredings- en einddatum.
    """
    peildatum = peildatum or date.today().isoformat()
    r = _haal(f"{REPO_BASE}/{identifier}/")
    if not r or "<work" not in r.text:
        return None

    toestanden = []
    for label, meta in _EXPRESSIE.findall(r.text):
        toestanden.append({
            "label": label,
            "start": _veld(meta, "datum_inwerkingtreding"),
            "eind": _veld(meta, "einddatum"),
        })
    if not toestanden:
        return None

    op_volgorde = sorted(toestanden, key=lambda t: t["start"] or "")
    actueel = None
    for t in op_volgorde:
        if t["start"] and t["start"] <= peildatum:
            actueel = t
    if actueel is None:
        actueel = op_volgorde[0]

    eind = actueel["eind"]
    return {
        "id": identifier,
        "toestand": actueel["label"],
        "ingegaan": actueel["start"],
        "eind": eind,
        "geldend": eind in ("", "9999-12-31") or eind >= peildatum,
        "aantal_toestanden": len(toestanden),
        "xml_url": f"{REPO_BASE}/{identifier}/{actueel['label']}/xml/{identifier}_{actueel['label']}.xml",
    }


def manifesten(identifiers: Iterable[str], peildatum: Optional[str] = None,
               werkers: int = REPO_WERKERS) -> dict[str, dict]:
    """Manifesten van veel regelingen tegelijk."""
    ids = list(identifiers)
    uit: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=werkers) as ex:
        for ident, m in zip(ids, ex.map(lambda i: manifest(i, peildatum), ids)):
            if m:
                uit[ident] = m
    return uit


# ── 3. De wettekst zelf ──────────────────────────────────────────────────────

def haal_wettekst(identifier: str, peildatum: Optional[str] = None) -> Optional[tuple[str, dict]]:
    """De XML van de actuele toestand van een regeling.

    Geeft (xml, manifestkaart), of None als de regeling niet op te halen is.
    """
    m = manifest(identifier, peildatum)
    if not m:
        return None
    r = _haal(m["xml_url"])
    if not r:
        # sommige regelingen hebben een afwijkend toestandslabel; probeer
        # het pad dat het manifest zelf als _latestItem noemt
        log.debug("XML niet gevonden op %s", m["xml_url"])
        return None
    return r.text, m


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Officiele BWB-bron bevragen")
    p.add_argument("--lijst", metavar="UIT.JSON",
                   help="Alle regelingen ophalen en als JSON wegschrijven")
    p.add_argument("--manifest", metavar="BWBR...", help="Manifest van een regeling tonen")
    p.add_argument("--tekst", metavar="BWBR...", help="XML van de actuele toestand tonen")
    p.add_argument("--peildatum", help="Peildatum voor geldigheid (standaard vandaag)")
    p.add_argument("--stil", action="store_true", help="Alleen fouten loggen")
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING if args.stil else logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")

    if args.lijst:
        regelingen = alle_regelingen(args.peildatum)
        with open(args.lijst, "w", encoding="utf-8") as f:
            json.dump(regelingen, f, ensure_ascii=False)
        print(f"{len(regelingen)} regelingen -> {args.lijst}")
        return 0

    if args.manifest:
        m = manifest(args.manifest, args.peildatum)
        if not m:
            print(f"Geen manifest voor {args.manifest}", file=sys.stderr)
            return 1
        print(json.dumps(m, ensure_ascii=False, indent=2))
        return 0

    if args.tekst:
        res = haal_wettekst(args.tekst, args.peildatum)
        if not res:
            print(f"Geen wettekst voor {args.tekst}", file=sys.stderr)
            return 1
        print(res[0])
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
