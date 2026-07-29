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
import datetime
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
    p.add_argument("--meta", default="meta.json")
    p.add_argument("--sitemap", default="sitemap.xml")
    args = p.parse_args()

    wetten_dir = Path(args.wetten)
    index = []
    zoekindex = []
    per_id = {}  # identifier -> positie in index, voor deduplicatie
    overgeslagen = 0

    bestanden = sorted(wetten_dir.rglob("*.md"))
    print(f"{len(bestanden)} bestanden verwerken...")

    for bestand in bestanden:
        meta = lees_frontmatter(bestand)
        if not meta:
            overgeslagen += 1
            print(f"  OVERGESLAGEN (geen frontmatter): {bestand}")
            continue

        rel = bestand.relative_to(wetten_dir)
        # Categorie = de map waarin de wet staat (bron van waarheid)
        cat_slug = rel.parts[0] if len(rel.parts) > 1 else "overig"
        categorie = CATEGORIE_NAAM.get(cat_slug, meta.get("categorie", "Overig"))

        soort = meta.get("soort", "")
        type_naam = SOORT_NAAM.get(soort, "Overig")

        status_raw = meta.get("status", "")
        status = STATUS_NAAM.get(status_raw, status_raw or "geldig")

        # De citeertitel is waar mensen op zoeken ("Awb", "Grondwet",
        # "Wegenverkeerswet 1994"); de officiele titel begint vaak met
        # "Wet van 21 april 1994, houdende...". Zonder citeertitel in de index
        # is een wet alleen te vinden via de volledige tekst.
        citeertitel = (meta.get("citeertitel") or meta.get("short_title") or "").strip()
        titel = meta.get("title", bestand.stem)

        entry = {
            "titel":      titel,
            "identifier": meta.get("identifier", ""),
            "categorie":  categorie,
            "type":       type_naam,
            # De schrijvers emitten Nederlandse sleutels; val terug op de oude Engelse
            "datum":      (meta.get("laatste_update") or meta.get("publicatiedatum")
                           or meta.get("last_updated") or meta.get("publication_date") or ""),
            "status":     status,
            "pad":        "wetten/" + str(rel).replace("\\", "/"),
        }
        if citeertitel and citeertitel.lower() != titel.lower():
            entry["citeertitel"] = citeertitel
        zoek_entry = {"b": lees_body(bestand)}

        # Dedupliceer op identifier: hetzelfde BWB-id kan (historisch) in twee
        # categorie-mappen staan. Eén kaart per wet; niet-overig wint, daarna
        # de nieuwste datum.
        ident = entry["identifier"]
        if ident and ident in per_id:
            pos = per_id[ident]
            oud = index[pos]
            oud_overig = oud["categorie"] == "Overig"
            nieuw_overig = entry["categorie"] == "Overig"
            vervang = (oud_overig and not nieuw_overig) or (
                oud_overig == nieuw_overig and entry["datum"] > oud["datum"])
            if vervang:
                index[pos] = entry
                zoekindex[pos] = zoek_entry
            continue

        if ident:
            per_id[ident] = len(index)
        index.append(entry)
        zoekindex.append(zoek_entry)

    if overgeslagen:
        print(f"LET OP: {overgeslagen} bestanden zonder frontmatter overgeslagen")
    dubbel = len([b for b in bestanden]) - overgeslagen - len(index)
    if dubbel:
        print(f"{dubbel} duplicaat-bestanden samengevoegd tot 1 kaart per identifier")

    # Sorteer beide op titel — met DEZELFDE permutatie, zodat zoekindex[pos]
    # de body van index[pos] blijft (de frontend koppelt ze positioneel)
    gesorteerd = sorted(range(len(index)), key=lambda x: index[x]["titel"].lower())
    index = [index[i] for i in gesorteerd]
    zoekindex_lijst = [zoekindex[i] for i in gesorteerd]

    # Regressie-guard: weiger een run die de dataset plotseling doet krimpen
    # (bv. een half-mislukte bron-run die goede wetten met afval zou overschrijven).
    oud_meta = Path(args.meta)
    if oud_meta.exists():
        try:
            oud_n = json.loads(oud_meta.read_text(encoding="utf-8")).get("aantal_wetten", 0)
            if oud_n and len(index) < 0.99 * oud_n:
                raise SystemExit(
                    f"AFGEBROKEN: index kromp van {oud_n} naar {len(index)} (<99%). "
                    "Waarschijnlijk een slechte bron-run; niets weggeschreven.")
        except (ValueError, KeyError):
            pass

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

    # Genereer verwijzingen.json (ook verdragen BWBV en BWBW-nummers)
    bwbr_pat = re.compile(r'BWB[RVW]\d{4,8}')
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

    # meta.json: één bron van waarheid voor telling + sync-datum
    meta = {"gegenereerd": datetime.date.today().isoformat(), "aantal_wetten": len(index)}
    Path(args.meta).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"meta.json: {meta}")

    # sitemap.xml — alle wet-URLs + hoofdpagina's (zoekmachine-neutraal)
    basis = "https://vrijewetgeving.nl"
    statisch = ["", "over.html", "api.html", "bevoegdheden.html", "bevoegdhedenketen.html", "rechten.html"]
    regels = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for s in statisch:
        regels.append(f"<url><loc>{basis}/{s}</loc></url>")
    for w in index:
        bid = w.get("identifier")
        if not bid:
            continue
        lm = f"<lastmod>{w['datum']}</lastmod>" if w.get("datum") else ""
        regels.append(f"<url><loc>{basis}/wet.html?id={bid}</loc>{lm}</url>")
    regels.append("</urlset>")
    Path(args.sitemap).write_text("\n".join(regels), encoding="utf-8")
    print(f"sitemap.xml: {len(index)+len(statisch)} URLs")


if __name__ == "__main__":
    main()
