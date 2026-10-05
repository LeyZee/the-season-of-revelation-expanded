#!/usr/bin/env python3
"""
retouches_cotes.py - formes de côte sans tuile de CA, corrigées dans la GRILLE (5.10.2026).

Pourquoi (Charles, 5.10.2026 : « attaque tout ça » ; recherche `05-journal\\2026-10-05-tuiles-cote\\RAPPORT.md` § 2 et 5,
GUIDE § 15 n° 170) : BOB n'a pas de tuile de côte pour (1) une langue de terre d'UN hex de large (isthme de Lyonesse,
(108, 676-680) : deux falaises s'y croisent) ; (2) une côte sur le bord de la grille (rangée 0, falaise de l'île du Bois
Rêveur). `cotes_expanded.lisser` ne retire que les langues d'une seule case.

Règles :
1. LANGUES : une case de terre côtière dont les voisins de terre forment au plus 1 suite et sont 1 ou 2 au plus est un bout
   de langue ; retirée (devient mer : sol et région de mer de ses voisins de mer les plus nombreux), puis on recommence
   (la langue raccourcit jusqu'à sa base) ; jamais dans la zone gardée de WH1, sur une ville, une étendue, une route, une
   rivière, un pont, une plage de port, ni dans le Bois Rêveur hors de son bord ;
2. BORD : aucune terre sur la rangée 0, la dernière rangée ni les colonnes 0 et W − 1 (mer de ses voisins).
Le nombre de cases changées est imprimé ; à blanc par défaut ; --apply : sauvegarde, import des couches GroundTypes,
Regions, Impassable, Climates.

Usage : python retouches_cotes.py [--apply]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
import villes_expanded as V                                                   # noqa: E402
from caime_layers import read_layer, encode_flat, caime_names, flat_names     # noqa: E402
from grow_town_slots import DIRS                                              # noqa: E402
from cadre_expanded import W, H                                               # noqa: E402

SAUVEGARDES = os.path.join(V.ATELIER, r"05-journal\terrain-backups")
COUCHES = ("ground_types", "regions", "impassable", "climates", "town_slots", "town_sprawl", "roads", "rivers",
           "bridges", "beaches")


def voisins(q, r):
    out = []
    for dq, dr in DIRS[q & 1]:
        a, b = q + dq, r + dr
        out.append((a, b) if 0 <= a < W and 0 <= b < H else None)
    return out


def corriger(c, n_terre, garde, journal):
    gt, reg, imp, clim = (c[k].copy() for k in ("ground_types", "regions", "impassable", "climates"))
    terre = lambda q, r: 0 <= gt[r, q] < n_terre  # noqa: E731
    fixe = (garde | (c["town_slots"] >= 0) | (c["town_sprawl"] > 0) | (c["roads"] > 0) | (c["rivers"] > 0)
            | (c["bridges"] > 0))
    n_lang, n_bord = 0, 0

    def vers_mer(q, r):
        mers = [(gt[b, a], reg[b, a], imp[b, a]) for v in voisins(q, r) if v for a, b in [v] if not terre(a, b)]
        if not mers:
            return False
        g, rg, ip = Counter(mers).most_common(1)[0][0]
        gt[r, q], reg[r, q], imp[r, q] = g, rg, ip
        return True
    # 2. bord de la grille : seulement la terre COTIÈRE du bord (premier essai : 804 cases, toute la terre de décor qui touche
    # le cadre ; une terre sans mer au bord n'a pas de tuile de côte, elle ne pose aucun problème)
    # (deuxième essai : encore 804, la conversion gagnait de proche en proche le long du bord) relevé fixé AVANT de changer
    bord = [(q, r) for r in range(H) for q in range(W)
            if (r in (0, H - 1) or q in (0, W - 1)) and terre(q, r) and not fixe[r, q]
            and any(v and not terre(*v) for v in voisins(q, r))]
    for q, r in bord:
        if vers_mer(q, r):
            n_bord += 1
    # 1. langues d'un hex de large, en boucle
    change = True
    while change:
        change = False
        for r in range(1, H - 1):
            for q in range(1, W - 1):
                if not terre(q, r) or fixe[r, q]:
                    continue
                vs = voisins(q, r)
                t = [bool(v and terre(*v)) for v in vs]
                n = sum(t)
                if n == 6 or n == 0:
                    continue
                suites = sum(1 for k in range(6) if t[k] and not t[k - 1])
                if n <= 2 and suites <= 1:
                    if vers_mer(q, r):
                        n_lang += 1
                        change = True
    journal.append(f"cases de langue d'un hex rendues à la mer : {n_lang} ; cases du bord de la grille : {n_bord}")
    return {"ground_types": gt, "regions": reg, "impassable": imp, "climates": clim}, n_lang + n_bord


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import projet_expanded as P
    listes = caime_names(V.CAIME, V.CARTE_EXP)[0]
    n_terre = len(listes.get("Land ground types", []))
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([V.CAIME, "export-layer", "--map", V.CARTE_EXP, "--out", d, "--format", "binary", "--all"],
                       capture_output=True)
        c = {n: read_layer(os.path.join(d, f"layer_{n}.hex_layer"))[1].reshape(H, W) for n in COUCHES}
    journal = []
    neuf, n = corriger(c, n_terre, P.garde_wh1_hex(), journal)
    for l in journal:
        print("  " + l)
    diff = {k: np.argwhere(neuf[k] != c[k]) for k in neuf}
    for k, v in diff.items():
        if len(v):
            print(f"  {k} : {len(v)} hex ; ex. {[(int(x[1]), int(x[0])) for x in v[:8]]}")
    if not a.apply or not n:
        print("  à blanc : rien d'écrit" if not a.apply else "  rien à écrire")
        return 0
    os.makedirs(SAUVEGARDES, exist_ok=True)
    sauve = os.path.join(SAUVEGARDES, time.strftime("%Y%m%d-%H%M%S") + "-map.hex-expanded-avant-retouches-cotes")
    shutil.copy2(V.CARTE_EXP, sauve)
    noms = {"ground_types": "GroundTypes", "regions": "Regions", "impassable": "Impassable", "climates": "Climates"}
    with tempfile.TemporaryDirectory() as d:
        args = [V.CAIME, "import-layer", "--map", V.CARTE_EXP]
        for k, nom in noms.items():
            f = os.path.join(d, f"{k}.hex_layer")
            open(f, "wb").write(encode_flat(nom, neuf[k].reshape(-1)))
            args += ["--layer", nom, "--file", f]
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    print(f"  sauvegarde : {sauve}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
