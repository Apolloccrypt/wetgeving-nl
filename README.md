# wetgeving-nl

> Nederlandse wetgeving in Markdown — elke wet een bestand, elke wijziging een commit, elke burger een potentiële bijdrager.

Geïnspireerd door [legalize-es](https://github.com/legalize-dev/legalize-es) (Spanje), maar met een echte community-laag voor wetsvoorstellen.

---

## Waarom dit project?

Officiële wetten zijn publiek eigendom — maar wetten.overheid.nl is ontoegankelijk, wijzigingen zijn onvindbaar en burgers hebben geen stem.

Dit project maakt wetgeving:
- **Leesbaar** — schone Markdown, geen juridisch HTML-geknoei
- **Traceerbaar** — elke wetswijziging is één commit met een leesbare diff
- **Participatief** — iedereen kan een wetsvoorstel indienen via een Pull Request

---

## Structuur

```
wetgeving-nl/
├── wetten/                   # Officiële wetten (automatisch bijgewerkt)
│   ├── strafrecht/
│   ├── burgerlijk-recht/
│   ├── bestuursrecht/
│   ├── belastingrecht/
│   ├── arbeidsrecht/
│   ├── staatsinrichting/
│   └── ...
├── proposals/                # Community wetsvoorstellen
│   └── templates/
└── scripts/                  # Parser en update-tools
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

1. Geen feit is strafbaar dan uit kracht van een daaraan voorafgegane wettelijke strafbepaling.
```

---

## Meedoen

**Fout gevonden in een wet?**
Open een [Issue](../../issues/new?template=fout-in-wet.md)

**Wetsvoorstel indienen?**
Lees de [bijdragegids](CONTRIBUTING.md) en open een PR met jouw voorstel in `proposals/`.

**Technisch bijdragen?**
Verbeter de parser, voeg wetten toe, of bouw de web-interface. Zie [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Data-bron

Alle officiële wetten komen van het **Basis Wetten Bestand (BWB)** via [data.overheid.nl](https://data.overheid.nl/dataset/basis-wetten-bestand).
De data is eigendom van de Nederlandse overheid en valt onder de CC0 licentie.

De community-bijdragen (proposals/) vallen onder CC BY-SA 4.0.

---

## Roadmap

- [ ] Parser: BWB-XML naar nette Markdown voor alle wetten
- [ ] GitHub Actions: dagelijkse automatische update
- [ ] Web-interface: wetten lezen en PR indienen met één klik
- [ ] Zoekfunctie over alle wetteksten
- [ ] Koppeling met Kamerstukken

---

*Dit project heeft geen officiële band met de Nederlandse overheid.*
