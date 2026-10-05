"""valider_caime.py - CAIME `validate --all` sur un ou plusieurs map.hex : compte des Error / Warning par validateur, et
les lignes des villes (Town Slot, Town Sprawl). Guide CAIME de l'Atlas et erreur 335 : à lire avant tout `process`.
Expanded : 0 Error depuis le 5.10.2026 (les 3 Error d'étalement des villes de col de WH1, Chêne des Âges, Défilé de la
Hache, Poste de la Pierre Noire, corrigées par cols_sprawl.py) et 1 Warning (terre sauvage en 11 morceaux).

Usage : python valider_caime.py <map.hex> [<map.hex> ...]"""
import re
import subprocess
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
CAIME = r"C:\TotalWar-CampaignMap\01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe"
for m in sys.argv[1:]:
    p = subprocess.run([CAIME, "validate", "--map", m, "--all"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    lignes = [l.strip() for l in (p.stdout + p.stderr).splitlines()]
    vus = set()
    c = Counter()
    villes = []
    for l in lignes:
        mm = re.match(r"(Error|Warning|Info): ([^:]+):", l)
        if not mm or l in vus:
            continue
        vus.add(l)
        c[(mm.group(1), mm.group(2))] += 1
        if mm.group(1) != "Info" and ("Town" in mm.group(2)):
            villes.append(l)
    print(f"== {m}")
    for (sev, val), n in sorted(c.items()):
        if sev != "Info":
            print(f"   {sev:7s} {val:40s} {n}")
    print(f"   total : Error {sum(n for (s, _), n in c.items() if s == 'Error')}, "
          f"Warning {sum(n for (s, _), n in c.items() if s == 'Warning')}")
    for l in villes:
        print("     ", l[:230])
