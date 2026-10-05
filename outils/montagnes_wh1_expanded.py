#!/usr/bin/env python3
"""
montagnes_wh1_expanded.py - les montagnes de WH1 (maillages drapés) dans Expanded : lesquelles garder, et la grille sous
leur roche (5.10.2026).

Pourquoi (Charles, 5.10.2026 : « que les montagnes soient vraiment cohérentes, jolies et naturelles entre elles… les
passages… ne doivent pas bloquer les armées… corrige tous les bugs, anomalies ou bizarreries visuelles » ; déjà le 5.10 au
matin : « deux styles de montagne qui se chevauchent ») : audit (`scratchpad\\audit_poses_wh1.py`) : 24 des 999 poses de
montagne de WH1 gardées (gardées parce que leur PIVOT est dans la zone de WH1) débordent sur 1 854 hex FRANCHISSABLES de
l'Atlas ; les plus grandes sont des montagnes de bordure de WH1 (43 × 43, 44 × 43…) à 80-92 % HORS de la zone de WH1,
posées sur Sanglac, La Maisontaal, les Sœurs Pâles, Grung Zint, Helmgart, les Voûtes : armées qui traversent la roche,
deux reliefs qui se chevauchent.

Règle :
- une pose dont MOINS DE LA MOITIÉ du rectangle est dans la zone gardée est RETIRÉE (`pivots_retires`, lu par
  projet_expanded : ni son objet, ni le relief de WH1 sous elle) : le relief et la grille de l'Atlas valent là ;
- une pose gardée qui déborde : les hex de l'Atlas hors de la zone gardée, franchissables, couverts à moitié au moins par
  sa ROCHE (`relief-wh1\\montagnes_wh1.npy`, emprise au pixel, pas le rectangle) deviennent INFRANCHISSABLES (`--apply`),
  jamais une ville, une étendue, une route, une rivière, un pont, une plage, et jamais en coupant l'accès d'une colonie
  (connexité contrôlée après, retour en arrière sinon).
Usage : python montagnes_wh1_expanded.py [--apply]
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
os.environ.setdefault("SAISON_CARTE", "expanded")
ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from cadre_expanded import W, H, UX, UZ, SW, SH, DX, DY                    # noqa: E402
from caime_layers import read_layer, encode_flat, caime_names               # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
EMPRISE = os.path.join(ATELIER, r"04-projets\saison-des-revelations\relief-wh1\montagnes_wh1.npy")
SAUVEGARDES = os.path.join(ATELIER, r"05-journal\terrain-backups")
PART_MIN = 0.5
COUVERTURE_HEX = 0.5
LARGEUR_S, PROF_S = 266.53, 338.9
_CACHE = {}


def poses_classees():
    """[(pose, (x, z) pivot dans les calques de la Saison, cases du rectangle (Expanded), part dans la zone gardée)] des
    poses dont le pivot est dans la zone gardée (les autres sont déjà retirées par projet_expanded)."""
    if "poses" in _CACHE:
        return _CACHE["poses"]
    import montagnes_wh1 as MW
    import projet_expanded as P
    garde = P.garde_wh1_hex()
    out = []
    for p in MW.poses():
        x, z, _ = MW.transformation(p)
        z = z * MW.Z_VERS_MONDE
        q, r = int(x / (LARGEUR_S / SW)), int(z / (PROF_S / SH))
        if not (0 <= q < SW and 0 <= r < SH and garde[DY + r, DX + q]):
            continue
        vx = np.array([0.0, 128.0 * p.W, 0.0, 128.0 * p.W])
        vz = np.array([0.0, 0.0, -128.0 * p.H, -128.0 * p.H])
        wx, wz = MW.vers_monde(p, vx, vz)
        wx = np.asarray(wx) + P.DX_U
        wz = np.asarray(wz) * MW.Z_VERS_MONDE + P.DZ_U
        q0, q1 = int(np.floor(wx.min() / UX)), int(np.ceil(wx.max() / UX))
        r0, r1 = int(np.floor(wz.min() / UZ)), int(np.ceil(wz.max() / UZ))
        cases = [(rr, qq) for rr in range(max(0, r0), min(H, r1)) for qq in range(max(0, q0), min(W, q1))]
        part = sum(1 for c in cases if garde[c]) / max(len(cases), 1)
        out.append((p, (float(x), float(z)), cases, part))
    _CACHE["poses"] = out
    return out


def pivots_retires():
    """Pivots (x, z) des poses retirées (moins de PART_MIN de leur rectangle dans la zone gardée)."""
    return [pv for _, pv, _, part in poses_classees() if part < PART_MIN]


def est_retiree(x, z, tol=0.05):
    pv = pivots_retires()
    return any(abs(x - a) <= tol and abs(z - b) <= tol for a, b in pv)


def roche_hex():
    """Part de chaque hex d'Expanded (H, W ; rangée 0 au sud) couverte par la roche des montagnes de WH1 (emprise au
    pixel de la Saison, placée dans la grille d'Expanded)."""
    e = np.load(EMPRISE).astype(np.float32)                 # Saison, nord en haut, 8 px par hex
    f = 8
    h_s = e[:SH * f].reshape(SH, f, SW, f).mean(axis=(1, 3))[::-1]   # rangée 0 au sud
    out = np.zeros((H, W), np.float32)
    out[DY:DY + SH, DX:DX + SW] = h_s
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import projet_expanded as P
    from grow_town_slots import components
    garde = P.garde_wh1_hex()
    poses = poses_classees()
    retirees = [x for x in poses if x[3] < PART_MIN]
    gardees = [x for x in poses if x[3] >= PART_MIN]
    print(f"  poses gardées par leur pivot : {len(poses)} ; retirées (moins de {PART_MIN:.0%} dans la zone de WH1) : "
          f"{len(retirees)}")
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([CAIME, "export-layer", "--map", CARTE, "--out", d, "--format", "binary", "--all"],
                       capture_output=True)
        c = {n: read_layer(os.path.join(d, f"layer_{n}.hex_layer"))[1].reshape(H, W) for n in
             ("ground_types", "impassable", "town_slots", "town_sprawl", "roads", "rivers", "bridges", "beaches")}
    n_terre = len(caime_names(CAIME, CARTE)[0].get("Land ground types", []))
    terre = (c["ground_types"] >= 0) & (c["ground_types"] < n_terre)
    roche = roche_hex()
    sous = np.zeros((H, W), bool)
    for _, _, cases, _ in gardees:
        for rc in cases:
            sous[rc] = True
    libre = ((c["town_slots"] < 0) & (c["town_sprawl"] == 0) & (c["roads"] == 0) & (c["rivers"] == 0)
             & (c["bridges"] == 0) & (c["beaches"] == 0))
    bloquer = sous & ~garde & terre & (c["impassable"] == 1) & (roche >= COUVERTURE_HEX) & libre
    print(f"  hex de l'Atlas sous la roche des poses gardées, franchissables, à rendre infranchissables : {int(bloquer.sum())}")
    imp = c["impassable"].copy()
    imp[bloquer] = 0
    from grow_town_slots import neighbours
    # (premier passage : une case infranchissable isolée, Info de CAIME) un hex bloqué sans voisin infranchissable reste
    # franchissable
    for r, q in np.argwhere(bloquer):
        if not any(imp[nr, nq] == 0 and terre[nr, nq] for nq, nr in neighbours(int(q), int(r), W, H)):
            imp[r, q] = 1
    # connexité : toutes les colonies sur un seul ensemble franchissable (terre et mer)
    lab, n_comp = components(imp == 1, W, H)                # terre et mer franchissables (comme connexite_expanded)
    villes = np.argwhere(c["town_slots"] == 0)
    ids = {int(lab[r, q]) for r, q in villes}
    # (premier passage : 2 poches franchissables enfermées par la roche, sans colonie) refermées : aucune case où une armée
    # ne peut aller
    if len(ids) == 1:
        principale = next(iter(ids))
        poches = (lab >= 0) & (lab != principale) & terre
        anciennes, _ = components(c["impassable"] == 1, W, H)
        # seulement les poches NÉES du blocage (pas les enclaves d'avant, s'il y en a)
        nees = poches & (anciennes == anciennes[tuple(villes[0])])
        imp[nees] = 0
        print(f"  poches franchissables enfermées par la roche, refermées : {int(nees.sum())} hex")
    print(f"  composantes franchissables touchées par les colonies après : {len(ids)}")
    if len(ids) > 1:
        raise SystemExit("une colonie serait coupée du reste : rien d'écrit")
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    os.makedirs(SAUVEGARDES, exist_ok=True)
    sauve = os.path.join(SAUVEGARDES, time.strftime("%Y%m%d-%H%M%S") + "-map.hex-expanded-avant-roche-wh1")
    shutil.copy2(CARTE, sauve)
    with tempfile.TemporaryDirectory() as d:
        f_ = os.path.join(d, "imp.hex_layer")
        open(f_, "wb").write(encode_flat("Impassable", imp.reshape(-1)))
        p = subprocess.run([CAIME, "import-layer", "--map", CARTE, "--layer", "Impassable", "--file", f_],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    print(f"  sauvegarde : {sauve}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
