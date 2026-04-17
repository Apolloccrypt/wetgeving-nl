#!/usr/bin/env python3
"""
seed_wetten.py — Vul de wetgeving-nl repo met echte Nederlandse wetten.

Strategie (in volgorde van makkelijk naar volledig):

  Fase 1 — Prioriteitswetten (snel, ~30 wetten, draait in minuten)
            Start hiermee: python seed_wetten.py --fase 1

  Fase 2 — Top-1000 meest geraadpleegde wetten via SRU-service
            python seed_wetten.py --fase 2

  Fase 3 — Alles via BWBIDLIST (alle ~45.000 regelingen, duurt uren)
            python seed_wetten.py --fase 3

Gebruik:
    python seed_wetten.py --fase 1
    python seed_wetten.py --fase 1 --dry-run     # Alleen printen, niet downloaden
    python seed_wetten.py --identifier BWBR0001840  # Één specifieke wet
"""

import argparse
import io
import logging
import re
import time
import unicodedata
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Optional

import requests

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("seed")

# ── Constanten ───────────────────────────────────────────────────────────────
REPO_BASE = "https://repository.officiele-overheidspublicaties.nl/BWB"
SRU_BASE  = "https://zoekservice.overheid.nl/sru/Search"
BWBIDLIST_URL = "https://repository.officiele-overheidspublicaties.nl/bwb/BWBIDLIST.zip"
REQUEST_DELAY = 0.4

# ── Fase 1: Prioriteitswetten ─────────────────────────────────────────────────
# De belangrijkste NL-wetten, direct aan de slag
PRIORITEITS_WETTEN = [
    # Staatsinrichting
    ("BWBR0001840", "Grondwet",                              "staatsinrichting"),
    ("BWBR0005537", "Gemeentewet",                           "staatsinrichting"),
    ("BWBR0005514", "Provinciewet",                          "staatsinrichting"),
    ("BWBR0006229", "Algemene wet bestuursrecht",            "bestuursrecht"),
    ("BWBR0001823", "Wet op de rechterlijke organisatie",    "staatsinrichting"),

    # Burgerlijk recht
    ("BWBR0002656", "Burgerlijk Wetboek Boek 1",             "burgerlijk-recht"),
    ("BWBR0003045", "Burgerlijk Wetboek Boek 2",             "burgerlijk-recht"),
    ("BWBR0005288", "Burgerlijk Wetboek Boek 3",             "burgerlijk-recht"),
    ("BWBR0005289", "Burgerlijk Wetboek Boek 6",             "burgerlijk-recht"),
    ("BWBR0005290", "Burgerlijk Wetboek Boek 7",             "burgerlijk-recht"),

    # Strafrecht
    ("BWBR0001854", "Wetboek van Strafrecht",                "strafrecht"),
    ("BWBR0001903", "Wetboek van Strafvordering",            "strafrecht"),

    # Arbeidsrecht
    ("BWBR0002014", "Wet minimumloon en minimumvakantiebijslag", "arbeidsrecht"),
    ("BWBR0010346", "Wet flexibel werken",                   "arbeidsrecht"),

    # Belastingrecht
    ("BWBR0002471", "Wet inkomstenbelasting 2001",           "belastingrecht"),
    ("BWBR0002672", "Wet op de omzetbelasting 1968",         "belastingrecht"),
    ("BWBR0011353", "Successiewet 1956",                     "belastingrecht"),

    # Sociaal recht
    ("BWBR0013021", "Wet werk en bijstand",                  "sociaal-recht"),
    ("BWBR0008796", "Wet op de arbeidsongeschiktheidsverzekering", "sociaal-recht"),
    ("BWBR0021335", "Wet maatschappelijke ondersteuning",    "sociaal-recht"),

    # Onderwijs
    ("BWBR0003420", "Wet op het primair onderwijs",          "onderwijs"),
    ("BWBR0002399", "Wet op het voortgezet onderwijs",       "onderwijs"),

    # Gezondheidszorg
    ("BWBR0011353", "Wet op de geneeskundige behandelingsovereenkomst", "gezondheidszorg"),
    ("BWBR0024919", "Wet publieke gezondheid",               "gezondheidszorg"),

    # Privacy & digitaal
    ("BWBR0040940", "Uitvoeringswet Algemene verordening gegevensbescherming", "digitaal"),
    ("BWBR0015807", "Wet bescherming persoonsgegevens",      "digitaal"),

    # Milieu
    ("BWBR0003245", "Wet milieubeheer",                      "milieu"),
    ("BWBR0006504", "Wet bodembescherming",                  "milieu"),

    # Verkeer
    ("BWBR0006622", "Wegenverkeerswet 1994",                 "verkeer"),
]

# ── Categorieën ──────────────────────────────────────────────────────────────
CATEGORIE_MAP = {
    "staatsinrichting": "Staatsinrichting en bestuur",
    "bestuursrecht": "Bestuursrecht",
    "burgerlijk-recht": "Burgerlijk recht",
    "strafrecht": "Strafrecht",
    "arbeidsrecht": "Arbeidsrecht",
    "belastingrecht": "Belastingrecht",
    "sociaal-recht": "Sociaal recht",
    "onderwijs": "Onderwijs",
    "gezondheidszorg": "Gezondheidszorg",
    "digitaal": "Digitaal en privacy",
    "milieu": "Milieu",
    "verkeer": "Verkeer",
    "internationaal-recht": "Internationaal recht",
    "overig": "Overig",
}


# ── Hulpfuncties ──────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:80]


def fetch(url: str, **kwargs) -> Optional[requests.Response]:
    for i in range(3):
        try:
            r = requests.get(url, timeout=30, **kwargs)
            r.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return r
        except requests.RequestException as e:
            log.warning(f"Poging {i+1}/3 mislukt ({url}): {e}")
            time.sleep(2 ** i)
    return None


# ── XML ophalen via de repository ─────────────────────────────────────────────

def haal_xml_op(identifier: str) -> Optional[str]:
    """
    Probeert de wet-XML op te halen via de BWB-repository.
    Probeert drie URL-patronen (de structuur varieert per wet).
    """
    prefix = identifier[:8]   # bv. BWBR0001 uit BWBR0001840

    url_opties = [
        # Patroon 1: directe XML-toestand (meest voorkomend)
        f"{REPO_BASE}/{identifier}/xml/{identifier}_xml.zip",
        # Patroon 2: via de repository-structuur
        f"{REPO_BASE}/{prefix}/{identifier}/xml/{identifier}_xml.zip",
        # Patroon 3: via wetten.overheid.nl als fallback
        f"https://wetten.overheid.nl/{identifier}/xml",
    ]

    for url in url_opties:
        r = fetch(url)
        if not r:
            continue

        # ZIP uitpakken
        if url.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    xml_bestanden = [n for n in z.namelist() if n.endswith(".xml") and "toestand" in n.lower()]
                    if not xml_bestanden:
                        xml_bestanden = [n for n in z.namelist() if n.endswith(".xml")]
                    if xml_bestanden:
                        return z.read(xml_bestanden[0]).decode("utf-8", errors="replace")
            except zipfile.BadZipFile:
                # Misschien is het toch gewone XML
                if r.text.strip().startswith("<"):
                    return r.text
        elif r.text.strip().startswith("<"):
            return r.text

    log.warning(f"⚠️  Geen XML gevonden voor {identifier}")
    return None


# ── WTI (Wetstechnische Informatie) ophalen voor metadata ─────────────────────

def haal_wti_op(identifier: str) -> dict:
    """Haal metadata op via de WTI-XML van een wet."""
    prefix = identifier[:8]
    url = f"{REPO_BASE}/{identifier}/xml/{identifier}_wti.zip"
    r = fetch(url)
    meta = {}

    if not r:
        return meta

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            wti_bestanden = [n for n in z.namelist() if "wti" in n.lower() and n.endswith(".xml")]
            if not wti_bestanden:
                return meta
            wti_xml = z.read(wti_bestanden[0]).decode("utf-8", errors="replace")

        root = ET.fromstring(wti_xml)
        for tag, sleutel in [
            ("officieleTitel", "titel"),
            ("citeertitel",    "citeertitel"),
            ("rechtsgebied",   "categorie"),
            ("datumInwerking", "publicatiedatum"),
            ("datumLaatsteWijziging", "laatste_update"),
        ]:
            el = root.find(f".//{tag}")
            if el is not None and el.text:
                meta[sleutel] = el.text.strip()

    except Exception as e:
        log.debug(f"WTI-fout voor {identifier}: {e}")

    return meta


# ── XML → Markdown ────────────────────────────────────────────────────────────

class BwbNaarMarkdown:
    """Converteert BWB-XML naar nette Markdown (schoner dan legalize-nl)."""

    def __init__(self, xml: str, identifier: str, meta_override: dict = None):
        self.identifier = identifier
        self.meta = meta_override or {}
        try:
            self.root = ET.fromstring(xml)
        except ET.ParseError as e:
            raise ValueError(f"Ongeldige XML: {e}")

    def _zoek(self, *tags: str) -> str:
        for tag in tags:
            el = self.root.find(f".//{tag}")
            if el is not None and el.text:
                return el.text.strip()
            # Probeer zonder namespace
            el = self.root.find(f"{{*}}{tag}")
            if el is not None and el.text:
                return el.text.strip()
        return ""

    def _tekst(self, el: Optional[ET.Element]) -> str:
        if el is None:
            return ""
        delen = []
        if el.text:
            delen.append(el.text.strip())
        for kind in el:
            deel = self._tekst(kind)
            if deel:
                delen.append(deel)
            if kind.tail and kind.tail.strip():
                delen.append(kind.tail.strip())
        return " ".join(filter(None, delen))

    def frontmatter(self, submap: str) -> str:
        titel      = self.meta.get("titel")      or self._zoek("officiele-titel", "officieleTitel", "citeertitel", "titel")
        citeertitel = self.meta.get("citeertitel") or self._zoek("citeertitel")
        categorie  = CATEGORIE_MAP.get(submap, self.meta.get("categorie", "Overig"))
        pub_datum  = self.meta.get("publicatiedatum") or self._zoek("publicatiedatum", "datumInwerking")
        upd_datum  = self.meta.get("laatste_update")  or self._zoek("datum-laatste-wijziging", "datumLaatsteWijziging")
        ingetrokken = self._zoek("datum-intrekking", "datumIntrekking")
        status     = "ingetrokken" if ingetrokken else "geldig"

        regels = ["---"]
        regels.append(f'title: "{titel or self.identifier}"')
        if citeertitel and citeertitel != titel:
            regels.append(f'citeertitel: "{citeertitel}"')
        regels.append(f'identifier: "{self.identifier}"')
        regels.append(f'categorie: "{categorie}"')
        if pub_datum:
            regels.append(f"publicatiedatum: {pub_datum[:10]}")
        if upd_datum:
            regels.append(f"laatste_update: {upd_datum[:10]}")
        regels.append(f"status: {status}")
        regels.append(f'bron: "https://wetten.overheid.nl/{self.identifier}"')
        regels.append("---")
        return "\n".join(regels)

    def _element_naar_md(self, el: ET.Element, diepte: int = 0) -> list[str]:
        tag = el.tag.split("}")[-1].lower()
        out = []

        if tag in ("hoofdstuk", "chapter", "titel", "boek"):
            kop_el = el.find(".//{*}kop") or el.find(".//{*}opschrift")
            kop = self._tekst(kop_el) if kop_el is not None else el.get("nr", "")
            niveau = "##" if tag in ("boek", "titel") else "##"
            out.append(f"\n{niveau} {kop}\n")
            for k in el:
                out.extend(self._element_naar_md(k, diepte + 1))

        elif tag in ("afdeling", "paragraaf", "subparagraaf", "section"):
            kop_el = el.find(".//{*}kop") or el.find(".//{*}opschrift")
            kop = self._tekst(kop_el) if kop_el is not None else el.get("nr", "")
            out.append(f"\n### {kop}\n")
            for k in el:
                out.extend(self._element_naar_md(k, diepte + 1))

        elif tag == "artikel":
            nr = el.get("nr", "?")
            # Zoek een echt opschrift (niet de eerste alinea)
            opschrift_el = el.find("{*}opschrift") or el.find(".//{*}rubriek")
            opschrift = ""
            if opschrift_el is not None:
                t = self._tekst(opschrift_el)
                if t and len(t) < 120:
                    opschrift = f" – {t}"
            out.append(f"\n#### Artikel {nr}{opschrift}\n")
            for k in el:
                k_tag = k.tag.split("}")[-1].lower()
                if k_tag not in ("opschrift", "rubriek"):
                    out.extend(self._element_naar_md(k, diepte + 1))

        elif tag == "lid":
            nr = el.get("nr", "")
            al_el = el.find("{*}al")
            tekst = self._tekst(al_el) if al_el is not None else ""
            if not tekst:
                # Probeer directe tekst
                tekst = el.text.strip() if el.text else ""
            prefix = f"{nr}." if nr else "-"
            if tekst:
                out.append(f"\n{prefix} {tekst}")
            for k in el:
                k_tag = k.tag.split("}")[-1].lower()
                if k_tag not in ("al",):
                    out.extend(self._element_naar_md(k, diepte + 1))

        elif tag in ("lijst", "list"):
            for item in el:
                item_tag = item.tag.split("}")[-1].lower()
                if item_tag in ("li", "lijstje", "onderdeel"):
                    letter = item.get("nr", "")
                    tekst = self._tekst(item)
                    prefix = f"   {letter}." if letter else "   -"
                    out.append(f"{prefix} {tekst}")

        elif tag == "al":
            tekst = self._tekst(el)
            if tekst:
                out.append(f"\n{tekst}")

        elif tag in ("kop", "opschrift", "rubriek", "intitule"):
            pass  # Afgehandeld door parent

        elif tag in ("aanhef", "preambule", "considerans"):
            tekst = self._tekst(el)
            if tekst:
                out.append(f"\n*{tekst}*\n")

        elif tag in ("table", "tabel", "plaatje", "afbeelding"):
            out.append(f"\n> *(tabel/afbeelding — zie [origineel](https://wetten.overheid.nl/{self.identifier}))*\n")

        elif tag in ("meta:metadata", "metadata", "wetciteer", "juridische-informatie"):
            pass  # Sla meta-blokken over

        else:
            tekst = self._tekst(el)
            if tekst and len(tekst) > 5:
                out.append(f"\n{tekst}")
            for k in el:
                out.extend(self._element_naar_md(k, diepte + 1))

        return out

    def naar_markdown(self, submap: str = "overig") -> str:
        fm = self.frontmatter(submap)

        titel = (
            self.meta.get("titel") or
            self._zoek("officiele-titel", "officieleTitel", "citeertitel")
            or self.identifier
        )

        # Zoek de wettekst (probeert meerdere bekende tags)
        wettekst = self.root.find(".//{*}wettekst")
        if wettekst is None:
            wettekst = self.root.find(".//{*}regeling-tekst")
        if wettekst is None:
            wettekst = self.root.find(".//{*}body")
        if wettekst is None:
            wettekst = self.root

        regels = [f"# {titel}\n"]
        for el in wettekst:
            regels.extend(self._element_naar_md(el))

        inhoud = "\n".join(regels)
        inhoud = re.sub(r"\n{3,}", "\n\n", inhoud)

        return fm + "\n\n" + inhoud.strip() + "\n"


# ── Opslaan ───────────────────────────────────────────────────────────────────

def opslaan(md: str, identifier: str, naam: str, submap: str, output_dir: Path) -> Path:
    pad = output_dir / submap
    pad.mkdir(parents=True, exist_ok=True)
    bestand = pad / (slugify(naam or identifier) + ".md")
    bestand.write_text(md, encoding="utf-8")
    return bestand


# ── BWBIDLIST ophalen (Fase 3) ─────────────────────────────────────────────────

def haal_alle_ids_op() -> list[str]:
    """Download BWBIDLIST.zip en geef alle BWBID's terug."""
    log.info("BWBIDLIST downloaden (~2MB)...")
    r = fetch(BWBIDLIST_URL)
    if not r:
        log.error("Kon BWBIDLIST niet downloaden.")
        return []
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            xml_naam = next(n for n in z.namelist() if n.endswith(".xml"))
            xml = z.read(xml_naam).decode("utf-8", errors="replace")
        root = ET.fromstring(xml)
        ids = [el.text.strip() for el in root.iter() if el.text and el.text.strip().startswith("BWBR")]
        log.info(f"{len(ids)} identifiers gevonden in BWBIDLIST.")
        return ids
    except Exception as e:
        log.error(f"BWBIDLIST-fout: {e}")
        return []


# ── SRU-zoekservice (Fase 2) ──────────────────────────────────────────────────

def zoek_via_sru(max_results: int = 1000) -> list[str]:
    """Haal populaire wetten op via de SRU-zoekservice (gesorteerd op relevantie)."""
    ids = []
    start = 1
    batch = 100
    log.info(f"SRU doorzoeken voor top-{max_results} wetten...")

    while len(ids) < max_results:
        params = {
            "operation": "searchRetrieve",
            "version": "1.2",
            "x-connection": "BWB",
            "query": "dcterms.type = wet",
            "maximumRecords": batch,
            "startRecord": start,
            "recordSchema": "dcterms",
        }
        r = fetch(SRU_BASE, params=params)
        if not r:
            break
        try:
            root = ET.fromstring(r.text)
            gevonden = [
                el.text.strip()
                for el in root.iter()
                if el.text and el.text.strip().startswith("BWBR") and "BWBR" == el.text.strip()[:4]
            ]
            if not gevonden:
                break
            ids.extend(gevonden)
            start += batch
        except Exception as e:
            log.warning(f"SRU-fout: {e}")
            break

    return ids[:max_results]


# ── Verwerk één wet ───────────────────────────────────────────────────────────

def verwerk_wet(identifier: str, naam: str, submap: str, output_dir: Path, dry_run: bool = False) -> bool:
    log.info(f"→ {identifier}  {naam or '(naam onbekend)'}")

    if dry_run:
        print(f"  [dry-run] Zou downloaden: {identifier}")
        return True

    xml = haal_xml_op(identifier)
    if not xml:
        return False

    try:
        conv = BwbNaarMarkdown(xml, identifier)
        md = conv.naar_markdown(submap)
        pad = opslaan(md, identifier, naam, submap, output_dir)
        log.info(f"  ✅  → {pad.relative_to(output_dir.parent)}")
        return True
    except Exception as e:
        log.error(f"  ❌  Conversiefout: {e}")
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Vul wetgeving-nl met echte wetten")
    p.add_argument("--output",      default="wetten/",      help="Output map")
    p.add_argument("--fase",        type=int, choices=[1,2,3], default=1,
                   help="1=prioriteit(~30), 2=SRU-top1000, 3=alles(~45k)")
    p.add_argument("--identifier",  help="Verwerk één specifieke wet")
    p.add_argument("--limit",       type=int, default=1000, help="Max voor fase 2/3")
    p.add_argument("--dry-run",     action="store_true",    help="Niet downloaden, alleen tonen")
    return p.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    fout = 0

    if args.identifier:
        wetten = [(args.identifier, "", "overig")]
    elif args.fase == 1:
        log.info(f"=== FASE 1: {len(PRIORITEITS_WETTEN)} prioriteitswetten ===")
        wetten = PRIORITEITS_WETTEN
    elif args.fase == 2:
        log.info(f"=== FASE 2: SRU top-{args.limit} ===")
        ids = zoek_via_sru(args.limit)
        wetten = [(i, "", "overig") for i in ids]
    else:
        log.info("=== FASE 3: Alle wetten via BWBIDLIST ===")
        ids = haal_alle_ids_op()
        wetten = [(i, "", "overig") for i in ids[:args.limit]]

    for identifier, naam, submap in wetten:
        if verwerk_wet(identifier, naam, submap, output_dir, dry_run=args.dry_run):
            ok += 1
        else:
            fout += 1

    log.info(f"\n{'='*50}")
    log.info(f"Klaar: {ok} succesvol, {fout} mislukt, {date.today()}")
    log.info(f"Wetten staan in: {output_dir.resolve()}")

    if not args.dry_run and ok > 0:
        log.info("\nVolgende stap: git add wetten/ && git commit -m '⚖️ Initiële vulling'")


if __name__ == "__main__":
    main()


# ── Basisset support (KOOP download) ─────────────────────────────────────────

def verwerk_basisset(basisset_pad: Path, output_dir: Path):
    """
    Verwerk de KOOP basisset (uitgepakte map met BWB-XML bestanden).
    Gebruik na ontvangst van de KOOP downloadlink:
        python seed_wetten.py --basisset /pad/naar/BWB/ --output wetten/
    """
    ok = 0
    fout = 0
    xml_bestanden = list(basisset_pad.rglob("*_xml.zip")) + list(basisset_pad.rglob("*.xml"))
    log.info(f"Basisset: {len(xml_bestanden)} bestanden gevonden in {basisset_pad}")

    for xml_pad in xml_bestanden:
        naam = xml_pad.stem.replace("_xml", "")
        if not naam.startswith("BWBR"):
            continue
        try:
            if xml_pad.suffix == ".zip":
                with zipfile.ZipFile(xml_pad) as z:
                    xml_namen = [n for n in z.namelist() if n.endswith(".xml")]
                    if not xml_namen:
                        continue
                    xml_content = z.read(xml_namen[0]).decode("utf-8", errors="replace")
            else:
                xml_content = xml_pad.read_text(encoding="utf-8", errors="replace")

            conv = BwbNaarMarkdown(xml_content, naam)
            md = conv.naar_markdown("overig")
            submap = "overig"
            for regel in md.split("\n"):
                if regel.startswith("categorie:"):
                    cat_waarde = regel.split(":", 1)[1].strip().strip('"')
                    for slug, voluit in CATEGORIE_MAP.items():
                        if voluit == cat_waarde:
                            submap = slug
                            break
            opslaan(md, naam, naam, submap, output_dir)
            ok += 1
            if ok % 100 == 0:
                log.info(f"  {ok} wetten verwerkt...")
        except Exception as e:
            log.debug(f"Fout bij {naam}: {e}")
            fout += 1

    log.info(f"Basisset klaar: {ok} succesvol, {fout} mislukt")
