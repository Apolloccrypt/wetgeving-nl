#!/usr/bin/env python3
"""
cleanup_legalize.py — Converteer legalize-nl bestanden naar nette wetgeving-nl Markdown.

Wat dit script doet:
  1. Strips alle rommelige interne metadata (stam_id, jci_*, toestand_uri, etc.)
  2. Hernoemt velden naar Nederlandse namen (publication_date → publicatiedatum, etc.)
  3. Gebruikt short_title als primaire titel (i.p.v. "Wet van 3 maart 1881")
  4. Vertaalt status: in_force → geldig, etc.
  5. Sorteert bestanden in categorieën (burgerlijk-recht, strafrecht, etc.)

Gebruik:
    python cleanup_legalize.py --input /pad/naar/legalize-nl/nl/ --output wetten/
    python cleanup_legalize.py --input ./temp-legalize-nl/nl/ --output wetten/ --limit 100
"""

import argparse
import re
import unicodedata
from pathlib import Path

import yaml  # pip install pyyaml

# ── Velden die we BEWAREN (de rest gooien we weg) ────────────────────────────
BEWAAR_VELDEN = {
    "title", "identifier", "country", "rank", "publication_date",
    "last_updated", "status", "source", "short_title",
}

# ── Status vertaling ──────────────────────────────────────────────────────────
STATUS_MAP = {
    "in_force":   "geldig",
    "repealed":   "ingetrokken",
    "expired":    "vervallen",
    "draft":      "voorstel",
}

# ── Rang → categorie map ──────────────────────────────────────────────────────
RANG_NAAR_CATEGORIE = {
    "grondwet":              "staatsinrichting",
    "rijkswet":              "staatsinrichting",
    "wet":                   "overig",           # Wordt verder verfijnd via trefwoorden
    "amvb":                  "bestuursrecht",
    "ministeriele-regeling": "bestuursrecht",
    "verdrag":               "internationaal-recht",
    "beleidsregel":          "bestuursrecht",
    "circulaire":            "bestuursrecht",
    "reglement":             "staatsinrichting",
}

# ── Trefwoorden per categorie (op basis van titel) ────────────────────────────
CATEGORIE_TREFWOORDEN = {
    "strafrecht":        ["strafrecht", "strafbaar", "strafvordering", "detentie", "gevangenis", "boete"],
    "burgerlijk-recht":  ["burgerlijk", "vermogensrecht", "verbintenis", "eigendom", "erfrecht", "huwelijk", "personen"],
    "arbeidsrecht":      ["arbeid", "werknemer", "werkgever", "cao", "ontslag", "minimumloon", "arbeidsomstandig"],
    "belastingrecht":    ["belasting", "inkomstenbelasting", "omzetbelasting", "vennootschapsbelasting", "btw", "successie", "accijns"],
    "bestuursrecht":     ["bestuur", "gemeente", "provincie", "omgevings", "vergunning", "handhaving", "awb"],
    "sociaal-recht":     ["bijstand", "uitkering", "sociale", "wmo", "jeugd", "zorg", "wia", "ww ", "werkloosheid"],
    "gezondheidszorg":   ["gezondheid", "zorg", "geneeskundig", "medisch", "farma", "ziekenhuis", "bevolkingsonder"],
    "onderwijs":         ["onderwijs", "school", "universiteit", "hoger onderwijs", "leerplicht", "student"],
    "milieu":            ["milieu", "natuur", "water", "bodem", "lucht", "klimaat", "afval"],
    "verkeer":           ["verkeer", "wegenverkeer", "rijbewijs", "voertuig", "luchtvaart", "scheepvaart"],
    "digitaal":          ["gegevens", "privacy", "persoonsgegevens", "avg", "telecommunicatie", "digitaal", "cyber"],
    "internationaal-recht": ["verdrag", "internationaal", "europees", "eu-richtlijn", "navo"],
    "staatsinrichting":  ["grondwet", "kiesrecht", "parlement", "koningshuis", "rijkswet", "gemeente", "provincie", "rechterlijke"],
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:80]


def bepaal_categorie(titel: str, rank: str) -> str:
    """Bepaal categorie op basis van titel-trefwoorden + rank."""
    titel_lower = titel.lower()
    for categorie, trefwoorden in CATEGORIE_TREFWOORDEN.items():
        if any(t in titel_lower for t in trefwoorden):
            return categorie
    return RANG_NAAR_CATEGORIE.get(rank, "overig")


def parse_frontmatter(inhoud: str) -> tuple[dict, str]:
    """Splits YAML-frontmatter van de bodytekst."""
    if not inhoud.startswith("---"):
        return {}, inhoud
    einde = inhoud.find("\n---", 3)
    if einde == -1:
        return {}, inhoud
    try:
        meta = yaml.safe_load(inhoud[3:einde]) or {}
    except yaml.YAMLError:
        meta = {}
    body = inhoud[einde + 4:].lstrip("\n")
    return meta, body


def maak_nette_frontmatter(meta: dict, categorie: str) -> str:
    """Bouw schone YAML-frontmatter (alleen wat we nodig hebben)."""
    # Kies beste titel
    titel = (
        meta.get("short_title") or
        meta.get("title") or
        meta.get("identifier", "")
    )
    # Verwijder lelijke formele titels als short_title beschikbaar is
    if meta.get("short_title") and meta.get("title", "").startswith("Wet van "):
        titel = meta["short_title"]

    identifier   = meta.get("identifier", "")
    pub_datum    = meta.get("publication_date", "")
    update_datum = meta.get("last_updated", "")
    status_raw   = meta.get("status", "in_force")
    status       = STATUS_MAP.get(status_raw, status_raw)
    bron         = meta.get("source", f"https://wetten.overheid.nl/{identifier}")

    regels = ["---"]
    regels.append(f'title: "{titel}"')
    regels.append(f'identifier: "{identifier}"')
    regels.append(f'categorie: "{CATEGORIE_NAAM[categorie]}"')
    if pub_datum:
        regels.append(f"publicatiedatum: {str(pub_datum)[:10]}")
    if update_datum:
        regels.append(f"laatste_update: {str(update_datum)[:10]}")
    regels.append(f"status: {status}")
    regels.append(f'bron: "{bron}"')
    regels.append("---")
    return "\n".join(regels)


# Categorie-slug → leesbare naam
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


def verbeter_body(body: str, titel: str) -> str:
    """
    Verbeter de bodytekst:
    - Vervang formele "Wet van X" heading door de echte citeertitel
    - Normaliseer heading-niveaus (##### Artikel → #### Artikel)
    """
    regels = body.split("\n")
    resultaat = []

    for i, regel in enumerate(regels):
        # Eerste H1: vervang formele titel door citeertitel als die beter is
        if regel.startswith("# Wet van ") and titel and not titel.startswith("Wet van "):
            regel = f"# {titel}"

        # ##### Artikel X → #### Artikel X (één niveau minder diep)
        if regel.startswith("#####"):
            regel = regel[1:]  # #### Artikel X

        resultaat.append(regel)

    inhoud = "\n".join(resultaat)
    # Opruimen: niet meer dan 2 lege regels
    inhoud = re.sub(r"\n{3,}", "\n\n", inhoud)
    return inhoud.strip()


def verwerk_bestand(src: Path, output_dir: Path) -> bool:
    """Converteer één legalize-nl bestand naar nettige wetgeving-nl versie."""
    try:
        inhoud = src.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(inhoud)

        if not meta:
            return False

        identifier = meta.get("identifier", src.stem)
        rank       = meta.get("rank", "")
        titel      = meta.get("short_title") or meta.get("title") or identifier

        categorie  = bepaal_categorie(titel, rank)
        fm         = maak_nette_frontmatter(meta, categorie)
        body_clean = verbeter_body(body, titel)

        # Bestandsnaam: gebruik short_title als die er is, anders identifier
        bestandsnaam = slugify(titel) + ".md"
        doel_map     = output_dir / categorie
        doel_map.mkdir(parents=True, exist_ok=True)
        doel         = doel_map / bestandsnaam

        doel.write_text(fm + "\n\n" + body_clean + "\n", encoding="utf-8")
        return True

    except Exception as e:
        print(f"  ⚠️  Fout bij {src.name}: {e}")
        return False


def main():
    p = argparse.ArgumentParser(description="Cleanup legalize-nl → wetgeving-nl")
    p.add_argument("--input",  required=True, help="Map met legalize-nl .md bestanden (nl/)")
    p.add_argument("--output", required=True, help="Output map (wetten/)")
    p.add_argument("--limit",  type=int, default=0, help="Max bestanden (0 = alles)")
    args = p.parse_args()

    src_map    = Path(args.input)
    output_dir = Path(args.output)
    bestanden  = sorted(src_map.glob("*.md"))

    if args.limit:
        bestanden = bestanden[:args.limit]

    print(f"🔄  {len(bestanden)} bestanden verwerken → {output_dir}")

    ok = fout = 0
    for i, bestand in enumerate(bestanden, 1):
        if verwerk_bestand(bestand, output_dir):
            ok += 1
        else:
            fout += 1
        if i % 500 == 0:
            print(f"   {i}/{len(bestanden)} ({ok} ok, {fout} fout)")

    print(f"\n✅  Klaar: {ok} succesvol, {fout} overgeslagen")
    print(f"   Wetten staan in: {output_dir.resolve()}")

    # Toon categorie-verdeling
    print("\n📂  Verdeling per categorie:")
    for cat_map in sorted(output_dir.iterdir()):
        if cat_map.is_dir():
            n = len(list(cat_map.glob("*.md")))
            print(f"   {cat_map.name:<25} {n} wetten")


if __name__ == "__main__":
    main()
