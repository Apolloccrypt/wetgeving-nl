# 🇳🇱 wetgeving-nl

> Nederlandse wetgeving in Markdown — elke wet een bestand, elke wijziging een commit, elke burger een potentiële bijdrager.

Geïnspireerd door [legalize-es](https://github.com/legalize-dev/legalize-es) (Spanje), maar dan beter en met een echte community-laag voor wetsvoorstellen.

---

## Waarom dit project?

Officiële wetten zijn publiek eigendom — maar wetten.overheid.nl is ontoegankelijk, wijzigingen zijn onvindbaar en burgers hebben geen stem.

Dit project maakt wetgeving:
- **Leesbaar** → schone Markdown, geen juridisch HTML-geknoei
- **Traceerbaar** → elke wetswijziging = één commit met een leesbare diff
- **Participatief** → iedereen kan een wetsvoorstel indienen via een Pull Request

---

## Structuur

```
wetgeving-nl/
├── wetten/                   # Officiële wetten (automatisch bijgewerkt)
│   ├── grondwet/
│   │   └── grondwet.md
│   ├── burgerlijk-wetboek/
│   │   ├── boek-1.md
│   │   └── boek-2.md
│   └── ...
├── proposals/                # Community wetsvoorstellen
│   ├── templates/
│   │   └── voorstel-template.md
│   └── open/                 # Actieve voorstellen
├── scripts/                  # Tools om wetten op te halen en te converteren
│   ├── fetch_bwb.py
│   └── convert_xml_to_md.py
└── .github/
    ├── ISSUE_TEMPLATE/
    └── workflows/
```

---

## Hoe een wet eruitziet

```markdown
---
title: "Grondwet"
identifier: "BWBR0001840"
categorie: "Staatsinrichting"
publicatiedatum: 1983-02-24
laatste_update: 2023-02-22
status: geldig
bron: "https://wetten.overheid.nl/BWBR0001840"
---

# Grondwet

## Hoofdstuk 1 – Grondrechten

### Artikel 1
Allen die zich in Nederland bevinden, worden in gelijke gevallen gelijk behandeld.
Discriminatie wegens godsdienst, levensovertuiging, politieke gezindheid,
ras, geslacht of op welke grond dan ook, is niet toegestaan.
```

---

## Meedoen

### 🐛 Fout gevonden in een wet?
[Open een Issue](../../issues/new?template=fout-in-wet.md)

### 💡 Wetsvoorstel indienen?
[Lees de bijdragegids](CONTRIBUTING.md) en [open een PR](../../compare) met jouw voorstel in `proposals/open/`.

### 🔧 Technisch bijdragen?
Verbeter de parser, voeg wetten toe, of bouw de web-interface. Zie [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Data-bron

Alle officiële wetten komen van het **Basis Wetten Bestand (BWB)** via [data.overheid.nl](https://data.overheid.nl/dataset/basis-wetten-bestand).  
De data is eigendom van de Nederlandse overheid en valt onder de [CC0 licentie](https://creativecommons.org/publicdomain/zero/1.0/deed.nl).

De community-bijdragen (proposals/) vallen onder [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

---

## Roadmap

- [ ] Parser: BWB-XML → nette Markdown voor alle ~20.000 wetten
- [ ] GitHub Actions: dagelijkse automatische update
- [ ] Web-interface: wetten lezen + PR indienen met één klik
- [ ] Zoekfunctie over alle wetteksten
- [ ] Koppeling met Kamerstukken (debatten over wetswijzigingen)

---

*Dit project heeft geen officiële band met de Nederlandse overheid.*
