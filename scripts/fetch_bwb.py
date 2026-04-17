#!/usr/bin/env python3
"""
fetch_bwb.py — Haal Nederlandse wetten op uit het Basis Wetten Bestand (BWB)
en converteer ze naar nette Markdown met YAML-frontmatter.

Gebruik:
    python fetch_bwb.py --output wetten/ --limit 10
    python fetch_bwb.py --identifier BWBR0001840  # Alleen de Grondwet
    python fetch_bwb.py --categorie Staatsinrichting

Data-bron: https://repository.officiele-overheidspublicaties.nl/BWB/
Licentie data: CC0 (Publiek domein)
"""

import argparse
import logging
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import requests

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bwb")

# ── Constanten ───────────────────────────────────────────────────────────────
BWB_REPO_BASE = "https://repository.officiele-overheidspublicaties.nl/BWB"
WETTEN_API = "https://wetten.overheid.nl/api/v1"
REQUEST_DELAY = 0.5          # Seconden tussen requests (beleefd scrapen)
MAX_RETRIES = 3

# Mapping BWB categorie → mapnaam in de repo
CATEGORIE_MAP = {
    "Staatsinrichting en bestuur": "staatsinrichting",
    "Burgerlijk recht": "burgerlijk-recht",
    "Strafrecht": "strafrecht",
    "Bestuursrecht": "bestuursrecht",
    "Arbeidsrecht": "arbeidsrecht",
    "Belastingrecht": "belastingrecht",
    "Sociaal recht": "sociaal-recht",
    "Internationaal recht": "internationaal-recht",
    "Overig": "overig",
}

# BWB XML namespaces
NS = {
    "bwb": "http://www.bwb.overheid.nl/bwb/",
    "tekst": "http://www.bwb.overheid.nl/bwb/tekst/",
    "meta": "http://www.bwb.overheid.nl/bwb/meta/",
}


# ── Hulpfuncties ─────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Zet een willekeurige string om naar een bestandsnaam-vriendelijke slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80]  # Max bestandsnaamlengte


def fetch_with_retry(url: str, **kwargs) -> Optional[requests.Response]:
    """Haal een URL op met retry-logica."""
    for poging in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=30, **kwargs)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return resp
        except requests.RequestException as e:
            wacht = 2 ** poging
            log.warning(f"Poging {poging+1}/{MAX_RETRIES} mislukt voor {url}: {e}. Wacht {wacht}s...")
            time.sleep(wacht)
    log.error(f"Kon {url} niet ophalen na {MAX_RETRIES} pogingen.")
    return None


# ── BWB XML → Markdown converter ─────────────────────────────────────────────

class BwbConverter:
    """Converteert een BWB XML-bestand naar nette Markdown."""

    def __init__(self, xml_content: str, identifier: str):
        self.identifier = identifier
        try:
            self.root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Ongeldige XML voor {identifier}: {e}")

    def _tekst(self, element: Optional[ET.Element]) -> str:
        """Haal alle tekst recursief op uit een XML-element."""
        if element is None:
            return ""
        parts = []
        if element.text:
            parts.append(element.text.strip())
        for child in element:
            parts.append(self._tekst(child))
            if child.tail:
                parts.append(child.tail.strip())
        return " ".join(filter(None, parts))

    def _meta_waarde(self, *tags: str) -> str:
        """Zoek een meta-waarde in de XML (probeert meerdere tags)."""
        for tag in tags:
            for ns_prefix in ("bwb:", "meta:", ""):
                elem = self.root.find(f".//{ns_prefix}{tag}", NS)
                if elem is not None and elem.text:
                    return elem.text.strip()
        return ""

    def _frontmatter(self) -> str:
        """Genereer YAML-frontmatter zoals de Spaanse versie."""
        titel = self._meta_waarde("officiele-titel", "citeertitel", "titel")
        citeertitel = self._meta_waarde("citeertitel")
        categorie = self._meta_waarde("rechtsgebied", "categorie")
        pub_datum = self._meta_waarde("publicatiedatum", "datum-inwerkingtreding")
        update_datum = self._meta_waarde("datum-laatste-wijziging", "tijdstip-laatste-wijziging")
        bron_url = f"https://wetten.overheid.nl/{self.identifier}"

        # Status bepalen
        ingetrokken = self._meta_waarde("datum-intrekking", "intrekking")
        status = "ingetrokken" if ingetrokken else "geldig"

        lines = ["---"]
        lines.append(f'title: "{titel or self.identifier}"')
        if citeertitel and citeertitel != titel:
            lines.append(f'citeertitel: "{citeertitel}"')
        lines.append(f'identifier: "{self.identifier}"')
        if categorie:
            lines.append(f'categorie: "{categorie}"')
        if pub_datum:
            lines.append(f"publicatiedatum: {pub_datum[:10]}")
        if update_datum:
            lines.append(f"laatste_update: {update_datum[:10]}")
        lines.append(f"status: {status}")
        lines.append(f'bron: "{bron_url}"')
        lines.append("---")
        return "\n".join(lines)

    def _converteer_element(self, element: ET.Element, diepte: int = 0) -> list[str]:
        """
        Recursief een XML-element omzetten naar Markdown-regels.
        Herkent de standaard BWB-structuur: hoofdstuk, afdeling, artikel, lid, etc.
        """
        regels = []
        tag = element.tag.split("}")[-1].lower()  # Verwijder namespace-prefix

        # ── Structuurelementen ───────────────────────────────────────────
        if tag in ("hoofdstuk", "chapter"):
            opschrift = self._tekst(element.find(".//{*}kop")) or \
                        self._tekst(element.find(".//{*}opschrift")) or \
                        element.get("nr", "")
            regels.append(f"\n## {opschrift}\n")
            for kind in element:
                regels.extend(self._converteer_element(kind, diepte + 1))

        elif tag in ("afdeling", "paragraaf", "section"):
            opschrift = self._tekst(element.find(".//{*}kop")) or \
                        self._tekst(element.find(".//{*}opschrift")) or \
                        element.get("nr", "")
            regels.append(f"\n### {opschrift}\n")
            for kind in element:
                regels.extend(self._converteer_element(kind, diepte + 1))

        elif tag == "artikel":
            nr = element.get("nr", "?")
            opschrift_el = element.find(".//{*}al")
            if opschrift_el is None:
                opschrift_el = element.find(".//{*}opschrift")
            opschrift = ""
            if opschrift_el is not None:
                tekst = self._tekst(opschrift_el)
                # Detecteer of het echt een opschrift is (kort, geen punt aan het eind)
                if len(tekst) < 100 and not tekst.endswith("."):
                    opschrift = f" – {tekst}"

            regels.append(f"\n#### Artikel {nr}{opschrift}\n")
            for kind in element:
                regels.extend(self._converteer_element(kind, diepte + 1))

        elif tag == "lid":
            nr = element.get("nr", "")
            tekst_el = element.find("{*}al")
            if tekst_el is None:
                tekst_el = element.find(".//{*}al")
            tekst = self._tekst(tekst_el) if tekst_el is not None else self._tekst(element)
            if nr:
                regels.append(f"\n{nr}. {tekst}")
            else:
                regels.append(f"\n{tekst}")
            for kind in element:
                if kind.tag.split("}")[-1].lower() not in ("al",):
                    regels.extend(self._converteer_element(kind, diepte + 1))

        elif tag in ("lijst", "list"):
            for onderdeel in element:
                sub_tag = onderdeel.tag.split("}")[-1].lower()
                if sub_tag in ("li", "lijstje", "onderdeel"):
                    letter = onderdeel.get("nr", "")
                    tekst = self._tekst(onderdeel)
                    prefix = f"   {letter}." if letter else "   -"
                    regels.append(f"{prefix} {tekst}")

        elif tag == "al":
            tekst = self._tekst(element)
            if tekst:
                regels.append(f"\n{tekst}")

        elif tag in ("kop", "opschrift", "intitule", "toelichting-opschrift"):
            pass  # Verwerkt bij parent-element

        elif tag in ("aanhef", "preambule"):
            tekst = self._tekst(element)
            if tekst:
                regels.append(f"\n*{tekst}*\n")

        elif tag in ("table", "tabel"):
            regels.append("\n> *(tabel — zie origineel op wetten.overheid.nl)*\n")

        else:
            # Generieke fallback: gewoon de tekst pakken
            tekst = self._tekst(element)
            if tekst and len(tekst) > 3:
                regels.append(f"\n{tekst}")
            for kind in element:
                regels.extend(self._converteer_element(kind, diepte + 1))

        return regels

    def naar_markdown(self) -> str:
        """Zet de volledige BWB-wet om naar Markdown."""
        fm = self._frontmatter()

        # Zoek de eigenlijke wetstructuur
        wet_tekst = self.root.find(".//{*}wettekst")
        if wet_tekst is None:
            wet_tekst = self.root.find(".//{*}regeling-tekst")
        if wet_tekst is None:
            wet_tekst = self.root.find(".//{*}body")
        if wet_tekst is None:
            wet_tekst = self.root

        # Titel ophalen
        titel = self._meta_waarde("officiele-titel", "citeertitel", "titel")
        regels = [f"# {titel or self.identifier}\n"]

        if wet_tekst is not None:
            for element in wet_tekst:
                regels.extend(self._converteer_element(element))

        # Opruimen: niet meer dan 2 lege regels achter elkaar
        inhoud = "\n".join(regels)
        inhoud = re.sub(r"\n{3,}", "\n\n", inhoud)

        return fm + "\n\n" + inhoud.strip() + "\n"


# ── BWB data ophalen ──────────────────────────────────────────────────────────

def haal_wet_op(identifier: str) -> Optional[str]:
    """
    Haal de XML van één wet op via het officiële BWB-repository.
    Probeert eerst de meest recente versie.
    """
    url = f"{BWB_REPO_BASE}/{identifier}/xml/{identifier}_xml.zip"
    log.info(f"Ophalen: {identifier}")

    # Probeer directe XML-URL (niet alle wetten hebben zip)
    xml_url = f"https://wetten.overheid.nl/{identifier}/xml"
    resp = fetch_with_retry(xml_url)
    if resp and resp.content:
        return resp.text

    log.warning(f"Geen XML gevonden voor {identifier}")
    return None


def zoek_wetten(categorie: Optional[str] = None, limit: int = 50) -> list[dict]:
    """
    Haal een lijst van wetten op via de wetten.overheid.nl API.
    Retourneert een lijst van dicts met identifier, titel, categorie.
    """
    params = {
        "aantal": min(limit, 100),
        "pagina": 1,
        "type": "wet",
    }
    if categorie:
        params["rechtsgebied"] = categorie

    url = f"{WETTEN_API}/regelingen"
    resp = fetch_with_retry(url, params=params)
    if not resp:
        return []

    try:
        data = resp.json()
        return data.get("resultaten", [])
    except Exception as e:
        log.error(f"API-fout: {e}")
        return []


# ── Opslaan ───────────────────────────────────────────────────────────────────

def sla_op(markdown: str, identifier: str, titel: str, categorie: str, output_dir: Path) -> Path:
    """Sla de Markdown op in de juiste submap."""
    map_naam = CATEGORIE_MAP.get(categorie, "overig")
    submap = output_dir / map_naam
    submap.mkdir(parents=True, exist_ok=True)

    bestandsnaam = slugify(titel or identifier) + ".md"
    pad = submap / bestandsnaam
    pad.write_text(markdown, encoding="utf-8")
    return pad


# ── Voorbeeld: directe XML converteren (voor testen) ─────────────────────────

VOORBEELD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<wet xmlns="http://www.bwb.overheid.nl/bwb/">
  <meta:metadata xmlns:meta="http://www.bwb.overheid.nl/bwb/meta/">
    <meta:officiele-titel>Grondwet</meta:officiele-titel>
    <meta:citeertitel>Grondwet</meta:citeertitel>
    <meta:rechtsgebied>Staatsinrichting en bestuur</meta:rechtsgebied>
    <meta:publicatiedatum>1983-02-24</meta:publicatiedatum>
    <meta:datum-laatste-wijziging>2023-02-22</meta:datum-laatste-wijziging>
  </meta:metadata>
  <wettekst>
    <hoofdstuk nr="1">
      <kop>Hoofdstuk 1 – Grondrechten</kop>
      <artikel nr="1">
        <al>Allen die zich in Nederland bevinden, worden in gelijke gevallen gelijk behandeld. Discriminatie wegens godsdienst, levensovertuiging, politieke gezindheid, ras, geslacht of op welke grond dan ook, is niet toegestaan.</al>
      </artikel>
      <artikel nr="2">
        <lid nr="1"><al>De wet regelt wie Nederlander is.</al></lid>
        <lid nr="2"><al>De wet regelt de toelating en de uitzetting van vreemdelingen.</al></lid>
        <lid nr="3"><al>Uitlevering kan slechts geschieden krachtens verdrag. Verdere voorschriften omtrent uitlevering worden bij de wet gegeven.</al></lid>
        <lid nr="4"><al>Ieder heeft het recht het land te verlaten, behoudens in de gevallen, bij de wet bepaald.</al></lid>
      </artikel>
    </hoofdstuk>
  </wettekst>
</wet>"""


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="BWB XML → Markdown converter")
    p.add_argument("--output", default="wetten/", help="Output map (default: wetten/)")
    p.add_argument("--identifier", help="Verwerk één specifieke wet (bv. BWBR0001840)")
    p.add_argument("--categorie", help="Filter op rechtsgebied")
    p.add_argument("--limit", type=int, default=50, help="Max aantal wetten (default: 50)")
    p.add_argument("--voorbeeld", action="store_true", help="Converteer ingebouwde voorbeeldwet (Grondwet)")
    p.add_argument("--log", help="Schrijf samenvatting naar dit bestand")
    return p.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    verwerkt = 0
    fouten = 0

    if args.voorbeeld:
        # Snel testen zonder netwerk
        log.info("Voorbeeldwet (Grondwet) converteren...")
        conv = BwbConverter(VOORBEELD_XML, "BWBR0001840")
        md = conv.naar_markdown()
        pad = output_dir / "staatsinrichting" / "grondwet.md"
        pad.parent.mkdir(parents=True, exist_ok=True)
        pad.write_text(md, encoding="utf-8")
        print(f"\n✅ Opgeslagen: {pad}")
        print("\n" + "─" * 60)
        print(md[:1500])
        return

    if args.identifier:
        wetten = [{"identifier": args.identifier, "titel": "", "rechtsgebied": ""}]
    else:
        log.info(f"Zoeken naar wetten (limit={args.limit})...")
        wetten = zoek_wetten(categorie=args.categorie, limit=args.limit)
        log.info(f"{len(wetten)} wetten gevonden.")

    for wet_info in wetten:
        ident = wet_info.get("identifier") or wet_info.get("id", "")
        titel = wet_info.get("officieleTitel") or wet_info.get("citeertitel") or wet_info.get("titel", "")
        categorie = wet_info.get("rechtsgebied", "Overig")

        xml_content = haal_wet_op(ident)
        if not xml_content:
            fouten += 1
            continue

        try:
            conv = BwbConverter(xml_content, ident)
            md = conv.naar_markdown()
            pad = sla_op(md, ident, titel, categorie, output_dir)
            log.info(f"✅  {ident} → {pad}")
            verwerkt += 1
        except Exception as e:
            log.error(f"❌  {ident}: {e}")
            fouten += 1

    samenvatting = (
        f"Verwerkt: {verwerkt} wetten | Fouten: {fouten} | "
        f"Datum: {date.today().isoformat()}"
    )
    log.info(samenvatting)

    if args.log:
        Path(args.log).write_text(samenvatting + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
