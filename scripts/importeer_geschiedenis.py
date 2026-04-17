#!/usr/bin/env python3
"""
importeer_geschiedenis.py — Importeer de volledige wetsgeschiedenis van legalize-nl
en herschrijf alle 423.000+ commit-berichten naar nettig Nederlands.

Wat dit doet:
  1. Kloont legalize-nl met volledige history (eenmalig, ~1-2GB)
  2. Herschrijft elk commit-bericht:
     - Verwijdert Spaanse metadata (Norma:, Disposición:, Fecha:, etc.)
     - Maakt nette Nederlandse berichten: "Wetswijziging: Wetboek van Strafrecht (2026-01-15)"
  3. Koppelt de history aan jouw wetgeving-nl repo

Gebruik:
    python scripts/importeer_geschiedenis.py --stap 1   # Clone legalize-nl
    python scripts/importeer_geschiedenis.py --stap 2   # Herschrijf commits
    python scripts/importeer_geschiedenis.py --stap 3   # Koppel aan repo

WAARSCHUWING: Stap 1 downloadt ~1-2GB. Stap 2 duurt 30-60 minuten.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

LEGALIZE_URL = "https://github.com/legalize-dev/legalize-nl.git"
WORK_DIR     = Path("/tmp/legalize-full")
FILTER_SCRIPT = Path("/tmp/rewrite_commits.py")


# ── Filter-script voor git-filter-repo ───────────────────────────────────────

FILTER_CODE = '''
import re
from datetime import datetime

def schoon_bericht(msg: str) -> str:
    """Herschrijf een rommelig legalize-nl commit-bericht naar nettig Nederlands."""

    # Verwijder alle Spaanse/Engelse metadata-regels
    meta_patronen = [
        r"Norma:.*",
        r"Disposici[oó]n:.*",
        r"Fecha:.*",
        r"Fuente:.*",
        r"Source-Id:.*",
        r"Source-Date:.*",
        r"Norm-Id:.*",
        r"Art[ií]culos afectados:.*",
        r"NL-DAILY-\\d{4}-\\d{2}-\\d{2}",
        r"\\[reform\\]",
        r"\\[new\\]",
        r"\\[repeal\\]",
        r"Add new norm.*",
        r"Update norm.*",
        r"Repeal norm.*",
    ]
    for patroon in meta_patronen:
        msg = re.sub(patroon, "", msg, flags=re.IGNORECASE)

    # Verwijder lege regels en whitespace
    regels = [r.strip() for r in msg.split("\\n") if r.strip()]
    msg = " ".join(regels).strip()

    # Als er een BWBR-identifier in zit, gebruik die als basis
    bwbr = re.search(r"(BWBR\\d+|BWBV\\d+)", msg)

    # Probeer een datum te vinden
    datum = re.search(r"(\\d{4}-\\d{2}-\\d{2})", msg)
    datum_str = datum.group(1) if datum else ""

    # Titel opmaken
    if msg and len(msg) > 5:
        # Verwijder BWBR-codes en datums uit de titel
        titel = re.sub(r"BWBR\\d+|BWBV\\d+", "", msg)
        titel = re.sub(r"\\d{4}-\\d{2}-\\d{2}", "", titel)
        titel = re.sub(r"\\s+", " ", titel).strip()
        titel = titel[:80] if titel else "Wetswijziging"
    else:
        titel = "Wetswijziging"

    # Bouw nettig commit-bericht
    if datum_str:
        return f"Wetswijziging: {titel} ({datum_str})"
    else:
        return f"Wetswijziging: {titel}"


# git-filter-repo callback
msg = commit.message.decode("utf-8", errors="replace")
schoon = schoon_bericht(msg)
if not schoon.strip():
    schoon = "Wetswijziging"
commit.message = schoon.encode("utf-8")
'''


def run(cmd: str, cwd: Path = None, check: bool = True) -> subprocess.CompletedProcess:
    """Voer een shell-commando uit en print de output."""
    print(f"\n$ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=False, text=True
    )
    if check and result.returncode != 0:
        print(f"FOUT: commando mislukt (exit {result.returncode})")
        sys.exit(1)
    return result


def stap_1_clone():
    """Clone legalize-nl met volledige history."""
    if WORK_DIR.exists():
        print(f"Map {WORK_DIR} bestaat al. Overslaan.")
        print("Als je opnieuw wilt beginnen: rm -rf /tmp/legalize-full")
        return

    print("=" * 60)
    print("STAP 1: legalize-nl klonen met volledige history")
    print("Dit duurt 5-15 minuten en downloadt ~1-2GB.")
    print("=" * 60)

    run(f"git clone {LEGALIZE_URL} {WORK_DIR}")
    result = subprocess.run(
        "git log --oneline | wc -l",
        shell=True, cwd=WORK_DIR, capture_output=True, text=True
    )
    print(f"\nKlaar: {result.stdout.strip()} commits gekloned.")


def stap_2_herschrijf():
    """Herschrijf alle commit-berichten naar nettig Nederlands."""
    if not WORK_DIR.exists():
        print("Voer eerst stap 1 uit.")
        sys.exit(1)

    print("=" * 60)
    print("STAP 2: 423.000+ commit-berichten herschrijven")
    print("Dit duurt 30-90 minuten.")
    print("=" * 60)

    # Schrijf het filter-script
    FILTER_SCRIPT.write_text(FILTER_CODE, encoding="utf-8")

    run(
        f"git filter-repo --commit-callback 'exec(open(\"{FILTER_SCRIPT}\").read())'",
        cwd=WORK_DIR
    )

    # Check resultaat
    result = subprocess.run(
        "git log --oneline | head -10",
        shell=True, cwd=WORK_DIR, capture_output=True, text=True
    )
    print("\nEerste 10 commits na herschrijven:")
    print(result.stdout)


def stap_3_koppel(repo_pad: str):
    """Koppel de herschreven history aan de wetgeving-nl repo."""
    repo = Path(repo_pad).resolve()
    if not repo.exists():
        print(f"Repo niet gevonden: {repo}")
        sys.exit(1)

    print("=" * 60)
    print(f"STAP 3: History koppelen aan {repo}")
    print("=" * 60)

    # Voeg legalize-full toe als remote
    run(f"git remote add legalize-history {WORK_DIR}", cwd=repo, check=False)
    run("git fetch legalize-history", cwd=repo)

    # Maak een aparte branch met de history
    run(
        "git checkout -b wetgeschiedenis legalize-history/main",
        cwd=repo, check=False
    )
    run("git checkout main", cwd=repo)

    print("""
Klaar! De volledige wetsgeschiedenis staat nu in de branch 'wetgeschiedenis'.

Volgende stap: merge de history met een graft zodat jouw schone commits
bovenop de historische commits komen te staan:

    cd """ + str(repo) + """
    git replace --graft $(git rev-list --max-parents=0 HEAD) \\
        $(git rev-list --max-parents=0 legalize-history/main)
    git filter-repo --force

Dit verbindt de twee histories tot één doorlopende tijdlijn.
""")


def main():
    p = argparse.ArgumentParser(description="Importeer wetsgeschiedenis van legalize-nl")
    p.add_argument("--stap", type=int, choices=[1, 2, 3], required=True)
    p.add_argument("--repo", default=".", help="Pad naar wetgeving-nl repo (voor stap 3)")
    args = p.parse_args()

    if args.stap == 1:
        stap_1_clone()
    elif args.stap == 2:
        stap_2_herschrijf()
    elif args.stap == 3:
        stap_3_koppel(args.repo)


if __name__ == "__main__":
    main()
