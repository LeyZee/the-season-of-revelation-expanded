#!/usr/bin/env python3
"""
plages_expanded.py - les PLAGES de l'extension (couche Beaches de CAIME), là où la côte est basse (5.10.2026).

Pourquoi (Charles, en jeu, 5.10.2026 : « mets les falaises là où il faut, les plages là où il faut… que tout soit logique,
naturel ») : la doc de CAIME, « Beaches : coastal landing hexes where amphibious armies can come ashore » ; CAIME peint
« falaise » toute terre côtière qui n'est pas une plage. L'extension n'avait AUCUNE plage hors des 10 ports (une case
chacun) : aucune côte où débarquer, et ces plages d'une case sont exactement les formes que BOB ne sait pas paver
(recherche `05-journal\\2026-10-05-tuiles-cote\\RAPPORT.md` : 10 plages d'une case sur 10 en trou ; chez CA, les plages
sont des suites de cases).

Règle : sur la terre côtière de l'Atlas (hors zone gardée de WH1, des Voûtes et du Bois Rêveur), une case est plage si la
terre est basse alentour (relief du projet au plus BAS_U sur RAYON_HEX hex vers l'intérieur), hors montagne, route,
rivière ; les plages se gardent en suites d'au moins SUITE_MIN cases le long de la côte (les plus courtes redeviennent
falaise). Chaque plage de port est prolongée le long de la côte jusqu'à SUITE_MIN cases. La forme terre / mer ne change
pas (règle n° 97 intacte).

Usage : python plages_expanded.py [--apply]     (grille du bac à sable ; sauvegarde avant écriture)
"""
import argparse
import glob
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
from cadre_expanded import W, H, DY, UX, UZ, px_de                            # noqa: E402

BAS_U = 0.8                            # (5.10.2026 : 1,6 en faisait 85 % de la côte ; 0,8 : creux bas, ~1/5)
RAYON_HEX = 3
SUITE_MIN = 3
SAUVEGARDES = os.path.join(V.ATELIER, r"05-journal\terrain-backups")


def relief_hex():
    """Relief du projet du bac à sable au centre de chaque hex (H, W), rangée 0 au sud."""
    from PIL import Image
    import projet_expanded as P
    Image.MAX_IMAGE_PIXELS = None
    h = np.asarray(Image.open(glob.glob(os.path.join(P.DST, "*.height.*.tif"))[0]), np.float32)
    qq, rr = np.meshgrid(np.arange(W), np.arange(H))
    a, b = px_de((qq + 0.5) * UX, (rr + 0.5) * UZ, h.shape)
    return h[np.clip(np.rint(b).astype(int), 0, h.shape[0] - 1), np.clip(np.rint(a).astype(int), 0, h.shape[1] - 1)]


def trace_atlas_hex():
    """Hex (H, W), rangée 0 au sud, des tracés des rivières de l'Atlas (rivieres_atlas, champ ≥ 0,5 à 4 px par hex)."""
    import rivieres_atlas
    f = 4
    ch = rivieres_atlas.champ(f, 0)[:H * f].reshape(H, f, W, f).max(axis=(1, 3))
    return (ch >= 0.5)[::-1]


def calculer(c, n_terre, sols, hh, garde, trace_atlas=None):
    trace_atlas = np.zeros((H, W), bool) if trace_atlas is None else trace_atlas
    terre = (c["ground_types"] >= 0) & (c["ground_types"] < n_terre)
    cote = np.zeros((H, W), bool)
    for r, q in np.argwhere(terre):
        if any(not terre[nr, nq] for nq, nr in neighbours(int(q), int(r), W, H)):
            cote[r, q] = True
    montagne = c["ground_types"] == sols.index("mountain")
    zone = cote & ~garde & (np.arange(H)[:, None] >= DY)
    # terre basse vers l'intérieur : maximum du relief sur la terre à RAYON_HEX hex
    haut = np.full((H, W), np.inf, np.float32)
    for r, q in np.argwhere(zone):
        vus, front, m = {(int(r), int(q))}, [(int(r), int(q))], float(hh[r, q])
        for _ in range(RAYON_HEX):
            nouv = []
            for cr, cq in front:
                for nq, nr in neighbours(cq, cr, W, H):
                    if (nr, nq) not in vus and terre[nr, nq]:
                        vus.add((nr, nq))
                        nouv.append((nr, nq))
                        m = max(m, float(hh[nr, nq]))
            front = nouv
        haut[r, q] = m
    cand = zone & (haut <= BAS_U) & ~montagne & (c["roads"] == 0) & (c["rivers"] == 0) & (c["impassable"] == 1)
    plages = c["beaches"] > 0
    # ports : leur plage prolongée le long de la côte jusqu'à SUITE_MIN cases (suites de côte franchissable sans route)
    prolong = 0
    for r, q in np.argwhere(plages & zone):
        suite, front = {(int(r), int(q))}, [(int(r), int(q))]
        while front and len(suite) < SUITE_MIN:
            nouv = []
            for cr, cq in front:
                for nq, nr in neighbours(cq, cr, W, H):
                    if (nr, nq) in suite or len(suite) >= SUITE_MIN:
                        continue
                    if cote[nr, nq] and terre[nr, nq] and c["impassable"][nr, nq] == 1 and c["roads"][nr, nq] == 0 \
                            and c["rivers"][nr, nq] == 0 and not garde[nr, nq]:
                        suite.add((nr, nq))
                        nouv.append((nr, nq))
            front = nouv
        for x in suite:
            if not cand[x]:
                cand[x] = True
                prolong += 1
    cand |= plages & zone
    # (5.10.2026, Charles : « des rivières qui n'arrivent pas » ; code de CAIME, BaselineTilemapExporter.cs : un hex de terre
    # côtier non plage est une falaise, même avec une rivière ; « river ending at beach » = rivière ET plage) chaque
    # EMBOUCHURE (terre côtière qui porte une rivière de la couche Rivers ou un tracé de l'Atlas) est une plage, partout
    # (zone de WH1 comprise : le chenal des fleuves en a de nouvelles), prolongée le long de la côte jusqu'à SUITE_MIN cases
    riv = (c["rivers"] > 0) | trace_atlas
    bouches = cote & terre & riv & (c["roads"] == 0) & (c["impassable"] == 1) & (np.arange(H)[:, None] >= DY)
    n_bouches = 0
    for r, q in np.argwhere(bouches):
        suite, front = {(int(r), int(q))}, [(int(r), int(q))]
        while front and len(suite) < SUITE_MIN:
            nouv = []
            for cr, cq in front:
                for nq, nr in neighbours(cq, cr, W, H):
                    if (nr, nq) in suite or len(suite) >= SUITE_MIN:
                        continue
                    if cote[nr, nq] and terre[nr, nq] and c["impassable"][nr, nq] == 1 and c["roads"][nr, nq] == 0 \
                            and not montagne[nr, nq]:
                        suite.add((nr, nq))
                        nouv.append((nr, nq))
            front = nouv
        for x in suite:
            if not cand[x]:
                cand[x] = True
                n_bouches += 1
    # suites le long de la côte : au moins SUITE_MIN cases
    lab = -np.ones((H, W), int)
    garder = np.zeros((H, W), bool)
    n_suites = Counter()
    for r, q in np.argwhere(cand):
        if lab[r, q] >= 0:
            continue
        f, cs = deque([(int(r), int(q))]), []
        lab[r, q] = 1
        while f:
            cr, cq = f.popleft()
            cs.append((cr, cq))
            for nq, nr in neighbours(cq, cr, W, H):
                if cand[nr, nq] and lab[nr, nq] < 0:
                    lab[nr, nq] = 1
                    f.append((nr, nq))
        if len(cs) >= SUITE_MIN or any(plages[x] for x in cs):
            for x in cs:
                garder[x] = True
            n_suites["gardées"] += 1
        else:
            n_suites["trop courtes"] += 1
    neuf = (plages & ~zone) | garder
    # (5.10.2026, coupe de la berge nord de la Brienne : terre à 1,25 u, « plage » du lot des fleuves, profil de plage de
    # CA forcé : une pente raide déguisée en plage, ombre sombre) chez CA une plage est sur une terre BASSE (+0,12 à 1 u du
    # trait) : partout (zone de WH1 et berges des fleuves comprises), une plage dont la terre monte au-delà de BAS_U à
    # RAYON_HEX hex vers l'intérieur redevient falaise, sauf les plages de PORT (CA : [mer, mer, plage]) et les EMBOUCHURES
    port_voisin = np.zeros((H, W), bool)
    for r, q in np.argwhere(c["town_slots"] == 1):
        port_voisin[r, q] = True
        for nq, nr in neighbours(int(q), int(r), W, H):
            port_voisin[nr, nq] = True
    haut_partout = np.full((H, W), np.inf, np.float32)
    for r, q in np.argwhere(neuf):
        vus, front, m = {(int(r), int(q))}, [(int(r), int(q))], -np.inf
        for _ in range(RAYON_HEX):
            nouv = []
            for cr, cq in front:
                for nq, nr in neighbours(cq, cr, W, H):
                    if (nr, nq) not in vus and terre[nr, nq]:
                        vus.add((nr, nq))
                        nouv.append((nr, nq))
                        m = max(m, float(hh[nr, nq]))
            front = nouv
        haut_partout[r, q] = m
    hautes = neuf & (haut_partout > BAS_U) & ~port_voisin & ~riv & (c["roads"] == 0)
    neuf = neuf & ~hautes
    # les restes de moins de SUITE_MIN cases (BOB n'a pas de tuile pour une plage d'une case) sauf les plages de port
    vu = np.zeros((H, W), bool)
    n_restes = 0
    for r, q in np.argwhere(neuf):
        if vu[r, q]:
            continue
        f_, cs = deque([(int(r), int(q))]), []
        vu[r, q] = True
        while f_:
            cr, cq = f_.popleft()
            cs.append((cr, cq))
            for nq, nr in neighbours(cq, cr, W, H):
                if neuf[nr, nq] and not vu[nr, nq]:
                    vu[nr, nq] = True
                    f_.append((nr, nq))
        if len(cs) < SUITE_MIN and not any(port_voisin[x] for x in cs):
            for x in cs:
                neuf[x] = False
            n_restes += len(cs)
    hautes_info = int(hautes.sum()) + n_restes
    return neuf, {"côte de l'Atlas (hex)": int(zone.sum()), "basses": int((zone & (haut <= BAS_U)).sum()),
                  "plages de port prolongées (cases)": prolong, "embouchures": int(bouches.sum()),
                  "cases de plage d'embouchure": n_bouches, "suites": dict(n_suites),
                  "plages sur terre haute (et leurs restes) rendues à la falaise": hautes_info,
                  "plages avant": int(plages.sum()), "plages après": int(neuf.sum())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import projet_expanded as P
    listes = caime_names(V.CAIME, V.CARTE_EXP)[0]
    sols = flat_names(listes, "GroundTypes")
    n_terre = len(listes.get("Land ground types", []))
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([V.CAIME, "export-layer", "--map", V.CARTE_EXP, "--out", d, "--format", "binary", "--all"],
                       capture_output=True)
        c = {n: read_layer(os.path.join(d, f"layer_{n}.hex_layer"))[1].reshape(H, W) for n in
             ("ground_types", "beaches", "roads", "rivers", "impassable", "town_slots")}
    neuf, bilan = calculer(c, n_terre, sols, relief_hex(), P.garde_wh1_hex(), trace_atlas_hex())
    print("  plages de l'extension : " + " ; ".join(f"{k} {v}" for k, v in bilan.items()))
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    os.makedirs(SAUVEGARDES, exist_ok=True)
    sauve = os.path.join(SAUVEGARDES, time.strftime("%Y%m%d-%H%M%S") + "-map.hex-expanded-avant-plages")
    shutil.copy2(V.CARTE_EXP, sauve)
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "plages.hex_layer")
        open(f, "wb").write(encode_flat("Beaches", neuf.astype(np.int64).reshape(-1)))
        p = subprocess.run([V.CAIME, "import-layer", "--map", V.CARTE_EXP, "--layer", "Beaches", "--file", f],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    p = subprocess.run([V.CAIME, "validate", "--map", V.CARTE_EXP, "--beaches"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "each" in l)[-1500:])
    print(f"  sauvegarde : {sauve}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
