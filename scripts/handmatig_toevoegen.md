# Wetten handmatig toevoegen (terwijl je wacht op KOOP)

Ga naar wetten.overheid.nl, zoek de wet op, en download de XML via de downloadknop.

## Prioriteitswetten om mee te beginnen

| Wet | URL |
|-----|-----|
| Grondwet | https://wetten.overheid.nl/BWBR0001840 |
| Wetboek van Strafrecht | https://wetten.overheid.nl/BWBR0001854 |
| Burgerlijk Wetboek Boek 1 | https://wetten.overheid.nl/BWBR0002656 |
| Algemene wet bestuursrecht | https://wetten.overheid.nl/BWBR0005537 |
| Wet inkomstenbelasting 2001 | https://wetten.overheid.nl/BWBR0011353 |

## Hoe je de XML omzet naar Markdown

Na het downloaden van de XML:

```bash
python scripts/fetch_bwb.py --xml-bestand grondwet.xml --output wetten/
```

Of geef de identifier mee als je het script vanuit GitHub Actions draait:
```bash
python scripts/fetch_bwb.py --identifier BWBR0001840
```

## Na ontvangst van de KOOP basisset

Pak de ZIP uit en run:
```bash
python scripts/seed_wetten.py --basisset /pad/naar/BWB/ --output wetten/
```

Dan heb je alle 45.000 wetten in één keer.
