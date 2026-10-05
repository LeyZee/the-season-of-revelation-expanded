#!/usr/bin/env python3
"""
nature_expanded.py - les objets NATURELS de WH1 sur la terre de l'extension (4.10.2026), appelé par `projet_expanded.py`
(calque `nature_expanded`) ; seul, il fait un essai à blanc et une image (`apercus\\nature-expanded.png`).

Pourquoi (Charles, 4.10.2026 : « que tout semble naturel et vivant… aucune bizarrerie visuelle ») : mesure du 4.10 au
soir, maillages des calques par hex de terre : 0,470 dans le cadre de WH1 gardé, 0,006 sur la terre de l'Atlas (abords
des villes neuves seulement). Hors des forêts (arbres de BOB), l'extension était nue à côté de WH1 : pas une pierre, pas
un buisson.

Règle, « WH1 tel quel, sans rien inventer » (comme `royaume_slaanesh`) : la terre de l'Atlas est pavée de cellules
(CELLULE_U) ; chaque cellule reçoit, par SIMPLE TRANSLATION, les objets naturels d'une cellule de WH1 (zone gardée) qui
lui RESSEMBLE : même mélange de sols CAIME (histogramme), pente voisine ; tirée parmi les meilleures pour ne pas répéter
le même morceau côte à côte. Seuls les objets naturels passent (FAMILLES, DECALQUES) : roches, buissons, herbes, roseaux,
menhirs et pierres dressées bretonniens, racines, mousse ; jamais les décors propres à une région de WH1 (fissures des
peaux-vertes, crânes, lave, Chaos, tombes et toiles de Mousillon, pointes, ruines, campements, ressources). Chaque objet
garde son écart au sol de WH1 (borné), son orientation et son échelle ; écarté hors de la terre de l'Atlas (zone gardée,
Bois Rêveur, Voûtes, mer, eau), sur une ville, une route ou une rivière, sur une pente trop raide pour lui, à moins de
DEGAGEMENT_U d'un maillage déjà posé (abords des villes), ou trop près du bord de la carte.

Usage : python nature_expanded.py      (à blanc, sur le projet du bac à sable)
"""
import glob
import hashlib
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H, SUD, DY, UX, UZ, px_de                      # noqa: E402

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APERCU = os.path.join(ICI, "apercus", "nature-expanded.png")
ZH = 3 ** 0.5 / 2
CELLULE_U = 6.0                        # rayon d'une cellule (u du monde)
GRAINE = 20261004
MEILLEURES = 8                         # tirage parmi les N cellules de WH1 les plus ressemblantes
VOUTES = True                          # les Voûtes aussi (accord de Charles, 4.10.2026)
# (premier essai sur les Voûtes : 79 menhirs bretonniens) les pierres levées par les hommes de Bretonnie n'ont rien à
# faire dans les Voûtes ; roches, aiguilles, cairns naturels et buissons de montagne y passent
EXCLUS_VOUTES = ("brt_menhir",)
BORD_CARTE_U = 6.0
DEGAGEMENT_U = 0.5                     # d'un maillage déjà posé (abords des villes)
HAUT_MIN_NATURE_U = 0.3                # (5.10.2026) même une petite roche penchée flotte d'un côté : posée par son emprise
PENTE_MAX = 0.6                        # pente de plus que celle de l'objet chez WH1 (u par u)
DY_BORNES = (-1.0, 0.15)               # écart au sol de WH1 gardé (roches à demi enterrées : oui ; en l'air : non)
FAMILLES = ("generic_props/rocks/", "vegetation/single_shrubs/", "vegetation/grass/", "vegetation/shrubs_and_grass/")
EXCLUS = ("vmp_", "chs_", "nur_", "sla_", "tze_", "kho_", "nor_", "norsca", "grn_crack", "dragon_stone", "obsidian",
          "skull", "lava", "cobweb", "spike", "bone", "grave", "chaos",
          # (premier essai, familles relevées) propres à une région de WH1 : pierres levées et pierres de voie elfes,
          # dallage elfe, éclats de glace de Winterheart, champignons des peaux-vertes, herbes des hommes-bêtes
          "waystone", "standing_stone", "wef_tile", "ice_shard", "grn_mushroom", "geomushroom", "bst_")
# (premier essai) les MAILLAGES elfes (wef_ : pierres, flore d'Athel Loren) restent à Athel Loren ; leurs décalques de
# racines, de mousse et de feuilles passent
MAILLAGES_EXCLUS = ("wef_",)
DECALQUES = ("/roots/", "/rocks/", "/moss/", "/leaves/", "/dead_plants/", "/marsh/")
RX_ENT = re.compile(r'[ \t]*<entity id="[^"]*">.*?</entity>[ \t]*\r?\n', re.S)
RX_POS = re.compile(r'(<ECTransform position=")([-0-9.eE]+) ([-0-9.eE]+) ([-0-9.eE]+)(")')
RX_MOD = re.compile(r'<(ECMesh|ECDecal) model_path="([^"]+)"')


def naturel(sorte, chemin):
    c = chemin.replace("\\", "/").lower()
    if any(e in c.rsplit("/", 1)[-1] for e in EXCLUS):
        return False
    if sorte == "ECMesh":
        return any(f in c for f in FAMILLES) and not c.rsplit("/", 1)[-1].startswith(MAILLAGES_EXCLUS)
    return any(d in c for d in DECALQUES)


def sols_grille():
    """Sols CAIME (H, W) de la grille d'Expanded du bac à sable, rangée 0 au sud."""
    import villes_expanded as V
    from caime_layers import read_layer
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run([V.CAIME, "export-layer", "--map", V.CARTE_EXP, "--out", d, "--format", "binary",
                            "--layer", "GroundTypes"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode:
            raise SystemExit(p.stdout + p.stderr)
        return read_layer(os.path.join(d, "layer_ground_types.hex_layer"))[1].reshape(H, W)


def objets_wh1(dst, height):
    """Objets naturels des calques de régions de WH1 du projet (positions d'Expanded, zone gardée)."""
    out = []
    for f in glob.glob(os.path.join(dst, "*.layer")):
        t = open(f, encoding="utf-8").read()
        nom = re.search(r"<!-- (.*?) -->", t[:300])
        if nom and not nom.group(1).startswith("wh_dlc05"):
            continue                       # nos calques (abords, royaume, vie, rivières…) ; ceux de WH1 n'ont pas d'en-tête
        for e in RX_ENT.findall(t):
            m, p = RX_MOD.search(e), RX_POS.search(e)
            if not (m and p) or not naturel(m.group(1), m.group(2)):
                continue
            x, y, z = float(p.group(2)), float(p.group(3)), float(p.group(4))
            a, b = px_de(np.asarray(x), np.asarray(z), height.shape)
            hy = float(height[int(np.clip(round(float(b)), 0, height.shape[0] - 1)),
                              int(np.clip(round(float(a)), 0, height.shape[1] - 1))])
            tr = re.search(r'rotation="([^"]+)" scale="([^"]+)"', e)
            out.append({"xml": e, "x": x, "z": z, "dy": y - hy, "maillage": m.group(1) == "ECMesh",
                        "modele": m.group(2), "rot": tr.group(1) if tr else "0 0 0", "ech": tr.group(2) if tr else "1 1 1"})
    return out


def poser(height, tuiles, villes=None, routes=None, rivieres=None, sols=None):
    """Texte du calque `nature_expanded` et liste des poses (x, z, maillage)."""
    import cv2
    import projet_expanded as P
    import vie_expanded
    if villes is None:
        import royaume_slaanesh
        villes, routes, rivieres = royaume_slaanesh.couches_grille()
    if sols is None:
        sols = sols_grille()
    rng = np.random.default_rng(GRAINE)
    import pose_au_sol
    import arbres_expanded
    sys.path.insert(0, os.path.join(os.path.dirname(ICI), "..", "02-scripts"))
    from contenu_pack import SourcePacks
    packs = SourcePacks(r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data",
                        exclure=("saison_des_revelations", "zz_startpos_db", "saison_expanded", "!saison", "!!essai"))
    cache_b = {}

    def boite(m):
        return arbres_expanded._boite_ca(m, packs, cache_b)
    garde = P.garde_wh1_hex()
    mer = vie_expanded._eau_mer(tuiles, height.shape)
    # (essai sur les Voûtes : 1 688 objets écartés) le calque déjà posé de la nature ne s'évite pas lui-même, ni la vie
    # (posée après, elle s'écarte des objets)
    encombre, _ = vie_expanded._encombrement(P.DST, height.shape, DEGAGEMENT_U, sauf=("vie_expanded", "nature_expanded"))
    gy, gx = np.gradient(cv2.GaussianBlur(height, (0, 0), 1.0))
    pente_px = np.hypot(gx * height.shape[1] / (W * UX), gy * height.shape[0] / (H * UZ * ZH))

    def ici(x, z):
        a, b = px_de(np.asarray(x, float), np.asarray(z, float), height.shape)
        return (np.clip(np.rint(b).astype(int), 0, height.shape[0] - 1),
                np.clip(np.rint(a).astype(int), 0, height.shape[1] - 1))

    # par hex : terre, zone, pente moyenne
    qq, rr = np.meshgrid(np.arange(W), np.arange(H))
    hy, hx = ici((qq + 0.5) * UX, (rr + 0.5) * UZ)
    terre_h = (height[hy, hx] > 0.12) & ~mer[hy, hx]
    pente_h = pente_px[hy, hx]
    # (4.10.2026, Charles : « si ça peut rendre très bien, des belles montagnes, ajoute les objets naturels de WH1 sur les
    # Voûtes » ; la session des Voûtes n'a pas d'habillage en objets prévu) : terre de l'Atlas ET des Voûtes ; ni zone
    # gardée, ni Bois Rêveur (r < SUD)
    atlas = terre_h & ~garde & (rr >= (SUD if VOUTES else DY))
    source = terre_h & garde & (rr >= DY) & ~villes & ~routes & ~rivieres
    # histogrammes de sols sur le disque de la cellule (hex à peu près carrés : 0,666 × 0,667 u)
    rq = int(math.ceil(CELLULE_U / UX))
    noyau = (np.hypot(*np.mgrid[-rq:rq + 1, -rq:rq + 1]) <= CELLULE_U / UX).astype(np.float32)
    types = [int(t) for t in np.unique(sols[terre_h])]
    hist = np.stack([cv2.filter2D(((sols == t) & terre_h).astype(np.float32), -1, noyau,
                                  borderType=cv2.BORDER_CONSTANT) for t in types], -1)
    n_terre = hist.sum(-1, keepdims=True)
    hist_n = hist / np.maximum(n_terre, 1)
    pente_m = cv2.filter2D(np.where(terre_h, pente_h, 0).astype(np.float32), -1, noyau,
                           borderType=cv2.BORDER_CONSTANT) / np.maximum(n_terre[..., 0], 1)
    # cellules de WH1 candidates : disque entier dans la terre gardée sans ville, route ni rivière
    plein = cv2.erode(source.astype(np.uint8), noyau.astype(np.uint8), borderType=cv2.BORDER_CONSTANT) > 0
    cr, cq = np.nonzero(plein)
    sous = rng.permutation(len(cq))[:6000]
    cq, cr = cq[sous], cr[sous]
    objets = objets_wh1(P.DST, height)
    pos = np.array([(o["x"], o["z"]) for o in objets], float)
    # ancres : réseau hexagonal (monde) sur la terre de l'Atlas
    pas = CELLULE_U * 3 ** 0.5
    ancres = []
    for j, zw in enumerate(np.arange((SUD if VOUTES else DY) * UZ * ZH, H * UZ * ZH + pas, pas * ZH)):
        for xw in np.arange((j % 2) * pas / 2, W * UX + pas, pas):
            q, r = int(xw / UX), int(zw / ZH / UZ)
            if 0 <= q < W and 0 <= r < H and hist[r, q].sum() > 0 and (atlas[max(0, r - rq):r + rq + 1,
                                                                             max(0, q - rq):q + rq + 1]).any():
                ancres.append((xw, zw / ZH))
    ancres = np.array(ancres)
    bilan, sortie, poses = Counter(), [], []
    for ia, (ax, az) in enumerate(ancres):
        q0, r0 = int(ax / UX), int(az / UZ)
        cout = np.abs(hist_n[cr, cq] - hist_n[r0, q0]).sum(-1) + 0.5 * np.abs(pente_m[cr, cq] - pente_m[r0, q0])
        k = np.argsort(cout)[:MEILLEURES]
        c = rng.choice(k)
        cx, cz = (cq[c] + 0.5) * UX, (cr[c] + 0.5) * UZ
        d = np.hypot(pos[:, 0] - cx, (pos[:, 1] - cz) * ZH)
        sel = np.flatnonzero(d <= CELLULE_U * 1.15)
        if not len(sel):
            bilan["cellule de WH1 sans objet naturel"] += 1
            continue
        tx, tz = pos[sel, 0] - cx + ax, pos[sel, 1] - cz + az
        voisins = np.flatnonzero(np.hypot(ancres[:, 0] - ax, (ancres[:, 1] - az) * ZH) < 3 * pas)
        dd = np.hypot(tx[:, None] - ancres[None, voisins, 0], (tz[:, None] - ancres[None, voisins, 1]) * ZH)
        a_moi = voisins[dd.argmin(1)] == ia
        for i, x, z in zip(sel[a_moi], tx[a_moi], tz[a_moi]):
            o = objets[i]
            q, r = int(x / UX), int(z / UZ)
            if min(x, z, W * UX - x, H * UZ - z) < BORD_CARTE_U:
                bilan["trop près du bord de la carte"] += 1
                continue
            if not (0 <= q < W and 0 <= r < H and atlas[r, q]):
                bilan["hors de la terre de l'Atlas"] += 1
                continue
            if r < DY and any(e in o["modele"].lower() for e in EXCLUS_VOUTES):
                bilan["objet bretonnien écarté des Voûtes"] += 1
                continue
            py, px_ = ici(x, z)
            autour = [ici(x + dx * UX, z + dz * UZ) for dx, dz in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5))]
            if mer[py, px_] or any(mer[a] or height[a] < 0.06 for a in autour):
                bilan["eau"] += 1
                continue
            if villes[r, q] or routes[r, q] or rivieres[r, q]:
                bilan["ville, route ou rivière"] += 1
                continue
            sy, sx = ici(o["x"], o["z"])
            if float(pente_px[py, px_]) > float(pente_px[sy, sx]) + PENTE_MAX:
                bilan["sol trop raide"] += 1
                continue
            if o["maillage"] and encombre[py, px_]:
                bilan["trop près d'un objet posé"] += 1
                continue
            y = float(height[py, px_]) + min(max(o["dy"], DY_BORNES[0]), DY_BORNES[1])
            rot = o["rot"]
            if o["maillage"]:
                # (5.10.2026, Charles : « des montagnes flottantes ») WH1 penchait ses roches et ses fissures pour la pente
                # de leur place ; ici : objet PLAT (fissure, dalle) couché sur NOTRE pente, objet HAUT (menhir, aiguille)
                # debout ; puis posé par son emprise, pas par son pivot (dès HAUT_MIN_NATURE_U)
                sol_f = lambda xs, zs: height[ici(xs, zs)]  # noqa: E731
                bt = boite(o["modele"])
                if bt is not None:
                    ech = [float(v) for v in o["ech"].split()]
                    larg = max(bt[1][0] - bt[0][0], bt[1][2] - bt[0][2]) * max(ech[0], ech[2])
                    hautb = (bt[1][1] - bt[0][1]) * ech[1]
                    plat = hautb < 0.6 * larg
                    ang, M = pose_au_sol.orienter(o["rot"], o["ech"], pose_au_sol.normale(x, z, sol_f), 1.0 if plat else 0.0)
                    rot = " ".join(f"{v:.5f}" for v in ang)
                else:
                    M = pose_au_sol.matrice_terry(o["rot"], o["ech"])
                y, verdict = pose_au_sol.ajuster(x, y, z, M, bt, sol_f, haut_min=HAUT_MIN_NATURE_U)
                if y is None:
                    bilan["objet qui flotterait sur la pente"] += 1
                    continue
                if verdict == "abaissé":
                    bilan["objet abaissé jusqu'au sol"] += 1
            ident = "1" + hashlib.sha1(f"saison_expanded/nature/{ia}/{i}".encode()).hexdigest()[:14]
            e = re.sub(r'<entity id="[^"]*">', f'<entity id="{ident}">', o["xml"], count=1)
            e = RX_POS.sub(lambda m: f"{m.group(1)}{x:.5f} {y:.5f} {z:.5f}{m.group(5)}", e, count=1)
            if rot != o["rot"]:
                e = re.sub(r'(<ECTransform position="[^"]*" )rotation="[^"]*"', lambda m: f'{m.group(1)}rotation="{rot}"',
                           e, count=1)
            sortie.append(e if e.endswith("\n") else e + "\n")
            poses.append((x, z, o["maillage"]))
            bilan["posés : " + ("maillage" if o["maillage"] else "décalque")] += 1
    n_m = bilan["posés : maillage"]
    n_hex = int(atlas.sum())
    print(f"  nature d'Expanded : {len(ancres)} cellules, {len(objets)} objets naturels de WH1 en source ; "
          f"{n_m} maillages sur {n_hex} hex de terre de l'Atlas ({n_m / max(n_hex, 1):.3f} par hex)")
    print("   " + " ; ".join(f"{k_} {v}" for k_, v in sorted(bilan.items())))
    texte = ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- nature_expanded -->\n<layer version="41">\n\t<entities>\n'
             + "".join(sortie) + "\t</entities>\n\t<associations>\n\t\t<Logical/>\n\t\t<Transform/>\n\t</associations>\n"
             "</layer>\n")
    return texte, poses


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    from PIL import Image
    import projet_expanded as P
    Image.MAX_IMAGE_PIXELS = None
    height = np.asarray(Image.open(glob.glob(os.path.join(P.DST, "*.height.*.tif"))[0]), np.float32)
    tuiles = np.asarray(Image.open(os.path.join(P.DST, "tile_map.png")).convert("RGBA"))
    texte, poses = poser(height, tuiles)
    # aperçu : relief ombré au quart, maillages en vert, décalques en brun
    petit = height[::4, ::4]
    gy, gx = np.gradient(petit)
    img = np.stack([np.clip(128 + (-gx + gy) * 60, 0, 255).astype(np.uint8)] * 3, -1)
    for x, z, m in poses:
        a, b = px_de(x, z, height.shape)
        i, j = int(round(float(b) / 4)), int(round(float(a) / 4))
        if 0 <= i < img.shape[0] and 0 <= j < img.shape[1]:
            img[i, j] = (40, 200, 60) if m else (150, 90, 40)
    Image.fromarray(img).save(APERCU)
    if "--apply" in sys.argv:
        import decors_expanded
        decors_expanded.declarer(P.DST, P.CIBLE_CLE, "nature_expanded", texte)
        print(f"  aperçu : {APERCU} ; calque nature_expanded écrit dans {P.DST} ({len(poses)} entités)")
    else:
        print(f"  aperçu : {APERCU} ; à blanc : {len(poses)} entités ({len(texte) // 1024} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
