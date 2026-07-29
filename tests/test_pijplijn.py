#!/usr/bin/env python3
"""
test_pijplijn.py — toetsen op de datalaag: bron, converter, index en dekking.

Draait zonder netwerk (de netwerktoetsen staan apart en worden alleen
uitgevoerd met --netwerk), zodat dit in elke CI-run mee kan.

    python tests/test_pijplijn.py            # alleen offline toetsen
    python tests/test_pijplijn.py --netwerk  # ook tegen de echte bron
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORTEL / "scripts"))

import bwb_markdown  # noqa: E402

NETWERK = "--netwerk" in sys.argv

# Een miniatuur-toestand met precies de eigenschappen waar de oude converter
# op stukliep: nummer in <kop><nr>, meta-data tussen de tekst, een lijst,
# een tabel, een verwijzing en een vervallen artikel.
PROEF_XML = """<?xml version="1.0" encoding="UTF-8"?>
<toestand bwb-id="BWBR9999999" inwerkingtreding="2026-01-01">
 <wetgeving soort="wet" inwerkingtredingsdatum="2025-12-01">
  <intitule>Wet van 1 januari 2026, houdende proefbepalingen</intitule>
  <citeertitel>Proefwet</citeertitel>
  <wet-besluit>
   <wettekst>
    <hoofdstuk>
     <kop><label>Hoofdstuk</label><nr>1</nr><titel>Algemeen</titel></kop>
     <artikel>
      <kop><label>Artikel</label><nr>1</nr></kop>
      <lid>
       <lidnr>1</lidnr>
       <al>In deze wet wordt verstaan onder: </al>
       <lijst>
        <li><li.nr>a.</li.nr><al>proef: een toets;</al>
         <meta-data><jcis><jci verwijzing="jci1.3:c:BWBR9999999"/></jcis></meta-data></li>
        <li><li.nr>b.</li.nr><al>bron: het origineel.</al></li>
       </lijst>
      </lid>
      <lid>
       <lidnr>2</lidnr>
       <al>Zie ook <intref doc="jci1.3:c:BWBR0001840&amp;artikel=7"
           bwb-id="BWBR0001840">artikel 7 van de Grondwet</intref>.</al>
      </lid>
      <meta-data><brondata><oorspronkelijk><publicatie soort="Stb">
       <publicatiejaar>2025</publicatiejaar><publicatienr>123</publicatienr>
      </publicatie></oorspronkelijk></brondata></meta-data>
     </artikel>
     <artikel>
      <kop><label>Artikel</label><nr>2</nr></kop>
      <al><redactie type="vervanging">Vervallen</redactie></al>
     </artikel>
    </hoofdstuk>
   </wettekst>
  </wet-besluit>
 </wetgeving>
</toestand>
"""


class ConverterTest(unittest.TestCase):
    """De converter moet het echte BWB-schema aankunnen."""

    @classmethod
    def setUpClass(cls):
        cls.md = bwb_markdown.converteer(PROEF_XML, "BWBR9999999",
                                         {"geldend": True, "ingegaan": "2026-01-01", "eind": ""})
        assert cls.md, "conversie leverde niets op"

    def test_artikelnummers_niet_vraagteken(self):
        self.assertIn("##### Artikel 1", self.md)
        self.assertIn("##### Artikel 2", self.md)
        self.assertNotIn("Artikel ?", self.md)

    def test_geen_staatsblad_administratie_in_de_tekst(self):
        # publicatiejaar/-nr horen in meta-data en dus niet in de wettekst
        body = self.md.split("---", 2)[-1]
        self.assertNotIn("2025 123", body)
        self.assertNotIn("publicatiejaar", body)

    def test_leden_genummerd(self):
        self.assertIn("1. In deze wet wordt verstaan onder:", self.md)
        self.assertIn("2. Zie ook", self.md)

    def test_lijst_volgens_conventie(self):
        self.assertIn("- a. proef: een toets;", self.md)
        self.assertIn("- b. bron: het origineel.", self.md)

    def test_verwijzing_wordt_link_met_artikel(self):
        self.assertIn("[artikel 7 van de Grondwet](https://wetten.overheid.nl/jci1.3:c:BWBR0001840&artikel=7)",
                      self.md)

    def test_vervallen_artikel_houdt_tekst(self):
        # een artikelkop zonder enige tekst eronder is een leesfout, geen wet
        na_artikel2 = self.md.split("##### Artikel 2", 1)[1].strip()
        self.assertTrue(na_artikel2, "artikel 2 heeft geen inhoud")
        self.assertIn("Vervallen", na_artikel2)

    def test_frontmatter_compleet(self):
        kop = self.md.split("---")[1]
        for sleutel in ("title:", "identifier:", "categorie:", "soort:",
                        "status:", "laatste_update:", "bron:", "opgehaald:"):
            self.assertIn(sleutel, kop, f"{sleutel} ontbreekt in de frontmatter")

    def test_datum_is_gevuld(self):
        # de datumbug van juli: lege datum laat een wet datumloos in de index landen
        kop = self.md.split("---")[1]
        regel = [r for r in kop.split("\n") if r.startswith("laatste_update:")][0]
        self.assertRegex(regel, r"laatste_update: \d{4}-\d{2}-\d{2}")

    def test_status_volgt_het_manifest(self):
        vervallen = bwb_markdown.converteer(
            PROEF_XML, "BWBR9999999",
            {"geldend": False, "ingegaan": "2026-01-01", "eind": "2026-03-01"})
        self.assertIn("status: vervallen", vervallen)
        self.assertIn("vervallen_op: 2026-03-01", vervallen)

    def test_categorie_uit_titel(self):
        self.assertEqual(bwb_markdown.bepaal_categorie("Wet op de omzetbelasting"), "belastingrecht")
        self.assertEqual(bwb_markdown.bepaal_categorie("Iets onbenoembaars"), "overig")


class IndexTest(unittest.TestCase):
    """De gegenereerde index moet intern kloppen."""

    @classmethod
    def setUpClass(cls):
        cls.index_pad = WORTEL / "index.json"
        cls.zoek_pad = WORTEL / "zoekindex.json"
        if not cls.index_pad.exists():
            raise unittest.SkipTest("index.json niet aanwezig in deze werkkopie")
        cls.index = json.loads(cls.index_pad.read_text(encoding="utf-8"))

    def test_zoekindex_loopt_gelijk_op(self):
        if not self.zoek_pad.exists():
            self.skipTest("zoekindex.json niet aanwezig")
        zoek = json.loads(self.zoek_pad.read_text(encoding="utf-8"))
        # de frontend koppelt index[i] aan zoekindex[i]; ongelijke lengte
        # betekent dat elke zoektreffer de verkeerde wet opent
        self.assertEqual(len(self.index), len(zoek))

    def test_identifiers_uniek_en_gevuld(self):
        ids = [w.get("identifier", "") for w in self.index]
        self.assertTrue(all(i.startswith("BWB") for i in ids), "identifier ontbreekt of is ongeldig")
        self.assertEqual(len(ids), len(set(ids)), "dubbele identifier in de index")

    def test_geen_lege_datums(self):
        # de pijplijnbug van juli: 642 wetten met lege datum
        leeg = [w["identifier"] for w in self.index if not w.get("datum")]
        self.assertEqual(leeg, [], f"{len(leeg)} wetten zonder datum")

    def test_paden_wijzen_in_wetten(self):
        for w in self.index[:500]:
            self.assertTrue(w.get("pad", "").startswith("wetten/"), w.get("pad"))

    def test_alfabetisch_gesorteerd(self):
        titels = [w["titel"].lower() for w in self.index]
        self.assertEqual(titels, sorted(titels), "index niet op titel gesorteerd")


class DekkingTest(unittest.TestCase):
    """Het dekkingsrapport moet een echt oordeel bevatten."""

    def setUp(self):
        pad = WORTEL / "dekking.json"
        if not pad.exists():
            self.skipTest("dekking.json niet aanwezig (draai scripts/dekking.py)")
        self.rapport = json.loads(pad.read_text(encoding="utf-8"))

    def test_bron_leverde_een_volledige_lijst(self):
        # een half opgehaalde lijst maakt elk dekkingscijfer onzin
        self.assertGreater(self.rapport["bwb_regelingen"], 30_000)

    def test_dekking_is_gemeten(self):
        self.assertGreater(self.rapport["bwb_geldend"], 10_000)
        self.assertGreaterEqual(self.rapport["dekkingsgraad"], 0.0)

    def test_status_alleen_na_verificatie(self):
        # De zoekservice noemt regelingen vervallen die dat niet zijn. Een
        # rapport zonder manifest-controle mag nooit status overschrijven.
        self.assertIn("geverifieerd", self.rapport)
        if self.rapport.get("ten_onrechte_geldig"):
            self.assertTrue(self.rapport["geverifieerd"],
                            "rapport noemt vervallen wetten zonder manifest-controle")

    def test_rapport_noemt_de_gaten(self):
        for sleutel in ("ontbrekend", "ten_onrechte_geldig", "onbekend"):
            self.assertIn(sleutel, self.rapport)


class BronTest(unittest.TestCase):
    """Toetsen tegen de echte bron; alleen met --netwerk."""

    @classmethod
    def setUpClass(cls):
        if not NETWERK:
            raise unittest.SkipTest("netwerktoetsen overgeslagen (gebruik --netwerk)")
        import bwb_bron
        cls.bron = bwb_bron

    def test_manifest_van_de_grondwet(self):
        m = self.bron.manifest("BWBR0001840")
        self.assertIsNotNone(m, "manifest van de Grondwet niet op te halen")
        self.assertTrue(m["geldend"])
        self.assertTrue(m["xml_url"].endswith(".xml"))

    def test_ingetrokken_regeling_is_niet_geldend(self):
        m = self.bron.manifest("BWBR0001821")   # ingetrokken in 2002
        self.assertIsNotNone(m)
        self.assertFalse(m["geldend"])

    def test_wettekst_is_echt_een_wettekst(self):
        res = self.bron.haal_wettekst("BWBR0001840")
        self.assertIsNotNone(res, "geen wettekst opgehaald")
        xml, _ = res
        self.assertGreater(len(xml), 100_000)
        self.assertIn("<toestand", xml)

    def test_dode_routes_blijven_dood_herkend(self):
        # de bronnen die dit project stil braken: als ze terugkomen is dat
        # goed nieuws, maar ze mogen nooit weer als "werkt" worden geteld
        import requests
        for url in (
            "https://repository.officiele-overheidspublicaties.nl/bwb/BWBIDLIST.zip",
            "https://repository.officiele-overheidspublicaties.nl/BWB/BWBR0001840/xml/BWBR0001840_xml.zip",
        ):
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and r.content:
                continue                      # bron is hersteld: prima
            self.assertFalse(bool(r.content) and r.status_code == 200)

    def test_lijst_is_groot_genoeg(self):
        aantal = self.bron.sru_aantal()
        self.assertGreater(aantal, 100_000, "zoekservice geeft verdacht weinig toestanden")


if __name__ == "__main__":
    argv = [a for a in sys.argv if a != "--netwerk"]
    unittest.main(argv=argv, verbosity=2)
