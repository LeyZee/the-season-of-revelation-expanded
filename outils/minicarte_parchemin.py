#!/usr/bin/env python3
"""
minicarte_parchemin.py - la minicarte d'Expanded en jeu, au style EXACT de celle de la Saison : le parchemin sépia de
Warhammer I (papier taché, zone hors jeu brune et pointillée, montagnes en pics hachurés, forêts et collines pointillées,
rivières en double trait, golfes en lavis gris-brun, provinces cernées d'un trait d'encre, noms calligraphiés).

Pourquoi (3.10.2026, Charles : « retravailler la minimap en jeu de la carte Expanded, avec les provinces bien définies…
exactement le même style parchemin sépia que la Saison ») : la minimap d'Expanded était l'Atlas en couleurs, sans
provinces. Celle de la Saison est le parchemin de WH1, qui ne couvre que la carte de WH1 et dont les provinces ne sont plus
toutes celles d'Expanded (découpes, régions neuves) : celle-ci est dessinée d'après les données d'Expanded elles-mêmes.

Sources (lecture seule) : grilles de l'Atlas (`extension_regions.npz`, `extension_geo.npz`, `reves_grilles.npz`,
`extension_rivieres.json`), déclaration (`expanded_declaration.json`), fiche du kit (`map_spec_expanded.json` : province de
chaque région), régions de la Saison (couche de CAIME), noms et places des noms de province de la carte de l'Atlas
(`carte_papier_v2.svg`). La trame hex -> pixels est celle de l'image de correspondance du jeu (`lookup_expanded.trame`,
contrôlée sur la Saison) : la minicarte tombe exactement sur les régions du jeu. Depuis le 3.10.2026 au soir, quand la
grille du jeu existe (`couches-expanded\\layer_regions.hex_layer` et `caime\\saison_expanded_map\\map.hex`, session
d'intégration), les provinces, les mers et la côte en jeu viennent d'elle, case pour case (`grille_du_jeu`).

Sorties (`04-projets\\saison-expanded\\images-carte\\`) : `saison_expanded_minimap_en.png` (pack principal, anglais) et
`saison_expanded_minimap_fr.png` (traduction), moitié de l'image de correspondance que CAIME a calculée (1120 × 2090 pour
2240 × 4180, comme la Saison : 800 × 1016 pour 1600 × 2032), et un aperçu réduit.

Usage :
    python minicarte_parchemin.py
"""
import html
import json
import math
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ATELIER = r"C:\TotalWar-CampaignMap"
ICI_OUTILS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
sys.path.insert(0, ICI_OUTILS)
from caime_layers import read_layer, caime_names, flat_names    # noqa: E402
from cadre_expanded import W, H, DX, DY, SW, SH, SUD, RANG_ATLAS  # noqa: E402
import lookup_expanded as LE                                    # noqa: E402

Image.MAX_IMAGE_PIXELS = None
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
CARTE_SAISON = os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex")
COUCHES_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots")
ATLAS = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
SORTIE = os.path.join(ICI, "images-carte")
POLICE = r"C:\Windows\Fonts\CENTAUR.TTF"          # (la plus proche de l'écriture du parchemin de WH1, essai du 3.10)
POLICE_MER = POLICE                               # (les golfes de WH1 sont dans la même écriture, 3.10.2026)
LW, LH = int(W * LE.PX_COL), int(round(H * 2032 / 440))
# (3.10.2026, soir, session d'intégration : la taille attendue est la moitié du lookup de CAIME, 2240 × 4180 ; l'arrondi
# d'ici donnait 4179, d'où une minicarte de 2089 au lieu de 2090) la taille de l'image de correspondance de CAIME, si elle
# existe, comme `lookup_expanded`
LOOKUP_BMP = os.path.join(KIT, r"working_data\campaign_maps\saison_expanded_map\saison_expanded_lookup.bmp")
if os.path.exists(LOOKUP_BMP):
    LW, LH = Image.open(LOOKUP_BMP).size
GRILLE_JEU = (os.path.join(ICI, r"caime\saison_expanded_map\map.hex"),
              os.path.join(ICI, r"couches-expanded\layer_regions.hex_layer"))
# les teintes du parchemin de WH1 (relevées sur la minicarte de la Saison)
# (3.10.2026 : reprises sur des échantillons du parchemin de WH1 en taille réelle, `m12_echantillons_wh1.py` : papier nu
# ≈ (209, 184, 154), fumée des golfes ≈ (178, 153, 125) en moyenne, (109, 90, 72) au plus creux)
PAPIER, PAPIER_SOMBRE, TACHE = (215, 189, 158), (192, 163, 132), (142, 117, 93)
FUMEE, FUMEE_CREUX = (158, 134, 108), (110, 91, 72)
ENCRE, ENCRE_BRUNE, RIVIERE = (38, 28, 20), (82, 62, 45), (112, 90, 68)
ETHER = (104, 88, 94)                             # (fumée mauve-brun : le pourpre en soupçon, jamais en aplat)
# (3.10.2026 : un peu sous geo_extension.SEUIL_INFRANCHISSABLE (5,3), car le parchemin de WH1 hachure ses massifs presque
# en entier, Massif d'Orquemont, Défilé de la Hache ; collines de l'Atlas)
SEUIL_MONT, SEUIL_COLL = 4.8, 3.2


# ------------------------------------------------------------------ les grilles d'Expanded
def grille_du_jeu(prov, est_mer, unites):
    """(unités H × W, mers du jeu, terres en jeu) depuis la grille de CAIME de la session d'intégration, ou None."""
    if not all(os.path.exists(c) for c in GRILLE_JEU):
        return None
    listes, w, h = caime_names(CAIME, GRILLE_JEU[0])
    noms = flat_names(listes, "Regions")
    g = read_layer(GRILLE_JEU[1])[1].reshape(h, w)
    if (h, w) != (H, W):
        print(f"  !! grille du jeu en {w} x {h}, cadre en {W} x {H} : grille de l'Atlas gardée")
        return None
    ids = np.full((H, W), -1, np.int32)
    mer = np.zeros((H, W), bool)
    terre_sauvage = np.zeros((H, W), bool)
    for i, n in enumerate(noms):
        if n.startswith("sauvage") or "wilderness" in n:
            # (la terre et la mer hors jeu du jeu font aussi la côte, hors du Bois Rêveur, dessiné d'après ses grilles)
            if n.endswith("_sea"):
                mer[SUD:] |= (g == i)[SUD:]
            else:
                terre_sauvage[SUD:] |= (g == i)[SUD:]
            continue
        m = g == i
        u = prov.get(n) or ("mer:" + n if est_mer.get(n) else "region:" + n)
        ids[m] = unites.setdefault(u, len(unites))
        if est_mer.get(n):
            mer |= m
    return ids, mer, ((ids >= 0) | terre_sauvage) & ~mer


def grilles():
    """(unités : grille H × W d'indices, -1 hors jeu ; noms des unités ; masques de terrain H × W)."""
    d = json.load(open(os.path.join(ATLAS, "expanded_declaration.json"), encoding="utf-8"))
    spec = json.load(open(os.path.join(ICI, "map_spec_expanded.json"), encoding="utf-8"))
    G = {"extension_regions.npz": np.load(os.path.join(ATLAS, "extension_regions.npz")),
         "extension_geo.npz": np.load(os.path.join(ATLAS, "extension_geo.npz")),
         "reves_grilles.npz": np.load(os.path.join(ATLAS, "reves_grilles.npz"))}
    r_at, g_at, rv = G["extension_regions.npz"], G["extension_geo.npz"], G["reves_grilles.npz"]

    def place(a, rang):
        out = np.zeros((H, W), a.dtype)
        out[rang:rang + a.shape[0], :a.shape[1]] = a
        return out
    # les régions, par clé (la logique de regions_expanded.py, sans CAIME)
    s_noms = flat_names(caime_names(CAIME, CARTE_SAISON)[0], "Regions")
    remplace = {t["cle_jeu"]: t["remplacee_par"] for t in d.get("regions_wh1_touchees", [])
                if t.get("dans_expanded") == 0 and t.get("remplacee_par")}
    noms_s = np.array([remplace.get(n, n) for n in s_noms] + [""], object)
    v = read_layer(os.path.join(COUCHES_SAISON, "layer_regions.hex_layer"))[1].reshape(SH, SW)
    reg = np.full((H, W), "", object)
    reg[DY:DY + SH, DX:DX + SW] = noms_s[np.where(v < 0, len(s_noms), v)]
    terre, mer = place(r_at["terre"], RANG_ATLAS), place(r_at["mer"], RANG_ATLAS)
    hors_cadre = np.ones((H, W), bool)
    hors_cadre[DY:DY + SH, DX:DX + SW] = False
    reg[hors_cadre & terre & (reg == "")] = "sauvage_terre"
    reg[hors_cadre & mer & (reg == "")] = "sauvage_mer"
    sud = np.zeros((H, W), bool)
    sud[:SUD] = True
    voile = place(rv["voile"], 0)
    reg[sud & (reg == "")] = "sauvage_mer"
    reg[voile] = "sauvage_terre"
    ordre = {"bois_reveur": 0, "mer": 1, "reprise": 2, "neuve": 3, "decoupe": 4}
    for e in sorted(d["regions"], key=lambda e: ordre.get(e["categorie"], 9)):
        gr = e["grille"]
        m = G[gr["fichier"]][gr["couche"]] == gr["valeur"]
        m = place(m, 0 if gr["fichier"] == "reves_grilles.npz" else RANG_ATLAS)
        if e["categorie"] == "reprise":
            continue
        if e["categorie"] == "bois_reveur":
            m &= ~voile
        reg[m] = e["cle_jeu"]
    lac = place(g_at["lac"], RANG_ATLAS)
    reg[lac & (reg == "")] = "sauvage_mer"
    reg[reg == ""] = "sauvage_terre"
    # les unités de la minicarte : la province de chaque région ; une mer déclarée est sa propre unité ; le sauvage, hors jeu
    prov = {r["key"]: r.get("province") for r in spec["regions"]}
    est_mer = {r["key"]: bool(r.get("is_sea")) for r in spec["regions"]}
    unites, ids = {}, np.full((H, W), -1, np.int32)
    for k in np.unique(reg):
        if k.startswith("sauvage") or "wilderness" in k:
            continue
        u = prov.get(k) or ("mer:" + k if est_mer.get(k) else "region:" + k)
        ids[reg == k] = unites.setdefault(u, len(unites))
    # (3.10.2026, Charles : « une province sans nom entre Couronne, les Marches, les Sœurs Pâles, Gisoreux et l'Artois ».
    # C'est la bande sauvage du bord nord de WH1 (montagnes de bordure), enclavée dans la Bretonnie d'Expanded : une
    # enclave de terre hors jeu qui ne touche ni le bord ni la terre sauvage extérieure, et dont les voisins sont jouables,
    # revient aux unités TERRESTRES voisines, à la plus proche ; les îlots entourés de mer restent hors jeu. Même règle
    # proposée à la session d'intégration pour regions_expanded : la minicarte doit rester identique au jeu.)
    mer_u = np.array([v for k, v in unites.items() if k.startswith("mer:")] + [-99])
    terre_u = (ids >= 0) & ~np.isin(ids, mer_u)
    terre_tot = place(r_at["terre"], RANG_ATLAS) | (sud & place(rv["terre"], 0))
    terre_tot[DY:DY + SH, DX:DX + SW] |= (v >= 0)
    hors_t = (ids < 0) & terre_tot & ~voile
    n_h, lab_h, st_h, _ = cv2.connectedComponentsWithStats(hors_t.astype(np.uint8), 4)
    enclaves = np.zeros((H, W), bool)
    for k in range(1, n_h):
        m = lab_h == k
        if st_h[k, 4] > 20000 or m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any():
            continue
        bord_m = (cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & ~m
        if (ids[bord_m] >= 0).mean() >= 0.95 and terre_u[bord_m].any():
            enclaves |= m
    if enclaves.any():
        src = np.where(terre_u, 0, 1).astype(np.uint8)
        _, lab_d = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        ys_g, xs_g = np.nonzero(terre_u)
        graine = np.zeros(int(lab_d.max()) + 1, np.int32)
        graine[lab_d[ys_g, xs_g]] = ids[ys_g, xs_g]
        ids[enclaves] = graine[lab_d[enclaves]]
        print(f"  enclaves hors jeu rendues aux provinces voisines : {int(enclaves.sum())} hex")
    # (3.10.2026, soir, session d'intégration : « sur la grille d'aujourd'hui », Golfe du Bidouze ouvert sur la lisière de mer
    # de WH1, île de Landri gardée) la grille du jeu, quand elle existe, l'emporte case pour case : la minicarte doit
    # tomber sur le lookup du jeu ; la grille ci-dessus ne sert plus qu'à défaut
    jeu = grille_du_jeu(prov, est_mer, unites)
    if jeu is not None:
        print(f"  grille du jeu : {int((jeu[0] != ids).sum())} hex changés")
        ids = jeu[0]
    # le terrain
    alt = place(r_at["alt"].astype(np.float32), RANG_ATLAS)
    rv_terre = place(rv["terre"] & ~rv["voile"], 0)
    alt = np.where(sud, place(rv["alt"].astype(np.float32), 0), alt)
    eau = ~terre & ~sud | lac
    eau |= sud & ~rv_terre & ~voile
    if jeu is not None:
        # la côte en jeu : une mer du jeu est de l'eau, une terre du jeu est de la terre (hors lacs de l'Atlas)
        print(f"  côte du jeu : {int((jeu[1] & ~eau).sum())} hex passés en mer, "
              f"{int((jeu[2] & ~lac & eau).sum())} en terre")
        eau = (eau | jeu[1]) & ~(jeu[2] & ~lac)
    foret = place(g_at["foret"], RANG_ATLAS) | (rv_terre & np.isin(place(rv["biome"], 0), (1, 5, 7)))
    T = dict(eau=eau, lac=lac, mont=(alt >= SEUIL_MONT) & ~eau, coll=(alt >= SEUIL_COLL) & (alt < SEUIL_MONT) & ~eau,
             foret=foret & ~eau, voile=voile, reve=rv_terre, ether=sud & ~rv_terre & ~voile,
             alt=np.where(eau, 0.0, alt).astype(np.float32))
    print(f"  unités (provinces et mers) : {len(unites)} ; hex hors jeu : {int((ids < 0).sum())}")
    return ids, unites, T


# ------------------------------------------------------------------ la trame et les textures
def tramer(grille, dec, lisse=0.0):
    t = LE.trame(grille.astype(np.int64), LW, LH, dec)
    if lisse:
        t = cv2.GaussianBlur(t.astype(np.float32), (0, 0), lisse)
    return t


def bruit(h, w, s, rng):
    b = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), s)
    return b / (b.std() + 1e-6)


def cailloutis(h, w, pas, rng):
    """Le pointillé du parchemin de WH1 (petites cellules sombres à bord, comme des cailloux) : un bruit de cellules."""
    n = int(h * w / (pas * pas))
    m = np.ones((h, w), np.uint8)
    ys, xs = rng.integers(0, h, n), rng.integers(0, w, n)
    m[ys, xs] = 0
    d = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    return np.clip(d / (pas * 0.55), 0, 1) ** 1.4          # (0 au cœur des cellules, 1 entre elles : les « joints »)


def ecailles(h, w, pas, rng):
    """Les écailles des forêts du parchemin de WH1 : de petites cellules serrées, en quinconce, cernées d'un trait.
    (joints : 1 sur le trait ; creux : 0 au cœur de la cellule, 1 à son bord)."""
    ys, xs = np.arange(pas / 2, h, pas), np.arange(pas / 2, w, pas)
    gy, gx = np.meshgrid(ys, xs, indexing="ij")
    gx = gx + (np.arange(len(ys))[:, None] % 2) * pas / 2 + rng.uniform(-pas / 4, pas / 4, gx.shape)
    gy = gy + rng.uniform(-pas / 4, pas / 4, gy.shape)
    m = np.ones((h, w), np.uint8)
    m[np.clip(gy.round().astype(int), 0, h - 1), np.clip(gx.round().astype(int), 0, w - 1)] = 0
    d, lab = cv2.distanceTransformWithLabels(m, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    joint = np.zeros((h, w), np.float32)
    joint[:, 1:] = np.maximum(joint[:, 1:], lab[:, 1:] != lab[:, :-1])
    joint[1:, :] = np.maximum(joint[1:, :], lab[1:, :] != lab[:-1, :])
    joint = np.clip(cv2.GaussianBlur(joint, (0, 0), 0.6) * 1.6, 0, 1)
    return joint, np.clip(d / (pas * 0.6), 0, 1)


def serpenter(p, rng, amp=3.0, pas=4.0):
    """Une rivière qui serpente comme sur le parchemin de WH1 : le tracé, redécoupé tous les `pas` px, s'écarte de sa
    ligne par un bruit lent (les méandres) et un plus vif ; aucun écart aux deux bouts (confluences, embouchures)."""
    p = np.asarray(p, np.float32)
    seg = np.hypot(*np.diff(p, axis=0).T)
    L = np.concatenate([[0.0], np.cumsum(seg)])
    if L[-1] < 4 * pas:
        return [tuple(q) for q in p]
    s = np.arange(0.0, L[-1], pas)
    x, y = np.interp(s, L, p[:, 0]), np.interp(s, L, p[:, 1])
    dx, dy = np.gradient(x), np.gradient(y)
    n = np.hypot(dx, dy) + 1e-6
    # (3.10.2026 : l'échelle du bruit est fixée par le flou, pas mesurée sur le tracé : sur un tronçon court, le bruit
    # flouté est presque constant, et le diviser par son écart-type, presque nul, faisait jaillir de longues aiguilles
    # droites, la « rivière » rectiligne des Marches de la Couronne ; l'écart est aussi borné)
    lent = cv2.GaussianBlur(rng.standard_normal((1, len(s))).astype(np.float32), (0, 0), 3)[0] * 3.26
    vif = cv2.GaussianBlur(rng.standard_normal((1, len(s))).astype(np.float32), (0, 0), 1)[0] * 1.88
    ecart = np.clip(amp * (lent + 0.5 * vif), -2.5 * amp, 2.5 * amp)
    ecart *= np.clip(np.minimum(s, L[-1] - s) / 12.0, 0, 1)
    return list(zip(x - dy / n * ecart, y + dx / n * ecart))


def adoucir_trace(p, pas=3.0, sigma=3.0):
    """Un tracé relevé pixel par pixel, redécoupé tous les `pas` px et lissé (gaussienne de `sigma` pas) ; les deux bouts
    ne bougent pas (confluences, embouchures)."""
    p = np.asarray(p, np.float32)
    L = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
    if L[-1] < 3 * pas:
        return [tuple(q) for q in p]
    s = np.arange(0.0, L[-1] + 1e-6, pas)
    x, y = np.interp(s, L, p[:, 0]), np.interp(s, L, p[:, 1])
    k = cv2.getGaussianKernel(int(6 * sigma) | 1, sigma)[:, 0]
    if len(s) > len(k):
        xs = np.convolve(np.pad(x, len(k) // 2, mode="edge"), k, "valid")
        ys = np.convolve(np.pad(y, len(k) // 2, mode="edge"), k, "valid")
        xs[0], ys[0], xs[-1], ys[-1] = x[0], y[0], x[-1], y[-1]
        x, y = xs, ys
    return list(zip(x, y))


def melange(col, alpha, couleur):
    """col teinté vers couleur (une teinte ou une image) à hauteur d'alpha (0..1, par pixel)."""
    return col * (1 - alpha[..., None]) + np.asarray(couleur, np.float32) * alpha[..., None]


# ------------------------------------------------------------------ les noms
def titre(s):
    petits = {"de", "du", "des", "la", "le", "les", "et", "of", "the", "and", "en", "au", "aux", "d'", "l'",
              "nord", "sud", "est", "ouest"}           # (« Voûtes du nord », comme sur l'Atlas)
    propres_l = {"l'anguille", "l'île"}                 # (noms propres en L' : L'Anguille, L'Île Silencieuse)
    mots = s.lower().split()
    out = []
    for i, m in enumerate(mots):
        if i and m in petits:
            out.append(m)
        elif m.startswith(("d'", "l'")) and len(m) > 2:
            haut = i == 0 or m in propres_l
            if m.startswith("l'") and not haut and m[2:] in {"ouest", "est"}:
                out.append(m)
            else:
                out.append((m[:1].upper() if haut else m[:1]) + m[1:2] + m[2:3].upper() + m[3:])
        else:
            out.append(m[:1].upper() + m[1:])
    return " ".join(out)


def noms_provinces():
    """[(x, y en px de la minicarte, fr, en, sorte)] : les noms de province et de mer de la carte de l'Atlas (même repère
    que la grille : 2 px par unité du SVG)."""
    t = open(os.path.join(ATLAS, "carte_papier_v2.svg"), encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<text[^>]*class="lib (lib-province|lib-mer)([^"]*)"[^>]*>', t):
        if "saison-seule" in m.group(2):
            continue
        a = dict(re.findall(r'(data-[a-z]+)="([^"]*)"', m.group(0)))
        if "data-x" not in a:
            continue
        out.append((float(a["data-x"]) * LW / 1120, float(a["data-y"]) * LH / 2090,
                    html.unescape(a.get("data-fr", "")), html.unescape(a.get("data-en", "")), m.group(1),
                    a.get("data-cible", "")))
    return out


def rivieres_svg():
    """Les rivières de la carte de l'Atlas, déjà raccordées et lissées (`carte_papier_v2.reseau_riviere`), en px de la
    minicarte : la Saison (« riviere »), l'Atlas (« riviere neuve ») et le Bois Rêveur (« rv-riviere »). (3.10.2026 : les
    tracés bruts de `extension_rivieres.json` sont des milliers de bouts d'une case en escalier, d'où des zigzags.)"""
    t = open(os.path.join(ATLAS, "carte_papier_v2.svg"), encoding="utf-8").read()
    sx, sy = LW / 1120, LH / 2090
    garder = {"riviere", "riviere neuve", "riviere neuve ajout", "riviere rv-riviere"}
    out = []
    for m in re.finditer(r'<path d="([^"]*)" class="(riviere[^"]*)"', t):
        if m.group(2) not in garder:
            continue
        jetons = re.findall(r"[MmLl]|-?(?:\d+\.?\d*|\.\d+)", m.group(1))
        cmd, i, x, y, p = None, 0, 0.0, 0.0, []
        while i < len(jetons):
            if jetons[i].isalpha():
                cmd = jetons[i]
                i += 1
                if cmd in "Mm":
                    if len(p) >= 2:
                        out.append(p)
                    dx_, dy_ = float(jetons[i]), float(jetons[i + 1])
                    x, y = (x + dx_, y + dy_) if cmd == "m" else (dx_, dy_)
                    p = [(x * sx, y * sy)]
                    i += 2
                    cmd = "l" if cmd == "m" else "L"
                continue
            dx_, dy_ = float(jetons[i]), float(jetons[i + 1])
            x, y = (x + dx_, y + dy_) if cmd == "l" else (dx_, dy_)
            p.append((x * sx, y * sy))
            i += 2
        if len(p) >= 2:
            out.append(p)
    return out


def reseaux_rivieres(traces, jeu, eau, joint=3.0):
    """Les tronçons de rivière à dessiner. Les tronçons dont un bout touche (à `joint` px près) un bout d'un autre forment
    un réseau ; on garde les réseaux dont un point est dans la zone jouable, entiers (sources comprises). Écartés : un
    tronçon isolé de moins de 15 hex, un trait isolé tiré à la règle, un tracé qui longe la côte sur plus de la moitié de
    sa longueur (bout de rivage relevé comme une rivière)."""
    h, w = jeu.shape
    d_eau = cv2.distanceTransform((~eau).astype(np.uint8), cv2.DIST_L2, 5)
    n = len(traces)
    bouts = np.array([[t[0][0], t[0][1], t[-1][0], t[-1][1]] for t in traces], np.float32).reshape(-1, 2)
    parent = list(range(n))

    def racine(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(bouts)):
        d = np.hypot(*(bouts - bouts[i]).T)
        for j in np.nonzero(d <= joint)[0]:
            a, b = racine(i // 2), racine(int(j) // 2)
            if a != b:
                parent[a] = b
    taille, longueur = {}, {}
    for i in range(n):
        a = np.asarray(traces[i])
        taille[racine(i)] = taille.get(racine(i), 0) + 1
        longueur[racine(i)] = longueur.get(racine(i), 0.0) + float(np.hypot(*np.diff(a, axis=0).T).sum())

    def dedans(t, masque):
        a = np.asarray(t)
        xi = np.clip(a[:, 0].astype(int), 0, w - 1)
        yi = np.clip(a[:, 1].astype(int), 0, h - 1)
        return masque[yi, xi]
    touche_jeu = {}
    for i, t in enumerate(traces):
        if dedans(t, jeu).any():
            touche_jeu[racine(i)] = True
    out = []
    for i, t in enumerate(traces):
        a = np.asarray(t)
        L = float(np.hypot(*np.diff(a, axis=0).T).sum())
        droit = float(np.hypot(*(a[-1] - a[0]))) / max(L, 1e-6)
        isole = taille[racine(i)] == 1
        if not touche_jeu.get(racine(i)) or longueur[racine(i)] < 40:
            continue        # (hors jeu, ou un débris de moins de 10 hex en tout ; l'Atlas a déjà soudé et nettoyé le reste)
        if isole and (L < 60 or (droit > 0.985 and L > 60)):
            continue
        if (dedans(t, d_eau < 4)).mean() > 0.85 and L > 20:
            continue        # (un trait collé au rivage sur presque toute sa longueur ; une embouchure courte reste)
        out.append(t)
    return out


ROYAUMES_AL = {"anmyr", "argwylon", "arranoc", "atylwyth", "cavaroc", "cythral", "fyr_darric", "modryn", "talsyn", "tirsyth",
               "torgovann", "wydrioth"}


def etiquettes(unite_px, unites, langue):
    """[(x, y, lignes, sorte)] : un nom par unité (province ou mer), au cœur de sa surface (le point le plus loin de ses
    bords, comme les noms du parchemin de WH1). Nom anglais : celui du jeu (fiche du kit) ; nom français : celui de la
    carte de l'Atlas quand elle l'écrit, sinon les textes du projet, sinon la forme de WH1 (« Royaume de … »)."""
    spec = json.load(open(os.path.join(ICI, "map_spec_expanded.json"), encoding="utf-8"))
    en_prov = {p["key"]: p.get("onscreen", p["key"]) for p in spec["provinces"]}
    en_reg = {r["key"]: r.get("onscreen", r["key"]) for r in spec["regions"]}
    d = json.load(open(os.path.join(ATLAS, "expanded_declaration.json"), encoding="utf-8"))
    fr_reg = {e["cle_jeu"]: e.get("nom") for e in d["regions"]}
    # (les noms français des provinces de l'extension, dans la liste des provinces de l'Atlas : y compris celles qui n'ont
    # qu'une région et dont la carte n'écrit que la ville, Les Sœurs Pâles, Pré de Ceren)
    fr_atlas = {f"saison_province_{k}": v.get("nom") for k, v in
                json.load(open(os.path.join(ATLAS, "extension_regions.json"), encoding="utf-8"))["provinces"].items()}
    fr_textes = {}
    for f in os.listdir(os.path.join(ATELIER, r"04-projets\saison-des-revelations\textes")):
        try:
            t = json.load(open(os.path.join(ATELIER, r"04-projets\saison-des-revelations\textes", f), encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(t, dict):
            for k, v in t.items():
                if str(k).startswith("provinces_onscreen_") and isinstance(v, dict) and v.get("fr"):
                    fr_textes[k[len("provinces_onscreen_"):]] = v["fr"]
                if str(k).startswith("regions_onscreen_") and isinstance(v, dict) and v.get("fr"):
                    fr_reg.setdefault(k[len("regions_onscreen_"):], v["fr"])
    # (puis les noms français officiels de WH1 : les mers de la Saison, « Golfe sud du Bidouze »)
    wh1 = json.load(open(os.path.join(ATELIER, r"03-references\saison-des-revelations\textes-wh1.json"), encoding="utf-8"))
    for k, v in wh1.items():
        if str(k).startswith("regions_onscreen_") and isinstance(v, dict) and v.get("text"):
            fr_reg.setdefault(k[len("regions_onscreen_"):], v["text"])
    # les noms de l'Atlas, rattachés à leur province par sa clé (data-cible : l'identifiant de l'Atlas, « aquitaine » ->
    # wh_dlc05_aquitaine, « voutes_ouest » -> saison_province_voutes_ouest), à défaut à l'unité qui est sous eux
    atlas = {}
    for x, y, fr, en, sorte, cible in noms_provinces():
        u = -1
        for cle in (f"saison_province_{cible}", f"wh_dlc05_{cible}", f"mer:{cible}", f"mer:saison_sea_{cible}"):
            if cible and cle in unites:
                u = unites[cle]
                break
        if u < 0:
            xi, yi = int(np.clip(x, 0, LW - 1)), int(np.clip(y, 0, LH - 1))
            u = int(unite_px[yi, xi])
        if u >= 0:
            atlas.setdefault(u, (fr, en))
    inv = {v: k for k, v in unites.items()}
    out = []
    for u in range(len(unites)):
        cle = inv[u]
        m = (unite_px == u).astype(np.uint8)
        if not m.any():
            continue
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        k = 1 + int(np.argmax(st[1:, 4]))
        dist = cv2.distanceTransform((lab == k).astype(np.uint8), cv2.DIST_L2, 5)
        yi, xi = np.unravel_index(int(np.argmax(dist)), dist.shape)
        if cle.startswith("mer:"):
            sorte, k_ = "lib-mer", cle[4:]
            # (une mer de WH1 : son nom des textes du projet ; une mer neuve : celui de l'Atlas)
            fr = fr_reg.get(k_) or (atlas[u][0] if u in atlas else en_reg.get(k_, k_))
            en = en_reg.get(k_, k_)
        elif cle.startswith("region:"):
            continue
        else:
            sorte = "lib-province"
            nu = en_prov.get(cle, cle)
            court = cle.replace("wh_dlc05_", "").replace("saison_province_", "")
            # (le parchemin anglais de WH1 écrit « Realm of Tirsyth », comme le français « Royaume de Tirsyth »)
            en = f"Realm of {nu}" if court in ROYAUMES_AL and not nu.startswith("Realm") else nu
            if u in atlas:
                fr = atlas[u][0]
            elif fr_atlas.get(cle):
                fr = fr_atlas[cle]
            elif court in fr_textes:
                fr = fr_textes[court]
            elif court in ROYAUMES_AL:
                # (élision, comme le parchemin de WH1 : « Royaume d'Anmyr », « Royaume de Tirsyth »)
                fr = f"Royaume d'{nu}" if nu[:1].upper() in "AEIOUY" else f"Royaume de {nu}"
            else:
                fr = nu
        out.append((float(xi), float(yi), lignes_nom(fr if langue == "fr" else en), sorte, float(dist[yi, xi]), u))
    # (et les mers hors jeu que la carte de l'Atlas nomme : Mer des Griffes, Baie de Lyonen…)
    for x, y, fr, en, sorte, _ in noms_provinces():
        xi, yi = int(np.clip(x, 0, LW - 1)), int(np.clip(y, 0, LH - 1))
        if sorte == "lib-mer" and unite_px[yi, xi] < 0:
            out.append((x, y, lignes_nom(fr if langue == "fr" else en), sorte, 60.0, -1))
    return out


def deux_lignes(texte):
    """« Realm of Anmyr » -> [« Realm », « of Anmyr »] : coupé avant la première particule (rien si aucune)."""
    mots = texte.split()
    for i in range(1, len(mots)):
        m = mots[i].lower()
        if m in {"de", "du", "des", "of", "la", "le", "les"} or m.startswith(("d'", "l'")):
            return [" ".join(mots[:i]), " ".join(mots[i:])]
    return [texte]


def noms_pays():
    """[(x, y en px de la minicarte, fr, en)] : les pays hors jeu que la carte de l'Atlas nomme en capitales (lib-hors),
    sauf ceux que le jeu nomme déjà (le Reikland, province d'Expanded) et ceux de la seule Saison."""
    t = open(os.path.join(ATLAS, "carte_papier_v2.svg"), encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<text[^>]*class="lib lib-hors([^"]*)"[^>]*>', t):
        if "saison-seule" in m.group(1):
            continue
        a = dict(re.findall(r'(data-[a-z]+)="([^"]*)"', m.group(0)))
        fr, en = html.unescape(a.get("data-fr", "")), html.unescape(a.get("data-en", ""))
        if not en or en != en.upper() or en in {"REIKLAND"} or "data-x" not in a:
            continue
        out.append((float(a["data-x"]) * LW / 1120, float(a["data-y"]) * LH / 2090, fr, en))
    return out


def lignes_nom(texte):
    pre, _, nom = texte.partition("|")
    if not nom:
        pre, nom = "", pre
    pre = pre.strip()
    nom = titre(nom)
    if pre:
        tete, _, reste = pre.partition(" ")
        if pre.endswith("'"):
            return [tete, (reste + nom).strip()] if reste else [pre + nom]
        return [tete, (reste + " " + nom).strip()] if reste else [pre, nom]
    mots = nom.split()
    if len(nom) > 14 and len(mots) > 1:
        # (comme le parchemin de WH1 : « Duché / de Montfort », « Royaume / de Tirsyth » : on coupe avant la particule)
        if mots[1].lower() in {"de", "du", "des", "of", "d'", "la", "le", "les"} or mots[1].lower().startswith(("d'", "l'")):
            return [mots[0], " ".join(mots[1:])]
        coupe = max(range(1, len(mots)), key=lambda i: -abs(len(" ".join(mots[:i])) - len(" ".join(mots[i:]))))
        return [" ".join(mots[:coupe]), " ".join(mots[coupe:])]
    return [nom]


# ------------------------------------------------------------------ le rendu
def rendre(ids, unites, T, dec, langue, rng_graine=2512):
    rng = np.random.default_rng(rng_graine)
    print("  trame…")
    unite = tramer(ids, dec)
    # les noms d'abord (leurs boîtes : aucun pic dessous, comme sur le parchemin de WH1 où les noms sont au clair)
    # (les noms de WH1 sont d'un trait fin et le plus souvent sur une ligne ; mais à hauteur d'écran égale, Expanded montre
    # deux fois plus de pays que la Saison : ses noms sont plus grands par hex, pour se lire comme ceux de la Saison)
    polices = {t: ImageFont.truetype(POLICE, t) for t in (56, 52, 48, 44, 40, 36, 32)}
    polices_mer = {t: ImageFont.truetype(POLICE_MER, t) for t in (36, 32, 28)}
    noms, prises = [], []

    def boites_de(x, y, lignes, f):
        # (jamais coupé par le bord de l'image)
        demi = max(f.getbbox(l, anchor="mm")[2] for l in lignes) + 12
        x = min(max(x, demi), LW - demi)
        haut = f.size + 2
        demi_y = haut * len(lignes) / 2 + 8
        y = min(max(y, demi_y), LH - demi_y)
        y0 = y - haut * (len(lignes) - 1) / 2
        out = []
        # (une marge d'un demi-mot autour de chaque ligne : deux noms côte à côte se lisaient comme un seul, « Realm » de
        # Cavaroc devant « of Atylwyth », 3.10.2026)
        for k, l in enumerate(lignes):
            b = f.getbbox(l, anchor="mm")
            out.append((x + b[0] - 18, y0 + k * haut + b[1] - 6, x + b[2] + 18, y0 + k * haut + b[3] + 6))
        return x, y0, haut, out

    def touche(bs):
        return any(a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3] for a in bs for c in prises)

    eth_px = tramer((T["ether"] | T["voile"]).astype(np.int64), dec) > 0

    def deborde(bs, u_nom):
        # (la part du nom posée sur une AUTRE province ou mer : le parchemin de WH1 garde chaque nom chez lui)
        if u_nom < 0:
            return 0.0
        tot = autre = 0
        for x0, y0, x1, y1 in bs:
            z = unite[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))]
            tot += z.size
            # (l'éther et le voile comptent aussi : un nom de Reflet posé à cheval sur l'éther, « Reflection of Atylwyth » ;
            # le reste du hors-jeu non, un nom de la côte peut y déborder comme sur WH1, 3.10.2026)
            e_ = eth_px[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))]
            autre += int(((z != u_nom) & ((z >= 0) | e_)).sum())
        return autre / max(tot, 1)
    # (les plus grandes provinces d'abord ; la taille s'adapte à la place, et un nom qui en touche un autre s'écarte un
    # peu, puis rapetisse : jamais deux noms l'un sur l'autre)
    for x, y, lignes_2, sorte, place, u_nom in sorted(etiquettes(unite, unites, langue), key=lambda e: -e[4]):
        tailles = polices_mer if sorte == "lib-mer" else polices
        # (une province : d'abord sur une ligne, en 56 à 44, « Duché de Quenelles » comme sur le parchemin de WH1 ; sinon
        # en deux, « Royaume / de Tirsyth », à toutes les tailles ; un nom court à l'étroit se coupe aussi avant sa
        # particule, « Realm / of Anmyr », plutôt que de rapetisser)
        if sorte == "lib-province" and len(lignes_2) == 1:
            lignes_2 = deux_lignes(lignes_2[0])
        essais = [(t, lignes_2) for t in tailles]
        if sorte == "lib-province" and len(lignes_2) > 1:
            une = [" ".join(lignes_2)]
            essais = [(t, l) for t in tailles for l in ([une, lignes_2] if t >= 44 else [lignes_2])]
        retenu = None
        for t, lignes in essais:
            f = tailles[t]
            larg = max(f.getbbox(l, anchor="mm")[2] - f.getbbox(l, anchor="mm")[0] for l in lignes)
            if sorte != "lib-mer" and larg > 3.3 * place and t != min(tailles):
                continue
            for dx, dy in ((0, 0), (0, -18), (0, 18), (-24, 0), (24, 0), (0, -36), (0, 36), (-24, -24), (24, 24),
                           (-24, 24), (24, -24), (0, -54), (0, 54), (-48, 0), (48, 0)):
                xc, y0, haut, bs = boites_de(x + dx, y + dy, lignes, f)
                if not touche(bs) and deborde(bs, u_nom) < 0.14:
                    retenu = (xc, y0, haut, lignes, f, sorte, bs)
                    break
            if retenu:
                break
        # (une province minuscule, un sanctuaire comme Yn Edri Eternos : son nom ne tient pas dedans ; comme sur le
        # parchemin de WH1, il s'écrit juste au-dessus ou au-dessous de son cerne, en petit, quitte à déborder)
        if retenu is None and sorte == "lib-province" and place < 40:
            f = ImageFont.truetype(POLICE, 26)
            for dy in (-(place + 26), place + 26, -(place + 44), place + 44):
                for dx in (0, -30, 30):
                    xc, y0, haut, bs = boites_de(x + dx, y + dy, lignes_2, f)
                    if not touche(bs):
                        retenu = (xc, y0, haut, lignes_2, f, sorte, bs)
                        break
                if retenu:
                    break
        lignes = lignes_2
        if retenu is None:
            xc, y0, haut, bs = boites_de(x, y, lignes, tailles[min(tailles)])
            retenu = (xc, y0, haut, lignes, tailles[min(tailles)], sorte, bs)
        noms.append(retenu)
        prises += retenu[6]
    # les pays hors jeu (noms de l'Atlas : Terres Désolées, Estalie, Tilée, Wissenland), en capitales espacées, comme les
    # marges d'une carte gravée ; un nom qui toucherait une province ou une mer nommée s'écarte, sinon il est omis
    police_pays = ImageFont.truetype(POLICE, 30)
    for x, y, fr, en in noms_pays():
        texte = fr if langue == "fr" else en
        lig = ["   ".join(" ".join(m) for m in texte.split())]
        for dx, dy in ((0, 0), (0, -30), (0, 30), (-40, 0), (40, 0), (0, -60), (0, 60)):
            xc, y0, haut, bs = boites_de(x + dx, y + dy, lig, police_pays)
            dans_jeu = any((unite[max(0, int(b[1])):int(b[3]), max(0, int(b[0])):int(b[2])] >= 0).mean() > 0.05 for b in bs)
            if not touche(bs) and not dans_jeu:
                noms.append((xc, y0, haut, lig, police_pays, "lib-pays", bs))
                prises += bs
                break
    # (et le Bois Rêveur, au cœur de sa plus grande étendue d'éther, à l'encre pâle : l'autre monde a un nom)
    eth = tramer(T["ether"].astype(np.int64), dec, lisse=2.2) > 0.5
    if eth.any():
        # (le bord de l'image compte comme un rivage : sans cela, le nom tombait dans le coin)
        eth_c = eth.astype(np.uint8)
        eth_c[:, :1] = eth_c[:, -1:] = eth_c[-1:, :] = 0
        d_eth = cv2.distanceTransform(eth_c, cv2.DIST_L2, 5)
        ye, xe = np.unravel_index(int(np.argmax(d_eth)), d_eth.shape)
        texte = "LE BOIS RÊVEUR" if langue == "fr" else "THE DREAMING WOOD"
        lig = ["   ".join(" ".join(m) for m in texte.split())]
        police_reve = ImageFont.truetype(POLICE, 46)
        xc, y0, haut, bs = boites_de(float(xe), float(ye), lig, police_reve)
        if not touche(bs):
            noms.append((xc, y0, haut, lig, police_reve, "lib-reve", bs))
            prises += bs
    sous_noms = np.zeros((LH, LW), bool)
    for *_, boites in noms:
        for x0, y0, x1, y1 in boites:
            sous_noms[max(0, int(y0)):int(y1) + 22, max(0, int(x0)):int(x1)] = True
    jeu = unite >= 0
    jeu_l = cv2.GaussianBlur(jeu.astype(np.float32), (0, 0), 2.0) > 0.5
    M = {k: tramer(v.astype(np.int64), dec, lisse=2.2) > 0.5 for k, v in T.items() if k != "alt"}
    # (hors jeu, les petites eaux isolées, loin de la zone jouable, sont des taches sans nom : retirées ; les Terres
    # Désolées en étaient piquées)
    hors_eau = M["eau"] & ~jeu_l
    n_e, lab_e, st_e, _ = cv2.connectedComponentsWithStats(hors_eau.astype(np.uint8), 8)
    pres_jeu = np.unique(lab_e[hors_eau & (cv2.dilate(jeu_l.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)])
    petites = [k for k in range(1, n_e) if st_e[k, 4] < 2500 and k not in set(pres_jeu.tolist())]
    M["eau"] = M["eau"] & ~np.isin(lab_e, petites)
    # (l'altitude, en dixièmes : les pics sont plus serrés et plus grands au cœur des massifs, comme sur WH1)
    ALT = tramer(np.round(T["alt"] * 10).astype(np.int64), dec, lisse=2.2) / 10.0
    h, w = LH, LW
    # (3.10.2026, d'après le parchemin de WH1 en taille réelle : tout est papier ; les mers et les marges sont une fumée
    # brune qui colle aux terres, pas un gris ni un pointillé ; les forêts, de grandes taches en écailles ; les montagnes,
    # des grappes de petits pics bruns ; hors de la zone jouable, les dessins s'effacent avec la distance)
    tache = 0.6 * bruit(h, w, 70, rng) + 0.4 * bruit(h, w, 22, rng)
    fibres = bruit(h, w, 0.8, rng)
    marbre = np.clip(0.5 + 0.18 * (bruit(h, w, 5, rng) + bruit(h, w, 16, rng) + bruit(h, w, 40, rng)), 0, 1)
    caill2 = cailloutis(h, w, 6.0, rng)
    col = np.array(PAPIER, np.float32) * np.ones((h, w, 1), np.float32)
    # (le vieux papier : de grandes taches lentes, puis les petites, et les bords plus sombres, comme une feuille usée)
    grande = bruit(h, w, 220, rng)
    col = melange(col, np.clip(0.3 + 0.3 * tache + 0.2 * grande, 0, 1) * 0.6, PAPIER_SOMBRE)
    col *= (1 + 0.03 * fibres)[..., None]
    yy_b, xx_b = np.mgrid[0:h, 0:w]
    au_bord = np.minimum.reduce([xx_b, w - 1 - xx_b, yy_b, h - 1 - yy_b]).astype(np.float32)
    col = melange(col, np.clip(0.45 * np.exp(-au_bord / 70.0) * (0.7 + 0.5 * (0.5 + 0.25 * grande)), 0, 0.6),
                  (150, 121, 93))
    del yy_b, xx_b
    d_jeu = cv2.distanceTransform((~jeu_l).astype(np.uint8), cv2.DIST_L2, 5)
    efface = cv2.GaussianBlur(np.where(jeu_l, 1.0, np.exp(-d_jeu / 75.0)).astype(np.float32), (0, 0), 2)
    # les taches des terres : collines, forêts (en écailles), pied des montagnes
    joint, creux = ecailles(h, w, 5.5, rng)
    coll = cv2.GaussianBlur(M["coll"].astype(np.float32), (0, 0), 7) * efface
    col = melange(col, 0.16 * coll, TACHE)
    # (des taches douces aux bords fondus, comme un lavis, pas des aplats découpés)
    foret = cv2.GaussianBlur(M["foret"].astype(np.float32), (0, 0), 13)
    foret = np.clip((foret - 0.2 + 0.18 * tache) * 1.5, 0, 1) * efface
    col = melange(col, foret * (0.25 + 0.12 * creux), TACHE)
    col = melange(col, foret * 0.45 * joint, ENCRE_BRUNE)
    # (et le lavis de WH1 : de grandes taches lentes sur toutes les terres jouables, même sans forêt ; sans lui, le nord de
    # la Bretonnie, plat et peu boisé, restait un papier nu, 3.10.2026)
    terre_jeu = cv2.GaussianBlur((jeu_l & ~M["eau"]).astype(np.float32), (0, 0), 3)
    lavis = np.clip(0.5 * bruit(h, w, 38, rng) + 0.35 * bruit(h, w, 95, rng) - 0.15, 0, 1)
    col = melange(col, 0.24 * lavis * terre_jeu, TACHE)
    mont_doux = cv2.GaussianBlur(M["mont"].astype(np.float32), (0, 0), 8) * efface
    col = melange(col, np.clip(0.4 * mont_doux * (0.8 + 0.4 * marbre), 0, 1), TACHE)
    # la fumée : les mers en jeu, et une ombre qui colle à la zone jouable au dehors ; plus creuse le long des côtes
    eau = cv2.GaussianBlur(M["eau"].astype(np.float32), (0, 0), 1.2)
    jeu_d = cv2.GaussianBlur(jeu_l.astype(np.float32), (0, 0), 3)
    # (le halo de WH1 est large et pommelé : une ombre brune qui déborde des terres jouables, puis le papier)
    halo = np.exp(-(d_jeu / 85.0) ** 1.1) * (1 - jeu_d) * np.clip(0.7 + 0.25 * tache + 0.3 * (marbre - 0.5), 0.3, 1.1)
    fum = np.clip(np.maximum(eau * jeu_d, 0.95 * halo) * (0.82 + 0.36 * marbre), 0, 1)
    col = melange(col, 0.88 * fum, FUMEE)
    # (les mers hors jeu, plus claires que les mers jouables mais lisibles : sans elles, la mer Tiléenne était un papier
    # nu, et son nom flottait sur rien ; 3.10.2026)
    eau_hors = eau * (1 - jeu_d) * (1 - np.clip(0.95 * halo, 0, 1))
    col = melange(col, np.clip(0.5 * eau_hors * (0.8 + 0.4 * marbre), 0, 1), FUMEE)
    # (et, comme sur WH1, une bande plus sombre qui borde la zone jouable des deux côtés du bord : dehors, puis un peu
    # dedans, sous le trait)
    d_dedans = cv2.distanceTransform(jeu_l.astype(np.uint8), cv2.DIST_L2, 5)
    liseret = np.where(jeu_l, 0.35 * np.exp(-d_dedans / 22.0), np.exp(-d_jeu / 40.0)) * (1 - eau * jeu_d)
    liseret *= np.clip(0.6 + 0.3 * tache + 0.4 * (marbre - 0.5), 0.2, 1.0)
    col = melange(col, np.clip(0.55 * liseret, 0, 1), FUMEE_CREUX)
    # (le voile compte comme de l'éther : pas d'ombre de rivage le long de sa limite droite)
    d_cote = cv2.distanceTransform((M["eau"] | M["voile"]).astype(np.uint8), cv2.DIST_L2, 5)
    ombre = np.exp(-d_cote / 14.0) * eau * np.maximum(np.maximum(jeu_d, halo), 0.55) * (0.7 + 0.5 * marbre)
    col = melange(col, np.clip(0.5 * ombre, 0, 1), FUMEE_CREUX)
    # le Bois Rêveur : l'éther en fumée mauve-brun sur le papier, le voile en brume brune, un soupçon de pourpre sur le
    # reflet
    # (le voile : la déchirure de la carte de l'Atlas, validée par Charles, « une autre dimension » : le papier s'arrête net
    # sur un bord déchiré, roussi puis charbon, un fil de braise ; dessous, l'éther, plus sombre au pied de la déchirure.
    # Éther et voile ne font qu'une fumée, peinte d'une seule couche : deux couches laissaient un filet de papier à leur
    # couture, 3.10.2026)
    v_brut = M["voile"].astype(np.float32)
    ys_v = np.nonzero(v_brut.any(axis=1))[0]
    dechire = len(ys_v) > 0
    if dechire:
        haut_v = ys_v.min()
        dent = cv2.GaussianBlur(rng.standard_normal((1, w)).astype(np.float32), (0, 0), 9)[0]
        dent = 14 * dent / (np.abs(dent).max() + 1e-6) + 6 * bruit(1, w, 2, rng)[0] / 3
        yy0 = np.arange(h, dtype=np.float32)[:, None]
        v_brut = np.where(yy0 < haut_v + 18, (yy0 > haut_v + 6 + dent[None, :]).astype(np.float32), v_brut)
    dessous = v_brut > 0.5
    ether = cv2.GaussianBlur((M["ether"] | dessous).astype(np.float32), (0, 0), 1.5)
    # (avec le grain des marges de WH1 : de petites écailles fondues dans la fumée, et des nuées plus lentes)
    nuees_e = np.clip(0.5 + 0.35 * bruit(h, w, 60, rng) + 0.2 * bruit(h, w, 14, rng), 0, 1)
    teinte_e = np.array(ETHER, np.float32) * (0.84 + 0.22 * nuees_e + 0.06 * (caill2 - 0.5))[..., None]
    col = melange(col, 0.9 * ether, teinte_e)
    col = melange(col, 0.22 * ether * joint, (70, 56, 62))
    if dechire:
        # (distances depuis la déchirure seule : voile et éther d'un tenant, et rien au-delà de la bande, sinon la braise et
        # l'ombre suivaient aussi le bas du voile, en trait droit)
        fumee_reve = dessous | M["ether"]
        pres = yy0 < haut_v + 200
        d_bord = cv2.distanceTransform(fumee_reve.astype(np.uint8), cv2.DIST_L2, 5)
        d_papier = cv2.distanceTransform((~dessous).astype(np.uint8), cv2.DIST_L2, 5)
        au_dessus = (yy0 < haut_v + 40) & ~dessous
        # (l'ombre de la fosse se mesure depuis la DÉCHIRURE, pas depuis toute terre : un chenal étroit du Reflet
        # d'Atylwyth, à 20 hex sous la déchirure, en devenait une barre noire)
        d_fosse = cv2.distanceTransform((~(au_dessus | (yy0 < haut_v))).astype(np.uint8), cv2.DIST_L2, 5)
        col = melange(col, np.clip(0.5 * np.exp(-d_fosse / 40.0) * (fumee_reve & pres), 0, 1).astype(np.float32),
                      (62, 48, 54))
        col = melange(col, np.clip(0.55 * np.where(au_dessus, np.exp(-d_papier / 7.0), 0), 0, 1), (122, 84, 56))
        col = melange(col, np.clip(0.9 * np.where(au_dessus, np.exp(-d_papier / 2.2), 0), 0, 1), (42, 30, 26))
        braise = np.exp(-((d_bord - 1.2) / 1.0) ** 2) * (dessous & (yy0 < haut_v + 30))
        col = melange(col, np.clip(0.45 * braise, 0, 1).astype(np.float32), (196, 112, 98))
    reve = cv2.GaussianBlur(M["reve"].astype(np.float32), (0, 0), 4)
    col = melange(col, 0.1 * reve, (176, 140, 168))
    # les dessins à la plume (rivières, collines, montagnes) sur un calque, qui s'efface hors de la zone jouable
    dessin = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(dessin)
    # les rivières : un double trait brun à cœur clair, comme sur le parchemin de WH1
    # (sur leur propre calque : jamais sur la mer, l'éther ni le voile ; et un tracé presque droit serpente davantage)
    calque_riv = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dri = ImageDraw.Draw(calque_riv)
    traces_px = []
    # (3.10.2026, Charles : « la rivière du Reikland… qu'elle soit liée à sa source, là elle semble coupée ». Les rivières
    # de l'Atlas sont découpées en tronçons d'un confluent à l'autre : on les prend en RÉSEAUX. Un réseau qui touche la zone
    # jouable est dessiné en entier, jusqu'à ses sources, et ne s'efface que lentement au dehors ; un réseau tout entier
    # hors jeu ne l'est pas, comme sur WH1. Seuls les débris isolés et les traits qui longent la côte sont écartés.)
    for p in reseaux_rivieres(rivieres_svg(), jeu_l, M["eau"]):
        a_ = np.asarray(p)
        droit = float(np.hypot(*(a_[-1] - a_[0]))) / max(float(np.hypot(*np.diff(a_, axis=0).T).sum()), 1e-6)
        # (relevées pixel par pixel : lissées d'abord, puis le tremblé de la plume ; un tracé trop droit serpente plus)
        q = serpenter(adoucir_trace(p), rng, amp=1.0 + 2.5 * max(0.0, droit - 0.95) / 0.05)
        dri.line(q, fill=RIVIERE + (255,), width=7, joint="curve")
        dri.line(q, fill=(204, 180, 148, 255), width=3, joint="curve")
        traces_px.append(np.asarray(q, np.float32))
    r_ = np.asarray(calque_riv, np.float32)
    sec = (1 - eau) * (1 - ether) * (1 - cv2.GaussianBlur(M["voile"].astype(np.float32), (0, 0), 2))
    fondu_riv = cv2.GaussianBlur(np.where(jeu_l, 1.0, np.exp(-d_jeu / 220.0)).astype(np.float32), (0, 0), 2)
    # (sous un nom, la rivière s'estompe : elle passe sous l'écriture sans la rendre illisible, « Reikland »)
    sous_ecrit = np.zeros((h, w), np.float32)
    for *_, boites in noms:
        for x0_, y0_, x1_, y1_ in boites:
            sous_ecrit[max(0, int(y0_)):max(0, int(y1_)), max(0, int(x0_)):max(0, int(x1_))] = 1
    sous_ecrit = cv2.GaussianBlur(sous_ecrit, (0, 0), 3)
    col = melange(col, r_[..., 3] / 255.0 * fondu_riv * np.clip(sec, 0, 1) * (1 - 0.65 * sous_ecrit), r_[..., :3])
    del calque_riv, r_
    # les collines : de petits arcs à la plume, comme les pentes du parchemin de WH1. Dans les Reflets, le relief se dessine
    # ainsi, en pentes serrées à l'intérieur des terres (Charles, 3.10.2026 : des pics posés contre la séparation rendaient
    # mal ; WH1 borde Athel Loren de pentes hachurées, pas de pics)
    reve_dedans = cv2.erode(M["reve"].astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    pentes_reve = M["mont"] & reve_dedans
    collm = ((M["coll"] & ~M["mont"]) | pentes_reve) & ~M["eau"] & ~sous_noms
    for y in range(0, h, 11):
        for x in range(0, w, 13):
            xj, yj = x + rng.uniform(-4, 4), y + rng.uniform(-3, 3)
            xi, yi = int(np.clip(xj, 0, w - 1)), int(np.clip(yj, 0, h - 1))
            if collm[yi, xi] and rng.random() < (0.85 if pentes_reve[yi, xi] else 0.45):
                r = rng.uniform(3.0, 4.5)
                for k in range(2 if pentes_reve[yi, xi] else 1):
                    dr.arc([xj - r, yj - 0.8 * r + 3 * k, xj + r, yj + 0.8 * r + 3 * k], 200, 340,
                           fill=ENCRE_BRUNE + (210,), width=1)
    # les montagnes : des grappes de petits pics bruns, ombrés à droite, de l'arrière vers l'avant (jamais dans les Reflets)
    mont = M["mont"] & ~M["eau"] & ~M["reve"] & ~(cv2.dilate(M["voile"].astype(np.uint8), np.ones((25, 25), np.uint8)) > 0)
    # (jamais un pic sur une frontière : elles restent lisibles, comme sur WH1 ; les Sœurs Pâles s'y perdaient)
    fr_ = np.zeros((h, w), np.uint8)
    fr_[:, 1:] |= (unite[:, 1:] != unite[:, :-1]).astype(np.uint8)
    fr_[1:, :] |= (unite[1:, :] != unite[:-1, :]).astype(np.uint8)
    mont &= ~(cv2.dilate(fr_, np.ones((11, 11), np.uint8)) > 0)
    # (densité et taille selon l'altitude, et des trouées lentes : un massif, pas un papier peint ; 3.10.2026, teaser)
    trouee = np.clip(0.5 + 0.3 * bruit(h, w, 26, rng), 0, 1)
    pics = []
    for y in range(0, h, 11):
        for x in range(0, w, 11):
            xj, yj = x + rng.uniform(-5, 5), y + rng.uniform(-4, 4)
            xi, yi = int(np.clip(xj, 0, w - 1)), int(np.clip(yj, 0, h - 1))
            if not mont[yi, xi] or sous_noms[yi, xi]:
                continue
            haut_ = float(np.clip((ALT[yi, xi] - SEUIL_MONT) / 3.5, 0, 1))
            if rng.random() < (0.35 + 0.55 * haut_) * (0.55 + 0.6 * trouee[yi, xi]):
                pics.append((yj, xj, rng.uniform(12, 16) + 9 * haut_))
    # les sources : (3.10.2026, Charles : « là où la rivière s'arrête, c'est les sources ? il faut mettre des petites
    # montagnes tout autour, plus joli que des rivières qui s'arrêtent au milieu de nulle part ». Le lore le veut aussi :
    # la Sannez naît dans les Sœurs Pâles, le ruisseau des Contreforts dans les contreforts, celui d'Alençon dans les
    # « Great Mounds » de l'Atlas of the Old World.) À chaque bout de rivière libre, dans la zone jouable, loin de l'eau et
    # d'un autre cours, hors d'une montagne déjà dessinée : une butte, quelques pentes et deux ou trois petits pics, un peu
    # en amont, dans le prolongement de la rivière.
    tous = np.concatenate(traces_px) if traces_px else np.zeros((0, 2), np.float32)
    proprio = np.concatenate([np.full(len(t), i) for i, t in enumerate(traces_px)]) if traces_px else np.zeros(0)
    eau_pres = cv2.dilate(M["eau"].astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    mont_pres = cv2.dilate(M["mont"].astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    n_sources = 0
    for i, t in enumerate(traces_px):
        if len(t) < 4:
            continue
        for bout in (0, 1):
            e = t[0] if bout == 0 else t[-1]
            v = e - (t[min(6, len(t) - 1)] if bout == 0 else t[max(0, len(t) - 7)])
            xi, yi = int(np.clip(e[0], 0, w - 1)), int(np.clip(e[1], 0, h - 1))
            if not jeu_l[yi, xi] or eau_pres[yi, xi] or mont_pres[yi, xi] or M["reve"][yi, xi]:
                continue
            d_ = np.hypot(*(tous - e).T)
            if ((d_ < 6) & (proprio != i)).any():
                continue                      # (un confluent, pas une source)
            n_v = float(np.hypot(*v))
            if n_v < 1e-6:
                continue
            u = v / n_v
            nrm = np.array([-u[1], u[0]])
            c = e + u * 9
            # la butte : quelques pentes en arc autour du point de source
            for k in range(7):
                ang = rng.uniform(0, 2 * np.pi)
                rr = rng.uniform(6, 16)
                px_, py_ = c + rr * np.array([np.cos(ang), np.sin(ang)])
                if 0 <= int(py_) < h and 0 <= int(px_) < w and not sous_noms[int(py_), int(px_)]:
                    r = rng.uniform(3.0, 4.5)
                    dr.arc([px_ - r, py_ - 0.8 * r, px_ + r, py_ + 0.8 * r], 200, 340, fill=ENCRE_BRUNE + (210,), width=1)
            # deux ou trois petits pics, en éventail en amont
            for k, dec_ in enumerate((-1.0, 1.0, 0.0)):
                pc = c + u * (4 + 3 * (1 - abs(dec_))) + nrm * dec_ * 9
                if 0 <= int(pc[1]) < h and 0 <= int(pc[0]) < w and not sous_noms[int(pc[1]), int(pc[0])]:
                    pics.append((float(pc[1]), float(pc[0]), rng.uniform(12, 15) + (3 if dec_ == 0 else 0)))
            n_sources += 1
    print(f"  sources marquées : {n_sources}")
    pics.sort()
    for y, x, s in pics:
        hh = s * rng.uniform(0.8, 1.05)
        apex = (x + rng.uniform(-2, 2), y - hh)
        g, dd = (x - s / 2, y), (x + s / 2, y)
        dr.polygon([g, apex, (x + 1, y)], fill=(214, 194, 162, 255))
        dr.polygon([(x + 1, y), apex, dd], fill=(166, 140, 110, 255))
        for k in range(1, 4):
            t = k / 4
            a = (apex[0] + (dd[0] - apex[0]) * t * 0.9, apex[1] + (dd[1] - apex[1]) * t * 0.9)
            dr.line([a, (a[0] - s * 0.16, a[1] + hh * 0.3)], fill=ENCRE_BRUNE + (230,), width=1)
        dr.line([g, apex, dd], fill=ENCRE_BRUNE + (255,), width=2, joint="curve")
    d = np.asarray(dessin, np.float32)
    col = melange(col, d[..., 3] / 255.0 * efface, d[..., :3])
    # l'encre : les côtes, les frontières des provinces (tremblées), le contour de la zone jouable
    gx = np.clip(bruit(h, w, 14, rng) * 2.2, -4, 4)
    gy = np.clip(bruit(h, w, 14, rng) * 2.2, -4, 4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    def trembler(a):
        # (au bord de l'image, on recopie le bord : sans cela, le tremblement va chercher des zéros hors de l'image et
        # dessine une frange d'encre le long du bord nord, 3.10.2026)
        return cv2.remap(a.astype(np.float32), xx + gx, yy + gy, cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    u = trembler(unite)
    # (comme sur le parchemin de WH1 : un trait entre deux provinces ou entre deux mers, jamais le long d'une côte ;
    # la côte n'est qu'un liseré brun léger, la fumée de la mer fait le reste)
    S = np.isin(u, np.array([v for k, v in unites.items() if k.startswith("mer:")], np.float32))
    bord = np.zeros((h, w), bool)
    bord[:, 1:] |= (u[:, 1:] != u[:, :-1]) & (S[:, 1:] == S[:, :-1])
    bord[1:, :] |= (u[1:, :] != u[:-1, :]) & (S[1:, :] == S[:-1, :])
    entre_prov = bord & (u >= 0)
    cote = np.zeros((h, w), bool)
    e = trembler(M["eau"]) > 0.5
    cote[:, 1:] |= e[:, 1:] != e[:, :-1]
    cote[1:, :] |= e[1:, :] != e[:-1, :]
    contour = np.zeros((h, w), bool)
    j = trembler(jeu_l) > 0.5
    contour[:, 1:] |= j[:, 1:] != j[:, :-1]
    contour[1:, :] |= j[1:, :] != j[:-1, :]
    # (pas de trait droit au pied des Voûtes : là, c'est le bord déchiré du voile qui fait la limite ; pas de trait en
    # pleine mer au bout des mers jouables : la fumée s'y fond dans le papier)
    contour &= ~(cv2.dilate(M["voile"].astype(np.uint8), np.ones((31, 31), np.uint8)) > 0)
    contour &= ~(cv2.dilate(M["eau"].astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    # (et les bouts de contour de moins de 40 px que la côte laisse : des tirets noirs sur le rivage nord-est)
    n_c, lab_c, st_c, _ = cv2.connectedComponentsWithStats(contour.astype(np.uint8), 8)
    contour &= np.isin(lab_c, np.nonzero(st_c[:, 4] >= 40)[0][1:])
    def trait(m, larg):
        m = cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (larg, larg)))
        return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.7)
    # (assez large pour le tremblé de la plume, qui décale le bord de 4 px)
    voile_large = cv2.dilate(M["voile"].astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    # (hors jeu, la côte s'efface plus lentement que les dessins : la mer Tiléenne, l'Estalie restent lisibles)
    efface_cote = np.where(jeu_l, 1.0, np.exp(-d_jeu / 260.0)).astype(np.float32)
    col = melange(col, 0.35 * trait(cote & ~voile_large, 2) * efface_cote, ENCRE_BRUNE)
    # (entre deux mers, un trait brun léger, comme le seul trait des golfes de WH1 ; noir, il chargeait l'ouest de lignes)
    col = melange(col, 0.5 * trait(entre_prov & S, 2), ENCRE_BRUNE)
    encre = np.maximum(0.85 * trait(entre_prov & ~S, 2), 0.9 * trait(contour, 3))
    col = melange(col, encre, ENCRE)
    # les noms (d'un trait fin, sans graisse, comme sur le parchemin de WH1) ; sous les noms de province, un halo de papier
    # très doux, pour qu'aucune frontière ni rivière ne les coupe (« Duchy of Aquitaine », « Reikland ») ; les pays hors
    # jeu en encre pâle
    calque = Image.new("L", (w, h), 0)
    calque_pays = Image.new("L", (w, h), 0)
    calque_halo = Image.new("L", (w, h), 0)
    calque_reve = Image.new("L", (w, h), 0)
    dc, dp_, dh = ImageDraw.Draw(calque), ImageDraw.Draw(calque_pays), ImageDraw.Draw(calque_halo)
    dr_ = ImageDraw.Draw(calque_reve)
    n = 0
    for x, y0, haut, lignes, f, sorte, _ in noms:
        for k, l in enumerate(lignes):
            cible = {"lib-pays": dp_, "lib-reve": dr_}.get(sorte, dc)
            cible.text((x, y0 + k * haut), l, font=f, fill=255, anchor="mm")
            if sorte == "lib-province":
                dh.text((x, y0 + k * haut), l, font=f, fill=255, anchor="mm", stroke_width=5, stroke_fill=255)
        n += 1
    halo_n = cv2.GaussianBlur(np.asarray(calque_halo, np.float32) / 255.0, (0, 0), 3.5)
    col = melange(col, np.clip(0.42 * halo_n, 0, 1), col * 0.45 + np.array(PAPIER, np.float32) * 0.55)
    a = cv2.GaussianBlur(np.asarray(calque_pays, np.float32) / 255.0, (0, 0), 0.6) * 0.5
    col = melange(col, a, ENCRE_BRUNE)
    a = cv2.GaussianBlur(np.asarray(calque_reve, np.float32) / 255.0, (0, 0), 0.7) * 0.6
    col = melange(col, a, (214, 194, 204))
    a = cv2.GaussianBlur(np.asarray(calque, np.float32) / 255.0, (0, 0), 0.6) * 0.92
    col = melange(col, a, ENCRE)
    print(f"  {langue} : {n} noms")
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    acc = LE.controle_saison()
    dec, taux = max(acc.items(), key=lambda kv: kv[1])
    print(f"  trame contrôlée sur la Saison : {100 * taux:.2f} % (décalage {dec:+.1f})")
    ids, unites, T = grilles()
    os.makedirs(SORTIE, exist_ok=True)
    # (--apercu : le français seul, pour essayer un réglage deux fois plus vite)
    for langue in (("fr",) if "--apercu" in sys.argv else ("en", "fr")):
        im = rendre(ids, unites, T, dec, langue)
        petite = im.resize((LW // 2, LH // 2), Image.LANCZOS).convert("RGBA")
        chemin = os.path.join(SORTIE, f"saison_expanded_minimap_{langue}.png")
        petite.save(chemin)
        print("  ->", chemin, petite.size)
    petite.convert("RGB").resize((LW // 6, LH // 6), Image.LANCZOS).save(os.path.join(ICI, "apercus", "minimap_parchemin_fr.jpg"),
                                                                        quality=90)
    return 0


if __name__ == "__main__":
    sys.exit(main())
