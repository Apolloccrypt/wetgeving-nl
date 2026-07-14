#!/usr/bin/env python3
"""End-to-end regressiesuite voor vrijewetgeving.nl.

Draait tegen een lokale preview-server met Playwright (Chromium). Legt de
gedragingen vast die in de audit van 2026-07-14 gefixt zijn, zodat een latere
wijziging die weer breekt meteen opvalt.

Gebruik (op de NUC):
    # preview serveren vanuit de repo-root:
    python3 -m http.server 8766 --bind 127.0.0.1 -d /home/mick/vrijewetgeving-redesign/repo &
    /home/mick/Documents/BeforeYouMick/env/bin/python tests/e2e_vrijewetgeving.py

Vereist: een handvol echte wetten in wetten/ (voor de detailpagina) en de
samenvatting van BWBR0001854. Exit-code != 0 als een test faalt.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8766"
resultaten = []

def check(naam, conditie, detail=""):
    resultaten.append((naam, bool(conditie), detail))
    vlag = "PASS" if conditie else "FAIL"
    print(f"[{vlag}] {naam}" + (f" — {detail}" if detail else ""))

def wacht_zoekklaar(page, timeout=30000):
    page.wait_for_function("() => window.__zoekKlaar === true", timeout=timeout)

def run(page_factory):
    # ---------- HOMEPAGE ----------
    page = page_factory()
    reqs = []
    page.on("request", lambda r: reqs.append(r.url))
    page.goto(BASE + "/index.html", wait_until="networkidle")
    stat = page.inner_text("#stat-n")
    check("home: statteller gevuld", stat.replace(".", "").replace(" ", "").isdigit() and int(stat.replace(".", "").replace(" ", "")) > 19000, stat)

    # lazy zoekindex: nog niet geladen voor interactie
    geladen_voor = any("zoekindex.json" in u for u in reqs)
    check("home: zoekindex NIET geladen voor zoekintentie", not geladen_voor)

    # titelzoek werkt meteen
    page.fill("#zoek-mini", "huur")
    page.wait_for_timeout(300)
    n_titel = page.eval_on_selector_all(".wet-kaart", "els => els.length")
    check("home: titelzoek 'huur' geeft kaarten", n_titel > 0, f"{n_titel} kaarten")

    # nu wordt de zoekindex geladen (op zoekintentie)
    wacht_zoekklaar(page)
    check("home: zoekindex geladen na zoekintentie", any("zoekindex.json" in u for u in reqs))

    # BWBR-zoek: exacte wet moet bovenaan, geen 900+ valse treffers
    page.fill("#zoek-mini", "BWBR0001854")
    page.wait_for_timeout(400)
    info = page.inner_text("#info")
    subs = page.eval_on_selector_all(".wet-kaart .wet-sub", "els => els.map(e => e.textContent)")
    bevat = any("BWBR0001854" in s for s in subs[:5])
    check("home: BWBR-zoek toont exacte wet in top-5", bevat, info)
    check("home: BWBR-zoek geeft weinig treffers (geen 900+)", len(subs) < 50, f"{len(subs)} kaarten")

    # diakriet-vouwen: met en zonder accent even veel treffers
    def tel(term):
        page.fill("#zoek-mini", term)
        page.wait_for_timeout(400)
        return int(page.inner_text("#info").split()[0].replace(".", "").replace(" ", ""))
    a = tel("reintegratie"); b = tel("reïntegratie")
    check("home: diakriet-ongevoelig (reintegratie == reïntegratie)", a == b and a > 0, f"{a} vs {b}")

    # A-Z knop wordt 'Relevantie' tijdens full-text
    page.fill("#zoek-mini", "ontslag")
    page.wait_for_timeout(400)
    az_label = page.inner_text('.sort-btn[data-sort="az"]')
    check("home: A-Z heet 'Relevantie' tijdens full-text", az_label.strip() == "Relevantie", az_label)

    # filters: contextuele telling
    page.fill("#zoek-mini", "")
    page.wait_for_timeout(200)
    page.click("#dd-cat .dropdown-knop")
    page.wait_for_timeout(100)
    page.click('#dd-cat-menu .dd-optie[data-waarde="Strafrecht"]')
    page.wait_for_timeout(200)
    info_cat = page.inner_text("#info")
    check("home: categoriefilter Strafrecht telt", "Strafrecht" in info_cat, info_cat)

    # infinite scroll voegt toe (append), geen volledige herbouw
    page.goto(BASE + "/index.html", wait_until="networkidle")
    page.wait_for_timeout(300)
    n0 = page.eval_on_selector_all("#resultaten .wet-kaart", "els => els.length")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)
    n1 = page.eval_on_selector_all("#resultaten .wet-kaart", "els => els.length")
    check("home: infinite scroll laadt meer kaarten", n1 > n0, f"{n0} -> {n1}")

    # skip-link + main + aria-live aanwezig
    check("home: skip-link aanwezig", page.eval_on_selector_all("a.skip-link", "e=>e.length") == 1)
    check("home: <main> aanwezig", page.eval_on_selector_all("main#inhoud", "e=>e.length") == 1)
    check("home: aria-live op #info", page.get_attribute("#info", "aria-live") == "polite")

    # '/' focust de zoekbalk
    page.keyboard.press("/")
    focused = page.evaluate("() => document.activeElement.id")
    check("home: '/' focust zoekbalk", focused == "zoek-mini", focused)
    page.close()

    # ---------- WET.HTML ----------
    page = page_factory()
    page.goto(BASE + "/wet.html?id=BWBR0001854", wait_until="networkidle")
    page.wait_for_timeout(400)
    h1 = page.inner_text("h1")
    check("wet: titel gerenderd", len(h1) > 3, h1[:40])
    check("wet: inhoudsopgave gebouwd", page.eval_on_selector_all("#toc a", "e=>e.length") > 1)
    check("wet: 'In het kort'-samenvatting bij BWBR0001854", page.eval_on_selector_all(".samenvatting", "e=>e.length") >= 1)
    # jci-links omgezet naar intern
    intern = page.eval_on_selector_all('#tekst a[href^="wet.html?id="]', "e=>e.length")
    check("wet: in-tekst jci-links omgezet naar intern", intern > 0, f"{intern} interne links")
    # nog externe wetten.overheid.nl in-tekst? (toegestaan voor onbekende wetten, maar er moeten interne bij zijn)
    # error-pad
    page.goto(BASE + "/wet.html?id=BWBR9999999", wait_until="networkidle")
    check("wet: onbekend id toont nette melding", "niet gevonden" in page.inner_text(".wet-melding").lower())
    page.goto(BASE + "/wet.html?id=../../etc/passwd", wait_until="networkidle")
    check("wet: kwaadaardig id geweigerd", "geldige" in page.inner_text(".wet-melding").lower())
    # mobiele TOC ingeklapt
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(BASE + "/wet.html?id=BWBR0001854", wait_until="networkidle")
    page.wait_for_timeout(400)
    open_attr = page.get_attribute("#toc-details", "open")
    check("wet: mobiele inhoudsopgave ingeklapt", open_attr is None)
    page.close()

    # ---------- BEVOEGDHEDEN ----------
    page = page_factory()
    page.goto(BASE + "/bevoegdheden.html", wait_until="networkidle")
    page.wait_for_timeout(1500)  # laadt index + zoekindex
    # resultaatrij is een button (toetsenbord)
    page.fill("#zoek", "mandaat")
    page.wait_for_timeout(600)
    tag = page.eval_on_selector(".besluit-item", "e => e.tagName") if page.query_selector(".besluit-item") else ""
    check("bevoegdheden: resultaatrij is <button>", tag == "BUTTON", tag)
    # autocomplete opent de wet (i.p.v. 0 treffers)
    page.fill("#zoek", "politie")
    page.wait_for_timeout(600)
    if page.query_selector(".ac-item"):
        page.click(".ac-item")
        page.wait_for_timeout(300)
        detail = page.inner_text("#detail")
        telling = page.inner_text("#telling")
        check("bevoegdheden: AC opent de wet (1 treffer, detail gevuld)", "1 wet" in telling and len(detail) > 30, telling)
    else:
        check("bevoegdheden: AC-suggestie beschikbaar", False, "geen ac-item")
    # cap-melding bij brede zoekterm
    page.fill("#zoek", "minister")
    page.wait_for_timeout(600)
    heeft_cap = page.eval_on_selector_all(".cap-melding", "e=>e.length") >= 1
    check("bevoegdheden: cap-melding bij >150 treffers", heeft_cap)
    page.close()

    # ---------- KETEN ----------
    page = page_factory()
    page.goto(BASE + "/bevoegdhedenketen.html", wait_until="networkidle")
    page.wait_for_timeout(800)
    page.fill("#zoek", "minister")
    page.wait_for_timeout(400)
    tagk = page.eval_on_selector(".besluit-item", "e => e.tagName") if page.query_selector(".besluit-item") else ""
    check("keten: resultaatrij is <button>", tagk == "BUTTON", tagk)
    check("keten: cap-melding bij >100 treffers", page.eval_on_selector_all(".cap-melding", "e=>e.length") >= 1)
    page.close()

    # ---------- RECHTEN ----------
    page = page_factory()
    reqs2 = []
    page.on("request", lambda r: reqs2.append(r.url))
    page.goto(BASE + "/rechten.html", wait_until="networkidle")
    page.wait_for_timeout(500)
    check("rechten: zoekindex NIET gedownload (36 MB bespaard)", not any("zoekindex.json" in u for u in reqs2))
    # dode situatie-knop nu gevuld: Patient -> Medisch dossier
    page.click('.rol-btn:has-text("Patient")')
    page.wait_for_timeout(300)
    page.click('.sit-btn:has-text("Medisch dossier")')
    page.wait_for_timeout(300)
    leeg = page.query_selector(".leeg")
    check("rechten: 'Medisch dossier' geeft nu resultaten (was dood)", leeg is None)
    page.close()

    # ---------- SERVICE WORKER / OFFLINE ----------
    ctx = page_factory.__self__ if hasattr(page_factory, "__self__") else None
    page = page_factory()
    page.goto(BASE + "/index.html", wait_until="networkidle")
    page.evaluate("() => navigator.serviceWorker && navigator.serviceWorker.ready")
    page.wait_for_timeout(1500)
    # ga offline en navigeer naar een wet met query-string
    try:
        page.context.set_offline(True)
        r = page.goto(BASE + "/wet.html?id=BWBR0001854", wait_until="domcontentloaded")
        ok = r is not None and r.status < 400
        check("sw: wet.html?id werkt offline (ignoreSearch)", ok, f"status {r.status if r else 'None'}")
        r2 = page.goto(BASE + "/", wait_until="domcontentloaded")
        check("sw: start_url / werkt offline", r2 is not None and r2.status < 400)
    except Exception as e:
        check("sw: offline-test", False, str(e)[:80])
    finally:
        page.context.set_offline(False)
    page.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(bypass_csp=True, service_workers="allow")
        def factory():
            return context.new_page()
        try:
            run(factory)
        finally:
            context.close(); browser.close()

    fails = [r for r in resultaten if not r[1]]
    print("\n" + "=" * 50)
    print(f"TOTAAL {len(resultaten)}  PASS {len(resultaten)-len(fails)}  FAIL {len(fails)}")
    if fails:
        print("Gefaald:")
        for naam, _, detail in fails:
            print(f"  - {naam} ({detail})")
        sys.exit(1)
    print("ALLE TESTS GESLAAGD")


if __name__ == "__main__":
    main()
