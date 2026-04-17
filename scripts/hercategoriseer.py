#!/usr/bin/env python3
"""
hercategoriseer.py — Verbeter de categorisering van wetten in 'overig'.

Gebruik:
    python scripts/hercategoriseer.py --wetten wetten/ --dry-run
    python scripts/hercategoriseer.py --wetten wetten/
"""

import argparse
import re
import shutil
from pathlib import Path

# Uitgebreide trefwoorden inclusief alles wat we zagen in 'overig'
CATEGORIE_TREFWOORDEN = {
    "strafrecht": [
        "strafrecht", "strafbaar", "strafvordering", "detentie", "gevangenis",
        "boete", "opsporings", "justitie", "rechtbank", "vervolging", "delict",
        "sanctie", "reclassering", "penitentiair", "tbs", "jeugdstraf",
    ],
    "burgerlijk-recht": [
        "burgerlijk wetboek", "vermogensrecht", "verbintenis", "eigendom",
        "erfrecht", "huwelijk", "personen en familierecht", "aansprakelijkheid",
        "hypotheek", "pacht", "huur", "koop", "geregistreerd partnerschap",
        "faillissement", "surseance", "bewindvoering",
    ],
    "arbeidsrecht": [
        "arbeid", "werknemer", "werkgever", "cao ", "ontslag", "minimumloon",
        "arbeidsomstandig", "baan", "banen", "werk en inkomen", "uwv",
        "vakantie", "pensioen", "ambtena", "zzp", "uitzendkracht",
    ],
    "belastingrecht": [
        "belasting", "inkomstenbelasting", "omzetbelasting", "vennootschaps",
        "btw", "accijns", "successie", "douane", "fiscaal", "toeslagen",
        "belastingdienst", "heffing", "tarief", "aangifte belasting",
        "motorrijtuigenbelasting", "overdrachtsbelasting", "loonbelasting",
    ],
    "bestuursrecht": [
        "bestuur", "awb", "vergunning", "handhaving", "bezwaar en beroep",
        "mandaat", "mandaatbesluit", "organisatieregeling", "aanwijzing",
        "aanbestedingswet", "subsidie", "aanvraag", "beschikking",
        "toezicht", "inspectie", "boa", "opsporingsambtenaar",
    ],
    "sociaal-recht": [
        "bijstand", "uitkering", "sociale", "wmo", "wlz", "wia",
        "werkloosheid", "ww ", "aow", "pgb", "zorgkantoor", "jeugdwet",
        "participatie", "re-integratie", "schuldsanering", "wsnp",
        "beheerskosten", "beschikbaarheidbijdrage",
    ],
    "gezondheidszorg": [
        "gezondheid", "zorg", "geneeskundig", "medisch", "farma",
        "ziekenhuis", "geneesmiddel", "bevolkingsonderzoek", "ggz",
        "verpleeg", "huisarts", "tandarts", "apotheker", "vaccin",
        "rivm", "infectieziekte", "longrevalidatie", "orgaan",
        "bekostiging", "seh ", "spoedeisende hulp",
    ],
    "onderwijs": [
        "onderwijs", "school", "universiteit", "hoger onderwijs",
        "leerplicht", "student", "diploma", "examen", "mbo", "hbo",
        "bachelor", "master", "bekostigingsexperiment",
    ],
    "milieu": [
        "milieu", "natuur", "water", "bodem", "lucht", "klimaat", "afval",
        "emissie", "stikstof", "beschermingszone", "vogelrichtlijn",
        "habitatrichtlijn", "nucleair", "straling", "kern", "fochteloo",
        "nieuwkoopse", "speciale beschermingszone",
    ],
    "verkeer": [
        "verkeer", "wegenverkeer", "rijbewijs", "voertuig", "luchtvaart",
        "scheepvaart", "spoorweg", "haven", "transport", "vrachtwagen",
        "truck", "aze", "zero-emissie", "rdw ", "its-",
    ],
    "digitaal": [
        "persoonsgegevens", "privacy", "avg", "telecommunicatie", "digitaal",
        "cyber", "internet", "elektronisch", "ict ", "burgerservicenummer",
        "gba ", "basisregistratie",
    ],
    "internationaal-recht": [
        "verdrag", "internationaal", "europees", "eu-richtlijn", "navo",
        "sanctie", "sanctiebesluit", "richtlijn", "verordening nr",
        "eeg-richtlijn", "ccr", "markham",
    ],
    "staatsinrichting": [
        "grondwet", "kiesrecht", "parlement", "koningshuis", "rijkswet",
        "gemeente", "provincie", "rechterlijke", "kamer", "rijk",
        "bonaire", "sint eustatius", "saba", "openbare lichamen",
        "politie", "defensie", "ministerie", "rijksoverheid",
    ],
    "financieel-recht": [
        "financieel toezicht", "wft ", "bank", "verzekering", "effecten",
        "prospectus", "krediet", "financiele weerbaarheid", "acm ",
        "energieleverancier", "aansluit", "transportcode",
    ],
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
    "financieel-recht":     "Financieel recht",
    "overig":               "Overig",
}


def bepaal_categorie(titel: str) -> str:
    titel_lower = titel.lower()
    for cat, trefwoorden in CATEGORIE_TREFWOORDEN.items():
        if any(t in titel_lower for t in trefwoorden):
            return cat
    return "overig"


def verwerk_bestand(pad: Path, wetten_dir: Path, dry_run: bool) -> tuple[str, str]:
    """Hercategoriseer één bestand. Geeft (oud_cat, nieuw_cat) terug."""
    inhoud = pad.read_text(encoding="utf-8", errors="replace")

    # Lees huidige categorie
    huidige_cat = "overig"
    for regel in inhoud.split("\n"):
        if regel.startswith("categorie:"):
            huidige_cat = regel.split(":", 1)[1].strip().strip('"')
            break

    # Alleen 'Overig' hercategoriseren
    if huidige_cat != "Overig":
        return huidige_cat, huidige_cat

    # Haal titel op
    titel = pad.stem
    for regel in inhoud.split("\n"):
        if regel.startswith("title:"):
            titel = regel.split(":", 1)[1].strip().strip('"')
            break

    nieuwe_cat_slug = bepaal_categorie(titel)
    nieuwe_cat_naam = CATEGORIE_NAAM[nieuwe_cat_slug]

    if nieuwe_cat_slug == "overig":
        return "Overig", "Overig"

    if not dry_run:
        # Update frontmatter
        nieuwe_inhoud = inhoud.replace(
            'categorie: "Overig"',
            f'categorie: "{nieuwe_cat_naam}"'
        )

        # Verplaats bestand naar nieuwe map
        nieuwe_map = wetten_dir / nieuwe_cat_slug
        nieuwe_map.mkdir(parents=True, exist_ok=True)
        nieuw_pad = nieuwe_map / pad.name
        nieuw_pad.write_text(nieuwe_inhoud, encoding="utf-8")
        pad.unlink()

    return "Overig", nieuwe_cat_naam


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wetten", default="wetten/")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    wetten_dir = Path(args.wetten)
    overig_dir = wetten_dir / "overig"

    if not overig_dir.exists():
        print(f"Map niet gevonden: {overig_dir}")
        return

    bestanden = list(overig_dir.glob("*.md"))
    print(f"{len(bestanden)} bestanden in 'overig' verwerken...")
    if args.dry_run:
        print("(dry-run: geen wijzigingen)")

    verplaatst = {}
    blijft = 0

    for bestand in bestanden:
        oud, nieuw = verwerk_bestand(bestand, wetten_dir, args.dry_run)
        if nieuw != "Overig":
            verplaatst[nieuw] = verplaatst.get(nieuw, 0) + 1
        else:
            blijft += 1

    print(f"\nResultaat:")
    for cat, n in sorted(verplaatst.items(), key=lambda x: -x[1]):
        print(f"  {cat:<30} {n} wetten")
    print(f"  {'Overig (blijft)':<30} {blijft} wetten")
    print(f"\nTotaal verplaatst: {sum(verplaatst.values())}")


if __name__ == "__main__":
    main()
