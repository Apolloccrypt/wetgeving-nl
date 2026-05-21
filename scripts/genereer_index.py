#!/usr/bin/env python3
"""
genereer_index.py — Genereer een JSON index van alle wetten voor de website.

Leest alle .md bestanden in wetten/, pakt de YAML-frontmatter eruit,
en schrijft een index.json die de website kan laden.

De categorie (rechtsgebied) wordt afgeleid uit de map waarin een wet staat
(wetten/<categorie>/...), want die plaatsing is de bron van waarheid — de
frontmatter bevat zelf geen categorie. Het soort regeling (wet/besluit/...)
komt uit het autoritatieve BWB-veld `soort`.

Gebruik:
    python scripts/genereer_index.py --wetten wetten/ --output index.json
"""

import argparse
import json
import re
from pathlib import Path


# Map-slug (rechtsgebied) -> nette weergavenaam
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

# BWB-soort -> nette weergavenaam (soort regeling). BES/archiefselectielijst-
# varianten vallen samen met hun hoofdsoort.
SOORT_NAAM = {
    "wet":                              "Wet",
    "wet-BES":                          "Wet",
    "rijkswet":                         "Rijkswet",
    "AMvB":                             "AMvB",
    "AMvB-BES":                         "AMvB",
    "rijksAMvB":                        "AMvB",
    "KB":                               "Koninklijk besluit",
    "rijksKB":                          "Koninklijk besluit",
    "ministeriele-regeling":            "Ministeriële regeling",
    "ministeriele-regeling-BES":        "Ministeriële regeling",
    "ministeriele-regeling-archiefselectielijst": "Ministeriële regeling",
    "beleidsregel":                     "Beleidsregel",
    "beleidsregel-BES":                 "Beleidsregel",
    "circulaire":                       "Circulaire",
    "circulaire-BES":                   "Circulaire",
    "verdrag":                          "Verdrag",
    "zbo":                              "ZBO-regeling",
    "pbo":                              "PBO-verordening",
    "reglement":                        "Reglement",
}

STATUS_NAAM = {
    "in_force": "Geldig",
    "geldig":   "Geldig",
}


def lees_frontmatter(pad: Path) -> dict:
    """Lees YAML-frontmatter uit een Markdown-bestand."""
    try:
        inhoud = pad.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    if not inhoud.startswith("---"):
        return {}

    einde = inhoud.find("\n---", 3)
    if einde == -1:
        return {}

    meta = {}
    for regel in inhoud[3:einde].split("\n"):
        if ":" in regel:
            sleutel, _, waarde = regel.partition(":")
            meta[sleutel.strip()] = waarde.strip().strip('"')

    return meta


def lees_body(pad: Path, max_tekens: int = 2000) -> str:
    """Lees de bodytekst van een wet (na de frontmatter).

    2000 tekens i.p.v. 400: voldoende voor full-text zoeken in korte wetten
    en besluiten plus de aanhef van lange wetten, zonder dat zoekindex.json
    onhanteerbaar groot wordt."""
    try:
        inhoud = pad.read_text(encoding="utf-8", errors="replace")
        einde = inhoud.find("\n---", 3)
        if einde < 0:
            return ""
        body = inhoud[einde + 4:].strip()
        body = re.sub(r"^#{1,6}\s+", "", body, flags=re.MULTILINE)
        body = re.sub(r"\n+", " ", body)
        body = re.sub(r"\s+", " ", body)
        return body[:max_tekens].strip()
    except Exception:
        return ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wetten",  default="wetten/")
    p.add_argument("--output",  default="index.json")
    p.add_argument("--zoekindex", default="zoekindex.json")
    p.add_argument("--verwijzingen", default="verwijzingen.json")
    args = p.parse_args()

    wetten_dir = Path(args.wetten)
    index = []
    zoekindex = []

    bestanden = sorted(wetten_dir.rglob("*.md"))
    print(f"{len(bestanden)} bestanden verwerken...")

    for i, bestand in enumerate(bestanden):
        meta = lees_frontmatter(bestand)
        if not meta:
            continue

        rel = bestand.relative_to(wetten_dir)
        # Categorie = de map waarin de wet staat (bron van waarheid)
        cat_slug = rel.parts[0] if len(rel.parts) > 1 else "overig"
        categorie = CATEGORIE_NAAM.get(cat_slug, meta.get("categorie", "Overig"))

        soort = meta.get("soort", "")
        type_naam = SOORT_NAAM.get(soort, "Overig")

        status_raw = meta.get("status", "")
        status = STATUS_NAAM.get(status_raw, status_raw or "geldig")

        index.append({
            "titel":      meta.get("title", bestand.stem),
            "identifier": meta.get("identifier", ""),
            "categorie":  categorie,
            "type":       type_naam,
            "datum":      meta.get("last_updated", meta.get("publication_date", "")),
            "status":     status,
            "pad":        "wetten/" + str(rel).replace("\\", "/"),
        })

        body = lees_body(bestand)
        zoekindex.append({"i": i, "b": body})

    # Sorteer beide op titel
    gesorteerd = sorted(range(len(index)), key=lambda x: index[x]["titel"].lower())
    index = [index[i] for i in gesorteerd]
    zoekindex_gesorteerd = {gesorteerd[i]: zoekindex[i] for i in range(len(gesorteerd))}
    zoekindex_lijst = [zoekindex_gesorteerd[i] for i in range(len(index))]

    output_pad = Path(args.output)
    output_pad.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    print(f"index.json: {len(index)} wetten ({output_pad.stat().st_size/1024/1024:.1f} MB)")

    zoek_pad = Path(args.zoekindex)
    zoek_pad.write_text(
        json.dumps(zoekindex_lijst, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    print(f"zoekindex.json: {zoek_pad.stat().st_size/1024/1024:.1f} MB")

    # Genereer verwijzingen.json
    bwbr_pat = re.compile(r'BWBR\d{7}')
    bwbr_naar_idx = {w['identifier']: i for i, w in enumerate(index) if w.get('identifier')}
    verwijzingen = {}
    for i, item in enumerate(zoekindex_lijst):
        body = item.get('b', '')
        eigen_id = index[i].get('identifier', '') if i < len(index) else ''
        if not eigen_id:
            continue
        refs = set(bwbr_pat.findall(body))
        refs.discard(eigen_id)
        refs = [r for r in refs if r in bwbr_naar_idx]
        if refs:
            verwijzingen[eigen_id] = refs
    verw_pad = Path(args.verwijzingen)
    verw_pad.write_text(json.dumps(verwijzingen, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"verwijzingen.json: {verw_pad.stat().st_size/1024:.0f} KB ({len(verwijzingen)} wetten)")


if __name__ == "__main__":
    main()
