#!/usr/bin/env python3
"""
villes_expanded.py - emplacements de colonie (TownSlots, TownSprawl) et passage (Impassable) de la grille d'Expanded.

Pourquoi (25.09.2026, 19 h 45 ; Charles : « continue à travailler sur Expanded ») : les régions sont posées
(`regions_expanded.py`) ; chaque région terrestre neuve a besoin de sa ville, et l'extension doit devenir franchissable
selon l'Atlas (session « Extension », 18 h : franchissable = couche de WH1 dans le cadre + régions neuves + les cinq
ouvertures des cols ; terre sauvage infranchissable).

Étapes (rien dans le kit ; la carte vit dans `04-projets\\saison-expanded\\caime\\`) :
1. villes de la Saison recopiées dans le cadre, telles quelles (« aucune ville de WH1 ne bouge », Atlas) ; contrôle : la
   ville de chaque région de WH1 reste dans sa région après les découpes ;
2. passage : cadre = couche de WH1 ; hors cadre et découpes : les cases des régions neuves (terre) et des mers déclarées
   deviennent franchissables ; les ouvertures (`extension_routes.json`, `ouvertures[].points`, tracé d'un hex de large)
   aussi ; le voile reste infranchissable ;
3. une graine de ville par région terrestre neuve, au `hex_ville_expanded` de la déclaration (ou à la case de terre de la
   région la plus proche), plus 3 hex de port sur la mer voisine pour une région `port` ;
4. `02-scripts\\grow_town_slots.py` fait pousser chaque ville à 19 hex (16 pour un port) et l'étalement, d'abord à blanc ;
5. import dans le map.hex de TownSlots, TownSprawl et Impassable seulement (erreur de `grow_town_slots` : il écrit tout).

Usage :
    python villes_expanded.py [--sans-import]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, encode_flat, caime_names, flat_names    # noqa: E402
from grow_town_slots import neighbours, hex_distance                          # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
COUCHES_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE_EXP = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
COUCHES = os.path.join(ICI, "couches-expanded")
TRAVAIL = os.path.join(COUCHES, "villes-travail")
SORTIE = os.path.join(COUCHES, "villes-sortie")
ATLAS = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
GROW = os.path.join(ATELIER, r"02-scripts\grow_town_slots.py")
W, H, DX, DY, SW, SH = 560, 825, 120, 250, 400, 440
MAIN, PORT = 0, 1


def lire(dossier, fichier):
    return read_layer(os.path.join(dossier, fichier))[1]


def trace(points):
    """Hex traversés par une ligne brisée (coordonnées de l'Atlas -> grille : x + 120, y + 250)."""
    out = set()
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for t in np.linspace(0, 1, n):
            out.add((int(round(x0 + (x1 - x0) * t)) + DX, int(round(y0 + (y1 - y0) * t)) + DY))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-import", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.load(open(os.path.join(ATLAS, "expanded_declaration.json"), encoding="utf-8"))
    routes = json.load(open(os.path.join(ATLAS, "extension_routes.json"), encoding="utf-8"))
    rv = np.load(os.path.join(ATLAS, "reves_grilles.npz"))
    listes, w, h = caime_names(CAIME, CARTE_EXP)
    assert (w, h) == (W, H)
    noms = flat_names(listes, "Regions")
    idx = {n: i for i, n in enumerate(noms)}
    n_sols_terre = len(listes.get("Land ground types", []))
    reg = lire(COUCHES, "layer_regions.hex_layer").reshape(H, W)
    sol = lire(COUCHES, "layer_groundtypes.hex_layer").reshape(H, W)
    climat = lire(COUCHES, "layer_climates.hex_layer").reshape(H, W)
    # 0. la bande du sud (Bois Rêveur) : sols et climats REFLÉTÉS d'Athel Loren (rangée R' = 507 − R, comme le relief de
    # projet_expanded.py) sur les cases du reflet ; éther = mer ; voile = montagne (infranchissable)
    rterre = np.zeros((H, W), bool)
    rterre[0:rv["terre"].shape[0], :W] = rv["terre"]
    rvoile = np.zeros((H, W), bool)
    rvoile[0:rv["voile"].shape[0], :W] = rv["voile"]
    sols_noms = flat_names(listes, "GroundTypes")
    mer_eth = sols_noms.index("sea_ocean") if "sea_ocean" in sols_noms else n_sols_terre
    montagne = sols_noms.index("mountain")
    miroir = lambda a: a[507 - np.arange(H)[:, None].clip(0, 507), np.arange(W)[None, :]]      # noqa: E731
    sud = np.zeros((H, W), bool)
    sud[0:250] = True
    sol = np.where(sud & rterre & ~rvoile, miroir(sol), sol)
    climat = np.where(sud & rterre & ~rvoile, miroir(climat), climat)
    sol = np.where(sud & ~rterre, mer_eth, sol)
    sol = np.where(rvoile, montagne, sol)
    with open(os.path.join(COUCHES, "layer_groundtypes.hex_layer"), "wb") as fh:
        fh.write(encode_flat("GroundTypes", sol.reshape(-1)))
    with open(os.path.join(COUCHES, "layer_climates.hex_layer"), "wb") as fh:
        fh.write(encode_flat("Climates", climat.reshape(-1)))
    terre = (sol >= 0) & (sol < n_sols_terre)
    print(f"  Bois Rêveur : {int((sud & terre).sum())} hex de terre reflétés")
    cadre = np.zeros((H, W), bool)
    cadre[DY:DY + SH, DX:DX + SW] = True

    # 1. villes de la Saison dans le cadre
    slots = np.full((H, W), -1, np.int64)
    sprawl = np.zeros((H, W), np.int64)
    slots[DY:DY + SH, DX:DX + SW] = lire(COUCHES_SAISON, "layer_town_slots.hex_layer").reshape(SH, SW)
    sprawl[DY:DY + SH, DX:DX + SW] = lire(COUCHES_SAISON, "layer_town_sprawl.hex_layer").reshape(SH, SW)
    s_reg = lire(COUCHES_SAISON, "layer_regions.hex_layer").reshape(SH, SW)
    s_noms = flat_names(caime_names(CAIME, os.path.join(
        r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit",
        r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex"))[0], "Regions")
    deplacees = []
    for i in np.unique(s_reg[lire(COUCHES_SAISON, "layer_town_slots.hex_layer").reshape(SH, SW) == MAIN]):
        m = np.zeros((H, W), bool)
        m[DY:DY + SH, DX:DX + SW] = (s_reg == i)
        m &= slots == MAIN
        dans = set(noms[k] for k in np.unique(reg[m]))
        if len(dans) != 1:
            deplacees.append((s_noms[i], sorted(dans)))
    print(f"  villes de WH1 recopiées ; villes coupées ou passées dans une autre région : {deplacees or 'aucune'}")

    # 2. passage
    imp = np.zeros((H, W), np.int64)
    imp[DY:DY + SH, DX:DX + SW] = lire(COUCHES_SAISON, "layer_impassable.hex_layer").reshape(SH, SW)
    terrestres = [e for e in d["regions"] if not e["is_sea"]]
    mers = [e for e in d["regions"] if e["is_sea"]]
    for e in terrestres:
        m = (reg == idx[e["cle_jeu"]]) & terre
        imp[m] = 1
    for e in mers:
        imp[(reg == idx[e["cle_jeu"]]) & ~terre] = 1
    ouv = set()
    for o in routes["ouvertures"]:
        ouv |= trace(o["points"])
    for q, r in ouv:
        if 0 <= q < W and 0 <= r < H:
            imp[r, q] = 1
    voile = np.zeros((H, W), bool)
    voile[0:rv["voile"].shape[0], :W] = rv["voile"]
    imp[voile] = 0
    print(f"  passage : {int(imp.sum())} hex franchissables ; ouvertures : {len(ouv)} hex")

    # 3. graines des villes neuves
    graines, sans_ville = 0, []
    for e in terrestres:
        rid = idx[e["cle_jeu"]]
        if (slots[reg == rid] == MAIN).any():
            continue                                   # reprise de Fort Solstice : ville de WH1 déjà là
        cible = e.get("hex_ville_expanded")
        if not cible and e.get("reflet_de") in idx:
            # ville reflétée : le reflet du centre de la ville de WH1 (rangée 507 − R)
            m = (reg == idx[e["reflet_de"]]) & (slots == MAIN)
            if m.any():
                rr, qq = np.argwhere(m).mean(0)
                cible = [int(round(qq)), int(507 - round(rr))]
        cases = np.argwhere((reg == rid) & terre)
        if not len(cases):
            sans_ville.append(e["cle_jeu"])
            continue
        if cible:
            dist = [hex_distance((int(c[1]), int(c[0])), (int(cible[0]), int(cible[1]))) for c in cases]
            r0, q0 = cases[int(np.argmin(dist))]
        else:
            r0, q0 = cases[len(cases) // 2]
            sans_ville.append(e["cle_jeu"] + " (centre pris au milieu)")
        slots[r0, q0] = MAIN
        for nq, nr in neighbours(int(q0), int(r0), W, H):
            if reg[nr, nq] == rid and terre[nr, nq]:
                slots[nr, nq] = MAIN
        if e.get("port"):
            mer_proche = [(nq, nr) for q, r in [(int(q0), int(r0))] + list(neighbours(int(q0), int(r0), W, H))
                          for nq, nr in neighbours(q, r, W, H) if not terre[nr, nq]]
            if not mer_proche:
                pts = np.argwhere(~terre)
                dist = [hex_distance((int(p[1]), int(p[0])), (int(q0), int(r0))) for p in pts]
                pr, pq = pts[int(np.argmin(dist))]
                mer_proche = [(int(pq), int(pr))]
            for nq, nr in mer_proche[:3]:
                slots[nr, nq] = PORT
                reg[nr, nq] = rid          # comme dans WH1 : les hex de port, en mer, sont à la région de la ville
        graines += 1
    print(f"  graines de villes neuves : {graines} ; remarques : {sans_ville or 'aucune'}")

    # 4. croissance (à blanc puis pour de bon)
    shutil.rmtree(TRAVAIL, ignore_errors=True)
    os.makedirs(TRAVAIL)
    couches = {"Regions": reg, "GroundTypes": sol, "TownSlots": slots, "TownSprawl": sprawl, "Impassable": imp,
               "Rivers": lire(COUCHES, "layer_rivers.hex_layer"), "Beaches": lire(COUCHES, "layer_beaches.hex_layer")}
    for nom, v in couches.items():
        with open(os.path.join(TRAVAIL, f"layer_{nom.lower()}.hex_layer"), "wb") as fh:
            fh.write(encode_flat(nom, np.asarray(v).reshape(-1)))
    base = [sys.executable, GROW, "--caime", CAIME, "--map", CARTE_EXP, "--layers", TRAVAIL, "--out", SORTIE]
    p = subprocess.run(base + ["--dry-run"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("  " + "\n  ".join((p.stdout + p.stderr).strip().splitlines()[-14:]))
    shutil.rmtree(SORTIE, ignore_errors=True)
    subprocess.run(base, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if a.sans_import:
        return 0
    args = [CAIME, "import-layer", "--map", CARTE_EXP]
    for nom in ("TownSlots", "TownSprawl", "Impassable", "Regions", "GroundTypes"):
        args += ["--layer", nom, "--file", os.path.join(SORTIE, f"layer_{nom.lower()}.hex_layer")]
    args += ["--layer", "Climates", "--file", os.path.join(COUCHES, "layer_climates.hex_layer")]
    # la couche des régions avec les hex de port rattachés à leur ville devient la référence du chantier
    shutil.copy2(os.path.join(SORTIE, "layer_regions.hex_layer"), os.path.join(COUCHES, "layer_regions.hex_layer"))
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
