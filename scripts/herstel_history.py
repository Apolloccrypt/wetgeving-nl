#!/usr/bin/env python3
"""
herstel_history.py — Herschrijf de git-history zodat per bestand
de volledige wetsgeschiedenis zichtbaar is.

Het probleem: de legalize-nl commits hadden bestanden in nl/BWBR0001854.md
maar onze bestanden staan in wetten/strafrecht/wetboek-van-strafrecht.md.
Dit script koppelt die twee aan elkaar via een rename in de git history.

Gebruik:
    python scripts/herstel_history.py --stap 1   # Genereer mapping
    python scripts/herstel_history.py --stap 2   # Herschrijf history (30-60 min)
    python scripts/herstel_history.py --stap 3   # Push

WAARSCHUWING: Stap 2 herschrijft de volledige git history.
Maak eerst een backup: git clone . ../wetgeving-nl-backup
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

MAPPING_PAD = Path("scripts/bwbr_mapping.json")
FILTER_SCRIPT = Path("/tmp/rename_callback.py")


def stap_1_genereer_mapping(index_pad: str):
    """Genereer mapping van BWBR-identifier naar nieuw bestandspad."""
    index = json.loads(Path(index_pad).read_text(encoding="utf-8"))

    mapping = {}
    for wet in index:
        ident = wet.get("identifier", "")
        pad   = wet.get("pad", "")
        if ident and pad:
            # Oud pad in legalize-nl: nl/BWBR0001854.md
            oud_pad = f"nl/{ident}.md"
            mapping[oud_pad] = pad

    MAPPING_PAD.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Mapping opgeslagen: {len(mapping)} wetten → {MAPPING_PAD}")
    print("\nVoorbeelden:")
    for oud, nieuw in list(mapping.items())[:5]:
        print(f"  {oud} → {nieuw}")


def stap_2_herschrijf():
    """Herschrijf git history met git filter-repo."""
    if not MAPPING_PAD.exists():
        print("Voer eerst stap 1 uit.")
        sys.exit(1)

    mapping = json.loads(MAPPING_PAD.read_text(encoding="utf-8"))

    # Schrijf filter-repo callback
    callback = f'''
import json

mapping = {json.dumps(mapping)}

def rename_bestand(filename):
    decoded = filename.decode("utf-8", errors="replace")
    if decoded in mapping:
        return mapping[decoded].encode("utf-8")
    return filename

filename = rename_bestand(filename)
'''
    FILTER_SCRIPT.write_text(callback, encoding="utf-8")

    print("=" * 60)
    print("STAP 2: Git history herschrijven")
    print("Dit duurt 30-90 minuten.")
    print("=" * 60)

    result = subprocess.run(
        f'git filter-repo --filename-callback "exec(open(\\"{FILTER_SCRIPT}\\").read())" --force',
        shell=True, text=True
    )

    if result.returncode != 0:
        print("FOUT bij filter-repo")
        sys.exit(1)

    print("\nKlaar! Controleer met:")
    print("  git log --oneline --follow wetten/strafrecht/wetboek-van-strafrecht.md | head -10")


def stap_3_push():
    """Push de herschreven history."""
    print("Remote opnieuw instellen en pushen...")
    subprocess.run(
        "git remote add origin https://github.com/Apolloccrypt/wetgeving-nl.git",
        shell=True
    )
    result = subprocess.run(
        "git push origin main --force",
        shell=True, text=True
    )
    if result.returncode == 0:
        print("Gepusht! Controleer GitHub → een wet → History.")
    else:
        print("Push mislukt. Probeer handmatig: git push origin main --force")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stap", type=int, choices=[1, 2, 3], required=True)
    p.add_argument("--index", default="index.json")
    args = p.parse_args()

    if args.stap == 1:
        stap_1_genereer_mapping(args.index)
    elif args.stap == 2:
        stap_2_herschrijf()
    elif args.stap == 3:
        stap_3_push()


if __name__ == "__main__":
    main()
