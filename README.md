# wetgeving-nl

> Nederlandse wetgeving in Markdown — elke wet een bestand, elke wijziging een commit, elke burger een potentiele bijdrager.

**Website:** [apolloccrypt.github.io/wetgeving-nl](https://apolloccrypt.github.io/wetgeving-nl)

Geinspireerd door [legalize-es](https://github.com/legalize-dev/legalize-es) (Spanje), maar met een echte community-laag voor wetsvoorstellen en een betere parser.

---

## Waarom dit project?

Officiele wetten zijn publiek eigendom — maar wetten.overheid.nl is ontoegankelijk, wijzigingen zijn onvindbaar en burgers hebben geen stem.

Dit project maakt wetgeving:

- **Leesbaar** — schone Markdown met nette YAML-frontmatter, geen juridisch HTML-geknoei
- **Traceerbaar** — elke wetswijziging is een commit met een leesbare diff
- **Doorzoekbaar** — zoek via de website of direct in de bestanden
- **Participatief** — iedereen kan een wetsvoorstel indienen via een Pull Request

---

## De repo in cijfers

| | |
|---|---|
| Wetten | 21.407 officiele regelingen |
| Commits | 423.000+ historische wetswijzigingen |
| Update | Dagelijks automatisch via GitHub Actions |
| Bron | Basis Wetten Bestand (BWB), data.overheid.nl |
| Licentie wetten | CC0 (publiek domein) |
| Licentie code | MIT |

---

## Structuur

```
wetgeving-nl/
├── wetten/                        # Officiele wetten (dagelijks bijgewerkt)
│   ├── strafrecht/
│   ├── burgerlijk-recht/
│   ├── bestuursrecht/
│   ├── belastingrecht/
│   ├── arbeidsrecht/
│   ├── sociaal-recht/
│   ├── gezondheidszorg/
│   ├── onderwijs/
│   ├── milieu/
│   ├── verkeer/
│   ├── digitaal/
│   ├── staatsinrichting/
│   ├── internationaal-recht/
│   ├── financieel-recht/
│   └── overig/
├── proposals/                     # Community wetsvoorstellen
│   └── templates/
│       └── voorstel-template.md
├── scripts/                       # Parser en update-tools
│   ├── cleanup_legalize.py        # Hoofdconverter
│   ├── dagelijkse_update.py       # Dagelijkse BWB-sync
│   └── hercategoriseer.py         # Categorisering
├── .github/
│   ├── workflows/
│   │   └── update-wetten.yml      # Dagelijkse GitHub Actions
│   └── ISSUE_TEMPLATE/
├── index.html                     # Web-interface
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
└── SECURITY.md
```

---

## Hoe een wet eruitziet

```markdown
---
title: "Wetboek van Strafrecht"
identifier: "BWBR0001854"
categorie: "Strafrecht"
publicatiedatum: 1886-09-01
laatste_update: 2026-01-01
status: geldig
bron: "https://wetten.overheid.nl/BWBR0001854"
---

# Wetboek van Strafrecht

## Boek Eerste. Algemene bepalingen

#### Artikel 1

1. Geen feit is strafbaar dan uit kracht van een daaraan voorafgegane
   wettelijke strafbepaling.
```

---

## Meedoen

**Fout gevonden in een wet?**
Open een [Issue](../../issues/new?template=fout-in-wet.md)

**Wetsvoorstel indienen?**
Lees de [bijdragegids](CONTRIBUTING.md) en open een PR met jouw voorstel in `proposals/`.

**Technisch bijdragen?**
Verbeter de parser, voeg wetten toe, of bouw mee aan de web-interface. Zie [CONTRIBUTING.md](CONTRIBUTING.md).

**Discussie starten?**
Ga naar [Discussions](../../discussions).

---

## Roadmap

### Klaar

- [x] 21.407 Nederlandse wetten in schone Markdown
- [x] Gesorteerd in 14 categorieen
- [x] Automatische dagelijkse updates via GitHub Actions
- [x] Community proposals-sectie met templates en issue-templates
- [x] Web-interface op apolloccrypt.github.io/wetgeving-nl
- [x] Volledige wetsgeschiedenis (423.000+ commits)
- [x] LICENSE, CODE_OF_CONDUCT, SECURITY
- [x] GitHub Discussions

### In ontwikkeling

- [ ] Volledige zoekfunctie over alle wetteksten
- [ ] Betere web-interface zonder GitHub-kennis vereist
- [ ] Koppeling met Kamerstukken (debatten bij wetswijzigingen)

### Toekomst

- [ ] Per-bestand git-history correct koppelen
- [ ] Dark mode op de website
- [ ] AI-zoekhulp: zoek in gewoon Nederlands
- [ ] Vergelijk twee versies van een wet
- [ ] Mijn wetten (persoonlijke lijst)
- [ ] Mobiele app

---

## Data-bron

Alle officiele wetten komen van het **Basis Wetten Bestand (BWB)** via
[data.overheid.nl](https://data.overheid.nl/dataset/basis-wetten-bestand).
De data is eigendom van de Nederlandse overheid en valt onder de CC0 licentie.

De community-bijdragen in `proposals/` vallen onder CC BY-SA 4.0.
De scripts vallen onder de MIT licentie.

Zie [LICENSE](LICENSE) voor details.

---

*Dit project heeft geen officiele band met de Nederlandse overheid.*
