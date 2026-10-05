#!/usr/bin/env python3
"""
cols_sprawl.py - les 3 « Error » de CAIME `validate --all` (Town Sprawl) des villes de col de WH1 (5.10.2026).

Pourquoi (Charles, 5.10.2026 : « il faudrait corriger les trois erreurs qu'à chaque validation CAIME affiche ») : le
validateur de CAIME (`SprawlValidator.cs`) veut qu'une emprise de ville ne touche qu'UNE zone de danger (infranchissable,
rivière ou côte), et qu'aucune autre ne s'en approche à 2 hex sans la toucher ; les zones sont des composantes connexes de
TOUTE la carte. Le Chêne des Âges, le Poste de la Pierre Noire et le Défilé de la Hache (villes de col de WH1, à
l'identique de la Saison) touchent deux massifs que rien ne relie ailleurs. Relevé (`scratchpad\\sprawl_erreurs.py`,
`sprawl_fermeture.py`) : les deux massifs se rejoignent en fermant 1 ou 2 cases de recoin au pied des montagnes, à distance
de la ville ; la terre franchissable reste d'un seul tenant (seules ces cases la quittent).

Règle : pour chaque emprise en défaut, le plus court chemin (au plus LIAISON_MAX cases), hors de l'emprise et de son
premier anneau, entre la composante qu'elle touche et l'autre (touchée ou à 2 hex), par des cases franchissables sans
route, rivière, emplacement ni emprise de ville ; fermé seulement si la terre franchissable ne perd que ces cases (aucun
recoin ni passage coupé). Expanded seulement (la Saison garde ses villes de col telles que WH1).

Usage : python cols_sprawl.py [--apply] [--carte map.hex]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, deque

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
import villes_expanded as V                                                   # noqa: E402
from caime_layers import read_layer, encode_flat, caime_names, flat_names     # noqa: E402
from grow_town_slots import neighbours                                        # noqa: E402
from cadre_expanded import W, H                                               # noqa: E402

LIAISON_MAX = 3
SAUVEGARDES = os.path.join(V.ATELIER, r"05-journal\terrain-backups")


def composantes(m):
    lab = -np.ones((H, W), int)
    tailles = []
    for r, q in np.argwhere(m):
        if lab[r, q] >= 0:
            continue
        i = len(tailles)
        f = deque([(int(r), int(q))])
        lab[r, q] = i
        n = 0
        while f:
            cr, cq = f.popleft()
            n += 1
            for nq, nr in neighbours(cq, cr, W, H):
                if m[nr, nq] and lab[nr, nq] < 0:
                    lab[nr, nq] = i
                    f.append((nr, nq))
        tailles.append(n)
    return lab, tailles


def corriger(c, n_terre, noms, journal):
    """Couches `c` (dict H × W) ; rend la couche Impassable corrigée et la liste des cases fermées."""
    imp = c["impassable"].copy()
    terre = (c["ground_types"] >= 0) & (c["ground_types"] < n_terre)
    cote = np.zeros((H, W), bool)
    for r, q in np.argwhere(terre):
        if any(not terre[nr, nq] for nq, nr in neighbours(int(q), int(r), W, H)):
            cote[r, q] = True
    libre = (c["roads"] == 0) & (c["rivers"] == 0) & (c["town_slots"] < 0) & (c["town_sprawl"] == 0) & terre & ~cote
    fermees = []
    for _tour in range(6):
        danger = (imp != 1) | (c["rivers"] != 0) | cote
        comp, _ = composantes(danger)
        passe_avant = composantes((imp == 1) & terre)[1]
        vu = np.zeros((H, W), bool)
        fait = False
        for r0, q0 in np.argwhere(c["town_sprawl"] > 0):
            if vu[r0, q0]:
                continue
            blob, f = [], deque([(int(r0), int(q0))])
            vu[r0, q0] = True
            while f:
                cr, cq = f.popleft()
                blob.append((cr, cq))
                for nq, nr in neighbours(cq, cr, W, H):
                    if c["town_sprawl"][nr, nq] > 0 and not vu[nr, nq]:
                        vu[nr, nq] = True
                        f.append((nr, nq))
            bset = set(blob)
            ring1 = {(nr, nq) for cr, cq in blob for nq, nr in neighbours(cq, cr, W, H) if (nr, nq) not in bset}
            ring2 = {(nr, nq) for cr, cq in ring1 for nq, nr in neighbours(cq, cr, W, H)
                     if (nr, nq) not in bset and (nr, nq) not in ring1}
            touche = sorted({comp[x] for x in ring1 if comp[x] >= 0})
            proches = sorted({comp[x] for x in ring1 | ring2 if comp[x] >= 0})
            if len(touche) <= 1 and set(proches) <= set(touche):
                continue
            a = touche[0] if touche else proches[0]
            autres = [k for k in proches if k != a]
            nom = noms[Counter(c["regions"][x] for x in blob if terre[x]).most_common(1)[0][0]]
            for b in autres:
                src = [tuple(x) for x in np.argwhere(comp == a)]
                prev = {s: None for s in src}
                file_, fin = deque((s, 0) for s in src), None
                while file_ and fin is None:
                    x, d = file_.popleft()
                    for nq, nr in neighbours(x[1], x[0], W, H):
                        n = (nr, nq)
                        if n in prev or n in bset or n in ring1:
                            continue
                        if comp[n] == b:
                            prev[n] = x
                            fin = n
                            break
                        if danger[n] or not libre[n] or d >= LIAISON_MAX:
                            continue
                        prev[n] = x
                        file_.append((n, d + 1))
                if fin is None:
                    journal.append(f"{nom} : composantes {a} et {b} sans liaison de {LIAISON_MAX} cases au plus")
                    continue
                ch, x = [], prev[fin]
                while prev[x] is not None:
                    ch.append(x)
                    x = prev[x]
                essai = imp.copy()
                for x in ch:
                    essai[x] = 0
                apres = composantes((essai == 1) & terre)[1]
                if sorted(apres, reverse=True)[0] != sorted(passe_avant, reverse=True)[0] - len(ch) or len(apres) != len(passe_avant):
                    journal.append(f"{nom} : liaison {[(q, r) for r, q in ch]} refusée (couperait la terre franchissable)")
                    continue
                imp = essai
                fermees += [(q, r) for r, q in ch]
                journal.append(f"{nom} : composantes {a} et {b} reliées en fermant {[(q, r) for r, q in ch]}")
                fait = True
                break
            if fait:
                break
        if not fait:
            break
    return imp, fermees


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--carte", default=V.CARTE_EXP)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    listes = caime_names(V.CAIME, a.carte)[0]
    noms = flat_names(listes, "Regions")
    n_terre = len(listes.get("Land ground types", []))
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([V.CAIME, "export-layer", "--map", a.carte, "--out", d, "--format", "binary", "--all"],
                       capture_output=True)
        c = {n: read_layer(os.path.join(d, f"layer_{n}.hex_layer"))[1].reshape(H, W) for n in
             ("impassable", "ground_types", "rivers", "roads", "town_slots", "town_sprawl", "regions")}
    journal = []
    imp, fermees = corriger(c, n_terre, noms, journal)
    for l in journal:
        print("  " + l)
    print(f"  cols de WH1 : {len(fermees)} cases de recoin fermées")
    if not a.apply or not fermees:
        print("  à blanc : rien d'écrit" if not a.apply else "  rien à écrire")
        return 0
    os.makedirs(SAUVEGARDES, exist_ok=True)
    sauve = os.path.join(SAUVEGARDES, time.strftime("%Y%m%d-%H%M%S") + "-map.hex-expanded-avant-cols-sprawl")
    shutil.copy2(a.carte, sauve)
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "imp.hex_layer")
        open(f, "wb").write(encode_flat("Impassable", imp.reshape(-1)))
        p = subprocess.run([V.CAIME, "import-layer", "--map", a.carte, "--layer", "Impassable", "--file", f],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    print(f"  sauvegarde : {sauve}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
