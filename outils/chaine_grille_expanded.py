#!/usr/bin/env python3
"""
chaine_grille_expanded.py - toute la grille CAIME d'Expanded d'un coup, dans l'ordre de la REPRISE du 3.10.2026 :
grille -> régions -> villes (côtes, passages, villes) -> retouches -> connexité -> validation CAIME, avec le bilan de
chaque étape et les messages de la validation rangés par zone (cadre de WH1, Atlas, Voûtes, Bois Rêveur).

Rien dans le kit : tout se passe dans `04-projets\\saison-expanded\\` (carte `caime\\saison_expanded_map\\map.hex`).
`sync-names` n'est à refaire qu'après un changement de la déclaration dans le kit (régions, sols, climats).
(4.10.2026, relecture croisée du nettoyage, H1) après les étapes, avant la validation : `generate-region-borders` du fork
de CAIME (sans lui, la couche Region Borders reste vide et Pathfinding n'exporte aucune frontière franchissable ; le 4.10
elle avait été faite à la main, une relance l'aurait perdue).
À relancer ensuite, à la main (pas encore dans cette chaîne) : `ports_expanded.py` (ports au modèle de CA) puis
`routes_expanded.py --apply` (routes de l'Atlas, garde-fou des carrefours) ; puis à nouveau `generate-region-borders`
si les régions ont changé.

Usage :
    python chaine_grille_expanded.py <étiquette>       # journal : 05-journal\\2026-10-03-expanded-suite\\validations\\
"""
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

ICI = os.path.dirname(os.path.abspath(__file__))
ATELIER = r"C:\TotalWar-CampaignMap"
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ATELIER, r"04-projets\saison-expanded\caime\saison_expanded_map\map.hex")
JOURNAUX = os.path.join(ATELIER, r"05-journal\2026-10-03-expanded-suite\validations")
ETAPES = ("grille_expanded", "regions_expanded", "villes_expanded", "retouches_expanded", "connexite_expanded")
BRUIT = ("App root", "Info: ", "Saved map.hex", "xported", "wrote ", "hex posés", "Exporting")
sys.path.insert(0, ICI)
from cadre_expanded import W, H, DX, DY, SW, SH, SUD                 # noqa: E402


def zone(q, r):
    if r < SUD:
        return "Bois Rêveur"
    if DX <= q < DX + SW and DY <= r < DY + SH:
        return "cadre WH1"
    return "Voûtes" if r < DY else "Atlas"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    etiquette = sys.argv[1] if len(sys.argv) > 1 else "essai"
    for e in ETAPES:
        print(f"== {e}")
        p = subprocess.run([sys.executable, os.path.join(ICI, e + ".py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ICI)
        for l in (p.stdout + p.stderr).splitlines():
            if l.strip() and not any(b in l for b in BRUIT):
                print("  " + l.strip())
        if p.returncode not in (0, None) and e != "connexite_expanded":
            print(f"!! {e} a échoué (code {p.returncode}) : arrêt")
            return p.returncode
    # (5.10.2026, Charles : « corriger les trois erreurs de chaque validation CAIME ») villes de col de WH1 : les deux
    # massifs de chaque col reliés par quelques cases de recoin (cols_sprawl.py ; la terre franchissable n'est pas coupée)
    print("== cols_sprawl")
    p = subprocess.run([sys.executable, os.path.join(ICI, "cols_sprawl.py"), "--apply"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=ICI)
    for l in (p.stdout + p.stderr).splitlines():
        if l.strip() and not any(b in l for b in BRUIT):
            print("  " + l.strip())
    # les frontières de régions (verbe du fork de CAIME, commit 0f06478) : après toute écriture des régions
    print("== generate-region-borders")
    p = subprocess.run([CAIME, "generate-region-borders", "--map", CARTE], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for l in (p.stdout + p.stderr).splitlines():
        if l.strip() and ("border" in l.lower() or "rror" in l or "Saved" in l):
            print("  " + l.strip())
    if p.returncode:
        print(f"!! generate-region-borders a échoué (code {p.returncode}) : arrêt")
        return p.returncode
    os.makedirs(JOURNAUX, exist_ok=True)
    log = os.path.join(JOURNAUX, f"validation-{etiquette}.log")
    p = subprocess.run([CAIME, "validate", "--map", CARTE, "--all"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    open(log, "w", encoding="utf-8").write(p.stdout + p.stderr)
    par = defaultdict(Counter)
    for l in (p.stdout + p.stderr).splitlines():
        if not l.startswith(("Error", "Warning")):
            continue
        m = re.search(r"Hex\((\d+), (\d+)\)", l)
        cle = re.sub(r"Hex\(\d+, \d+\)", "H", l)[:120]
        cle = re.sub(r"Region \d+ ", "Region N ", cle)
        par[cle][zone(int(m.group(1)), int(m.group(2))) if m else "-"] += 1
    print(f"== validation CAIME (code {p.returncode}) : {log}")
    for cle, c in sorted(par.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {sum(c.values()):4d}  {cle}  {dict(c)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
