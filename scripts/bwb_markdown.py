#!/usr/bin/env python3
"""
bwb_markdown.py — BWB-toestand-XML omzetten naar de Markdown die deze site gebruikt.

De oude converter in dagelijkse_update.py is geschreven op een schema dat de
BWB-repository niet levert. Gevolg op elke wet die langs die weg binnenkwam:

  * elk artikel werd "Artikel ?" — het nummer staat in <kop><nr>, niet in @nr;
  * Staatsblad-metadata lekte de wettekst in — de skip-lijst noemt "metadata",
    het schema heet "meta-data";
  * geen datum in de frontmatter, waardoor de wet datumloos in de index landt;
  * geen soort, waardoor de wet als type "Overig" eindigt.

Deze module volgt het echte schema (BWB-toestand 2016-1) en de Markdown-conventie
van de bestaande 19.631 bestanden: '### Hoofdstuk N. Titel', '##### Artikel N',
leden als genummerde alinea's.

Gebruik:
    python scripts/bwb_markdown.py BWBR0001840          # haalt op en converteert
    python scripts/bwb_markdown.py --xml bestand.xml BWBR0001840
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from typing import Optional
from xml.etree import ElementTree as ET

# ── Wat nooit in de wettekst hoort ───────────────────────────────────────────
# Administratie van de uitgever: bronvermeldingen, revisienummers, jci-verwijzingen.
NEGEER = {
    "meta-data", "brondata", "jcis", "jci", "redactionele-correcties",
    "redactionele-correctie", "bwb-inputbestand", "bwb-wijzigingen",
    "wijzig-artikel", "wijzig-lid", "wijzigingen", "oorspronkelijk",
    "inwerkingtreding", "inwerkingtreding.datum", "publicatie", "publicatiejaar",
    "publicatienr", "uitgiftedatum", "ondertekeningsdatum", "dossierref",
    "verdragdata", "parlementair", "nootref",
}
# <redactie> hoort er juist wel in: daar staat "Vervallen" of "[Red: ...]".
# Die weglaten levert een artikelkop zonder enige tekst eronder.

# Structuurelementen en hun kopniveau, in de conventie die de site al gebruikt.
STRUCTUUR = {
    "boek": 2, "deel": 2, "hoofdstuk": 3, "titeldeel": 3, "titel-deel": 3,
    "afdeling": 4, "paragraaf": 4, "sub-paragraaf": 5, "subparagraaf": 5,
    # circulaires en beleidsregels kennen geen artikelen maar genummerde
    # divisies; zonder deze regel bleef hun tekst helemaal buiten beeld
    "circulaire.divisie": 3, "divisie": 3,
}

# Waar de leestekst begint. Per soort regeling een ander element: wetten hebben
# <wettekst>, regelingen <regeling-tekst>, circulaires <circulaire-tekst>.
TEKST_WORTELS = ("wettekst", "regeling-tekst", "verdragtekst", "circulaire-tekst")

CATEGORIE_TREFWOORDEN = {
    "strafrecht":        ["strafrecht", "strafbaar", "strafvordering", "penitentiair"],
    "burgerlijk-recht":  ["burgerlijk", "vermogensrecht", "verbintenis", "erfrecht", "huwelijk"],
    "arbeidsrecht":      ["arbeid", "werknemer", "werkgever", "minimumloon", "cao"],
    "belastingrecht":    ["belasting", "inkomstenbelasting", "omzetbelasting", "btw", "accijns", "douane"],
    "bestuursrecht":     ["bestuur", "gemeente", "provincie", "omgevings", "vergunning", "awb"],
    "sociaal-recht":     ["bijstand", "uitkering", "sociale", "wmo", "wia", "werkloosheid", "pensioen"],
    "gezondheidszorg":   ["gezondheid", "geneeskundig", "medisch", "ziekenhuis", "zorgverzekering", "geneesmiddel"],
    "onderwijs":         ["onderwijs", "school", "universiteit", "leerplicht", "studiefinanciering"],
    "milieu":            ["milieu", "natuur", "water", "bodem", "klimaat", "afval", "stikstof"],
    "verkeer":           ["verkeer", "wegenverkeer", "rijbewijs", "luchtvaart", "spoorweg", "scheepvaart"],
    "digitaal":          ["persoonsgegevens", "privacy", "avg", "telecommunicatie", "digitale", "cyber"],
    "internationaal-recht": ["verdrag", "internationaal", "europese"],
    "staatsinrichting":  ["grondwet", "kiesrecht", "rijkswet", "rechterlijke", "koninkrijk"],
    "financieel-recht":  ["financieel toezicht", "wft", "financiele markten", "effecten", "verzekeraar", "bank"],
}

CATEGORIE_NAAM = {
    "staatsinrichting": "Staatsinrichting en bestuur", "bestuursrecht": "Bestuursrecht",
    "burgerlijk-recht": "Burgerlijk recht", "strafrecht": "Strafrecht",
    "arbeidsrecht": "Arbeidsrecht", "belastingrecht": "Belastingrecht",
    "sociaal-recht": "Sociaal recht", "onderwijs": "Onderwijs",
    "gezondheidszorg": "Gezondheidszorg", "digitaal": "Digitaal en privacy",
    "milieu": "Milieu", "verkeer": "Verkeer",
    "internationaal-recht": "Internationaal recht", "financieel-recht": "Financieel recht",
    "overig": "Overig",
}


def slugify(tekst: str) -> str:
    tekst = unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode()
    tekst = re.sub(r"[^\w\s-]", "", tekst).strip().lower()
    return re.sub(r"[\s_-]+", "-", tekst)[:80]


def bepaal_categorie(titel: str) -> str:
    laag = (titel or "").lower()
    for cat, woorden in CATEGORIE_TREFWOORDEN.items():
        if any(w in laag for w in woorden):
            return cat
    return "overig"


def _tag(el) -> str:
    return el.tag.split("}")[-1].lower()


def _plat(el, negeer_structuur: bool = True) -> str:
    """Alle leestekst van een element, zonder de administratie van de uitgever."""
    if el is None:
        return ""
    delen = []
    if el.text:
        delen.append(el.text)
    for kind in el:
        if _tag(kind) in NEGEER:
            if kind.tail:
                delen.append(kind.tail)
            continue
        if negeer_structuur and _tag(kind) in STRUCTUUR:
            continue
        delen.append(_plat(kind, negeer_structuur))
        if kind.tail:
            delen.append(kind.tail)
    return re.sub(r"\s+", " ", "".join(delen)).strip()


def _kop(el) -> tuple[str, str, str]:
    """(label, nummer, titel) uit een <kop>-element."""
    kop = el.find("kop")
    if kop is None:
        return "", "", ""
    def t(naam):
        k = kop.find(naam)
        return re.sub(r"\s+", " ", "".join(k.itertext())).strip() if k is not None else ""
    return t("label"), t("nr"), t("titel")


def _inline(el) -> str:
    """Tekst van een alinea, met verwijzingen als links."""
    delen = []
    if el.text:
        delen.append(el.text)
    for kind in el:
        tag = _tag(kind)
        if tag in NEGEER:
            if kind.tail:
                delen.append(kind.tail)
            continue
        binnen = _inline(kind)
        if tag in ("intref", "extref"):
            # De jci-verwijzing bevat het artikelnummer; de site zet die om naar
            # een interne link met anker, dus hem meenemen is winst.
            doel = kind.get("doc") or kind.get("url") or ""
            bwb = kind.get("bwb-id") or (re.search(r"BWB[RVW]\d+", doel) or [""])[0]
            if binnen and doel.startswith("jci"):
                delen.append(f"[{binnen}](https://wetten.overheid.nl/{doel})")
            elif binnen and bwb:
                delen.append(f"[{binnen}](https://wetten.overheid.nl/{bwb})")
            elif binnen and doel.startswith("http"):
                delen.append(f"[{binnen}]({doel})")
            else:
                delen.append(binnen)
        elif tag in ("nadruk", "cursief", "vet", "redactie"):
            delen.append(f"*{binnen}*" if binnen else "")
        else:
            delen.append(binnen)
        if kind.tail:
            delen.append(kind.tail)
    return re.sub(r"[ \t]+", " ", "".join(delen)).strip()


def _tabel(el) -> list[str]:
    """Een <table> als echte Markdown-tabel; de oude converter gooide hem weg."""
    rijen = []
    for tr in el.iter():
        if _tag(tr) != "row":
            continue
        cellen = [_plat(td).replace("|", "\\|") for td in tr if _tag(td) == "entry"]
        if cellen:
            rijen.append(cellen)
    if not rijen:
        return []
    breedte = max(len(r) for r in rijen)
    rijen = [r + [""] * (breedte - len(r)) for r in rijen]
    uit = ["", "| " + " | ".join(rijen[0]) + " |",
           "| " + " | ".join(["---"] * breedte) + " |"]
    for r in rijen[1:]:
        uit.append("| " + " | ".join(r) + " |")
    uit.append("")
    return uit


def _lijst(el, inspring: str = "") -> list[str]:
    uit = []
    for li in el:
        if _tag(li) != "li":
            continue
        nr_el = li.find("li.nr")
        nr = _plat(nr_el).strip() if nr_el is not None else ""
        tekstdelen, subs = [], []
        for kind in li:
            k = _tag(kind)
            if k in ("li.nr",) or k in NEGEER:
                continue
            if k == "al":
                tekstdelen.append(_inline(kind))
            elif k == "lijst":
                subs.extend(_lijst(kind, inspring + "   "))
            else:
                t = _inline(kind)
                if t:
                    tekstdelen.append(t)
        tekst = " ".join(d for d in tekstdelen if d).strip()
        if tekst or nr:
            # conventie van de bestaande bestanden: "- a. tekst", losse alinea's
            uit.append(f"{inspring}- {nr} {tekst}".replace("-  ", "- ").rstrip())
            uit.append("")
        uit.extend(subs)
    return uit


def _blok(el, uit: list[str]) -> None:
    """Zet een structuur- of tekstelement om naar Markdown-regels."""
    tag = _tag(el)

    if tag in NEGEER:
        return

    if tag in STRUCTUUR:
        label, nr, titel = _kop(el)
        onderdelen = [d for d in (f"{label} {nr}".strip(), titel) if d]
        kop = ". ".join(onderdelen) if len(onderdelen) == 2 else (onderdelen[0] if onderdelen else "")
        if kop:
            uit.append("")
            uit.append("#" * STRUCTUUR[tag] + " " + kop)
        for kind in el:
            if _tag(kind) != "kop":
                _blok(kind, uit)
        return

    if tag == "artikel":
        label, nr, titel = _kop(el)
        if nr:
            kop = f"{label or 'Artikel'} {nr}".strip()
            if titel:
                kop += f". {titel}"
        else:
            kop = titel or label or "Artikel"
        uit.append("")
        uit.append("##### " + kop)
        uit.append("")
        for kind in el:
            if _tag(kind) != "kop":
                _blok(kind, uit)
        return

    if tag == "lid":
        nr_el = el.find("lidnr")
        nr = _plat(nr_el).strip() if nr_el is not None else ""
        regels: list[str] = []
        for kind in el:
            if _tag(kind) in ("lidnr",) or _tag(kind) in NEGEER:
                continue
            _blok(kind, regels)
        while regels and not regels[0].strip():
            regels.pop(0)
        if not regels:
            return
        uit.append("")
        # het lidnummer voor de eerste alinea; de rest (lijsten, tabellen)
        # blijft staan zoals hij is, inclusief de lege regels die hem scheiden
        uit.append(f"{nr}. {regels[0].lstrip()}" if nr else regels[0].lstrip())
        uit.extend(regels[1:])
        return

    if tag == "al":
        t = _inline(el)
        if t:
            uit.append("")
            uit.append(t)
        return

    if tag == "lijst":
        regels = _lijst(el)
        if regels:
            uit.append("")
            uit.extend(regels)
        return

    if tag in ("table", "tabel"):
        uit.extend(_tabel(el))
        return

    if tag in ("aanhef", "considerans", "preambule"):
        t = _plat(el)
        if t:
            uit.append("")
            uit.append(f"*{t}*")
        return

    if tag in ("kop", "citeertitel", "intitule"):
        return

    # onbekend element: doorlopen naar de kinderen, alleen eigen tekst meenemen
    eigen = (el.text or "").strip()
    if eigen:
        uit.append("")
        uit.append(re.sub(r"\s+", " ", eigen))
    for kind in el:
        _blok(kind, uit)


def _meta(root) -> dict:
    """Titel, citeertitel, soort en datums uit de kop van de toestand."""
    wetgeving = None
    for el in root.iter():
        if _tag(el) in ("wetgeving", "regeling"):
            wetgeving = el
            break
    bron = wetgeving if wetgeving is not None else root

    def eerste(naam) -> Optional[ET.Element]:
        for el in bron.iter():
            if _tag(el) == naam:
                return el
        return None

    intitule = eerste("intitule")
    citeer = eerste("citeertitel")
    titel_lang = _plat(intitule) if intitule is not None else ""
    citeertitel = _plat(citeer) if citeer is not None else ""

    return {
        "titel": titel_lang or citeertitel,
        "citeertitel": citeertitel,
        "soort": (wetgeving.get("soort") if wetgeving is not None else "") or "",
        "inwerkingtreding": (wetgeving.get("inwerkingtredingsdatum") if wetgeving is not None else "") or "",
        "toestand": root.get("inwerkingtreding", ""),
    }


def converteer(xml_tekst: str, identifier: str, kaart: Optional[dict] = None) -> Optional[str]:
    """BWB-toestand-XML -> Markdown met volledige frontmatter.

    `kaart` is de manifestkaart uit bwb_bron.manifest(): die levert de
    geldigheid en de toestandsdatum, zodat de status niet geraden hoeft te worden.
    """
    try:
        root = ET.fromstring(xml_tekst)
    except ET.ParseError:
        return None

    meta = _meta(root)
    titel = meta["titel"] or meta["citeertitel"] or identifier

    tekst_wortel = None
    for el in root.iter():
        if _tag(el) in TEKST_WORTELS:
            tekst_wortel = el
            break
    if tekst_wortel is None:
        return None

    regels: list[str] = [f"# {titel}", ""]
    for kind in tekst_wortel:
        _blok(kind, regels)

    body = "\n".join(regels)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) < 40:          # niets bruikbaars geconverteerd
        return None

    kaart = kaart or {}
    geldend = kaart.get("geldend", True)
    toestand = kaart.get("ingegaan") or meta["toestand"] or ""
    categorie = bepaal_categorie(f"{titel} {meta['citeertitel']}")

    fm = ["---", f'title: "{titel.replace(chr(34), chr(39))}"']
    if meta["citeertitel"] and meta["citeertitel"] != titel:
        fm.append(f'citeertitel: "{meta["citeertitel"].replace(chr(34), chr(39))}"')
    fm.append(f'identifier: "{identifier}"')
    fm.append(f'categorie: "{CATEGORIE_NAAM.get(categorie, "Overig")}"')
    if meta["soort"]:
        fm.append(f'soort: "{meta["soort"]}"')
    if meta["inwerkingtreding"]:
        fm.append(f"publicatiedatum: {meta['inwerkingtreding'][:10]}")
    if toestand:
        fm.append(f"laatste_update: {toestand[:10]}")
    fm.append(f"status: {'geldig' if geldend else 'vervallen'}")
    if not geldend and kaart.get("eind"):
        fm.append(f"vervallen_op: {kaart['eind'][:10]}")
    fm.append(f"toestand: {toestand[:10]}" if toestand else "toestand: ")
    fm.append(f'bron: "https://wetten.overheid.nl/{identifier}"')
    fm.append(f"opgehaald: {date.today().isoformat()}")
    fm.append("---")

    return "\n".join(fm) + "\n\n" + body + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="BWB-XML naar Markdown")
    p.add_argument("identifier")
    p.add_argument("--xml", help="Lokaal XML-bestand in plaats van ophalen")
    p.add_argument("--uit", help="Wegschrijven naar bestand")
    args = p.parse_args()

    kaart = None
    if args.xml:
        xml = open(args.xml, encoding="utf-8").read()
    else:
        sys.path.insert(0, str(__file__.rsplit("/", 1)[0]))
        import bwb_bron
        res = bwb_bron.haal_wettekst(args.identifier)
        if not res:
            print(f"Geen wettekst voor {args.identifier}", file=sys.stderr)
            return 1
        xml, kaart = res

    md = converteer(xml, args.identifier, kaart)
    if not md:
        print(f"Conversie mislukt voor {args.identifier}", file=sys.stderr)
        return 1
    if args.uit:
        open(args.uit, "w", encoding="utf-8").write(md)
        print(f"{len(md)} tekens -> {args.uit}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
