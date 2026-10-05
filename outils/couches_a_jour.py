#!/usr/bin/env python3
"""
couches_a_jour.py - les couches de la grille que lit la chaîne du terrain, réexportées du map.hex d'Expanded (5.10.2026).

Pourquoi (Charles, 5.10.2026, essai des fleuves en jeu : « la rivière flotte sur un énorme trou béant… il n'y a pas d'eau
sur la voie navigable ») : `projet_expanded`, `eau_expanded`, `habillage_expanded`, `arbres_expanded` et d'autres lisent
des COPIES des couches de la grille (`couches-expanded\\*.hex_layer`, `couches-expanded\\villes-sortie\\`), écrites par la
chaîne de la grille (`villes_expanded`, `retouches_expanded`) ; le lot des fleuves (02 h 05) et les routes ont changé le
map.hex APRÈS (copies de 00 h 13) : le terrain a été fait sur l'ancienne grille (pas de plan d'eau sur les chenaux, arbres
et décors dessus), sauf les tuiles et BOB, qui lisent le map.hex.

Règle : avant toute chaîne du terrain, ces copies sont refaites depuis le map.hex (CAIME export-layer, binaire), sous les
noms qu'elles portent (sauf `layer_impassable` de la racine, qui n'en est pas une, PAS_DES_COPIES) ; l'ancien jeu est rangé dans `couches-expanded\\archives\\<date>\\`. `--verifier` : compte, couche
par couche, les cases qui diffèrent entre les copies et le map.hex, sans rien écrire (0 partout = à jour). Appelé par
`projet_expanded.main` en tête.

Usage : python couches_a_jour.py [--verifier]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer                                      # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
COUCHES = os.path.join(ICI, "couches-expanded")
SORTIE = os.path.join(COUCHES, "villes-sortie")
ARCHIVES = os.path.join(COUCHES, "archives")
# nom de la copie -> nom du fichier exporté par CAIME
EXPORT = {"attritions": "attritions", "beaches": "beaches", "bridges": "bridges", "climates": "climates",
          "groundtypes": "ground_types", "impassable": "impassable", "regions": "regions", "rivers": "rivers",
          "roads": "roads", "townslots": "town_slots", "townsprawl": "town_sprawl"}


# (relevé du 5.10) `couches-expanded\layer_impassable` n'est PAS une copie du map.hex : entrée de la chaîne de la grille
# (70 087 cases à 1 contre 212 494 dans le map.hex), lue par `relief_monde` pour le relief des montagnes ; jamais remplacée
PAS_DES_COPIES = {os.path.join(COUCHES, "layer_impassable.hex_layer")}


def copies():
    """[(chemin de la copie, nom exporté)] de toutes les copies existantes."""
    out = []
    for d in (COUCHES, SORTIE):
        for nom, exp in EXPORT.items():
            p = os.path.join(d, f"layer_{nom}.hex_layer")
            if os.path.exists(p) and p not in PAS_DES_COPIES:
                out.append((p, exp))
    return out


def rafraichir(verifier=False, journal=print):
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run([CAIME, "export-layer", "--map", CARTE, "--out", d, "--format", "binary", "--all"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        frais = {}
        for exp in set(EXPORT.values()):
            f = os.path.join(d, f"layer_{exp}.hex_layer")
            if not os.path.exists(f):
                raise SystemExit(f"export CAIME sans layer_{exp} :\n{p.stdout[-2000:]}{p.stderr[-2000:]}")
            frais[exp] = f
        diff = {}
        for cop, exp in copies():
            a, b = read_layer(cop), read_layer(frais[exp])
            if a[0] != b[0]:
                raise SystemExit(f"{cop} : nom de couche {a[0]!r} contre {b[0]!r} à l'export : copie non remplaçable")
            diff[cop] = int((np.asarray(a[1]) != np.asarray(b[1])).sum())
        for cop, n in diff.items():
            journal(f"  {os.path.relpath(cop, COUCHES):40s} {n:7d} case(s) différente(s)")
        if verifier or not any(diff.values()):
            return diff
        dossier = os.path.join(ARCHIVES, time.strftime("%Y%m%d-%H%M%S"))
        for cop, exp in copies():
            if diff[cop]:
                dst = os.path.join(dossier, os.path.relpath(cop, COUCHES))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(cop, dst)
                shutil.copy2(frais[exp], cop)
        journal(f"  copies refaites depuis le map.hex ; anciennes dans {dossier}")
        return diff


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verifier", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rafraichir(a.verifier)
    return 0


if __name__ == "__main__":
    sys.exit(main())
