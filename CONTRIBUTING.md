# Bijdragen aan wetgeving-nl

Welkom! Dit project werkt zoals open-source software: via Issues en Pull Requests.  
Iedereen kan bijdragen — je hoeft geen jurist of developer te zijn.

---

## Soorten bijdragen

| Type | Hoe | Voor wie |
|------|-----|----------|
| Fout melden in een wet | Issue openen | Iedereen |
| Wetsvoorstel indienen | Pull Request in `proposals/open/` | Iedereen |
| Parser verbeteren | Pull Request in `scripts/` | Developers |
| Nieuwe wet toevoegen | Pull Request in `wetten/` | Developers |
| Discussie starten | GitHub Discussion | Iedereen |

---

## Een wetsvoorstel indienen (stap voor stap)

### 1. Check eerst of het al bestaat
Zoek in [Issues](../../issues) en [proposals/open/](proposals/open/) of jouw idee er al is.

### 2. Fork de repo
Klik rechtsboven op **Fork** → je krijgt je eigen kopie.

### 3. Maak je voorstel
Kopieer het [voorstel-template](proposals/templates/voorstel-template.md) naar `proposals/open/` en vul het in:

```
proposals/open/2024-artikel-1-grondwet-verduidelijking.md
```

Naamgevingsconventie: `JAAR-korte-beschrijving.md`

### 4. Als je een bestaand artikel wilt wijzigen
Pas het bestand in `wetten/` aan en leg in je PR-beschrijving **precies** uit:
- Welk artikel je aanpast
- Waarom deze wijziging beter is
- Wat de mogelijke bezwaren zijn

### 5. Open een Pull Request
- Base branch: `main`
- Gebruik de PR-template (verschijnt automatisch)
- Verwacht discussie — dat is de bedoeling

---

## Regels voor wetsvoorstellen

1. **Één onderwerp per PR** — geen bundels van twintig wijzigingen
2. **Motiveer altijd** — "dit is beter" is geen motivatie
3. **Respecteer de structuur** — gebruik de bestaande Markdown-hiërarchie
4. **Geen persoonlijke aanvallen** — debatteer over ideeën, niet over mensen
5. **Bronnen vermelden** — link naar relevante rechtszaken, rapporten of kamerstukken

---

## Kwaliteitsnormen Markdown

Elke wet volgt deze structuur:

```markdown
---
title: "Naam van de wet"
identifier: "BWBR0000000"
categorie: "Categorie"
publicatiedatum: JJJJ-MM-DD
laatste_update: JJJJ-MM-DD
status: geldig | ingetrokken | voorstel
bron: "https://wetten.overheid.nl/..."
---

# Naam van de wet

## Hoofdstuk 1 – Naam

### Artikel 1
Tekst van het artikel.

### Artikel 2
1. Eerste lid.
2. Tweede lid.
   a. Sub-onderdeel a.
   b. Sub-onderdeel b.
```

---

## Code of Conduct

Dit project volgt de [Contributor Covenant](CODE_OF_CONDUCT.md).  
Respectvol, constructief en feitelijk — altijd.

---

## Vragen?

Open een [Discussion](../../discussions) of stuur een Issue met het label `vraag`.
