# wetgeving-nl

> Nederlandse wetgeving in Markdown — elke wet een bestand, elke wijziging een commit, elke burger een potentiele bijdrager.

**Website:** [vrijewetgeving.nl](https://vrijewetgeving.nl)

Geinspireerd door [legalize-es](https://github.com/legalize-dev/legalize-es) (Spanje), maar met een echte community-laag voor wetsvoorstellen en een betere parser.

---

## Waarom dit project?

Officiele wetten zijn publiek eigendom — maar wetten.overheid.nl is ontoegankelijk, wijzigingen zijn onvindbaar en burgers hebben geen stem.

Dit project maakt wetgeving:

- **Leesbaar** — schone Markdown met nette YAML-frontmatter
- **Traceerbaar** — elke wetswijziging is een commit met een leesbare diff
- **Doorzoekbaar** — zoek op titel en volledige wettekst via vrijewetgeving.nl
- **Participatief** — iedereen kan een wetsvoorstel indienen via een Pull Request

---

## De repo in cijfers

| | |
|---|---|
| Wetten | 21.407 officiele regelingen |
| Categorieen | 14 (strafrecht, belastingrecht, bestuursrecht, etc.) |
| Commits | 423.000+ historische wetswijzigingen |
| Kamerstukken | Gekoppeld per wet via rijksoverheid.nl open data |
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
├── scripts/
│   ├── cleanup_legalize.py        # Hoofdconverter BWB naar Markdown
│   ├── dagelijkse_update.py       # Dagelijkse BWB-sync
│   ├── genereer_index.py          # Genereert index.json en zoekindex.json
│   ├── koppel_kamerstukken.py     # Koppelt Kamerstukken aan wetten
│   └── hercategoriseer.py         # Verbetert categorisering
├── .github/
│   └── workflows/
│       └── update-wetten.yml
├── index.html                     # Web-interface (vrijewetgeving.nl)
├── index.json                     # Metadata index (5MB)
├── zoekindex.json                 # Volledige tekst zoekindex (8MB)
├── CNAME                          # Domeinkoppeling
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
Verbeter de parser, voeg wetten toe, of bouw mee aan de website. Zie [CONTRIBUTING.md](CONTRIBUTING.md).

**Discussie starten?**
Ga naar [Discussions](../../discussions).

---

## Roadmap

### Klaar

- [x] 21.407 Nederlandse wetten in schone Markdown
- [x] Gesorteerd in 14 categorieen
- [x] Automatische dagelijkse updates via GitHub Actions
- [x] Community proposals-sectie met templates
- [x] Website op vrijewetgeving.nl
- [x] Volledige wetsgeschiedenis (423.000+ commits)
- [x] Zoeken op titel en volledige wettekst
- [x] Sorteren op naam en datum
- [x] Koppeling met Kamerstukken via rijksoverheid.nl
- [x] LICENSE, CODE_OF_CONDUCT, SECURITY
- [x] GitHub Discussions

### In ontwikkeling

- [ ] Betere web-interface zonder GitHub-kennis vereist
- [ ] Per-bestand git-history correct koppelen

### Toekomst

- [ ] Dark mode
- [ ] AI-zoekhulp: zoek in gewoon Nederlands
- [ ] Vergelijk twee versies van een wet
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
