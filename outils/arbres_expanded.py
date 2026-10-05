#!/usr/bin/env python3
"""
arbres_expanded.py - la liste d'arbres d'Expanded (3.10.2026), après BOB : les arbres de WH1 à leur place exacte dans la
partie gardée de WH1, et ceux de l'extension, compilés par BOB depuis les familles porteuses, rendus aux essences de WH1.

Pourquoi : dans la Saison, `build_pack` embarque à la place de la liste de BOB celle des arbres de WH1, chacun à sa position
de WH1 (`arbres_wh1.liste_wh1`, écrite par le générateur dans `04-projets\\saison-des-revelations\\arbres-wh1\\`). Dans
Expanded, la Saison n'est qu'une partie du monde :
1. la liste de la Saison est décalée de (+79,959 ; +254,175) u (monde agrandi) et limitée à la zone où le terrain de WH1 est
   gardé (`projet_expanded.garde_wh1_hex`) ; la hauteur de chaque arbre suit l'écart entre le relief d'Expanded et celui
   de la Saison sous lui (zéro dans la zone gardée, sauf sur son bord fondu) ;
2. la liste compilée par BOB pour Expanded (`working_data\\campaign_maps\\saison_expanded_map\\display\\trees\\`) donne les
   arbres de l'extension et du Bois Rêveur, en familles porteuses de WH3 ; ceux de la zone gardée sont écartés (WH1 les a
   déjà), les autres sont rendus aux essences de WH1 par `ArbresWH1().recomposer` (même règle que la Saison) ;
3. les deux sont fusionnés par identifiant ; en-tête de BOB (bornes du monde d'Expanded).
Sortie : `04-projets\\saison-expanded\\arbres-wh1\\trees.campaign_tree_list` (carte_config.dans_projet du profil expanded).
Rien n'est écrit dans `02-scripts` ni dans le kit. À lancer avec SAISON_CARTE=expanded (le module le pose lui-même).

Usage : python arbres_expanded.py [--apply]
"""
import argparse
import glob
import os
import struct
import sys
from collections import defaultdict

os.environ["SAISON_CARTE"] = "expanded"
import numpy as np                                                    # noqa: E402
from PIL import Image                                                 # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
import carte_config                                                   # noqa: E402
assert carte_config.NOM == "expanded"
import arbres_wh1 as A                                                # noqa: E402
from cadre_expanded import W, H, DX, DY, SW, SH, X_MONDE, Z_MONDE, ipx_de  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
LISTE_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\arbres-wh1\trees.campaign_tree_list")
LISTE_BOB = os.path.join(KIT, r"working_data\campaign_maps\saison_expanded_map\display\trees\trees.campaign_tree_list")
SORTIE = carte_config.dans_projet("arbres-wh1", "trees.campaign_tree_list")
TERRY_E = os.path.join(ATELIER, r"04-projets\saison-expanded\terry\saison_expanded_map")
TERRY_S = os.path.join(KIT, r"raw_data\terrain\campaigns\wh_dlc05_wood_elves_map_1")
UX, UZ = 266.53 / 400, 338.9 / 440
# famille générique de WH3 (tree.tif de la Saison) -> famille porteuse dont les essences de WH1 sont de même nature
GENERIQUES = {"tree_large": "tree_large_jungle", "tree_small": "tree_small_jungle", "grass": "grass_desert_def",
              "shrubs": "shrubs_desert_def", "shrubs_marsh": "shrubs_swamp", "tree_large_snow": "tree_large_snow_pro_tze",
              "tree_small_snow": "tree_small_snow_pro_tze"}
DX_U, DZ_U = DX * UX, DY * UZ
MARGE_EAU = 3                                   # px (12 par unité) autour de l'eau sans arbre


def relief(dossier):
    return np.asarray(Image.open(glob.glob(os.path.join(dossier, "*.height.*.tif"))[0]), np.float32)


def a_la(raster, x, z, rangs_hex):
    """Valeur du raster (nord en haut, étiré sur le monde de la carte : rangs_hex·UZ de haut) aux points du monde (x, z).
    (4.10.2026 : avant, (rangs_hex − z/UZ)·8, jusqu'à 3 px d'écart au nord d'Expanded ; cadre_expanded.px_de)"""
    cols_hex = W if rangs_hex == H else SW
    px = np.clip(np.rint(x * raster.shape[1] / (cols_hex * UX) - 0.5).astype(int), 0, raster.shape[1] - 1)
    py = np.clip(np.rint((rangs_hex * UZ - z) * raster.shape[0] / (rangs_hex * UZ) - 0.5).astype(int), 0,
                 raster.shape[0] - 1)
    return raster[py, px]


# (3.10.2026, première liste d'Expanded : 54 000 arbres empilés sur une ligne à la rangée ~560) BOB écrête la coordonnée z
# des arbres à world_width × 2/√3 (431,45 pour Expanded ; 307,8 pour la Saison, dont il n'emploie pas la liste) : il suppose
# une carte plus large que haute. Les rasters compilés et les objets (global_props.bin) ne sont pas touchés. Au nord de la
# limite, les arbres sont générés depuis le raster d'arbres du projet, comme BOB le fait au sud (mesure du 3.10 sur ses
# arbres au sud : une famille par valeur du raster, densité par pixel, rotation 0 à 5, octet 12 = 1, octet 14 = 255, au sol)
Z_MAX_BOB = 373.14 * 2 / 3 ** 0.5
PAR_VALEUR = {2: ("grass", 0.40), 7: ("tree_large", 0.32), 12: ("shrubs_marsh", 0.60), 29: ("tree_small", 0.35),
              40: ("shrubs", 0.34), 50: ("tree_large_snow", 0.24), 51: ("tree_small_snow", 0.24)}


def completer_nord(gb, h_e):
    """Groupes de BOB sans les arbres écrêtés, plus ceux du nord générés depuis le raster d'arbres. Rend (groupes, n)."""
    garde = []
    for nom, recs in gb:
        z = recs[:, 8:12].copy().view("<f4").reshape(-1)
        garde.append((nom, recs[z < Z_MAX_BOB - 0.3]))
    tr = np.asarray(Image.open(glob.glob(os.path.join(TERRY_E, "*.tree.*.tif"))[0]))
    rng = np.random.default_rng(20261003)
    nouveaux = defaultdict(list)
    p_lim = int((H - (Z_MAX_BOB - 0.3) / UZ) * 2)                  # rangées de pixels du raster (nord en haut) à générer
    zone = tr[:p_lim]
    n = 0
    for v, (fam, dens) in PAR_VALEUR.items():
        py, px = np.nonzero(zone == v)
        k = rng.poisson(dens, len(py))
        py, px = np.repeat(py, k), np.repeat(px, k)
        x = (px + rng.random(len(px))) * X_MONDE / tr.shape[1]
        z = Z_MONDE - (py + rng.random(len(py))) * Z_MONDE / tr.shape[0]
        y = a_la(h_e, x, z, H)
        rec = np.zeros((len(x), 15), np.uint8)
        rec[:, :12] = np.stack([x, y, z], 1).astype("<f4").view(np.uint8).reshape(-1, 12)
        rec[:, 12] = 1
        rec[:, 13] = rng.integers(0, 6, len(x))
        rec[:, 14] = 255
        suff = rng.integers(1, 5, len(x))
        for s in range(1, 5):
            if (suff == s).any():
                nouveaux[f"{fam}_0{s}"].append(rec[suff == s])
        n += len(x)
    groupes = dict(garde)
    for nom, l in nouveaux.items():
        groupes[nom] = np.concatenate([groupes[nom]] + l) if nom in groupes else np.concatenate(l)
    return list(groupes.items()), n


# LA RÉPARTITION DE WH1 (4.10.2026, Charles : « garde la même DA… que ça grouille de vie », étude de The Old World : des
# forêts en massifs, des campagnes ouvertes). Mesure sur la liste finale, par type de sol de la grille : WH1 boise 72 à
# 75 % de ses hex de forêt, d'un seul tenant (80 % de voisins boisés), et laisse ses prairies ouvertes (1,6 % d'hex avec
# un arbre) ; l'extension, semée par BOB pixel par pixel, boisait 46 à 52 % de ses forêts en paquets troués et 9,2 % de
# ses prairies : une poussière d'arbres partout. Hors de la zone gardée, le NOMBRE d'arbres de chaque hex est désormais
# tiré de la distribution de WH1 pour son type de sol (mesurée sur la zone gardée) ; on retire au hasard parmi les arbres
# de l'hex, on ajoute (position au hasard dans l'hex, au sol) seulement là où le raster d'arbres du projet en met
# (jamais sur les abords éclaircis des villes) et hors des emplacements de ville ; essences : celles des arbres de
# l'extension du même type de sol à moins de BLOC_ESSENCES hex, sinon de tout le type. Herbes et buissons : inchangés.
BLOC_ESSENCES = 16
VALEURS_ARBRE = (7, 29, 50, 51)                 # tree.tif : tree_large, tree_small, tree_large_snow, tree_small_snow
MIN_HEX_WH1 = 200                               # hex de WH1 d'un type de sol pour en tirer une distribution
# types de sol réglés sur WH1 : forêts et prairies (premier passage sur tous : les montagnes et collines de la zone gardée
# sont du décor de WH1, peu boisé hors des vallées ; appliqué aux montagnes de l'Atlas, il les dégarnissait de 70 %)
SOLS_COMME_WH1 = ("dense_forest", "light_forest", "hilly_light_forest", "grassland")


def comme_wh1(final, garde, h_e, graine=20261004):
    import cv2
    from caime_layers import read_layer, caime_names, flat_names
    import villes_expanded as V
    rng = np.random.default_rng(graine)
    sols = flat_names(caime_names(V.CAIME, V.CARTE_EXP)[0], "GroundTypes")
    gt = read_layer(os.path.join(V.SORTIE, "layer_groundtypes.hex_layer"))[1].reshape(H, W)
    slots = read_layer(os.path.join(V.SORTIE, "layer_townslots.hex_layer"))[1].reshape(H, W)
    tr = np.asarray(Image.open(glob.glob(os.path.join(TERRY_E, "*.tree.*.tif"))[0]))
    f_tr = tr.shape[1] // W
    # (premier rendu : la forêt s'arrêtait net sur la colonne 450 au nord-est, où la grille des forêts de l'Atlas s'arrête)
    # hors de WH1, le type de sol d'un hex est celui que l'habillage a tissé au centre de l'hex, lisières ondulées comprises
    # (habillage_expanded.categories_pixels, même tirage que le raster d'arbres : f = 2, graine 21), pas celui de la grille
    import habillage_expanded as HE
    _, _, sols_e, n_terre = HE._sols()
    cat_px = HE.categories_pixels(f_tr, tr.shape[0] - H * f_tr, np.random.default_rng(21), sols_e, n_terre)
    cat_hex = cat_px[:H * f_tr][::-1][f_tr // 2::f_tr, f_tr // 2::f_tr][:H, :W]
    gt = np.where(garde, gt, cat_hex)
    a_arbre = np.isin(tr[:H * f_tr], VALEURS_ARBRE)[::-1]                # (rangée de reste en bas ôtée) rangée 0 au sud
    # (premier passage : « permis » à l'hex près laissait les forêts trouées, le raster tissé l'étant aussi) : un hex à un
    # hex au plus d'un arbre du raster ; les abords des villes, éclaircis sur 7 hex, restent sans ajout en leur cœur
    permis = cv2.dilate(a_arbre.reshape(H, f_tr, W, f_tr).any(axis=(1, 3)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    permis &= slots < 0
    noms = [k for k in final if not ("grass" in k or "shrub" in k)]
    recs = [final[k] for k in noms]
    idn = np.concatenate([np.full(len(r), i) for i, r in enumerate(recs)])
    tout = np.concatenate(recs)
    xyz = tout[:, :12].copy().view("<f4").reshape(-1, 3).astype(np.float64)
    q = np.clip((xyz[:, 0] / UX).astype(int), 0, W - 1)
    r = np.clip((xyz[:, 2] / UZ).astype(int), 0, H - 1)
    dans_wh1 = garde[r, q]
    cle = r * W + q
    compte = np.bincount(cle, minlength=H * W).reshape(H, W)
    garder = np.ones(len(tout), bool)
    nouveaux = []
    bilan = []
    for s, nom_s in enumerate(sols):
        if nom_s not in SOLS_COMME_WH1:
            continue
        zw = garde & (gt == s)
        za = ~garde & (gt == s)
        if zw.sum() < MIN_HEX_WH1 or not za.any():
            continue
        dist = np.bincount(np.minimum(compte[zw], 8), minlength=9).astype(np.float64)
        dist /= dist.sum()
        hexs = np.flatnonzero(za.reshape(-1))
        voulu = rng.choice(9, size=len(hexs), p=dist)
        avant = int(compte.reshape(-1)[hexs].sum())
        # arbres de l'extension de ce type de sol : essences, par bloc
        sel = ~dans_wh1 & (gt[r, q] == s)
        if not sel.any():
            continue
        bloc_t = (r[sel] // BLOC_ESSENCES) * (W // BLOC_ESSENCES + 1) + q[sel] // BLOC_ESSENCES
        pool_bloc = defaultdict(list)
        for b, i in zip(bloc_t, np.flatnonzero(sel)):
            pool_bloc[b].append(i)
        pool_tout = np.flatnonzero(sel)
        par_hex = defaultdict(list)
        for i in np.flatnonzero(sel):
            par_hex[cle[i]].append(i)
        ajoutes = retires = 0
        for hx, k in zip(hexs, voulu):
            ici = par_hex.get(hx, [])
            if len(ici) > k:
                for i in rng.choice(ici, len(ici) - k, replace=False):
                    garder[i] = False
                retires += len(ici) - k
            elif len(ici) < k:
                rr, qq = divmod(int(hx), W)
                if not permis[rr, qq]:
                    continue
                pool = pool_bloc.get((rr // BLOC_ESSENCES) * (W // BLOC_ESSENCES + 1) + qq // BLOC_ESSENCES) or pool_tout
                for _ in range(k - len(ici)):
                    modele = int(pool[int(rng.integers(len(pool)))])
                    nouveaux.append((idn[modele], tout[modele].copy(), (qq + rng.random()) * UX, (rr + rng.random()) * UZ))
                ajoutes += k - len(ici)
        bilan.append(f"{nom_s} : {avant} -> {avant - retires + ajoutes} (−{retires} +{ajoutes})")
    print("  répartition de WH1 hors de la zone gardée (arbres par type de sol) : " + " ; ".join(bilan))
    out = {k: v for k, v in final.items() if k not in noms}
    for i, k in enumerate(noms):
        out[k] = recs[i][garder[idn == i]]
    if nouveaux:
        ni = np.array([n[0] for n in nouveaux])
        nr = np.stack([n[1] for n in nouveaux])
        nx = np.array([n[2] for n in nouveaux])
        nz = np.array([n[3] for n in nouveaux])
        ny = a_la(h_e, nx, nz, H)
        nr[:, :12] = np.stack([nx, ny, nz], 1).astype("<f4").view(np.uint8).reshape(-1, 12)
        nr[:, 13] = rng.integers(0, 6, len(nr))
        for i, k in enumerate(noms):
            if (ni == i).any():
                out[k] = np.concatenate([out[k], nr[ni == i]])
    return {k: v for k, v in out.items() if len(v)}


# LE BOIS RÊVEUR AUX ARBRES DE SLAANESH (4.10.2026, Charles : « que ce miroir d'Athel Loren soit vraiment le royaume de
# Slaanesh… tous les décors du royaume de Slaanesh ») : ses arbres, reflets de ceux d'Athel Loren, portaient nos
# identifiants `wh1_*`, sans variante pour la culture de Slaanesh qui tient le Bois Rêveur : le jeu y montrait la BASE
# (pins et feuillus de l'Empire). CA règle elle-même la forêt des elfes sous Slaanesh : ses familles génériques ont la
# variante WOODELVES = chêne d'Athel Loren (wef_tree_oak), SLAANESH = pin de Slaanesh (sla_tree_pine), herbe et buissons
# de Slaanesh (campaign_tree_variants du kit, relevé du 4.10). Les arbres du Bois Rêveur prennent donc ces identifiants de
# CA, à leur place et en même nombre : royaume de Slaanesh tant que Slaanesh le tient, Athel Loren si les elfes le
# reprennent, comme partout chez CA. Aucune ligne de base neuve. (shrubs_04 écarté : sans variante BASE chez CA, la piste
# du plantage de rendu de l'octet 12 et des BASE manquantes, arbres_wh1.BASE_DE_SECOURS.)
REVES_CA = {"tree_large": ("tree_large", 4), "tree_med": ("tree_large", 4), "brt_trees_large": ("tree_large", 4),
            "wef_aut_tree_large": ("tree_large", 4), "wef_aut_tree_medium": ("tree_large", 4),
            "tree_small": ("tree_small", 4), "wef_aut_tree_small": ("tree_small", 4),
            "wef_win_tree_large": ("tree_large_snow", 4), "wef_win_tree_medium": ("tree_large_snow", 4),
            "wef_win_tree_small": ("tree_small_snow", 4),
            "grass": ("grass", 4), "wef_wild_grass": ("grass", 4),
            "shrubs_grass": ("shrubs", 3), "wef_wild_shrubs_grass": ("shrubs", 3),
            "marsh": ("shrubs_swamp", 4), "marsh_shrubs": ("shrubs_swamp", 4)}


def reves_slaanesh(final, graine=20261004):
    """Les arbres du Bois Rêveur (rangées d'hex < SUD) sous les identifiants génériques de CA (REVES_CA)."""
    from cadre_expanded import SUD
    rng = np.random.default_rng(graine)
    out = defaultdict(list)
    n, inconnus = 0, defaultdict(int)
    for k, recs in final.items():
        z = recs[:, 8:12].copy().view("<f4").reshape(-1)
        rv = (z / UZ) < SUD
        if (~rv).any():
            out[k].append(recs[~rv])
        if not rv.any():
            continue
        fam = A.famille(k[len(A.PREFIXE_AL):] if k.startswith(A.PREFIXE_AL) else
                        k[len(A.PREFIXE):] if k.startswith(A.PREFIXE) else k)
        if fam not in REVES_CA:
            inconnus[k] += int(rv.sum())
            out[k].append(recs[rv])
            continue
        fam_ca, nb = REVES_CA[fam]
        sel = recs[rv]
        choix = rng.integers(1, nb + 1, len(sel))
        for s in range(1, nb + 1):
            if (choix == s).any():
                out[f"{fam_ca}_0{s}"].append(sel[choix == s])
        n += len(sel)
    print(f"  Bois Rêveur : {n} arbres sous les identifiants génériques de CA (royaume de Slaanesh tant que Slaanesh le "
          f"tient) ; non convertis : {dict(inconnus) or 0}")
    return {k: np.concatenate(v) for k, v in out.items()}


# (4.10.2026) LES DÉCORS DU ROYAUME DANS LA FORÊT : le royaume de CA n'a pas d'arbres, le Bois Rêveur en a ; sans rien
# faire, un arbre pousserait au travers d'une tour, d'un portail ou d'une corne de Slaanesh. Les arbres sous l'emprise au
# sol d'un objet du calque `royaume_slaanesh` (boîte du modèle de CA × sa rotation et son échelle, + MARGE_DECOR_U) sont
# retirés ; pas sous les objets plats (moins de HAUT_MIN_U au-dessus du sol), ni sous ceux qui flottent plus haut que la
# cime des arbres (FLOTTE_U).
# (premier passage, objets enfin au sol : 15 303 arbres sur 16 811 retirés, la forêt rasée ; le royaume de CA est dense
# en objets, c'est pourquoi il n'a pas d'arbres) seuls les objets HAUTS (griffes, falaises, portails, cornes, tours,
# tentacules) dégagent leurs arbres ; fissures, éboulis et pierres (moins de 1,5 u) restent parmi les arbres
MARGE_DECOR_U = 0.1
HAUT_MIN_U = 1.5
FLOTTE_U = 2.5


def _boite_ca(chemin, packs, cache):
    """(min xyz, max xyz) du premier maillage d'un modèle de CA (RMV2 ; un .wsmodel renvoie à sa géométrie)."""
    import re
    chemin = chemin.replace("\\", "/").lower()
    if chemin not in cache:
        b, res = packs.lire(chemin), None
        if not b:
            # (5.10.2026 : 11 926 objets de la nature d'Expanded « sans boîte lisible ») les modèles de WH1 que nos packs
            # embarquent ne sont pas dans ceux de CA : leurs fichiers convertis de la Saison
            loc = os.path.join(ATELIER, r"04-projets\saison-des-revelations\fichiers-wh1", *chemin.split("/"))
            if os.path.isfile(loc):
                b = open(loc, "rb").read()
        if b and chemin.endswith(".wsmodel"):
            m = re.search(rb"<geometry>([^<]+)</geometry>", b)
            res = _boite_ca(m.group(1).decode(), packs, cache) if m else None
        elif b and b[:4] == b"RMV2":
            first = int.from_bytes(b[152:156], "little")
            v = np.frombuffer(b, "<f4", count=6, offset=first + 24).astype(np.float64)
            res = (v[:3], v[3:])
        cache[chemin] = res
    return cache[chemin]


def degager_decors(final, h_e):
    """Retire les arbres sous les objets hauts du royaume de Slaanesh et de la nature de l'extension (calques
    `royaume_slaanesh` et `nature_expanded` du projet : menhirs, pierres dressées, aiguilles de roche translatés de WH1
    au milieu des forêts de BOB)."""
    import math
    import re
    calques = [p for p in glob.glob(os.path.join(TERRY_E, "*.layer"))
               if any(f"<!-- {n} -->" in open(p, encoding="utf-8").read(200) for n in ("royaume_slaanesh", "nature_expanded",
                                                                                      "camps_expanded"))]
    if not calques:
        print("  décors du royaume : calque absent du projet, aucun arbre dégagé")
        return final
    from contenu_pack import SourcePacks
    packs = SourcePacks(r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data",
                        exclure=("saison_des_revelations", "zz_startpos_db", "saison_expanded", "!saison", "!!essai"))
    cache, rects, sans_boite = {}, [], 0
    texte = "".join(open(c, encoding="utf-8").read() for c in calques)
    for e in re.findall(r"<entity id=\"[^\"]*\">(.*?)</entity>", texte, re.S):
        m = re.search(r'<ECMesh model_path="([^"]+)"', e)
        t = re.search(r'<ECTransform position="([^"]+)" rotation="([^"]+)" scale="([^"]+)"', e)
        if not m or not t:
            continue
        bt = _boite_ca(m.group(1), packs, cache)
        if bt is None:
            sans_boite += 1
            continue
        pos = np.array(t.group(1).split(), float)
        rx, ry, rz = (math.radians(-float(v)) for v in t.group(2).split())
        s = np.array(t.group(3).split(), float)
        cx, sx_, cy, sy_, cz, sz_ = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
        R = (np.array([[1, 0, 0], [0, cx, -sx_], [0, sx_, cx]]) @ np.array([[cy, 0, sy_], [0, 1, 0], [-sy_, 0, cy]])
             @ np.array([[cz, -sz_, 0], [sz_, cz, 0], [0, 0, 1]]))
        M = np.diag(s) @ R                          # props_wh1_vers_layers : lignes = axes, monde = v · M
        lo, hi = bt
        coins = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])]) @ M + pos
        sol = float(a_la(h_e, np.array([pos[0]]), np.array([pos[2]]), H)[0])
        if coins[:, 1].max() - sol < HAUT_MIN_U or coins[:, 1].min() - sol > FLOTTE_U:
            continue
        # (premier passage : boîte alignée sur les axes, gonflée par la rotation) la boîte ORIENTÉE de l'objet : un arbre
        # est dessous si, ramené dans le repère du modèle (w = v · M + pos  =>  v = (w − pos) · M⁻¹), il tombe dans la
        # boîte en x et en z (marge comprise), à toute hauteur
        rects.append((coins[:, 0].min() - 1, coins[:, 0].max() + 1, coins[:, 2].min() - 1, coins[:, 2].max() + 1,
                      pos, np.linalg.inv(M), lo, hi, s))
    if not rects:
        return final
    retires = 0
    for k in list(final):
        recs = final[k]
        xyz = recs[:, :12].copy().view("<f4").reshape(-1, 3).astype(np.float64)
        dessous = np.zeros(len(recs), bool)
        for x0, x1, z0, z1, pos, Minv, lo, hi, s in rects:
            cand = np.flatnonzero((xyz[:, 0] >= x0) & (xyz[:, 0] <= x1) & (xyz[:, 2] >= z0) & (xyz[:, 2] <= z1))
            if not len(cand):
                continue
            w = xyz[cand].copy()
            w[:, 1] = pos[1]                                          # à toute hauteur : y du pivot
            v = (w - pos) @ Minv
            mx, mz = MARGE_DECOR_U / max(s[0], 1e-6), MARGE_DECOR_U / max(s[2], 1e-6)
            dedans = ((v[:, 0] >= lo[0] - mx) & (v[:, 0] <= hi[0] + mx) & (v[:, 2] >= lo[2] - mz) & (v[:, 2] <= hi[2] + mz))
            dessous[cand[dedans]] = True
        if dessous.any():
            retires += int(dessous.sum())
            final[k] = recs[~dessous]
    print(f"  décors du royaume et nature de l'extension : {len(rects)} objets à dégager, {retires} arbres retirés de dessous"
          + (f" ; {sans_boite} modèles sans boîte lisible" if sans_boite else ""))
    return {k: v for k, v in final.items() if len(v)}


def ecrire(tete, groupes):
    out = bytearray(tete) + struct.pack("<I", len(groupes))
    for nom in sorted(groupes):
        recs = groupes[nom]
        out += struct.pack("<H", len(nom)) + nom.encode("ascii") + struct.pack("<I", len(recs)) + recs.tobytes()
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import projet_expanded
    garde = projet_expanded.garde_wh1_hex()                         # (H, W), rangée 0 au sud
    h_e, h_s = relief(TERRY_E), relief(TERRY_S)
    groupes = defaultdict(list)
    # 1. arbres de WH1 de la Saison, décalés, dans la zone gardée
    _, gs = A.lire_liste(open(LISTE_SAISON, "rb").read())
    n_s, n_s_garde = 0, 0
    for nom, recs in gs:
        xyz = recs[:, :12].copy().view("<f4").reshape(-1, 3).astype(np.float64)
        x, z = xyz[:, 0] + DX_U, xyz[:, 2] + DZ_U
        q = np.clip((x / UX).astype(int), 0, W - 1)
        r = np.clip((z / UZ).astype(int), 0, H - 1)
        ok = garde[r, q]
        n_s += len(recs)
        n_s_garde += int(ok.sum())
        if not ok.any():
            continue
        neuf = recs[ok].copy()
        y = xyz[ok, 1] + a_la(h_e, x[ok], z[ok], H) - a_la(h_s, xyz[ok, 0], xyz[ok, 2], SH)
        pos = np.stack([x[ok], y, z[ok]], 1).astype("<f4")
        neuf[:, :12] = pos.view(np.uint8).reshape(-1, 12)
        groupes[nom].append(neuf)
    # 2. arbres compilés par BOB, hors de la zone gardée, rendus aux essences de WH1
    brut = open(LISTE_BOB, "rb").read()
    tete, gb = A.lire_liste(brut)
    gb, n_nord = completer_nord(gb, h_e)
    print(f"  BOB écrête les arbres à z = {Z_MAX_BOB:.2f} (carte en portrait) : écrêtés retirés, {n_nord} arbres générés au "
          "nord d'après le raster d'arbres, à la densité et au mélange que BOB produit au sud")
    filtre, n_b, n_b_gardes = [], 0, 0
    for nom, recs in gb:
        xyz = recs[:, :12].copy().view("<f4").reshape(-1, 3).astype(np.float64)
        q = np.clip((xyz[:, 0] / UX).astype(int), 0, W - 1)
        r = np.clip((xyz[:, 2] / UZ).astype(int), 0, H - 1)
        hors = ~garde[r, q]
        n_b += len(recs)
        n_b_gardes += int(hors.sum())
        if hors.any():
            filtre.append((nom, recs[hors]))
    octets = bytearray(tete) + struct.pack("<I", len(filtre))
    for nom, recs in filtre:
        octets += struct.pack("<H", len(nom)) + nom.encode("ascii") + struct.pack("<I", len(recs)) + recs.tobytes()
    arbres = A.ArbresWH1()
    recompose, etrangers, comptes = arbres.recomposer(bytes(octets))
    _, gr = A.lire_liste(recompose)
    # (passage à blanc du 3.10 : 28 familles de BOB ne sont pas des porteuses, mais les familles génériques de WH3 du
    # tree.tif de la Saison ; laissées telles quelles, l'extension aurait eu des arbres de WH3, les pins que Charles avait
    # refusés le 23.09) : rendues aux essences de WH1 de même nature, comme les porteuses
    import random
    rng = random.Random(20261003)
    autres = defaultdict(int)
    for nom, recs in gr:
        fam = A.famille(nom)
        if nom.startswith(A.PREFIXE) or fam not in GENERIQUES:
            groupes[nom].append(np.array(recs))
            continue
        cibles = arbres.par_porteuse[GENERIQUES[fam]]
        choix = np.array([rng.randrange(len(cibles)) for _ in range(len(recs))])
        for k, c in enumerate(cibles):
            if (choix == k).any():
                groupes[A.PREFIXE + c].append(np.array(recs)[choix == k])
        autres[fam] += len(recs)
    print(f"  familles génériques de WH3 rendues aux essences de WH1 : {dict(autres)}")
    final = {k: np.concatenate(v) for k, v in groupes.items()}
    final = comme_wh1(final, garde, h_e)
    # (4.10.2026, controle_anomalies : 296 arbres dans la mer après le lissage des côtes, 268 dans l'eau des rivières de
    # l'Atlas) : aucun arbre où le sol final est sous la surface de la mer, ni dans le lit en eau d'une rivière de l'Atlas
    # (4.10.2026, après : encore 109 et 148 au contrôle) positions par cadre_expanded.ipx_de (celle du contrôle) et marge
    # de MARGE_EAU px : un arbre a une couronne, et un pied posé à un pixel de l'eau la touche
    import cv2
    import rivieres_atlas_eau as RE
    ch, niv = RE.champ_et_niveau(h_e)
    noyau = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * MARGE_EAU + 1, 2 * MARGE_EAU + 1))
    # ; dans la zone gardée de WH1, les arbres de WH1 restent où WH1 les a mis (sans marge)
    # (5.10.2026) plus les tuiles de mer : le relief y est continu avec la côte (cotes_relief, comme CA)
    import mer_tuiles
    mer0 = (h_e <= 0.04) | mer_tuiles.mer_px(h_e.shape)
    riv0 = (ch >= 0.2) & np.isfinite(niv) & (niv > h_e - 0.01)
    mer_m = cv2.dilate(mer0.astype(np.uint8), noyau) > 0
    riv_m = cv2.dilate(riv0.astype(np.uint8), noyau) > 0
    noye, mouille = 0, 0
    for k in list(final):
        recs = final[k]
        xyz = recs[:, :12].copy().view("<f4").reshape(-1, 3).astype(np.float64)
        px, py = ipx_de(xyz[:, 0], xyz[:, 2], h_e.shape)
        wh1 = garde[np.clip((xyz[:, 2] / UZ).astype(int), 0, H - 1), np.clip((xyz[:, 0] / UX).astype(int), 0, W - 1)]
        dans_mer = np.where(wh1, mer0[py, px], mer_m[py, px])
        dans_riv = np.where(wh1, riv0[py, px], riv_m[py, px])
        noye += int(dans_mer.sum())
        mouille += int((dans_riv & ~dans_mer).sum())
        garde_k = ~(dans_mer | dans_riv)
        if garde_k.all():
            continue
        if garde_k.any():
            final[k] = recs[garde_k]
        else:
            del final[k]
    print(f"  arbres retirés : {noye} dans la mer, {mouille} dans l'eau des rivières de l'Atlas")
    final = reves_slaanesh(final)
    final = degager_decors(final, h_e)
    print(f"  WH1 (Saison) : {n_s} arbres, {n_s_garde} dans la zone gardée ; BOB (Expanded) : {n_b} arbres, "
          f"{n_b_gardes} hors de la zone gardée, recomposés en essences de WH1 ; familles non recomposées : {etrangers}")
    print(f"  liste d'Expanded : {sum(len(v) for v in final.values())} arbres en {len(final)} identifiants "
          f"(en-tête de BOB : {struct.unpack_from('<I4f', tete)})")
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    open(SORTIE, "wb").write(ecrire(tete, final))
    print(f"  écrit : {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
