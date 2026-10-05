#!/usr/bin/env python3
"""
camps_expanded.py - les CAMPS DES HOMMES-BÊTES d'occupation dans les régions neuves d'Expanded (5.10.2026), à la manière
de WH1 ; appelé par `projet_expanded.py` (calque `camps_expanded`) ; seul, il fait un essai à blanc.

Pourquoi (Charles, 5.10.2026, planche de l'Arden : « oui, vas-y… et généralise à tout l'Atlas ») : dans WH1, chaque région
a son camp des hommes-bêtes, visible seulement quand une culture « du Chaos » la tient (culture_mask « démons,
hommes-bêtes, Norsca, Chaos ») : deux perches (bst_pole), boucliers, crânes, cornes, tissus sanglants, cage d'os, herbes
bst_ (relevé `scratchpad\\occupation_wh1.py`, `bst_groupes.py` : 27 camps entiers). Leur place, mesurée sur WH1
(`bst_distance_villes.py`) : à 13 hex de la ville en médiane (9 à 20), sur la prairie (24 / 27), une route à 3 hex ou
moins (22 / 27). Les régions neuves de l'Atlas n'en avaient aucun.

Règle : pour chaque région terrestre neuve (moins de la moitié de ses hex dans la zone gardée de WH1, hors Bois Rêveur et
terre sauvage, avec une ville), un camp de WH1 recopié TEL QUEL (pièces, positions relatives, échelles, masque de
culture), tourné d'un lacet (12 essais), posé sur la case la mieux notée : prairie d'abord (puis forêt claire, collines,
champs, forêt), à 9 à 20 hex de la ville (au plus près de 13), une route à 3 hex ou moins, hors ville, emprise, route,
rivière, pont, eau, pente > PENTE_MAX ; chaque pièce hors de l'encombrement des autres calques ; hauteur de chaque pièce =
notre relief + son écart au relief de WH1 (perches, cages qui pendent). Les camps se répartissent entre les 27 de WH1.
"""
import glob
import hashlib
import math
import os
import re
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H, SUD, UX, UZ, px_de                        # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names               # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
SORTIE_GRILLE = os.path.join(ICI, r"couches-expanded\villes-sortie")
COUCHES = os.path.join(ICI, "couches-expanded")
LARGEUR_S, PROF_S = 266.53, 338.9
GROUPE_U = 3.0                 # pièces bst_ à moins de 3 u l'une de l'autre : un même camp
CAMP_MIN = 9                   # pièces
D_MIN, D_MAX, D_VISEE = 9, 20, 13
ROUTE_HEX = 3
REGLE_ELARGIE = ((6, 24, 5),)  # (distance min, max, route à n hex) si la règle de WH1 ne trouve pas de place
PENTE_MAX = 0.45
DEGAGEMENT_U = 0.6
CANDIDATS = 40
SOLS = {"grassland": 0.0, "light_forest": 1.0, "hilly_light_forest": 1.2, "hills": 1.5, "farmland": 1.5,
        "forest": 2.0, "hilly_forest": 2.2}
MASQUE_OCCUPATION = "wh_dlc03_bst_beastmen"
ENT = re.compile(r'[ \t]*<entity id="[^"]*">.*?</entity>[ \t]*\r?\n', re.S)
RX_T = re.compile(r'<ECTransform position="([^"]*)" rotation="([^"]*)" scale="([^"]*)"')


def _h01(*cles):
    return int(hashlib.sha1("/".join(map(str, cles)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def _ident(*cles):
    return "1" + hashlib.sha1(("saison_expanded/camps/" + "/".join(map(str, cles))).encode()).hexdigest()[:14]


def camps_wh1(src, h_s):
    """Les camps d'occupation de WH1 : [[{texte, d (x, z relatifs au centre), dy (écart au relief de WH1), rot, ech}]]."""
    pieces = []
    for p in sorted(glob.glob(os.path.join(src, "*.layer"))):
        for e in ENT.findall(open(p, encoding="utf-8", errors="replace").read()):
            if "/bst_" not in e or MASQUE_OCCUPATION not in e or "<ECMesh " not in e:
                continue
            t = RX_T.search(e)
            if not t:
                continue
            x, y, z = map(float, t.group(1).split())
            pieces.append({"texte": e, "x": x, "y": y, "z": z, "rot": t.group(2), "ech": t.group(3)})
    xy = np.array([[q["x"], q["z"]] for q in pieces])
    lab = -np.ones(len(pieces), int)
    k = 0
    for i in range(len(pieces)):
        if lab[i] >= 0:
            continue
        pile, lab[i] = [i], k
        while pile:
            j = pile.pop()
            v = np.nonzero((lab < 0) & (np.hypot(*(xy - xy[j]).T) < GROUPE_U))[0]
            lab[v] = k
            pile.extend(v.tolist())
        k += 1
    rows, cols = h_s.shape
    camps = []
    for g in range(k):
        m = [pieces[i] for i in np.nonzero(lab == g)[0]]
        if len(m) < CAMP_MIN or not any("bst_pole" in q["texte"] for q in m):
            continue
        cx = float(np.mean([q["x"] for q in m]))
        cz = float(np.mean([q["z"] for q in m]))
        for q in m:
            c = int(np.clip(round(q["x"] * cols / LARGEUR_S - 0.5), 0, cols - 1))
            r = int(np.clip(round((PROF_S - q["z"]) * rows / PROF_S - 0.5), 0, rows - 1))
            dy = q["y"] - float(h_s[r, c])
            q["d"] = (q["x"] - cx, q["z"] - cz)
            q["dy"] = dy if abs(dy) <= 1.6 else 0.0
        camps.append(m)
    camps.sort(key=lambda m: (-len(m), round(m[0]["x"], 2)))
    return camps


def grille():
    listes = caime_names(CAIME, CARTE)[0]
    noms = flat_names(listes, "Regions")
    sols = flat_names(listes, "GroundTypes")
    n_terre = len(listes.get("Land ground types", []))
    lire = lambda d, n: read_layer(os.path.join(d, f"layer_{n}.hex_layer"))[1].reshape(H, W)   # noqa: E731
    c = {n: lire(SORTIE_GRILLE, n) for n in ("regions", "groundtypes", "townslots", "townsprawl", "rivers", "impassable")}
    c["roads"], c["bridges"] = lire(COUCHES, "roads"), lire(COUCHES, "bridges")
    return noms, sols, n_terre, c


def poser(height, src, h_s, dst):
    """Texte du calque `camps_expanded` et bilan."""
    import cv2
    import projet_expanded as P
    import pose_au_sol as PS
    import royaume_slaanesh as RS
    import vie_expanded as VE
    camps = camps_wh1(src, h_s)
    PETITS = list(range(len(camps)))[::-1][:3]          # les trois camps modèles les plus petits (tri par taille)
    noms, sols, n_terre, c = grille()
    reg, gt, sl, sp = c["regions"], c["groundtypes"], c["townslots"], c["townsprawl"]
    garde = P.garde_wh1_hex()
    encombre, n_obj = VE._encombrement(dst, height.shape, DEGAGEMENT_U, sauf=("camps_expanded",))
    terre = (gt >= 0) & (gt < n_terre)
    base = (terre & (c["impassable"] == 1) & (sl < 0) & (sp == 0) & (c["roads"] == 0) & (c["rivers"] == 0)
            & (c["bridges"] == 0) & ~garde)

    def pres_route(n):
        return cv2.dilate((c["roads"] > 0).astype(np.uint8), np.ones((2 * n + 1, 2 * n + 1), np.uint8)) > 0
    regles = [(D_MIN, D_MAX, base & pres_route(ROUTE_HEX), "règle de WH1")] + \
             [(a, b, base & pres_route(n), "règle élargie") for a, b, n in REGLE_ELARGIE]
    libre = base
    gy, gx = np.gradient(cv2.GaussianBlur(height, (0, 0), 1.0))
    pente = np.hypot(gx * height.shape[1] / (W * UX), gy * height.shape[0] / (H * UZ * 3 ** 0.5 / 2))

    def px(x, z):
        a, b = px_de(np.asarray(x, float), np.asarray(z, float), height.shape)
        return (int(np.clip(round(float(b)), 0, height.shape[0] - 1)), int(np.clip(round(float(a)), 0, height.shape[1] - 1)))

    def piece_ok(x, z, i):
        q, r = int(x / UX), int(z / UZ)
        if not (0 <= q < W and 0 <= r < H) or reg[r, q] != i or not libre[r, q]:
            return False
        p = px(x, z)
        return height[p] >= 0.12 and pente[p] <= PENTE_MAX and not encombre[p]

    sortie, bilan, poses = [], Counter(), []
    for i, nom in enumerate(noms):
        cases = np.argwhere(reg == i)
        if not len(cases) or "wilderness" in nom:
            continue
        if not terre[cases[:, 0], cases[:, 1]].any():
            continue
        if garde[cases[:, 0], cases[:, 1]].mean() >= 0.5 or (cases[:, 0] < SUD).any():
            continue
        v = np.argwhere((sl == 0) & (reg == i))
        if not len(v):
            bilan["région sans ville"] += 1
            continue
        vr, vq = v.mean(0)
        # (5.10.2026, premier passage : 8 régions sans camp) la règle de WH1 d'abord ; à défaut, la règle élargie
        # (REGLE_ELARGIE) et les camps modèles les plus petits
        camp_i = int(_h01(nom, "camp") * len(camps))
        modeles = [camp_i] + [j for j in PETITS if j != camp_i]
        trouve = None
        for d_min, d_max, libre_r, quelle in regles:
            rr, qq = np.nonzero(libre_r & (reg == i))
            d = np.hypot(qq - vq, rr - vr)
            m = (d >= d_min) & (d <= d_max)
            if not m.any():
                continue
            rr, qq, d = rr[m], qq[m], d[m]
            note = (np.array([SOLS.get(sols[g], 3.0) for g in gt[rr, qq]]) + 0.05 * np.abs(d - D_VISEE)
                    + 0.01 * np.array([_h01(nom, a, b) for a, b in zip(qq, rr)]))
            for ci in (modeles if quelle != "règle de WH1" else modeles[:1]):
                for k in np.argsort(note)[:CANDIDATS]:
                    q0, r0 = int(qq[k]), int(rr[k])
                    x0, z0 = (q0 + 0.5) * UX, (r0 + 0.5) * UZ
                    lacet0 = 360.0 * _h01(nom, "lacet")
                    for t in range(12):
                        lacet = lacet0 + 30.0 * t
                        R = PS._rot_y(lacet)
                        pts = [(x0 + (np.array([q["d"][0], 0, q["d"][1]]) @ R)[0],
                                z0 + (np.array([q["d"][0], 0, q["d"][1]]) @ R)[2]) for q in camps[ci]]
                        if all(piece_ok(x, z, i) for x, z in pts):
                            trouve = (q0, r0, lacet, pts, ci, quelle)
                            break
                    if trouve:
                        break
                if trouve:
                    break
            if trouve:
                break
        if not trouve:
            bilan["région sans place pour un camp entier"] += 1
            continue
        q0, r0, lacet, pts, camp_i, quelle = trouve
        bilan[f"camps posés par la {quelle}"] += 1
        R = PS._rot_y(lacet)
        for j, (q, (x, z)) in enumerate(zip(camps[camp_i], pts)):
            M = PS.matrice_terry(q["rot"], q["ech"]) @ R
            rot, ech = RS.rotation_terry(M)
            y = float(height[px(x, z)]) + q["dy"]
            e = re.sub(r'<entity id="[^"]*">', f'<entity id="{_ident(nom, j)}">', q["texte"], count=1)
            e = RX_T.sub(f'<ECTransform position="{x:.5f} {y:.5f} {z:.5f}" '
                         f'rotation="{rot[0]:.5f} {rot[1]:.5f} {rot[2]:.5f}" scale="{ech[0]:.5f} {ech[1]:.5f} {ech[2]:.5f}"',
                         e, count=1)
            sortie.append(e if e.endswith("\n") else e + "\n")
        poses.append((nom, q0, r0, len(pts)))
        bilan["camps posés"] += 1
        bilan["pièces"] += len(pts)
    texte = ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- camps_expanded -->\n<layer version="41">\n\t<entities>\n'
             + "".join(sortie) + "\t</entities>\n\t<associations>\n\t\t<Logical/>\n\t\t<Transform/>\n\t</associations>\n"
             "</layer>\n")
    print(f"  camps des hommes-bêtes (occupation, à la manière de WH1 ; {len(camps)} camps modèles de WH1) : "
          + " ; ".join(f"{k} {v}" for k, v in sorted(bilan.items())))
    return texte, poses


def main():
    """Essai à blanc sur le projet du bac à sable (relief et calques déjà écrits par projet_expanded)."""
    sys.stdout.reconfigure(encoding="utf-8")
    from PIL import Image
    import projet_expanded as P
    Image.MAX_IMAGE_PIXELS = None
    h = np.asarray(Image.open(glob.glob(os.path.join(P.DST, "*.height.*.tif"))[0]), np.float32)
    h_s = np.asarray(Image.open(glob.glob(os.path.join(P.SRC, "*.height.*.tif"))[0]), np.float32)
    _, poses = poser(h, P.SRC, h_s, P.DST)
    for p in poses[:80]:
        print("   ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
