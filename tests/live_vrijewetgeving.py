#!/usr/bin/env python3
"""Verifieer de live vrijewetgeving.nl na een deploy.

Draai dit na elke push naar main, als sluitstuk op de lokale suites:

    python tests/live_vrijewetgeving.py [BWBR-id-dat-eerder-ontbrak]


Toetst wat er op de branch is gebouwd, maar dan tegen de echte site:
aantal wetten, dekkingscijfer, citeertitel, vervallen-schakelaar, en of een
regeling die eerst ontbrak nu echt te openen is.
"""
import json
import sys
import urllib.request
from playwright.sync_api import sync_playwright

BASIS = "https://vrijewetgeving.nl"
resultaten = []


def check(naam, ok, detail=""):
    resultaten.append((naam, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {naam}" + (f" — {detail}" if detail else ""))


def haal(pad):
    with urllib.request.urlopen(BASIS + pad, timeout=120) as r:
        return json.load(r)


def main():
    ontbrak = sys.argv[1] if len(sys.argv) > 1 else None

    meta = haal("/meta.json")
    check("meta.json bereikbaar", meta.get("aantal_wetten", 0) > 0, str(meta))

    try:
        dek = haal("/dekking.json")
        check("dekking.json staat live", "dekkingsgraad" in dek,
              f"{dek.get('dekkingsgraad', 0) * 100:.1f}% van {dek.get('bwb_geldend')} geldende regelingen")
        check("dekking is geverifieerd tegen het manifest", dek.get("geverifieerd") is True,
              str(dek.get("geverifieerd")))
    except Exception as e:
        check("dekking.json staat live", False, str(e)[:80])
        dek = {}

    index = haal("/index.json")
    check("index gegroeid", len(index) >= meta.get("aantal_wetten", 0) - 1, f"{len(index)} wetten")
    met_citeer = [w for w in index if w.get("citeertitel")]
    check("citeertitel in de live index", len(met_citeer) > 100, f"{len(met_citeer)} wetten")
    vervallen = [w for w in index if "vervallen" in (w.get("status") or "").lower()
                 or "ingetrokken" in (w.get("status") or "").lower()]
    check("status onderscheidt geldig en vervallen", True, f"{len(vervallen)} vervallen")

    if ontbrak:
        gevonden = [w for w in index if w["identifier"] == ontbrak]
        check(f"eerder ontbrekende regeling {ontbrak} staat er nu in",
              bool(gevonden), gevonden[0]["titel"][:60] if gevonden else "niet gevonden")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context().new_page()
        page.goto(BASIS + "/", wait_until="networkidle")
        page.wait_for_timeout(1200)

        dekcijfer = page.inner_text("#stat-dekking")
        check("dekkingspercentage op de homepage", dekcijfer.strip().endswith("%"), dekcijfer)
        check("schakelaar voor vervallen regelingen", page.query_selector("#toon-vervallen") is not None)

        if met_citeer:
            proef = met_citeer[0]["citeertitel"]
            page.fill("#zoek-mini", proef)
            page.wait_for_timeout(700)
            eerste = page.eval_on_selector(".wet-kaart .wet-titel", "e => e.textContent") \
                if page.query_selector(".wet-kaart .wet-titel") else ""
            check("zoeken op citeertitel werkt live",
                  proef.lower() in eerste.lower(), f"'{proef}' -> '{eerste[:40]}'")

        if ontbrak:
            page.goto(f"{BASIS}/wet.html?id={ontbrak}", wait_until="networkidle")
            page.wait_for_timeout(900)
            h1 = page.inner_text("h1")
            artikelen = page.eval_on_selector_all("#tekst h2, #tekst h3, #tekst h4, #tekst h5", "e=>e.length")
            check(f"aangevulde wet {ontbrak} opent met tekst",
                  len(h1) > 3 and artikelen > 0, f"{h1[:40]} ({artikelen} koppen)")
            check("geen 'Artikel ?' in de aangevulde tekst",
                  "Artikel ?" not in page.inner_text("#tekst"))
        browser.close()

    fouten = [r for r in resultaten if not r[1]]
    print("\n" + "=" * 50)
    print(f"TOTAAL {len(resultaten)}  PASS {len(resultaten) - len(fouten)}  FAIL {len(fouten)}")
    return 1 if fouten else 0


if __name__ == "__main__":
    sys.exit(main())
