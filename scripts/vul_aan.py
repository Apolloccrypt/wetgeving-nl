#!/usr/bin/env python3
"""
vul_aan.py — brengt wetten/ naar de stand van de officiele BWB-lijst.

Drie taken, los aan te roepen:

  --ontbrekend N   regelingen die BWB geldend noemt en de site niet heeft
  --ververs N      wetten die het langst niet van de officiele bron kwamen
                   opnieuw ophalen (de bestaande set komt uit legalize-nl en
                   loopt achter: vervallen artikelen staan er nog in)
  --status         status van vervallen regelingen bijwerken zonder de hele
                   tekst opnieuw op te halen

De bron levert ongeveer twee regelingen per seconde en knijpt af boven ~24
gelijktijdige verbindingen. Daarom is dit werk per run begrensd: de dagelijkse
workflow doet elke dag een schijf, en de achterstand loopt zichtbaar terug in
dekking.json in plaats van in een enkele run van uren.

Gebruik:
    python scripts/vul_aan.py --ontbrekend 500 --dekking dekking.json
    python scripts/vul_aan.py --ververs 400
    python scripts/vul_aan.py --status --dekking dekking.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bwb_bron          # noqa: E402
import bwb_markdown      # noqa: E402
from dagelijkse_update import bouw_id_index, sla_op, _id_naar_pad, _lees_identifier  # noqa: E402

log = logging.getLogger("vul_aan")

WERKERS = 12


def _frontmatter(pad: Path) -> dict:
    """De frontmatter van een wetbestand als losse regels (geen yaml nodig)."""
    try:
        with pad.open(encoding="utf-8", errors="replace") as f:
            kop = f.read(4096)
    except OSError:
        return {}
    if not kop.startswith("---"):
        return {}
    eind = kop.find("\n---", 3)
    if eind < 0:
        return {}
    uit = {}
    for regel in kop[3:eind].split("\n"):
        if ":" in regel:
            sleutel, waarde = regel.split(":", 1)
            uit[sleutel.strip()] = waarde.strip().strip('"')
    return uit


def haal_en_schrijf(identifier: str, output_dir: Path) -> tuple[str, bool, str]:
    """Haal een regeling op en schrijf hem weg. Geeft (id, gelukt, reden)."""
    try:
        res = bwb_bron.haal_wettekst(identifier)
    except Exception as e:                      # netwerk, parser, van alles
        return identifier, False, f"fout: {e}"
    if not res:
        return identifier, False, "geen wettekst bij de bron"
    xml, kaart = res
    md = bwb_markdown.converteer(xml, identifier, kaart)
    if not md:
        return identifier, False, "conversie leverde niets op"
    sla_op(md, identifier, output_dir)
    return identifier, True, "vervallen" if not kaart["geldend"] else "geldig"


def verwerk(ids: list[str], output_dir: Path, wat: str) -> int:
    if not ids:
        log.info("%s: niets te doen", wat)
        return 0
    log.info("%s: %d regelingen ophalen...", wat, len(ids))
    ok = mislukt = 0
    with ThreadPoolExecutor(max_workers=WERKERS) as ex:
        for i, (ident, gelukt, reden) in enumerate(
                ex.map(lambda x: haal_en_schrijf(x, output_dir), ids), 1):
            if gelukt:
                ok += 1
            else:
                mislukt += 1
                log.debug("  %s overgeslagen: %s", ident, reden)
            if i % 100 == 0:
                log.info("  %d/%d (%d gelukt, %d mislukt)", i, len(ids), ok, mislukt)
    log.info("%s klaar: %d gelukt, %d mislukt", wat, ok, mislukt)
    return ok


def zet_status_vervallen(identifier: str, pad: Path, eind: str) -> bool:
    """Zet de status in de frontmatter op vervallen, zonder de tekst aan te raken."""
    try:
        inhoud = pad.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if not inhoud.startswith("---"):
        return False
    grens = inhoud.find("\n---", 3)
    if grens < 0:
        return False
    kop, rest = inhoud[:grens], inhoud[grens:]
    if re.search(r"^status:\s*(vervallen|ingetrokken)\s*$", kop, re.M):
        return False
    if re.search(r"^status:", kop, re.M):
        kop = re.sub(r"^status:.*$", "status: vervallen", kop, count=1, flags=re.M)
    else:
        kop += "\nstatus: vervallen"
    if eind and not re.search(r"^vervallen_op:", kop, re.M):
        kop += f"\nvervallen_op: {eind[:10]}"
    if not re.search(r"^gecontroleerd:", kop, re.M):
        kop += f"\ngecontroleerd: {date.today().isoformat()}"
    pad.write_text(kop + rest, encoding="utf-8")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="wetten/ bijwerken naar de officiele stand")
    p.add_argument("--output", default="wetten/")
    p.add_argument("--dekking", default="dekking.json")
    p.add_argument("--ontbrekend", type=int, metavar="N",
                   help="Maximaal N ontbrekende regelingen toevoegen")
    p.add_argument("--ververs", type=int, metavar="N",
                   help="De N langst niet ververste wetten opnieuw ophalen")
    p.add_argument("--status", action="store_true",
                   help="Status van vervallen regelingen bijwerken")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    bouw_id_index(output_dir)

    dekking = {}
    dekkingspad = Path(args.dekking)
    if dekkingspad.exists():
        dekking = json.loads(dekkingspad.read_text(encoding="utf-8"))
    elif args.ontbrekend is not None or args.status:
        log.error("%s ontbreekt — draai eerst scripts/dekking.py", dekkingspad)
        return 1

    totaal = 0

    # Let op: 0 is een geldige opdracht ("doe deze stap niet"), geen ontbrekende
    # opdracht. Vandaar overal 'is not None' en niet de waarheidswaarde.
    if args.ontbrekend is not None:
        ids = [w["id"] for w in dekking.get("ontbrekend", [])][:args.ontbrekend]
        totaal += verwerk(ids, output_dir, "Ontbrekend")

    if args.status:
        # Een wet ten onrechte op "vervallen" zetten is erger dan hem laten
        # staan: de site zou dan geldend recht als ingetrokken tonen. De
        # zoekservice alleen is daarvoor niet betrouwbaar genoeg.
        if not dekking.get("geverifieerd"):
            log.error("dekking.json is niet geverifieerd tegen het manifest; "
                      "draai scripts/dekking.py --verifieer voordat je status bijwerkt")
            return 1
        bijgewerkt = 0
        for w in dekking.get("ten_onrechte_geldig", []):
            pad = _id_naar_pad.get(w["id"])
            if pad and zet_status_vervallen(w["id"], pad, w.get("eind", "")):
                bijgewerkt += 1
        log.info("Status: %d wetten op vervallen gezet", bijgewerkt)
        totaal += bijgewerkt

    if args.ververs is not None:
        # oudste eerst: wetten zonder 'opgehaald' komen nog uit de legalize-seed
        kandidaten = []
        for pad in output_dir.rglob("*.md"):
            fm = _frontmatter(pad)
            ident = fm.get("identifier", "")
            if not ident.startswith("BWB"):
                continue
            kandidaten.append((fm.get("opgehaald", ""), ident))
        kandidaten.sort()
        ids = [ident for _, ident in kandidaten[:args.ververs]]
        nooit = sum(1 for stempel, _ in kandidaten if not stempel)
        log.info("Verversing: %d wetten kwamen nog nooit van de officiele bron", nooit)
        totaal += verwerk(ids, output_dir, "Verversen")

    if args.ontbrekend is None and args.ververs is None and not args.status:
        p.print_help()
        return 1

    log.info("Totaal %d wetten aangeraakt", totaal)
    return 0


if __name__ == "__main__":
    sys.exit(main())
