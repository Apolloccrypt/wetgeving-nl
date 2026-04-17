#!/usr/bin/env python3
"""
dagelijkse_update.py — Haal gewijzigde wetten rechtstreeks op van de overheid.

Strategie:
  1. Vraag SRU-service welke wetten gisteren gewijzigd zijn
  2. Download elke gewijzigde wet als XML van de BWB-repository
  3. Converteer naar nette Markdown
  4. Fallback: als BWB niet bereikbaar is, gebruik legalize-nl

Gebruik:
    python dagelijkse_update.py --output wetten/
    python dagelijkse_update.py --output wetten/ --dagen 7   # Laatste 7 dagen
    python dagelijkse_update.py --output wetten/ --test       # Test verbinding
"""

import argparse
import io
import logging
import re
import sys
import time
import unicodedata
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import requests
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("update")

SRU_URL   = "https://zoekservice.overheid.nl/sru/Search"
REPO_BASE = "https://repository.officiele-overheidspublicaties.nl/BWB"
LEGALIZE_RAW = "https://raw.githubusercontent.com/legalize-dev/legalize-nl/main/nl"
DELAY     = 0.5

CATEGORIE_TREFWOORDEN = {
    "strafrecht":        ["strafrecht", "strafbaar", "strafvordering"],
    "burgerlijk-recht":  ["burgerlijk", "vermogensrecht", "verbintenis", "erfrecht", "huwelijk"],
    "arbeidsrecht":      ["arbeid", "werknemer", "werkgever", "minimumloon"],
    "belastingrecht":    ["belasting", "inkomstenbelasting", "omzetbelasting", "btw", "accijns"],
    "bestuursrecht":     ["bestuur", "gemeente", "provincie", "omgevings", "vergunning", "awb"],
    "sociaal-recht":     ["bijstand", "uitkering", "sociale", "wmo", "wia", "werkloosheid"],
    "gezondheidszorg":   ["gezondheid", "geneeskundig", "medisch", "ziekenhuis"],
    "onderwijs":         ["onderwijs", "school", "universiteit", "leerplicht"],
    "milieu":            ["milieu", "natuur", "water", "bodem", "klimaat", "afval"],
    "verkeer":           ["verkeer", "wegenverkeer", "rijbewijs", "luchtvaart"],
    "digitaal":          ["persoonsgegevens", "privacy", "avg", "telecommunicatie"],
    "internationaal-recht": ["verdrag", "internationaal"],
    "staatsinrichting":  ["grondwet", "kiesrecht", "rijkswet", "rechterlijke"],
}

CATEGORIE_NAAM = {
    "staatsinrichting":     "Staatsinrichting en bestuur",
    "bestuursrecht":        "Bestuursrecht",
    "burgerlijk-recht":     "Burgerlijk recht",
    "strafrecht":           "Strafrecht",
    "arbeidsrecht":         "Arbeidsrecht",
    "belastingrecht":       "Belastingrecht",
    "sociaal-recht":        "Sociaal recht",
    "onderwijs":            "Onderwijs",
    "gezondheidszorg":      "Gezondheidszorg",
    "digitaal":             "Digitaal en privacy",
    "milieu":               "Milieu",
    "verkeer":              "Verkeer",
    "internationaal-recht": "Internationaal recht",
    "overig":               "Overig",
}

STATUS_MAP = {"in_force": "geldig", "repealed": "ingetrokken", "expired": "vervallen"}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:80]


def bepaal_categorie(titel: str) -> str:
    titel_lower = titel.lower()
    for cat, trefwoorden in CATEGORIE_TREFWOORDEN.items():
        if any(t in titel_lower for t in trefwoorden):
            return cat
    return "overig"


def fetch(url: str, **kwargs) -> Optional[requests.Response]:
    for i in range(3):
        try:
            r = requests.get(url, timeout=30, **kwargs)
            r.raise_for_status()
            time.sleep(DELAY)
            return r
        except requests.RequestException as e:
            time.sleep(2 ** i)
            if i == 2:
                log.warning(f"Mislukt: {url} — {e}")
    return None


# ── Stap 1: SRU — welke wetten zijn gewijzigd? ───────────────────────────────

def haal_gewijzigde_ids_op(vanaf_datum: str) -> list[str]:
    """
    Vraag de SRU-service welke wetten gewijzigd zijn vanaf een datum.
    Datum formaat: YYYY-MM-DD
    """
    ids = []
    start = 1
    batch = 100

    log.info(f"SRU: gewijzigde wetten ophalen vanaf {vanaf_datum}...")

    while True:
        params = {
            "operation":      "searchRetrieve",
            "version":        "1.2",
            "x-connection":   "BWB",
            "query":          f"dcterms.modified>={vanaf_datum}",
            "maximumRecords": batch,
            "startRecord":    start,
        }
        r = fetch(SRU_URL, params=params)
        if not r:
            break

        try:
            root = ET.fromstring(r.text)
            # Haal alle BWBR-identifiers op uit de resultaten
            gevonden = []
            for el in root.iter():
                if el.text and re.match(r"BWBR\d+|BWBV\d+", el.text.strip()):
                    gevonden.append(el.text.strip())

            if not gevonden:
                break

            ids.extend(gevonden)
            log.info(f"  {len(ids)} identifiers gevonden...")

            # Check of er meer pagina's zijn
            total_el = root.find(".//{http://www.loc.gov/zing/srw/}numberOfRecords")
            if total_el is not None:
                total = int(total_el.text or 0)
                if start + batch > total:
                    break
            else:
                break

            start += batch

        except Exception as e:
            log.warning(f"SRU parse-fout: {e}")
            break

    # Dedupliceer
    ids = list(dict.fromkeys(ids))
    log.info(f"SRU: {len(ids)} unieke gewijzigde wetten gevonden")
    return ids


# ── Stap 2: XML ophalen van BWB-repository ───────────────────────────────────

def haal_xml_op_bwb(identifier: str) -> Optional[str]:
    """Haal XML op van de officiële BWB-repository."""
    url = f"{REPO_BASE}/{identifier}/xml/{identifier}_xml.zip"
    r = fetch(url)
    if not r:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            xml_namen = [n for n in z.namelist() if "toestand" in n.lower() and n.endswith(".xml")]
            if not xml_namen:
                xml_namen = [n for n in z.namelist() if n.endswith(".xml")]
            if xml_namen:
                return z.read(xml_namen[0]).decode("utf-8", errors="replace")
    except zipfile.BadZipFile:
        if r.text.strip().startswith("<"):
            return r.text
    return None


def haal_xml_op_legalize(identifier: str) -> Optional[str]:
    """
    Fallback: haal Markdown op van legalize-nl en geef die terug.
    Dit is geen XML maar wordt direct als Markdown gebruikt.
    """
    url = f"{LEGALIZE_RAW}/{identifier}.md"
    r = fetch(url)
    return r.text if r else None


# ── Stap 3: XML → Markdown ───────────────────────────────────────────────────

def xml_naar_markdown(xml: str, identifier: str) -> Optional[str]:
    """Converteer BWB-XML naar nette Markdown."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None

    def zoek(root, *tags):
        for tag in tags:
            el = root.find(f".//{tag}")
            if el is None:
                el = root.find(f"{{*}}{tag}")
            if el is not None and el.text:
                return el.text.strip()
        return ""

    def tekst(el):
        if el is None:
            return ""
        delen = [el.text.strip()] if el.text else []
        for k in el:
            t = tekst(k)
            if t:
                delen.append(t)
            if k.tail and k.tail.strip():
                delen.append(k.tail.strip())
        return " ".join(filter(None, delen))

    def element_naar_md(el, diepte=0):
        tag = el.tag.split("}")[-1].lower()
        out = []

        if tag in ("hoofdstuk", "titel", "boek"):
            kop_el = el.find(".//{*}kop") or el.find(".//{*}opschrift")
            kop = tekst(kop_el) if kop_el is not None else el.get("nr", "")
            out.append(f"\n## {kop}\n")
            for k in el:
                out.extend(element_naar_md(k, diepte + 1))
        elif tag in ("afdeling", "paragraaf"):
            kop_el = el.find(".//{*}kop") or el.find(".//{*}opschrift")
            kop = tekst(kop_el) if kop_el is not None else el.get("nr", "")
            out.append(f"\n### {kop}\n")
            for k in el:
                out.extend(element_naar_md(k, diepte + 1))
        elif tag == "artikel":
            nr = el.get("nr", "?")
            opschrift_el = el.find("{*}opschrift")
            opschrift = ""
            if opschrift_el is not None:
                t = tekst(opschrift_el)
                if t and len(t) < 120:
                    opschrift = f" – {t}"
            out.append(f"\n#### Artikel {nr}{opschrift}\n")
            for k in el:
                if k.tag.split("}")[-1].lower() not in ("opschrift",):
                    out.extend(element_naar_md(k, diepte + 1))
        elif tag == "lid":
            nr = el.get("nr", "")
            al_el = el.find("{*}al")
            t = tekst(al_el) if al_el is not None else (el.text or "").strip()
            if t:
                prefix = f"{nr}." if nr else "-"
                out.append(f"\n{prefix} {t}")
            for k in el:
                if k.tag.split("}")[-1].lower() not in ("al",):
                    out.extend(element_naar_md(k, diepte + 1))
        elif tag in ("lijst", "list"):
            for item in el:
                item_tag = item.tag.split("}")[-1].lower()
                if item_tag in ("li", "onderdeel"):
                    letter = item.get("nr", "")
                    t = tekst(item)
                    out.append(f"   {letter}. {t}" if letter else f"   - {t}")
        elif tag == "al":
            t = tekst(el)
            if t:
                out.append(f"\n{t}")
        elif tag in ("kop", "opschrift", "metadata", "wetciteer"):
            pass
        elif tag in ("aanhef", "preambule"):
            t = tekst(el)
            if t:
                out.append(f"\n*{t}*\n")
        elif tag in ("table", "tabel"):
            out.append(f"\n> *(tabel — zie origineel op wetten.overheid.nl/{identifier})*\n")
        else:
            t = tekst(el)
            if t and len(t) > 5:
                out.append(f"\n{t}")
            for k in el:
                out.extend(element_naar_md(k, diepte + 1))
        return out

    titel = zoek(root, "officiele-titel", "officieleTitel", "citeertitel", "short_title")
    citeertitel = zoek(root, "citeertitel", "short_title")
    pub_datum = zoek(root, "publicatiedatum", "datumInwerking", "publication_date")
    upd_datum = zoek(root, "datum-laatste-wijziging", "datumLaatsteWijziging", "last_updated")
    ingetrokken = zoek(root, "datum-intrekking", "datumIntrekking")
    status = "ingetrokken" if ingetrokken else "geldig"
    categorie = bepaal_categorie(titel or identifier)

    fm = ["---"]
    fm.append(f'title: "{titel or identifier}"')
    if citeertitel and citeertitel != titel:
        fm.append(f'citeertitel: "{citeertitel}"')
    fm.append(f'identifier: "{identifier}"')
    fm.append(f'categorie: "{CATEGORIE_NAAM.get(categorie, "Overig")}"')
    if pub_datum:
        fm.append(f"publicatiedatum: {pub_datum[:10]}")
    if upd_datum:
        fm.append(f"laatste_update: {upd_datum[:10]}")
    fm.append(f"status: {status}")
    fm.append(f'bron: "https://wetten.overheid.nl/{identifier}"')
    fm.append("---")

    wettekst = root.find(".//{*}wettekst") or root.find(".//{*}regeling-tekst") or root
    regels = [f"# {titel or identifier}\n"]
    for el in wettekst:
        regels.extend(element_naar_md(el))

    inhoud = "\n".join(fm) + "\n\n" + "\n".join(regels)
    inhoud = re.sub(r"\n{3,}", "\n\n", inhoud)
    return inhoud.strip() + "\n"


def legalize_md_cleanup(md_inhoud: str, identifier: str) -> str:
    """Maak legalize-nl Markdown schoon (als fallback)."""
    if not md_inhoud.startswith("---"):
        return md_inhoud

    einde = md_inhoud.find("\n---", 3)
    if einde == -1:
        return md_inhoud

    try:
        meta = yaml.safe_load(md_inhoud[3:einde]) or {}
    except Exception:
        return md_inhoud

    body = md_inhoud[einde + 4:].lstrip("\n")
    titel = meta.get("short_title") or meta.get("title") or identifier
    categorie = bepaal_categorie(titel)

    fm = ["---"]
    fm.append(f'title: "{titel}"')
    fm.append(f'identifier: "{identifier}"')
    fm.append(f'categorie: "{CATEGORIE_NAAM.get(categorie, "Overig")}"')
    pub = meta.get("publication_date", "")
    upd = meta.get("last_updated", "")
    if pub:
        fm.append(f"publicatiedatum: {str(pub)[:10]}")
    if upd:
        fm.append(f"laatste_update: {str(upd)[:10]}")
    status_raw = meta.get("status", "in_force")
    fm.append(f"status: {STATUS_MAP.get(status_raw, status_raw)}")
    fm.append(f'bron: "https://wetten.overheid.nl/{identifier}"')
    fm.append("---")

    body = re.sub(r"^# Wet van .+$", f"# {titel}", body, flags=re.MULTILINE)
    body = re.sub(r"^#####", "####", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body)

    return "\n".join(fm) + "\n\n" + body.strip() + "\n"


def sla_op(inhoud: str, identifier: str, output_dir: Path) -> Path:
    # Haal categorie uit frontmatter
    categorie = "overig"
    for regel in inhoud.split("\n"):
        if regel.startswith("categorie:"):
            cat_waarde = regel.split(":", 1)[1].strip().strip('"')
            for slug, naam in CATEGORIE_NAAM.items():
                if naam == cat_waarde:
                    categorie = slug
                    break
            break

    # Haal titel op voor bestandsnaam
    titel = identifier
    for regel in inhoud.split("\n"):
        if regel.startswith("title:"):
            titel = regel.split(":", 1)[1].strip().strip('"')
            break

    submap = output_dir / categorie
    submap.mkdir(parents=True, exist_ok=True)
    pad = submap / (slugify(titel) + ".md")
    pad.write_text(inhoud, encoding="utf-8")
    return pad


# ── Hoofd ────────────────────────────────────────────────────────────────────

def test_verbinding() -> dict:
    """Test of SRU en BWB bereikbaar zijn."""
    resultaat = {}

    log.info("Verbinding testen met SRU-service...")
    r = fetch(SRU_URL, params={
        "operation": "searchRetrieve", "version": "1.2",
        "x-connection": "BWB", "query": "dcterms.type=wet",
        "maximumRecords": 1,
    })
    resultaat["sru"] = r is not None and r.status_code == 200

    log.info("Verbinding testen met BWB-repository...")
    r2 = fetch(f"{REPO_BASE}/BWBR0001840/xml/BWBR0001840_xml.zip")
    resultaat["bwb_repo"] = r2 is not None and r2.status_code == 200

    log.info("Verbinding testen met legalize-nl (fallback)...")
    r3 = fetch(f"{LEGALIZE_RAW}/BWBR0001840.md")
    resultaat["legalize_fallback"] = r3 is not None and r3.status_code == 200

    for naam, ok in resultaat.items():
        status = "OK" if ok else "GEBLOKKEERD"
        log.info(f"  {naam:<25} {status}")

    return resultaat


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="wetten/")
    p.add_argument("--dagen",  type=int, default=2, help="Wijzigingen ophalen van laatste N dagen")
    p.add_argument("--test",   action="store_true",  help="Test verbindingen")
    args = p.parse_args()

    if args.test:
        resultaat = test_verbinding()
        sys.exit(0 if any(resultaat.values()) else 1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Bepaal datumrange
    vanaf = (date.today() - timedelta(days=args.dagen)).isoformat()

    # Test welke bronnen werken
    verbinding = test_verbinding()
    bwb_werkt      = verbinding["bwb_repo"]
    sru_werkt      = verbinding["sru"]
    legalize_werkt = verbinding["legalize_fallback"]

    if not sru_werkt and not legalize_werkt:
        log.error("Geen enkele bron bereikbaar. Afbreken.")
        sys.exit(1)

    ok = fout = 0

    if sru_werkt:
        # Directe route: SRU + BWB
        ids = haal_gewijzigde_ids_op(vanaf)
        log.info(f"{len(ids)} gewijzigde wetten verwerken...")

        for identifier in ids:
            md = None

            if bwb_werkt:
                xml = haal_xml_op_bwb(identifier)
                if xml:
                    md = xml_naar_markdown(xml, identifier)

            if not md and legalize_werkt:
                # Fallback naar legalize-nl
                raw = haal_xml_op_legalize(identifier)
                if raw:
                    md = legalize_md_cleanup(raw, identifier)
                    log.debug(f"  Fallback legalize-nl gebruikt voor {identifier}")

            if md:
                pad = sla_op(md, identifier, output_dir)
                log.info(f"  Bijgewerkt: {pad.relative_to(output_dir.parent)}")
                ok += 1
            else:
                fout += 1

    elif legalize_werkt:
        # Alleen fallback beschikbaar: haal alles opnieuw op van legalize-nl
        log.warning("SRU niet bereikbaar, gebruik legalize-nl als fallback voor alle wetten")
        import subprocess
        result = subprocess.run(
            ["python", "scripts/cleanup_legalize.py",
             "--input", "/tmp/legalize-nl/nl/",
             "--output", str(output_dir)],
            capture_output=True, text=True
        )
        log.info(result.stdout)
        ok = 1

    log.info(f"Klaar: {ok} bijgewerkt, {fout} mislukt — {date.today()}")


if __name__ == "__main__":
    main()
