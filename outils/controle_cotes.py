#!/usr/bin/env python3
"""
controle_cotes.py - prédit, depuis la seule grille, les hex de côte où BOB ne trouvera pas de tuile de côte de CA
(« Failed to find tile », TileSet_cliff_gen / sea_coast), pour corriger la grille AVANT de compiler (4.10.2026).

Pourquoi : la carte des tuiles d'Expanded est l'export CAIME (côtes de CA, demande de Charles) ; chaque trou demandait
jusqu'ici une chaîne complète (CAIME, BOB) pour être vu. Règles tirées des compilations du 4.10 (280 puis 75 trous) et du
GUIDE § 15 n° 97 :
1. n° 97 : un hex de TERRE côtier a une seule série de 1 à 3 voisins de mer ; et son pendant côté mer (anse ou bras de mer
   d'un hex : plus de 3 voisins de terre, ou deux séries) ;
2. côte RAMIFIÉE (relevé du 4.10 : signatures CCCLCS, CCCCSS, CCSSCL, CSSSSS… : 0 succès) : un hex de falaise (terre
   côtière hors plage) qui a 3 voisins de côte ou plus : la bande de falaise doit être une simple ligne.
Avec --bob <dossier de journaux>, compare la prédiction aux trous réellement relevés par BOB.

Usage : python controle_cotes.py [--bob <dossier de compilation>]
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H                                               # noqa: E402
import villes_expanded as V                                                   # noqa: E402
from caime_layers import read_layer, caime_names                              # noqa: E402
from grow_town_slots import DIRS                                              # noqa: E402


def couches(carte=None):
    carte = carte or V.CARTE_EXP
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([V.CAIME, "export-layer", "--map", carte, "--out", d, "--format", "binary",
                        "--layer", "GroundTypes", "--layer", "Beaches"], capture_output=True)
        gt = read_layer(os.path.join(d, "layer_ground_types.hex_layer"))[1].reshape(H, W)
        pl = read_layer(os.path.join(d, "layer_beaches.hex_layer"))[1].reshape(H, W) > 0
    mer = gt >= len(caime_names(V.CAIME, carte)[0].get("Land ground types", []))
    return mer, pl


def voisins(r, q):
    for dq, dr in DIRS[q & 1]:
        a, b = r + dr, q + dq
        yield (a, b) if 0 <= a < H and 0 <= b < W else None


def predire(mer, pl):
    """{(q, r): motif} des hex de côte sans tuile de CA prévue (rangée 0 au sud)."""
    cote = np.zeros((H, W), bool)                 # terre côtière (falaise ou plage)
    for r, q in np.argwhere(~mer):
        if any(v is not None and mer[v] for v in voisins(r, q)):
            cote[r, q] = True
    out = {}
    for r in range(H):
        for q in range(W):
            vs = [v for v in voisins(r, q)]
            autre = [bool(v is not None and mer[v] != mer[r, q]) for v in vs]
            n = sum(autre)
            if n == 0:
                continue
            series = sum(1 for k in range(6) if autre[k] and not autre[k - 1])
            if n > 3 or series > 1:
                out[(q, r)] = ("mer" if mer[r, q] else "terre") + f" n° 97 ({n} voisins, {series} séries)"
                continue
            if cote[r, q] and not pl[r, q]:
                nc = sum(1 for v in vs if v is not None and cote[v])
                if nc >= 3:
                    out[(q, r)] = f"falaise ramifiée ({nc} voisins de côte)"
    return out


def trous_bob(dossier):
    log = glob.glob(os.path.join(dossier, "**", "bob_warnings.log"), recursive=True)[0]
    t = set()
    for l in open(log, encoding="utf-8", errors="replace"):
        m = re.search(r"points (\d+)x(\d+) to (\d+)x(\d+)'", l)
        if m:
            a, y, b, _ = map(int, m.groups())
            t.add(((a + b) // 4, y // 2))
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bob")
    ap.add_argument("--carte")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    mer, pl = couches(a.carte)
    p = predire(mer, pl)
    from collections import Counter
    print(f"  hex de côte sans tuile de CA prévue : {len(p)} ; " +
          str(Counter(m.split(" (")[0] for m in p.values()).most_common()))
    if a.bob:
        t = trous_bob(a.bob)
        proche = lambda c, s: any(abs(c[0] - x) <= 1 and abs(c[1] - y) <= 1 for x, y in s)  # noqa: E731
        expl = sum(proche(c, p) for c in t)
        print(f"  trous de BOB : {len(t)} hex ; expliqués (prédiction à 1 hex) : {expl} ; prédictions sans trou : "
              f"{sum(not proche(c, t) for c in p)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
