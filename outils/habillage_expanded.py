#!/usr/bin/env python3
"""
habillage_expanded.py - l'habillage des terres ajoutées d'Expanded (textures du sol, arbres, couleurs, neige), tiré de la
matière de la Saison elle-même (3.10.2026). Appelé par `projet_expanded.py`.

Pourquoi : jusqu'ici, hors de la zone gardée de WH1, chaque raster prenait UNE valeur par type de sol (la plus fréquente
de la Saison) : des aplats, sans vie. Charles veut des forêts, des prairies, des montagnes « bien placées », « de la
vie… que ça soit joli », et la Saison et l'Expanded « une seule vraie carte ». Or la Saison n'emploie pas les textures
de WH3 mais les 19 de WH1, et ses arbres sont ceux de WH1 (`textures_sol_wh1.py`, `arbres_wh1.py`) : l'extension doit
être faite de la même matière, mêlée comme WH1 la mêle.

Méthode (« tissage » d'exemples) :
1. pour chaque type de sol de la grille CAIME, une FENÊTRE de la Saison jouable (64 hex) où ce type domine ; les pixels
   d'un autre type y sont remplacés par le plus proche du bon type ; les types absents de WH1 empruntent : collines et
   plaines -> prairie, collines boisées -> forêt claire, marécage -> marais ;
2. la fenêtre est répétée en miroir (sans couture) et échantillonnée à des coordonnées lentement déformées (bruit de
   ~40 hex, amplitude de l'ordre de la fenêtre) : aucune répétition lisible ;
3. le type de chaque pixel vient de la grille, avec des lisières irrégulières (choix bruité entre types voisins) ; les
   couleurs se fondent entre types ;
4. montagnes de l'extension (leur sol de WH1 est plat sous des maillages ; ici le relief est vrai) : éboulis de WH1 sur
   les pentes (textures 110 à 113, comme `terrain_wh1_vers_terry.MONTAGNE`), neige du masque `SnowMask` sur les hauts
   sommets (comme les Empires : la neige de WH3 est un masque).
Les valeurs écrites sont celles du projet de la Saison (`blend` : numéros de textures de WH3 de la table TEXTURES ;
`tree` : index de palette des familles porteuses), donc la chaîne d'après BOB les reconnaît comme le reste.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, DX, DY, SW, SH, DY_HAUT               # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names          # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
CARTE_SAISON = os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex")
COUCHES_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE_EXP = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
SOLS_EXP = os.path.join(ICI, r"couches-expanded\villes-sortie\layer_groundtypes.hex_layer")
FENETRE = 64                                   # hex
SEUIL_FENETRE = 0.6                            # part du type dans la fenêtre, rapportée au maximum, pour être candidate
EMPRUNTS = {"hills": "grassland", "plains": "grassland", "hilly_light_forest": "light_forest", "swamp": "marsh",
            "tundra": "grassland", "wasteland": "grassland", "desert": "grassland", "jungle": "dense_forest",
            "chaotic_wasteland": "grassland", "river": "grassland"}
# éboulis : les deux de la table MONTAGNE de la Saison (scree_mountain2, 3), que la réécriture d'après BOB
# (textures_sol_wh1.appliquer : `garde_idx`) garde telles que BOB les a compilées ; 110 et 111 y seraient remplacées
EBOULIS = (112, 113)
_CACHE = {}


def _sols():
    if "sols" not in _CACHE:
        ls, _, _ = caime_names(CAIME, CARTE_SAISON)
        le, _, _ = caime_names(CAIME, CARTE_EXP)
        _CACHE["sols"] = (flat_names(ls, "GroundTypes"), flat_names(ls, "Regions"), flat_names(le, "GroundTypes"),
                          len(le.get("Land ground types", [])))
    return _CACHE["sols"]


def bruit(forme, echelle, rng, octaves=3):
    h, w = forme
    tot, amp, norme, e = np.zeros(forme, np.float32), 1.0, 0.0, float(echelle)
    for _ in range(octaves):
        gh, gw = max(2, int(h / e) + 3), max(2, int(w / e) + 3)
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        big = cv2.resize(g, (int((gw - 1) * e), int((gh - 1) * e)), interpolation=cv2.INTER_CUBIC)
        tot += amp * big[:h, :w]
        norme += amp
        amp *= 0.5
        e /= 2
    return tot / norme


def categories_pixels(f, reste, rng, sols_e, n_terre):
    """Type de sol (index de la grille d'Expanded) de chaque pixel, nord en haut, lisières bruitées (±1 hex)."""
    gt = read_layer(SOLS_EXP)[1].reshape(H, W)[::-1]
    gp = np.repeat(np.repeat(gt, f, 0), f, 1)
    if reste:
        gp = np.concatenate([gp, np.repeat(gp[-1:], reste, 0)])
    # lisières : on lit le type à une position déplacée d'un bruit lent (±1,2 hex) ; (3.10.2026, couture droite du
    # nord-est, forêt de l'Atlas contre prairie) dans le décor hors jeu (cases fermées), les lisières ondulent de ±8 hex
    hh, ww = gp.shape
    imp = read_layer(os.path.join(os.path.dirname(SOLS_EXP), "layer_impassable.hex_layer"))[1].reshape(H, W)[::-1]
    ferme = np.repeat(np.repeat((imp != 1).astype(np.float32), f, 0), f, 1)
    if reste:
        ferme = np.concatenate([ferme, np.repeat(ferme[-1:], reste, 0)])
    ampl = 1.2 * f + 7.0 * f * cv2.GaussianBlur(ferme, (0, 0), 4 * f)
    gx, gy = np.meshgrid(np.arange(ww, dtype=np.float32), np.arange(hh, dtype=np.float32))
    ox = (bruit((hh, ww), 3 * f, rng, 3) * 0.4 + bruit((hh, ww), 14 * f, rng, 2)) * ampl
    oy = (bruit((hh, ww), 3 * f, rng, 3) * 0.4 + bruit((hh, ww), 14 * f, rng, 2)) * ampl
    return cv2.remap(gp.astype(np.float32), gx + ox, gy + oy, cv2.INTER_NEAREST,
                     borderMode=cv2.BORDER_REPLICATE).astype(np.int32)


def exemples(rasters_saison, f_de):
    """Pour chaque type de sol de la Saison : la fenêtre (r0, q0) en hex (nord en haut) où il domine dans la partie
    jouable, et son masque."""
    sols_s, regions_s, _, _ = _sols()
    gt = read_layer(os.path.join(COUCHES_SAISON, "layer_ground_types.hex_layer"))[1].reshape(SH, SW)[::-1]
    rg = read_layer(os.path.join(COUCHES_SAISON, "layer_regions.hex_layer"))[1].reshape(SH, SW)[::-1]
    jou = ~np.isin(rg, [i for i, n in enumerate(regions_s) if "wilderness" in n]) & (rg >= 0)
    tex = _blend_saison_hex()
    out = {}
    for i, n in enumerate(sols_s):
        m = (gt == i) & jou
        if m.sum() < 200:
            continue
        fr = cv2.boxFilter(m.astype(np.float32), -1, (FENETRE, FENETRE), normalize=True, borderType=cv2.BORDER_CONSTANT)
        # (4.10.2026, gros plans du blend : patchwork serré dans l'extension) la fenêtre où le type domine le PLUS était
        # souvent un coin de champs bigarrés ; désormais, parmi les fenêtres où il domine presque autant (≥ 85 % du
        # maximum), celle dont les textures ressemblent le plus à celles de tout ce type dans WH1 (distance L1 des
        # histogrammes) : une campagne typique de WH1, pas son coin le plus chargé
        glob_h = np.bincount(tex[m], minlength=256).astype(np.float64)
        glob_h /= glob_h.sum()
        meilleur = None
        for cy in range(FENETRE // 2, SH - FENETRE // 2 + 1, 4):
            for cx in range(FENETRE // 2, SW - FENETRE // 2 + 1, 4):
                if fr[cy, cx] < SEUIL_FENETRE * fr.max():
                    continue
                r0, q0 = cy - FENETRE // 2, cx - FENETRE // 2
                mm = m[r0:r0 + FENETRE, q0:q0 + FENETRE]
                hh_ = np.bincount(tex[r0:r0 + FENETRE, q0:q0 + FENETRE][mm], minlength=256).astype(np.float64)
                d = np.abs(hh_ / max(hh_.sum(), 1) - glob_h).sum()
                if meilleur is None or d < meilleur[0]:
                    meilleur = (d, r0, q0)
        if meilleur is None:
            c = np.unravel_index(np.argmax(fr), fr.shape)
            meilleur = (0, int(np.clip(c[0] - FENETRE // 2, 0, SH - FENETRE)), int(np.clip(c[1] - FENETRE // 2, 0, SW - FENETRE)))
        _, r0, q0 = meilleur
        out[n] = (r0, q0, m[r0:r0 + FENETRE, q0:q0 + FENETRE])
    return out


def _blend_saison_hex():
    """Textures (blend) de la Saison au centre de chaque hex, 440 × 400, nord en haut."""
    if "tex" not in _CACHE:
        import glob
        from PIL import Image
        p = glob.glob(os.path.join(KIT, r"raw_data\terrain\campaigns\wh_dlc05_wood_elves_map_1", "*.blend.*.tif"))[0]
        b = np.asarray(Image.open(p))
        f = b.shape[1] // SW
        _CACHE["tex"] = b[f // 2::f, f // 2::f][:SH, :SW].astype(np.int64)
    return _CACHE["tex"]


def tuile(raster_s, f, ex):
    """La fenêtre `ex` du raster de la Saison (f px par hex), pixels d'un autre type remplacés par le plus proche du bon."""
    r0, q0, m = ex
    t = raster_s[r0 * f:(r0 + FENETRE) * f, q0 * f:(q0 + FENETRE) * f].copy()
    mp = np.repeat(np.repeat(m, f, 0), f, 1)[:t.shape[0], :t.shape[1]]
    if (~mp).any() and mp.any():
        # (4.10.2026, essai du tissage : traînées en traits parallèles) le plus proche pixel du bon type, recopié sur
        # tout un trou, tirait des rayures ; désormais le bon type POUSSE dans le trou, pixel par pixel, depuis un voisin
        # pris au hasard (8 directions mélangées à chaque pas) : des formes organiques, comme les taches de WH1
        hh, ww = mp.shape
        src = np.where(mp, np.arange(hh * ww).reshape(hh, ww), -1)
        rng = np.random.default_rng(r0 * 1000 + q0)
        dirs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        while (src < 0).any():
            for k in rng.permutation(8):
                dy, dx = dirs[k]
                dec = np.full_like(src, -1)
                dec[max(dy, 0):hh + min(dy, 0), max(dx, 0):ww + min(dx, 0)] = \
                    src[max(-dy, 0):hh + min(-dy, 0), max(-dx, 0):ww + min(-dx, 0)]
                prend = (src < 0) & (dec >= 0) & (rng.random((hh, ww)) < 0.5)
                src[prend] = dec[prend]
        plat = t.reshape((-1,) + t.shape[2:])
        t = plat[src.reshape(-1)].reshape(t.shape)
    return t


CELLULE = 36                                   # hex (28 jusqu'au 4.10) ; doit tenir dans FENETRE avec la marge des bruits


def cellules(hh, ww, f, rng):
    """Carte de cellules irrégulières (~CELLULE hex, bords ondulés), à la résolution des pixels."""
    # à l'échelle de l'hex : graines sur une grille secouée, plus proche graine
    h1, w1 = hh // f + 1, ww // f + 1
    nx, ny = w1 // CELLULE + 2, h1 // CELLULE + 2
    sx = (np.arange(nx)[None, :] + 0.5 + rng.uniform(-0.4, 0.4, (ny, nx))) * CELLULE
    sy = (np.arange(ny)[:, None] + 0.5 + rng.uniform(-0.4, 0.4, (ny, nx))) * CELLULE
    xs, ys = np.meshgrid(np.arange(w1, dtype=np.float32), np.arange(h1, dtype=np.float32))
    xs = xs + bruit((h1, w1), 10, rng, 2) * 4
    ys = ys + bruit((h1, w1), 10, rng, 2) * 4
    cx, cy = (xs // CELLULE).astype(int), (ys // CELLULE).astype(int)
    meilleur = np.full((h1, w1), np.inf, np.float32)
    idx = np.zeros((h1, w1), np.int32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            gx_, gy_ = np.clip(cx + dx, 0, nx - 1), np.clip(cy + dy, 0, ny - 1)
            d = (xs - sx[gy_, gx_]) ** 2 + (ys - sy[gy_, gx_]) ** 2
            plus = d < meilleur
            meilleur[plus] = d[plus]
            idx[plus] = (gy_ * nx + gx_)[plus]
    # (4.10.2026, gros plans du blend : patchwork serré, taches de 1,9 hex contre 3,4 dans WH1, et coupes DROITES aux
    # bords des cellules, calculées à l'hex puis agrandies au plus proche) : l'agrandissement lit la carte des cellules
    # à une position déplacée d'un bruit au pixel (±1,5 hex, échelle 2 hex) : bords ondulés, jamais en escalier
    gx, gy = np.meshgrid(np.arange(ww, dtype=np.float32), np.arange(hh, dtype=np.float32))
    u = (gx + bruit((hh, ww), 2 * f, rng, 2) * 1.5 * f) / f
    v = (gy + bruit((hh, ww), 2 * f, rng, 2) * 1.5 * f) / f
    big = cv2.remap(idx.astype(np.float32), u, v, cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    # boîte englobante de chaque cellule, en pixels (à l'hex, ± la marge du bruit)
    n = nx * ny
    ys_, xs_ = np.mgrid[0:h1, 0:w1]
    boites = np.zeros((n, 4), np.float32)
    boites[:, 0] = boites[:, 2] = 1e9
    np.minimum.at(boites[:, 0], idx.reshape(-1), ys_.reshape(-1))
    np.maximum.at(boites[:, 1], idx.reshape(-1), ys_.reshape(-1))
    np.minimum.at(boites[:, 2], idx.reshape(-1), xs_.reshape(-1))
    np.maximum.at(boites[:, 3], idx.reshape(-1), xs_.reshape(-1))
    _CACHE["boites"] = boites * f
    return big.astype(np.int32), n


def coords_tissage(hh, ww, f, rng, taille):
    """Coordonnées (lignes, colonnes) dans une tuile répétée en miroir : chaque cellule irrégulière puise à son propre
    endroit de la fenêtre, avec une déformation très faible. (Aperçus du 3.10 : une déformation forte étirait la matière
    en volutes, puis en traînées ; les vraies formes des bosquets de WH1 doivent rester entières.)"""
    gx, gy = np.meshgrid(np.arange(ww, dtype=np.float32), np.arange(hh, dtype=np.float32))
    cel, n = cellules(hh, ww, f, rng)
    # (4.10.2026, essai du tissage : formes symétriques « <|> » visibles) une cellule qui chevauchait la ligne de miroir de
    # la tuile en recopiait le reflet ; le décalage de chaque cellule est désormais tiré pour que toute sa boîte (plus la
    # marge des bruits : ~4 hex) tombe DANS la fenêtre ; au hasard seulement si elle est plus grande que la fenêtre
    b = _CACHE["boites"]
    marge = 4.0 * f
    ou = np.empty(n, np.float32)
    ov = np.empty(n, np.float32)
    for k, (lo, hi, out_) in enumerate(((b[:, 2], b[:, 3], ou), (b[:, 0], b[:, 1], ov))):
        bas = -lo + marge
        haut = taille - 1 - hi - marge - f
        tient = haut > bas
        out_[:] = np.where(tient, bas + rng.uniform(0, 1, n) * np.where(tient, haut - bas, 0),
                           rng.uniform(0, 2 * taille, n))
    u = gx + bruit((hh, ww), 30 * f, rng, 2) * f * 1.5 + ou[cel]
    v = gy + bruit((hh, ww), 30 * f, rng, 2) * f * 1.5 + ov[cel]

    def miroir(x):
        x = np.mod(x, 2 * taille)
        return np.where(x >= taille, 2 * taille - 1 - x, x).astype(np.int32)
    return np.clip(miroir(v), 0, taille - 1), np.clip(miroir(u), 0, taille - 1)


def habiller(k, raster_s, f, reste, graine=21, forcer=None):
    """Raster `k` de l'extension entière (nord en haut, f px par hex, `reste` rangées de plus), tissé depuis la Saison.
    `forcer` : {type de sol : type de la Saison dont prendre la fenêtre} (ex. la forêt sur la montagne)."""
    rng = np.random.default_rng(graine + sum(map(ord, k)))       # (hash() de Python change à chaque lancement)
    sols_s, _, sols_e, n_terre = _sols()
    ex = exemples(raster_s, f)
    hh, ww = H * f + reste, W * f
    cat = categories_pixels(f, reste, np.random.default_rng(graine), sols_e, n_terre)
    out = np.zeros((hh, ww) + raster_s.shape[2:], raster_s.dtype)
    defaut = "grassland"
    for i, n in enumerate(sols_e):
        if i >= n_terre:
            break
        m = cat == i
        if not m.any():
            continue
        src = n if n in ex else EMPRUNTS.get(n, defaut)
        if forcer and n in forcer:
            src = forcer[n]
        src = src if src in ex else defaut
        t = tuile(raster_s, f, ex[src])
        vv, uu = coords_tissage(hh, ww, f, rng, t.shape[0])
        out[m] = t[vv[m], uu[m]]
    # la mer (sols de mer) : la tuile de mer de la Saison si elle existe, sinon la prairie (sous l'eau, peu visible)
    mer = cat >= n_terre
    if mer.any():
        src = "sea_coast" if "sea_coast" in ex else defaut
        t = tuile(raster_s, f, ex[src])
        vv, uu = coords_tissage(hh, ww, f, rng, t.shape[0])
        out[mer] = t[vv[mer], uu[mer]]
    if k in ("blend", "tree", "color_overlay"):
        abords(k, out, raster_s, f, reste, cat, sols_e, n_terre, np.random.default_rng(graine + 5))
    return out, cat


# LES ABORDS DES VILLES (3.10.2026, Charles : « des prairies et des champs autour des villes bretonniennes », « de la vie »)
# : autour de chaque ville neuve d'un peuple qui cultive (bretonnien, impérial), les abords d'une ville bretonnienne de WH1
# (textures, arbres éclaircis, couleurs), sur RAYON_ABORDS hex aux bords irréguliers ; jamais sur la montagne ni la mer.
PEUPLES_CULTIVATEURS = ("bretonnien", "impérial")
PROVINCES_BRETONNES_WH1 = ("aquitaine", "bastonne", "bordeleaux", "brionne", "carcassonne", "gisoreux", "quenelles",
                           "parravon", "montfort", "couronne", "lyonesse")
RAYON_ABORDS = 7
DECLARATION = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\expanded_declaration.json")


def _abords():
    """[(centre neuf (r, q) nord en haut, centre source WH1 (r, q) nord en haut dans le cadre de la Saison)]."""
    if "abords" in _CACHE:
        return _CACHE["abords"]
    import json
    import re
    sols_s, regions_s, _, _ = _sols()
    le, _, _ = caime_names(CAIME, CARTE_EXP)
    regions_e = flat_names(le, "Regions")
    d = json.load(open(DECLARATION, encoding="utf-8"))
    cultive = {e["cle_jeu"] for e in d["regions"] if e.get("peuple") in PEUPLES_CULTIVATEURS}
    # sources : centres des villes de WH1 des provinces bretonnes, intérieures, sur prairie ou forêt claire
    sl = read_layer(os.path.join(COUCHES_SAISON, "layer_town_slots.hex_layer"))[1].reshape(SH, SW)[::-1]
    rg = read_layer(os.path.join(COUCHES_SAISON, "layer_regions.hex_layer"))[1].reshape(SH, SW)[::-1]
    gt = read_layer(os.path.join(COUCHES_SAISON, "layer_ground_types.hex_layer"))[1].reshape(SH, SW)[::-1]
    motif = re.compile(r"wh_dlc05_(" + "|".join(PROVINCES_BRETONNES_WH1) + r")_")
    sources = []
    for i, n in enumerate(regions_s):
        if not motif.match(n):
            continue
        m = (rg == i) & (sl == 0)
        if not m.any() or (sl[rg == i] == 1).any():          # pas de port
            continue
        r, q = np.argwhere(m).mean(0).round().astype(int)
        if sols_s[gt[r, q]] in ("grassland", "light_forest") and RAYON_ABORDS + 2 <= r < SH - RAYON_ABORDS - 2 \
                and RAYON_ABORDS + 2 <= q < SW - RAYON_ABORDS - 2:
            sources.append((int(r), int(q)))
    # villes neuves : couche des emplacements d'Expanded (villes-sortie), régions qui cultivent, hors ports
    d_s = os.path.dirname(SOLS_EXP)
    sle = read_layer(os.path.join(d_s, "layer_townslots.hex_layer"))[1].reshape(H, W)[::-1]
    rge = read_layer(os.path.join(d_s, "layer_regions.hex_layer"))[1].reshape(H, W)[::-1]
    rng = np.random.default_rng(77)
    out = []
    for i, n in enumerate(regions_e):
        if n not in cultive:
            continue
        m = (rge == i) & (sle == 0)
        if not m.any() or ((rge == i) & (sle == 1)).any():
            continue
        r, q = np.argwhere(m).mean(0).round().astype(int)
        out.append(((int(r), int(q)), sources[int(rng.integers(len(sources)))]))
    print(f"  abords des villes : {len(out)} villes neuves, {len(sources)} villes bretonnes de WH1 pour modèles")
    _CACHE["abords"] = out
    return out


def abords(k, out, raster_s, f, reste, cat, sols_e, n_terre, rng):
    """Pose les abords des villes de WH1 autour des villes neuves (en place dans `out`)."""
    mont = sols_e.index("mountain")
    R = RAYON_ABORDS * f
    yy, xx = np.mgrid[-R - f:R + f + 1, -R - f:R + f + 1]
    for (rn, qn), (rs, qs) in _abords():
        cy, cx = rn * f + f // 2, qn * f + f // 2
        sy, sx = (DY_HAUT + 0 + 0) * 0 + rs * f + f // 2, qs * f + f // 2      # dans le raster de la Saison
        bord = R * (0.8 + 0.35 * bruit(yy.shape, 2 * f, rng, 2))
        disque = np.hypot(yy, xx) < bord
        ys, xs = cy + yy, cx + xx
        ys2, xs2 = sy + yy, sx + xx
        ok = disque & (ys >= 0) & (ys < out.shape[0]) & (xs >= 0) & (xs < out.shape[1]) & \
            (ys2 >= 0) & (ys2 < raster_s.shape[0]) & (xs2 >= 0) & (xs2 < raster_s.shape[1])
        ys, xs, ys2, xs2 = ys[ok], xs[ok], ys2[ok], xs2[ok]
        c = cat[ys, xs]
        bon = (c != mont) & (c < n_terre)
        if out.ndim == 3:
            w = np.clip((bord[ok] - np.hypot(yy[ok], xx[ok])) / (2.0 * f), 0, 1)[bon][:, None]
            out[ys[bon], xs[bon]] = (out[ys[bon], xs[bon]] * (1 - w) + raster_s[ys2[bon], xs2[bon]] * w).astype(out.dtype)
        else:
            out[ys[bon], xs[bon]] = raster_s[ys2[bon], xs2[bon]]


def fondre_couleur(col, cat, f):
    """Couleurs : fondu doux entre types (moyenne locale sur ~1,5 hex), le grain de WH1 gardé."""
    c = col.astype(np.float32)
    flou = cv2.GaussianBlur(c, (0, 0), 1.5 * f)
    fin = c - cv2.GaussianBlur(c, (0, 0), 0.5 * f)
    return np.clip(flou + fin, 0, 255).astype(col.dtype)


def montagnes(blend, height, f_h, cat, sols_e, rng):
    """Éboulis de WH1 sur les pentes des montagnes de l'extension (blend à 8 px), en taches irrégulières."""
    hb = cv2.resize(height, (blend.shape[1], blend.shape[0]), interpolation=cv2.INTER_LINEAR) if height.shape != blend.shape else height
    gy, gx = np.gradient(cv2.GaussianBlur(hb, (0, 0), 4))
    pente = np.hypot(gx, gy) * 8                         # u par hex (8 px par hex)
    mont = cat == sols_e.index("mountain")
    choix = (bruit(blend.shape, 24, rng, 3) * 1.2 + 1).astype(np.int32).clip(0, len(EBOULIS) - 1)
    eboulis = np.array(EBOULIS, blend.dtype)[choix]
    seuil = 1.2 + bruit(blend.shape, 30, rng, 2) * 0.5
    roc = (mont & (pente > seuil)) | (mont & (hb > 9.0))
    return np.where(roc, eboulis, blend), roc


def neige(height, f, rng, bas=12.0, haut=14.0, coeur=150):
    """Masque de neige des hauts sommets (à f px par hex), bord fondu et irrégulier."""
    n = bruit(height.shape, 6 * f, rng, 3) * 0.6
    t = np.clip((height + n - bas) / (haut - bas), 0, 1)
    t = t * t * (3 - 2 * t)
    return (t * coeur).astype(np.uint8)
