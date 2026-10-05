#!/usr/bin/env python3
r"""
projet_expanded.py - le projet de terrain (Terry) de Saison Expanded, fabriqué À PARTIR de celui de la Saison (phase 3).

Pourquoi (25.09.2026, Charles : « attaque la phase 3 ») : plutôt que de retoucher le générateur de la bêta, on lit son
projet Terry (LECTURE SEULE : `raw_data\terrain\campaigns\wh_dlc05_wood_elves_map_1\`) et on écrit un projet neuf
`saison_expanded_map` dans le BAC À SABLE du chantier (`04-projets\saison-expanded\terry\saison_expanded_map\`), jamais dans
le kit : la bêta n'est pas touchée.

Règles :
- dans TOUT le cadre 400 × 440 de la Saison, tout reste celui de WH1 (relief, textures, arbres, eau, objets) : ses
  montagnes sont des maillages DRAPÉS sur son relief, qu'on ne doit pas déplacer d'un cheveu ;
- autour : le terrain de l'Atlas (relief modelé `relief_atlas`, sols de la grille CAIME d'Expanded) ; raccord HORS du
  cadre, sur RACCORD_HEX hex, du relief de l'Atlas vers le bord de la Saison ;
- rasters agrandis à la même densité (8, 4 ou 2 px par hex ; masque de visibilité par pavés de 28 px), la Saison posée à
  (x + 120 hex, 135 hex sous le haut) ;
- calques d'objets : chaque `ECTransform position` décalé de (+DX_U, +DZ_U) (monde de la Saison : 266,53 × 338,9 u pour
  400 × 440 hex) ; fichiers renommés à la clé d'Expanded ;
- `.terry` : `terrain_setup` et éclairage à la clé d'Expanded, `world_width` = 373,142 ; `rules.bob` : clé remplacée.
Les zones d'éclairage (cylindres) et la liste compilée des arbres se décalent à l'étape suivante (à faire).

Usage :
    python projet_expanded.py            # écrit le projet dans le bac à sable + aperçus de contrôle
"""
import glob
import os
import re
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relief_alpin                                                  # noqa: E402
import habillage_expanded                                            # noqa: E402
import eau_expanded                                                  # noqa: E402
import decors_expanded                                               # noqa: E402
import rivieres_atlas                                                # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names        # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
SOURCE_CLE = "wh_dlc05_wood_elves_map_1"
CIBLE_CLE = "saison_expanded_map"
SRC = os.path.join(KIT, r"raw_data\terrain\campaigns", SOURCE_CLE)
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
DST = os.path.join(ICI, "terry", CIBLE_CLE)
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
# (3.10.2026, les Voûtes : 560 × 905, la Saison en (x + 120, y + 330) ; cadre_expanded.py)
from cadre_expanded import W, H, SW, SH, DX as DXH, DY, DY_HAUT as DYH_HAUT, RANG_ATLAS, NH_ATLAS, REFLET_PX  # noqa: E402
LARGEUR_S, PROF_S = 266.53, 338.9
DX_U = DXH * LARGEUR_S / SW                    # 79,959 u vers l'est
DZ_U = DY * PROF_S / SH                        # 254,175 u vers le nord (z croît vers le nord ; 192,557 avant les Voûtes)
LARGEUR_E = LARGEUR_S * W / SW                 # 373,142
UX_PX = LARGEUR_E / (W * 8)                     # u par pixel des rasters à 8 px par hex (0,0833)
RACCORD_HEX = 12
GRAIN_MAX_PX = 40                             # px (8 par hex) : terre isolée plus petite = grain à rentrer sous l'eau
RACCORD_BORD_HEX = 2.0                       # hex, hors de la zone gardée : base et détail rejoignent le prolongement
WH1_BLEND = os.path.join(ATELIER, r"03-references\saison-des-revelations\terrain-wh1\terrain\campaigns",
                         SOURCE_CLE, r"global_map\global_blend.dds")
MONDE_WH1 = os.path.join(ICI, r"terrain-wh1\wh1_blend_monde.npy")   # nord en haut, 8 px par hex, index de WH1
MONTAGNES_MONDE = os.path.join(ICI, r"terrain-wh1\montagnes_wh1_monde.npy")
PENTE_MAX_RACCORD = 0.5                       # u d'altitude par hex, au plus, dans le raccord
HAUTEUR_SUR_MER, SOUS_TERRE_MER = 0.02, 1.0
PROFONDEUR_LIT = 0.17                          # lit des rivières de l'Atlas sous les berges (WH1 : ~0,17 u, GUIDE n° 149)
PENTE_COTE = 0.25                              # u par px (8 px par hex) : falaise côtière la plus raide permise (4.10)
from cadre_expanded import SUD, ipx_de                                    # noqa: E402


def remplir_lisse(val, connu):
    """Prolonge `val` (connu où `connu`) partout, sans rayures : « push-pull » par pyramide (moyennes pondérées aux
    échelles grossières, puis remontée en ne remplaçant que l'inconnu). Donne un prolongement lisse du bord de la Saison."""
    v = np.where(connu, val, 0).astype(np.float32)
    m = connu.astype(np.float32)
    pile = [(v, m)]
    while min(v.shape) > 8:
        v = cv2.resize(v * 1.0, (max(1, v.shape[1] // 2), max(1, v.shape[0] // 2)), interpolation=cv2.INTER_AREA)
        m = cv2.resize(m, (v.shape[1], v.shape[0]), interpolation=cv2.INTER_AREA)
        pile.append((v, m))
    # au niveau le plus grossier : moyenne des connus
    v, m = pile[-1]
    moy = float((v.sum() / max(m.sum(), 1e-6)))
    courant = np.where(m > 1e-6, v / np.maximum(m, 1e-6), moy).astype(np.float32)
    for v, m in reversed(pile[:-1]):
        haut = cv2.resize(courant, (v.shape[1], v.shape[0]), interpolation=cv2.INTER_LINEAR)
        propre = v / np.maximum(m, 1e-6)
        courant = (propre * np.clip(m, 0, 1) + haut * (1 - np.clip(m, 0, 1))).astype(np.float32)
    return courant


def agrandir(a, f, remplissage, reste):
    """`a` (nord en haut, `f` px par hex, `reste` rangées de plus que 440·f) dans la toile d'Expanded, remplie de
    `remplissage`."""
    fond = np.empty((H * f + reste, W * f) + a.shape[2:], a.dtype)
    fond[...] = remplissage
    y0, x0 = DYH_HAUT * f, DXH * f
    fond[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
    return fond


def cadre_masque(f, reste):
    m = np.zeros((H * f + reste, W * f), bool)
    y0, x0 = DYH_HAUT * f, DXH * f
    m[y0:y0 + SH * f + reste, x0:x0 + SW * f] = True
    return m


# BORDURE DE WH1 (25.09.2026, 20 h ; décision de Charles de 19 h : « dans Expanded, l'Atlas l'emporte ») : la carte de WH1 a
# une bordure décorative hors jeu (montagnes, falaises) tout autour de sa partie jouable ; l'Atlas y a posé ~25 000 hex de
# régions et de mers neuves (Couronne, Artois, Grung Zint, baies...). Le terrain de WH1 est donc gardé seulement sur sa
# partie jouable (couche Impassable de la Saison, 1 = franchissable) élargie de MARGE_WH1_HEX, et partout où l'Atlas ne met
# ni région ni mer neuve ; ailleurs, le relief de l'Atlas, raccordé. Les objets de WH1 hors de cette zone sont retirés.
MARGE_WH1_HEX = 2        # (3.10.2026 : 4 gardait encore le bourrelet du cadre de WH1, en arêtes droites ; « sans cadre »)
REBORD_WH1_HEX = 8
_GARDE = {}


def garde_wh1_hex():
    """Hex (H × W, ligne 0 = sud) où le terrain de WH1 est gardé."""
    if "hex" in _GARDE:
        return _GARDE["hex"]
    # la carte de WH1 proprement dite = les cases de ses régions (tout sauf terre et mer sauvages), massifs infranchissables
    # intérieurs compris (20 h 20 : la couche de passage seule en excluait les sommets du Massif Orcal et des Grises)
    noms_s, _, _ = caime_names(CAIME, os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex"))
    regions_s = flat_names(noms_s, "Regions")
    sauvages = [i for i, n in enumerate(regions_s) if "wilderness" in n]
    _, rg = read_layer(os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots\layer_regions.hex_layer"))
    jouable = np.zeros((H, W), np.uint8)
    jouable[DY:DY + SH, DXH:DXH + SW] = ~np.isin(rg.reshape(SH, SW), sauvages) & (rg.reshape(SH, SW) >= 0)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * MARGE_WH1_HEX + 1, 2 * MARGE_WH1_HEX + 1))
    proche = cv2.dilate(jouable, k).astype(bool)
    r = np.load(REGIONS_ATLAS)
    neuf = np.zeros((H, W), bool)
    neuf[RANG_ATLAS:RANG_ATLAS + r["lab"].shape[0], :W] = (r["lab"] >= 0) | (r["labm"] >= 0)
    cadre = np.zeros((H, W), bool)
    cadre[DY:DY + SH, DXH:DXH + SW] = True
    # 20 h 15 : d'abord gardée partout où l'Atlas n'avait rien de neuf, la bordure décorative laissait un cadre visible
    # à l'est et au sud (terre sauvage de l'Atlas contre montagnes de WH1). Désormais : WH1 sur sa partie jouable et la
    # marge seulement ; partout ailleurs, l'Atlas, raccordé (Charles : « sans bordure »).
    garde = cadre & proche
    # (3.10.2026) sous des régions NEUVES de l'Atlas (les Voûtes au sud d'Athel Loren), la marge de WH1 tombe à 1 hex : sur
    # 4 hex, elle gardait le bourrelet de décor de WH1, une longue arête droite le long du bord sud de la zone jouable,
    # entre la forêt et les contreforts des Voûtes
    proche1 = cv2.dilate(jouable, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))).astype(bool)
    garde &= proche1 | ~neuf
    # (3.10.2026) même chose dans les enclaves de terre sauvage réparties entre des régions (regions_expanded) : la bande
    # de bordure du nord de WH1 (entre Gisoreux, Couronne et l'Artois) est jouable dans Expanded, ses montagnes de décor
    # (relief et maillages) n'ont plus lieu d'être ; le massif intérieur des Grises, fermé, prend le relief de l'Atlas
    p_enc = os.path.join(ICI, "couches-expanded", "enclaves.npy")
    if os.path.exists(p_enc):
        garde &= proche1 | ~np.load(p_enc)
    # 21 h 05 (relief ombré, `captures-article\12-relief-ombre.jpg`) : le relief de WH1 plonge vers 0 sur ses derniers hex
    # (rebord de carte) ; gardé, il faisait une falaise droite le long du bord est. Sur une bande de REBORD_WH1_HEX hex au
    # bord du cadre, on ne garde WH1 que sur ses cases franchissables (couche Impassable de la Saison) ; le rebord
    # infranchissable passe au raccord vers l'Atlas.
    _, imp = read_layer(os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots\layer_impassable.hex_layer"))
    passe = np.zeros((H, W), np.uint8)
    passe[DY:DY + SH, DXH:DXH + SW] = imp.reshape(SH, SW) == 1
    passe = cv2.dilate(passe, np.ones((5, 5), np.uint8)).astype(bool)
    interieur = np.zeros((H, W), np.uint8)
    interieur[DY + REBORD_WH1_HEX:DY + SH - REBORD_WH1_HEX, DXH + REBORD_WH1_HEX:DXH + SW - REBORD_WH1_HEX] = 1
    mers_s = [i for i, n in enumerate(regions_s) if "sea" in n]
    mer_wh1 = np.zeros((H, W), bool)
    mer_wh1[DY:DY + SH, DXH:DXH + SW] = np.isin(rg.reshape(SH, SW), mers_s)
    # 21 h 30 (bande de terre verticale dans la mer, à l'ouest du golfe) : dans la bande du bord, seules les TERRES
    # franchissables de WH1 sont gardées ; ses mers y cèdent à celle de l'Atlas
    garde &= interieur.astype(bool) | (passe & ~mer_wh1)
    # 21 h 20 : une région TERRESTRE neuve posée sur une mer de WH1 (l'Île Silencieuse sur le golfe du Bidouze) prend le
    # relief de l'Atlas, même si le golfe est une région de WH1
    terre_neuve = np.zeros((H, W), bool)
    terre_neuve[RANG_ATLAS:RANG_ATLAS + r["lab"].shape[0], :W] = r["lab"] >= 0
    garde &= ~(terre_neuve & mer_wh1)
    _GARDE["hex"] = garde
    _GARDE["jouable"] = jouable.astype(bool) & garde
    print(f"  terrain de WH1 gardé sur {int(garde.sum())} hex du cadre ; remplacé par l'Atlas sur "
          f"{int((cadre & ~garde).sum())} hex (bordure décorative sous des régions ou mers neuves)")
    return garde


BORD_ORGANIQUE_HEX = 1.0                      # hex : élargissement moyen, ondulé, du bord de la zone gardée de WH1
BAS_CUVETTE = 0.05                           # u : une cuvette sous ce niveau, loin de toute eau, est comblée
FONDU_SOL_HEX = 1.5                           # hex : la couleur du sol de WH1 fondue dans celle de l'extension
FONDU_EAU_HEX = 6.0                         # hex : la couleur de l'eau de WH1 fondue dans celle de l'extension
# u : fond marin au plus, sous la mer (guide Terry : « sous 0 ») ; −0,3 effaçait les hauts-fonds des côtes (70 080 px
# ramenés au premier passage) : juste sous 0, seuls les fonds ≥ 0 bougent
FOND_MER_MAX = -0.03
CREUX_U, CREUX_PLAINE_U = 0.2, 2.5                # u : creux étroit à refermer ; plaine (au-delà : vallées de montagne)
MARCHE_U = 0.5                                     # u : saut d'un pixel au voisin au-delà duquel le relief est fondu
FORET_MONTAGNE = 0.55                              # part boisée au plus de la montagne de l'extension (bas des pentes)
LISIERE_HEX = 6                                    # hex : prolongement des arbres de WH1 hors de la zone gardée
ROUTE_TUILE = np.array((93, 66, 24, 255), np.uint8)
GENERIC_TUILE = np.array((223, 180, 145, 255), np.uint8)


def double_caime(a):
    """BaselineTilemapExporter.Doubled de CAIME, à l'identique : tableau d'hex (H, W, rangée 0 au sud) -> pixels
    (2H + 1, 2W), colonnes impaires décalées d'un demi-hex ; rangée de pixels 0 au sud, comme l'export."""
    h, w = a.shape
    out = np.zeros((2 * h + 1, 2 * w), a.dtype)
    for row in range(h):
        for col in range(w):
            v_ = a[row, col]
            if col % 2 == 0:
                out[2 * row:2 * row + 2, 2 * col:2 * col + 2] = v_
            else:
                out[2 * row, 2 * col:2 * col + 2] = a[row - 1, col] if row > 0 else v_
                out[2 * row + 1, 2 * col:2 * col + 2] = v_
            if row == h - 1:
                out[2 * row + 2, 2 * col:2 * col + 2] = v_
    return out


def montagnes_gardees(f, reste):
    """(5.10.2026, Charles en jeu, capture : « des montagnes qui flottent… deux styles de montagne qui se chevauchent »)
    les maillages de montagne de WH1 sont DRAPÉS d'avance sur le relief de WH1 (`02-scripts\\montagnes_wh1.py`, une pose =
    un modèle) ; gardés dans Expanded quand leur pivot est dans la zone gardée, ils flottaient là où Expanded change ce
    relief : marge de décor lissée, et bord de la zone que leur rectangle dépasse. Masque (f px par hex, nord en haut) des
    rectangles de ces poses, élargi d'un hex : le relief y reste celui de WH1."""
    cle = ("montagnes", f, reste)
    if cle in _GARDE:
        return _GARDE[cle]
    sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
    import montagnes_wh1 as MW
    import montagnes_wh1_expanded
    from cadre_expanded import px_de
    garde = garde_wh1_hex()
    m = np.zeros((H * f + reste, W * f), np.uint8)
    n = 0
    for p in MW.poses():
        x, z, _ = MW.transformation(p)
        z = z * MW.Z_VERS_MONDE                            # (premier essai : 217 pivots sur 818) z des calques = z × 2/√3
        q, r = int(x / (LARGEUR_S / SW)), int(z / (PROF_S / SH))
        if not (0 <= q < SW and 0 <= r < SH and garde[DY + r, DXH + q]):
            continue                                       # pose retirée de la bordure (projet_expanded, trie)
        # (5.10.2026) ni les montagnes de bordure de WH1 surtout HORS de la zone gardée (montagnes_wh1_expanded)
        if montagnes_wh1_expanded.est_retiree(float(x), float(z)):
            continue
        vx = np.array([0.0, 128.0 * p.W, 0.0, 128.0 * p.W])
        vz = np.array([0.0, 0.0, -128.0 * p.H, -128.0 * p.H])
        wx, wz = MW.vers_monde(p, vx, vz)
        a, b = px_de(np.asarray(wx) + DX_U, np.asarray(wz) * MW.Z_VERS_MONDE + DZ_U, m.shape)
        x0, x1 = int(np.floor(a.min())), int(np.ceil(a.max()))
        y0, y1 = int(np.floor(b.min())), int(np.ceil(b.max()))
        m[max(0, y0):max(0, y1) + 1, max(0, x0):max(0, x1) + 1] = 1
        n += 1
    m = cv2.dilate(m, np.ones((2 * f + 1, 2 * f + 1), np.uint8)) > 0
    print(f"  montagnes de WH1 gardées (maillages drapés) : {n} poses ; relief de WH1 gardé sous leur emprise : "
          f"{int(m.sum())} px")
    _GARDE[cle] = m
    return m


def garde_masque(f, reste):
    """La zone gardée de WH1, à f px par hex, nord en haut, `reste` rangées de plus en bas. (4.10.2026, aperçus de la
    jonction des Grises : bord en ESCALIER d'hex, relief détaillé de WH1 coupé case par case, couleurs et textures en dents
    de scie) à f ≥ 4, le bord est ORGANIQUE : la zone s'élargit, dans le cadre de WH1 seulement (où son relief existe),
    d'une bande de BORD_ORGANIQUE_HEX ± 0,8 hex, ondulée par un bruit lent ; elle ne rétrécit jamais (les objets de WH1
    gardés restent sur le relief de WH1)."""
    cle = ("garde", f, reste)
    if cle in _GARDE:
        return _GARDE[cle]
    g = np.repeat(np.repeat(garde_wh1_hex()[::-1], f, 0), f, 1)
    if reste:
        g = np.concatenate([g, np.repeat(g[-1:], reste, 0)])
    if f >= 4:
        d = cv2.distanceTransform((~g).astype(np.uint8), cv2.DIST_L2, 5) / f
        br = habillage_expanded.bruit(g.shape, 3 * f, np.random.default_rng(41004), 2)
        br = br / max(float(np.abs(br).max()), 1e-6)
        g = g | ((d < BORD_ORGANIQUE_HEX + 0.8 * br) & cadre_masque(f, reste))
    _GARDE[cle] = g
    return g


# LE BOIS RÊVEUR (Charles, 25.09.2026 : « le bois au sud, en reflet miroir », « effets démoniaques sur les contours du
# miroir et sur la séparation ») : grilles de la session « Extension » (bois_des_reves.py, exporter_grilles), 250 × 560,
# ligne 0 = sud, colonne = x + 120 : `terre` (les 18 régions d'Athel Loren reflétées), `voile` (26 rangées contre la
# Saison), `riviere`, `region`, `domaine`. Reflet : hex (x, y) de la Saison -> (x, 7 − y), soit la rangée de grille
# R' = 507 − R ; dans les rasters (nord en haut, f px par hex) : rangée de pixel p' <- 1142·f − 1 − p. (3.10.2026, les
# Voûtes entre la Saison et le voile : (x, −73 − y), R' = 587 − R, p' <- 1222·f − 1 − p ; cadre_expanded.) Le reflet prend
# TOUT de WH1 (relief, eau, sols, arbres, neige d'hiver), sous une teinte de Slaanesh ; la lisière est corrompue.
# (Rangées de parité opposée : le reflet est décalé d'un demi-hex en x par rapport aux hex de la grille, 4 px à 8 px par
# hex ; invisible à l'œil, sans effet sur les régions, qui viennent de la grille.)
REVES = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\reves_grilles.npz")
# (4.10.2026, 23 h 28 : l'île lissée par la session des Voûtes est écrite pendant que la chaîne du kit attend son préavis)
# une étape d'après BOB (textures_reves) doit lire l'île avec laquelle le projet a été construit : SAISON_REVES_NPZ
REVES = os.environ.get("SAISON_REVES_NPZ") or REVES
SUD = 250                                       # rangées d'hex du Bois Rêveur, sous la Saison
# (4.10.2026, Charles : « que ce miroir soit vraiment le royaume de Slaanesh » des Royaumes du Chaos) le sol est celui
# du royaume de CA (textures_reves.py) ; sur ce sol, la carte wh3_main_chaos_map_1 a un colour_overlay GRIS NEUTRE
# (médiane 115, 113, 115) et un lf_sea_colour gris (123, 125, 123), relevés dans ses DDS : plus de teinte lilas ni de
# lisière magenta (la teinte doublait la couleur des textures du royaume ; « bande rose en frontière » refusée le 3.10)
GRIS_ROYAUME = np.array((115, 113, 115), np.float32)
GRIS_ROYAUME_EAU = np.array((123, 125, 123), np.float32)


def grille_sud(g, f, reste):
    """Grille du sud (250 × 560, ligne 0 = sud) posée dans la toile à f px par hex, nord en haut (float 0/1)."""
    m = np.zeros((H * f + reste, W * f), np.float32)
    b = np.repeat(np.repeat(g[::-1].astype(np.float32), f, 0), f, 1)
    m[(H - SUD) * f:H * f] = b
    if reste:
        m[H * f:] = b[-1:]
    return m


def refleter(a, f):
    """Reflet d'Athel Loren dans la bande du sud : rangée p' <- REFLET_PX·f − 1 − p (le reste de `a` est inchangé)."""
    out = a.copy()
    p2 = np.arange((H - SUD) * f, a.shape[0])
    p = REFLET_PX * f - 1 - p2
    ok = (p >= 0) & (p < a.shape[0])
    out[p2[ok]] = a[p[ok]]
    return out


_REVES = {}


def bois_reveur(f, reste):
    """(poids du reflet, reflet net, lisière 0..1, voile) à f px par hex."""
    if (f, reste) in _REVES:
        return _REVES[(f, reste)]
    g = np.load(REVES)
    # (4.10.2026 : un bord organique a été essayé puis retiré : l'éther est de la MER dans la grille, le contour de l'île
    # en jeu est celui de la grille de l'Atlas ; l'élargir dans les seuls rasters poserait de la terre sur des cases de mer)
    terre = grille_sud(g["terre"] & ~g["voile"], f, reste)
    net = terre > 0.5
    poids = np.clip(cv2.GaussianBlur(terre, (0, 0), 0.75 * f) * 1.3 - 0.15, 0, 1)
    b = cv2.GaussianBlur(terre, (0, 0), 1.5 * f)
    lisiere = np.clip(b * (1 - b) * 4, 0, 1)
    voile = grille_sud(g["voile"], f, reste) > 0.5
    _REVES[(f, reste)] = (poids.astype(np.float32), net, lisiere.astype(np.float32), voile)
    return _REVES[(f, reste)]


def ether_sud(f, reste, poids, voile):
    """Poids de l'éther (18 h 35, premier aperçu : l'éther en plaine verte se lisait comme une terre vide) : dans la bande
    du sud, hors du reflet et du voile, une mer d'éther sombre et violette, où le reflet flotte comme une île.
    (3.10.2026) plus LA DÉCHIRURE (`abime`) : le voile et le bord sud des Voûtes deviennent l'éther."""
    sud = grille_sud(np.ones((SUD, W), bool), f, reste)
    abi, chaussee = abime(f, reste)
    # (4.10.2026, aperçu du Bois Rêveur : des grains de terre clairs en chapelet tout le long du bas du voile, coupés à la
    # règle) la déchirure, déchiquetée au pixel, laissait des trous dans le voile, où ni elle ni l'éther du sud (hors voile)
    # ne passaient : le relief du voile y restait de la terre. Tout le voile est éther (sauf la chaussée du fil caché),
    # fondu contre la terre reflétée comme l'éther du sud
    voile_eth = voile & ~chaussee
    return np.maximum(np.maximum(sud * (1 - poids) * (~voile), abi), voile_eth * (1 - poids)).astype(np.float32)


# LA DÉCHIRURE (3.10.2026 ; Atlas : « le vélin de la carte, brûlé par le sud, s'ouvre sur le vélin pourpre… bord déchiré à
# toutes les échelles » ; Charles : « une autre dimension ») : le voile était une fosse sèche tirée à la règle, et les Voûtes
# s'y arrêtaient en mur droit (rangée 250). Désormais le voile est de l'éther, et le bord sud des Voûtes une falaise au
# tracé déchiqueté (jusqu'à DECHIRURE_HEX dans le massif), qui plonge dans l'éther ; seulement sur des cases FERMÉES, à
# plus d'un hex de tout passage. Le fil de rivière caché (passage de jeu qui relie le Bois Rêveur) reste une chaussée
# étroite, au-dessus de l'eau : le terrain ne cache pas un passage.
DECHIRURE_HEX = 14
CHAUSSEE = 0.12
_ABIME = {}


def abime_hex():
    """(abîme, chaussée) en cases de la grille (rangée 0 = sud)."""
    if "hex" in _ABIME:
        return _ABIME["hex"]
    rv = np.load(REVES)
    voile = np.zeros((H, W), bool)
    voile[:rv["voile"].shape[0], :W] = rv["voile"]
    _, imp = read_layer(os.path.join(ICI, r"couches-expanded\villes-sortie\layer_impassable.hex_layer"))
    passe = imp.reshape(H, W) == 1
    chaussee = voile & passe
    rng = np.random.default_rng(31)
    # profondeur de la déchirure le long du bord : bruit lent et vif, de 1 à DECHIRURE_HEX hex
    lent = cv2.GaussianBlur(rng.standard_normal((1, W)).astype(np.float32), (0, 0), 9)[0]
    vif = cv2.GaussianBlur(rng.standard_normal((1, W)).astype(np.float32), (0, 0), 2)[0]
    moyen = cv2.GaussianBlur(rng.standard_normal((1, W)).astype(np.float32), (0, 0), 4)[0]
    # (premier essai : bord presque droit, dents régulières) : anses et éperons (lent), festons (moyen), déchiquetures (vif)
    prof = 1 + (DECHIRURE_HEX - 1) * np.clip(0.45 + 0.35 * lent / (lent.std() + 1e-6) + 0.2 * moyen / (moyen.std() + 1e-6)
                                             + 0.12 * vif / (vif.std() + 1e-6), 0, 1)
    rangs = np.arange(H)[:, None]
    bande = (rangs >= SUD) & (rangs < SUD + prof[None, :])
    loin_passage = ~cv2.dilate(passe.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))).astype(bool)
    abime = (voile & ~chaussee) | (bande & ~passe & loin_passage)
    _ABIME["hex"] = (abime, chaussee)
    print(f"  déchirure : {int(abime.sum())} cases d'éther (voile {int((voile & ~chaussee).sum())}), "
          f"chaussée du fil caché : {int(chaussee.sum())} cases")
    return _ABIME["hex"]


def abime(f, reste):
    """(abîme, chaussée) à f px par hex, nord en haut, bord déchiqueté au pixel (bruit de ±0,6 hex)."""
    if (f, reste) in _ABIME:
        return _ABIME[(f, reste)]
    a, c = abime_hex()
    out = []
    for m in (a, c):
        p = np.repeat(np.repeat(m[::-1].astype(np.float32), f, 0), f, 1)
        if reste:
            p = np.concatenate([p, np.repeat(p[-1:], reste, 0)])
        out.append(p)
    hh, ww = out[0].shape
    rng = np.random.default_rng(32)
    gx, gy = np.meshgrid(np.arange(ww, dtype=np.float32), np.arange(hh, dtype=np.float32))
    jx = np.zeros((hh, ww), np.float32)
    jy = np.zeros((hh, ww), np.float32)
    for pas, ampl in ((3.0, 0.9), (1.0, 0.45), (0.35, 0.2)):          # hex : déchiré à toutes les échelles
        gh, gw = int(hh / (pas * f)) + 2, int(ww / (pas * f)) + 2
        jx += cv2.resize(rng.standard_normal((gh, gw)).astype(np.float32), (ww, hh), interpolation=cv2.INTER_CUBIC) * ampl * f
        jy += cv2.resize(rng.standard_normal((gh, gw)).astype(np.float32), (ww, hh), interpolation=cv2.INTER_CUBIC) * ampl * f
    abi = cv2.remap(out[0], gx + jx, gy + jy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    abi = (cv2.GaussianBlur(abi, (0, 0), 0.3 * f) > 0.5).astype(np.float32) * (1 - out[1])
    _ABIME[(f, reste)] = (abi, out[1] > 0.5)
    return _ABIME[(f, reste)]


ETHER_FOND, ETHER_SURFACE = -1.2, 0.02
ETHER_EAU = np.array((46, 20, 68), np.float32)        # couleur de l'eau d'éther (color_overlay_sea)
ETHER_LIT = np.array((58, 36, 72), np.float32)        # lit de l'éther (color_overlay)


# COUTURES TERRE / MER (décision de Charles, 25.09.2026, 19 h : « dans Expanded, c'est l'Atlas qui gagne ») : trois régions
# de l'Atlas débordent dans le cadre de WH1 (expanded_declaration.json, conflits_terre_mer_wh1) : l'Île Silencieuse (lab 31)
# sur la mer de WH1, la Baie Moussille (labm 3) et Manaanspoort (labm 9) sur la bordure de décor de WH1. Convention de WH1
# relevée : mer = `height` plat à 0,02 et fond dans `sea_height` (≈ −0,97) ; terre = `sea_height` bien sous `height`.
DECLARATION = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\expanded_declaration.json")
REGIONS_ATLAS = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\extension_regions.npz")


def coutures(f, reste):
    """(poids de la terre à lever, poids de la mer à creuser), dans le cadre de WH1 seulement, à f px par hex."""
    import json
    d = json.load(open(DECLARATION, encoding="utf-8"))
    r = np.load(REGIONS_ATLAS)
    lever = np.zeros((NH_ATLAS, W), bool)
    creuser = np.zeros((NH_ATLAS, W), bool)
    for c in d["conflits_terre_mer_wh1"]:
        gr = next(x for x in d["regions"] if x["cle_jeu"] == c["cle_jeu"])["grille"]
        m = r[gr["couche"]] == gr["valeur"]
        (lever if c["atlas"] == "terre" else creuser)[...] |= m
    # (4.10.2026, Charles : « naturel, cohérent et joli » ; gros plans des raccords) : fondu sur 0,6 hex et coupé net au bord
    # du cadre, la couture faisait une côte en marches d'hex et une île tranchée d'un trait sur la ligne du cadre (îlot du
    # golfe du Bidouze). Désormais : fondu sur COUTURE_FLOU hex, côte rendue irrégulière par un bruit doux (±COUTURE_BRUIT
    # du seuil, ~1 hex), et cadre adouci sur 3 hex de part et d'autre (dehors, la même côte de l'Atlas : rien ne change)
    cm = cv2.GaussianBlur(cv2.dilate(cadre_masque(f, reste).astype(np.uint8), np.ones((4 * f, 4 * f), np.uint8))
                          .astype(np.float32), (0, 0), 1.5 * f)
    rng = np.random.default_rng(4102026)
    br = habillage_expanded.bruit((H * f + reste, W * f), 3 * f, rng)
    toile = []
    for m in (lever, creuser):
        t = np.zeros((H * f + reste, W * f), np.float32)
        t[:NH_ATLAS * f] = np.repeat(np.repeat(m[::-1].astype(np.float32), f, 0), f, 1)
        t = cv2.GaussianBlur(t, (0, 0), COUTURE_FLOU * f)
        t = np.clip((t - 0.5 + COUTURE_BRUIT * br) * 2.2 + 0.5, 0, 1) * (t > 0.02)
        toile.append(t * cm)
    return toile


COUTURE_FLOU = 1.2
COUTURE_BRUIT = 0.22


# (4.10.2026, gros plans des raccords : « crête droite » au sud-ouest) la bordure décorative de la carte de WH1, reprise
# par l'Atlas en bandeau de montagnes INFRANCHISSABLES (terre sauvage, sol « mountain », altitude d'Atlas ~7,5 à 8 sur
# des dizaines d'hex), donnait après érosion une arête rectiligne le long du bord du cadre. La barrière de jeu reste (les
# cases ne changent pas) ; seul le relief de ces cases change : au-dessus d'un niveau de base (le relief prolongé
# depuis les cases voisines hors du bandeau), l'amplitude varie le long de la crête (sommets, cols visuels) et décroît
# vers les bords du bandeau selon une distance bruitée (contreforts irréguliers). Jamais sur une case franchissable.
CRETE_BANDE_HEX = 26        # distance au bord du cadre de WH1 dans laquelle on cherche le bandeau
CRETE_RAMPE_HEX = 5.0
CRETE_MIN = 0.45


def crete_bord(height, f, reste):
    from caime_layers import read_layer as _rl
    S = os.path.join(ICI, r"couches-expanded\villes-sortie")
    imp = _rl(os.path.join(S, "layer_impassable.hex_layer"))[1].reshape(H, W)[::-1]
    gt8, sols = sols_grille(f, reste)
    montagne = np.array([n == "mountain" for n in sols] + [False])[np.where(gt8 < 0, len(sols), gt8)]
    ferme = np.repeat(np.repeat(imp == 0, f, 0), f, 1)
    ferme = np.concatenate([ferme, np.repeat(ferme[-1:], reste, 0)]) if reste else ferme
    cm = cadre_masque(f, reste).astype(np.uint8)
    pres_bord = (cv2.distanceTransform(cm, cv2.DIST_L2, 5) / f <= CRETE_BANDE_HEX) & cm.astype(bool)
    # montagnes hautes seulement (jamais les îles ni les côtes basses) ; masque à la case ADOUCI avant tout usage (la
    # première version, appliquée case par case, faisait des marches d'hex : gros plan du 4.10, 13 h 15)
    bande = ferme & montagne & pres_bord & ~garde_masque(f, reste) & ~montagnes_gardees(f, reste) & (height > 1.5)
    if not bande.any():
        return height, 0
    wb = cv2.GaussianBlur(cv2.erode(bande.astype(np.uint8), np.ones((f, f), np.uint8)).astype(np.float32), (0, 0),
                          1.2 * f)
    base = remplir_lisse(height, wb < 0.05)
    base = cv2.GaussianBlur(base, (0, 0), 3 * f)
    d = cv2.distanceTransform((wb > 0.5).astype(np.uint8), cv2.DIST_L2, 5) / f
    rng = np.random.default_rng(41026)
    n1 = habillage_expanded.bruit(height.shape, 6 * f, rng)
    n2 = habillage_expanded.bruit(height.shape, 14 * f, rng)
    t = np.clip((d + 2.5 * n1) / CRETE_RAMPE_HEX, 0, 1)
    t = t * t * (3 - 2 * t)
    s = np.clip(CRETE_MIN + (1 - CRETE_MIN) * t, 0, 1) * np.clip(0.8 + 0.45 * n2, 0.5, 1.15)
    s = cv2.GaussianBlur(s.astype(np.float32), (0, 0), 1.5 * f)
    nouveau = base + np.maximum(height - base, 0) * s + np.minimum(height - base, 0)
    # jamais au-dessus du relief d'avant (on n'élève rien) ; fondu continu (wb), sans masque à la case
    nouveau = np.minimum(nouveau, height)
    return (height * (1 - wb) + nouveau * wb).astype(np.float32), int(bande.sum() / f / f)


# (4.10.2026, gros plans des raccords : côtes en marches d'hex le long de la zone gardée de WH1 et des coutures, îlot du
# Bidouze à moitié en escalier) : passe finale de LISSAGE DES CÔTES hors de la partie jouable de WH1 (qui reste à 100 %
# celle de WH1) : le masque de mer est flouté sur COTE_FLOU hex et seuillé avec un bruit doux (côte irrégulière, ~0,3
# hex) ; une case de terre qui passe en mer descend à la surface de la mer, une case de mer qui passe en terre monte à
# COTE_TERRE au moins ; le fond de mer suit.
COTE_FLOU = 0.9
COTE_BRUIT = 0.12
COTE_TERRE = 0.08


def lisser_cotes(height, sea, f, reste, h_bord):
    # protégée : la TERRE jouable de WH1 et un hex autour (ses côtes restent celles de WH1) ; la mer jouable de WH1
    # (golfe du Bidouze…) n'est pas protégée : les îles de l'Atlas y ont leur côte lissée
    jou = np.repeat(np.repeat(_GARDE["jouable"][::-1], f, 0), f, 1).astype(bool)
    jou = np.concatenate([jou, np.repeat(jou[-1:], reste, 0)]) if reste else jou
    terre_wh1 = (jou & (h_bord > 0.035)).astype(np.uint8)
    hors = cv2.dilate(terre_wh1, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * f + 1, 2 * f + 1))) == 0
    mer = (height <= 0.035).astype(np.float32)
    rng = np.random.default_rng(41027)
    t = cv2.GaussianBlur(mer, (0, 0), COTE_FLOU * f) + COTE_BRUIT * habillage_expanded.bruit(height.shape, 2 * f, rng)
    nouvelle = t > 0.5
    vers_mer = hors & nouvelle & (mer < 0.5)
    vers_terre = hors & ~nouvelle & (mer > 0.5)
    height = np.where(vers_mer, HAUTEUR_SUR_MER, height)
    height = np.where(vers_terre, np.maximum(height, COTE_TERRE), height)
    sea = np.where(vers_mer, np.minimum(sea, -0.3), sea)
    sea = np.where(vers_terre, height - SOUS_TERRE_MER, sea)
    # terrasses en marches d'hex sur les terres basses du littoral (îlot du Bidouze : bord de la zone gardée sous la
    # couture) : sur 2 hex de la mer, la terre basse (< 1,5 u) est fondue dans sa version lissée sur 0,8 hex
    terre = height > 0.035
    pres_mer = cv2.distanceTransform(terre.astype(np.uint8), cv2.DIST_L2, 5) < 2 * f
    lisse = cv2.GaussianBlur(np.where(terre, height, COTE_TERRE).astype(np.float32), (0, 0), 0.8 * f)
    # poids fondu (pas de limite nette, qui laissait un anneau) : 1 au rivage, 0 à 2 hex ; décroît aussi vers 1,5 u
    dist = cv2.distanceTransform(terre.astype(np.uint8), cv2.DIST_L2, 5) / f
    wz = np.clip(1 - dist / 2.0, 0, 1) * np.clip((1.5 - height) / 0.7, 0, 1) * hors * terre
    wz = cv2.GaussianBlur(wz.astype(np.float32), (0, 0), 0.5 * f) * terre
    height = np.where(terre, height * (1 - wz) + np.maximum(lisse, COTE_TERRE) * wz, height)
    return height.astype(np.float32), sea.astype(np.float32), int(vers_mer.sum() + vers_terre.sum())


def sols_grille(f, reste):
    """Types de sol de la grille CAIME d'Expanded (index à plat) à f px par hex, nord en haut."""
    noms, _, _ = caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))
    sols = flat_names(noms, "GroundTypes")
    _, gt = read_layer(os.path.join(ICI, "couches-expanded", "layer_groundtypes.hex_layer"))
    gt = gt.reshape(H, W)[::-1]
    g = np.repeat(np.repeat(gt, f, 0), f, 1)
    g = np.concatenate([g, np.repeat(g[-1:], reste, 0)]) if reste else g
    return g, sols


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if os.path.exists(DST):
        shutil.rmtree(DST)                     # bac à sable du chantier : refait à chaque passage
    os.makedirs(DST)
    # (5.10.2026, fleuves en jeu : « un énorme trou béant… pas d'eau sur la voie navigable ») les copies des couches de la
    # grille que lit ce chantier (couches-expanded, villes-sortie) dataient d'avant le lot des fleuves : refaites depuis
    # le map.hex avant tout
    import couches_a_jour
    couches_a_jour.rafraichir()
    # ---- rasters
    tifs = {os.path.basename(p).split(".")[1]: p for p in glob.glob(os.path.join(SRC, f"{SOURCE_CLE}.*.tif"))}
    lus = {k: np.asarray(Image.open(p)) for k, p in tifs.items()}
    modes = {k: Image.open(p).mode for k, p in tifs.items()}
    palettes = {k: Image.open(p).getpalette() for k, p in tifs.items() if modes[k] == "P"}
    # relief : Saison telle quelle dans le cadre ; Atlas dehors, raccordé hors du cadre vers le bord de la Saison
    h_s = lus["height"].astype(np.float32)
    f, reste = 8, h_s.shape[0] - SH * 8
    # (3.10.2026) relief v4 de l'Atlas : montagnes par érosion fluviale avec soulèvement, vallées de jeu creusées
    # (`relief_alpin.py`) ; la v3 (`relief_atlas`) faisait des montagnes en « marbre fondu »
    atlas, _ = relief_alpin.relief(8, 7, 1.0)                            # NH_ATLAS·8 rangées, nord en haut
    h_a = np.full((H * f + reste, W * f), ETHER_FOND, np.float32)       # bande du sud (Bois Rêveur) : fond d'éther
    h_a[:atlas.shape[0], :atlas.shape[1]] = atlas
    cadre = garde_masque(f, reste)          # 20 h : la zone gardée de WH1, plus tout le cadre (bordure de l'Atlas)
    h_bord = agrandir(h_s, f, 0.0, reste)
    # RACCORD NATUREL (Charles, 17 h 55 : « que la map de WH1 déboule naturellement, sans bordure ») : le relief de WH1
    # descend doucement vers ses bords, sans mur (mesure `bords_wh1.py`) ; on le prolonge hors du cadre par un remplissage
    # lisse (push-pull, aucune rayure), puis on le fond dans celui de l'Atlas en smoothstep sur RACCORD_HEX hex.
    prolonge = remplir_lisse(h_bord, cadre)
    d = cv2.distanceTransform((~cadre).astype(np.uint8), cv2.DIST_L2, 5) / f
    # 21 h 10 (profil de l'est : plateau des Grises à 10-14 u, puis chute de 10 u sur 6 hex vers la plaine du Reikland) :
    # largeur du raccord proportionnelle à l'écart d'altitude, pente limitée à PENTE_MAX_RACCORD u par hex (les versants
    # de WH1 : ~0,6), jamais moins de RACCORD_HEX ; largeur lissée pour ne pas dessiner de lignes
    largeur = np.maximum(RACCORD_HEX, np.abs(prolonge - h_a) / PENTE_MAX_RACCORD)
    largeur = cv2.GaussianBlur(largeur.astype(np.float32), (0, 0), 6 * f)
    t = np.clip(d / largeur, 0, 1)
    w = t * t * (3 - 2 * t)
    # 21 h 25 (Tor Martel noyée à 72 %) : là où le prolongement de WH1 est de la MER et l'Atlas de la TERRE (îles au
    # large du golfe du Bidouze), la côte est celle de l'Atlas : pas de raccord
    w = np.where((h_a > 0.05) & (prolonge <= 0.05), 1.0, w)
    height = np.where(cadre, h_bord, prolonge * (1 - w) + h_a * w).astype(np.float32)
    # (3.10.2026, Charles : « trop pixelisé… tout smooth ») : le bord de la zone gardée de WH1 suit les cases, d'où des
    # escarpements en dents de scie et des marches droites (sud d'Athel Loren, clairière d'Arranoc). Dans la marge de
    # décor de WH1 (jamais sur ses régions jouables), le relief de WH1 cède en douceur, sur 2,5 hex, à sa version lissée,
    # qui se raccorde sans marche au prolongement de l'extérieur.
    jou = np.repeat(np.repeat(_GARDE["jouable"][::-1], f, 0), f, 1)
    jou = np.concatenate([jou, np.repeat(jou[-1:], reste, 0)]) if reste else jou
    din = cv2.distanceTransform(cadre.astype(np.uint8), cv2.DIST_L2, 5) / f
    gw = np.clip(din / 2.5, 0, 1)
    gw = np.maximum(gw * gw * (3 - 2 * gw), jou.astype(np.float32))
    hs = cv2.GaussianBlur(prolonge, (0, 0), 1.5 * f)
    height = np.where(cadre, h_bord * gw + hs * (1 - gw), height).astype(np.float32)
    # 22 h 10 (trait droit dans les Grises de l'est, rangée 532 : bord de la zone gardée, relief fin de WH1 d'un côté,
    # remplissage lisse de l'autre) : dans le cadre de WH1, hors de la zone gardée, le DÉTAIL de WH1 (relief moins sa
    # version floutée sur 2 hex) est rendu au raccord, et s'efface à mesure que l'Atlas l'emporte (1 − w) ; pas sur le
    # rebord de carte de WH1 (REBORD_WH1_HEX), dont le détail est la chute vers le bord
    # (5.10.2026, contrôle des marches : lignes droites et escaliers d'hex de 0,6 à 2 u dans la bordure remplacée, mêmes
    # endroits que dans le relief de WH1 (89, 44, 68… marches) : dans la Saison, ses maillages de montagne les couvrent ;
    # ici, ces objets sont retirés de la bordure) le détail de WH1 est pris sur son relief aux marches fondues
    hb_d = h_bord
    for _ in range(2):
        mh = np.zeros(h_bord.shape, bool)
        mh[:-1] |= np.abs(np.diff(hb_d, axis=0)) > 0.25
        mh[:, :-1] |= np.abs(np.diff(hb_d, axis=1)) > 0.25
        pm = np.clip(cv2.GaussianBlur(cv2.dilate(mh.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32),
                                      (0, 0), 1.5) * 1.5, 0, 1)
        hb_d = (hb_d * (1 - pm) + cv2.GaussianBlur(hb_d, (0, 0), 2.0) * pm).astype(np.float32)
    detail = np.clip(hb_d - cv2.GaussianBlur(hb_d, (0, 0), 2 * f), -1.5, 1.5)
    dedans = np.zeros_like(cadre)
    y0, x0, b = DYH_HAUT * f, DXH * f, REBORD_WH1_HEX * f
    dedans[y0 + b:y0 + SH * f - b, x0 + b:x0 + SW * f - b] = True
    dedans = cv2.GaussianBlur(dedans.astype(np.float32), (0, 0), 2 * f)
    # (4.10.2026, gros plan (440, 408) : mur droit de 0,4 à 0,55 u PILE sur le bord de la zone gardée, en escalier d'hex)
    # deux ruptures s'additionnaient au bord : dedans, la marge de décor cède à `hs` (prolongement flouté), dehors on
    # repartait du prolongement NET ; et le détail de WH1 rendu dehors commençait à plein dès le premier pixel. Désormais,
    # dehors, sur RACCORD_BORD_HEX : la base part de ce que le bord intérieur affiche (moyenne locale de gw : WH1 net sur
    # le jouable, `hs` sur la marge) et rejoint le prolongement ; le détail entre en smoothstep
    gwn = (cv2.GaussianBlur(np.where(cadre, gw, 0).astype(np.float32), (0, 0), 0.75 * f)
           / np.maximum(cv2.GaussianBlur(cadre.astype(np.float32), (0, 0), 0.75 * f), 1e-3))
    kb = np.clip(d / RACCORD_BORD_HEX, 0, 1)
    kb = kb * kb * (3 - 2 * kb)
    base_bord = prolonge * gwn + hs * (1 - gwn)
    height = np.where(cadre, height, height + (base_bord - prolonge) * (1 - kb) * (1 - w)).astype(np.float32)
    height = np.where(cadre, height, height + detail * (1 - w) * dedans * kb).astype(np.float32)
    # (5.10.2026) sous les montagnes de WH1 gardées (maillages drapés sur le relief de WH1) : le relief de WH1, exact sous
    # leur rectangle élargi d'un hex, fondu sur ~2 hex autour ; jamais hors du cadre de WH1 (son relief n'y existe pas)
    mg = montagnes_gardees(f, reste) & cadre_masque(f, reste)
    w_mg = np.clip(cv2.GaussianBlur(mg.astype(np.float32), (0, 0), 1.0 * f) * 2.0, 0, 1) * cadre_masque(f, reste)
    w_mg[mg] = 1.0
    height = (height * (1 - w_mg) + h_bord * w_mg).astype(np.float32)
    # le Bois Rêveur : relief de WH1 d'Athel Loren, reflété, fondu dans l'éther sur ~1 hex
    poids_r, net_r, lisiere_r, voile_r = bois_reveur(f, reste)
    height = (height * (1 - poids_r) + refleter(h_bord, f) * poids_r).astype(np.float32)
    print(f"  Bois Rêveur : {int(net_r.sum() / f / f)} hex reflétés, voile de {int(voile_r.sum() / f / f)} hex")
    # la mer de l'extension (sols de mer de la grille) : surface à HAUTEUR_SUR_MER, fond = relief (négatif)
    gt8, sols = sols_grille(f, reste)
    # côtes lissées (17 h 55 : la mer de la grille, case par case, faisait des côtes en marches) : masque de mer flouté
    # sur ~1,2 hex puis seuillé à 0,5 (le tracé suit la côte de l'Atlas sans les angles de l'hex)
    mer_brut = np.array([n.startswith("sea") for n in sols] + [False])[np.where(gt8 < 0, len(sols), gt8)]
    est_mer = (cv2.GaussianBlur(mer_brut.astype(np.float32), (0, 0), 1.2 * f) > 0.5) & ~cadre
    sea = agrandir(lus["sea_height"].astype(np.float32), f, 0.0, reste)
    # 22 h 25 (bande claire, trop peu profonde, le long du cadre : le fond y venait de la SURFACE prolongée de WH1, 0,02,
    # soit −0,1) : c'est le FOND de la mer de WH1 qu'on prolonge, fondu dans celui de l'Atlas avec le même poids w
    mer_g = cadre & (h_bord <= 0.03)
    fond_p = remplir_lisse(sea, mer_g)
    fond = np.minimum(fond_p * (1 - w) + np.minimum(height, -0.1) * w, -0.1)
    sea = np.where(cadre, sea, np.where(est_mer, fond, height - SOUS_TERRE_MER)).astype(np.float32)
    height = np.where(est_mer, HAUTEUR_SUR_MER, height).astype(np.float32)
    # 22 h 35 : LITS DES RIVIÈRES DE L'ATLAS (`rivieres_atlas.py`) hors de la zone gardée de WH1 et de la mer : lit à
    # PROFONDEUR_LIT sous le sol au fil de l'eau (convention de WH1), jamais sous le niveau de la mer ; l'eau (maillages
    # drapés) viendra avec la chaîne d'Expanded
    lit = rivieres_atlas.champ(f, reste) * (~cadre) * (~est_mer)
    height = np.where(lit > 0, np.maximum(height - PROFONDEUR_LIT * lit, np.minimum(height, 0.06)), height).astype(np.float32)
    print(f"  lits de l'Atlas : {int((lit > 0.5).sum() / f / f)} hex creusés")
    # l'eau d'Athel Loren (rivières, étangs), reflétée avec le même poids que le relief
    sea = (sea * (1 - poids_r) + refleter(agrandir(lus["sea_height"].astype(np.float32), f, 0.0, reste), f) * poids_r)
    eth = ether_sud(f, reste, poids_r, voile_r)
    # (3.10.2026) convention de WH1 pour une mer : surface plate à HAUTEUR_SUR_MER dans `height`, fond sous 0 dans
    # `sea_height` ; l'éther avait l'inverse (fond à +0,02), qui aurait masqué ses plans d'eau (eau_expanded)
    sea = (sea * (1 - eth) + ETHER_FOND * eth).astype(np.float32)
    height = (height * (1 - eth) + HAUTEUR_SUR_MER * eth).astype(np.float32)
    _, chaussee = abime(f, reste)
    height = np.where(chaussee, CHAUSSEE, height).astype(np.float32)
    sea = np.where(chaussee, CHAUSSEE - SOUS_TERRE_MER, sea).astype(np.float32)
    # coutures de l'Atlas dans le cadre : l'île levée (relief de l'Atlas, au moins 0,15), les baies creusées (surface 0,02,
    # fond jusqu'à −1, rivage adouci sur la moitié extérieure du fondu)
    w_terre, w_mer = coutures(f, reste)
    ile = np.maximum(h_a, 0.15)
    # (4.10.2026, îlot du Bidouze en terrasses) sous la couture, le relief porte la marche du bord de la zone gardée (mer
    # de WH1 d'un côté, Atlas de l'autre) ; là où le fondu est partiel, elle transparaissait : on fond sur sa version lissée
    sous = np.where((w_terre > 0) & (w_terre < 1), cv2.GaussianBlur(height, (0, 0), 1.2 * f), height)
    height = np.where(w_terre > 0, sous * (1 - w_terre) + ile * w_terre, height)
    sea = np.where(w_terre > 0, sea * (1 - w_terre) + (ile - SOUS_TERRE_MER) * w_terre, sea)
    eau = w_mer > 0.5
    rivage = np.clip(w_mer * 2, 0, 1)
    # rivage : on ne fait que DESCENDRE la terre vers 0,15 u (21 h 35 : là où la mer de l'Atlas était déjà là, le fondu
    # relevait une lisière de mer en fine bande de terre, à l'ouest du golfe)
    rive = height * (1 - rivage) + 0.15 * rivage
    height = np.where(eau, HAUTEUR_SUR_MER, np.where(w_mer > 0, np.minimum(height, rive), height))
    sea = np.where(eau, -0.2 - 0.8 * np.clip((w_mer - 0.5) * 2, 0, 1), sea)
    height, sea = height.astype(np.float32), sea.astype(np.float32)
    # 22 h 20 (trait droit dans la mer, près de l'Île Silencieuse : fond à −0,64 côté Atlas, −1 côté WH1, la baie creusée
    # s'arrêtant au bord du cadre ; la profondeur fonce l'eau, la marche se voit) : sous l'eau, le fond est lissé sur
    # ±6 hex de part et d'autre du bord du cadre (moyenne floutée des seules cases d'eau)
    cm = cadre_masque(f, reste).astype(np.uint8)
    bord = np.minimum(cv2.distanceTransform(cm, cv2.DIST_L2, 5), cv2.distanceTransform(1 - cm, cv2.DIST_L2, 5)) / f
    sous_eau = (height <= 0.03).astype(np.float32)
    lisse = cv2.GaussianBlur(sea * sous_eau, (0, 0), 3 * f) / np.maximum(cv2.GaussianBlur(sous_eau, (0, 0), 3 * f), 1e-3)
    t_b = np.clip(1 - bord / 6, 0, 1)
    t_b = (t_b * t_b * (3 - 2 * t_b)) * sous_eau
    sea = np.where(t_b > 0, sea * (1 - t_b) + np.minimum(lisse, -0.1) * t_b, sea).astype(np.float32)
    print(f"  coutures de l'Atlas : {int((w_terre > 0.5).sum() / f / f)} hex levés, {int(eau.sum() / f / f)} hex creusés")
    height, n_crete = crete_bord(height, f, reste)
    sea = np.where(height > 0.035, np.minimum(sea, height - SOUS_TERRE_MER), sea).astype(np.float32)
    print(f"  bordure de WH1 en bandeau de montagnes : {n_crete} hex de crête rendus irréguliers")
    height, sea, n_cote = lisser_cotes(height, sea, f, reste, h_bord)
    print(f"  côtes lissées hors de la partie jouable de WH1 : {n_cote} px changés")
    # (4.10.2026, controle_anomalies) a. une rangée à −1,2 sous l'éther (rangée 224, bas du voile : fond d'éther laissé
    # dans `height` au lieu de la surface) : hors de la zone gardée, aucune SURFACE sous le niveau de la mer ;
    # b. murs côtiers (relief de l'Atlas qui tombe à pic dans la mer, nord de la Lyonesse, côte nord) : au bord de la mer,
    # pente plafonnée à PENTE_COTE u par px (falaise franche mais pas un mur), hors du Bois Rêveur (lisière d'un autre
    # monde, voulue) et de la terre jouable de WH1
    g8 = garde_masque(f, reste)
    # (4.10.2026, aperçu de la Lyonesse : deux creux CARRÉS d'un hex au fond d'une anse, à plat au niveau de l'eau) des
    # cuvettes du relief de l'Atlas sous la mer, sur des cases que la grille dit TERRE ; relevées à plat ci-dessous, elles
    # faisaient de petits étangs carrés sans eau. Toute cuvette basse (< BAS_CUVETTE) hors de WH1 qui ne touche ni la mer
    # ni l'éther est comblée par le sol qui l'entoure (remplissage lisse), au-dessus de l'eau
    # (premier passage : 1 px seulement ; les creux de la Lyonesse sont reliés à l'anse par une bande basse) au pixel :
    # bas, à plus d'un hex de toute mer de la GRILLE et de l'éther, hors des lits et des baies creusées
    eau_vraie = (mer_brut | (eth > 0.5) | eau).astype(np.uint8)
    # (4.10.2026, fosses en hex au bout des bras de mer du nord-ouest, (94, 821) et (95, 820) : hex de TERRE de la grille,
    # creux du relief de l'Atlas collés à l'anse, épargnés par cette marge d'un hex, puis relevés à 0,02 et pris pour de
    # la mer par l'adoucissement des murs côtiers, qui en faisait des hexagones) marge de 2 px : le trait de côte reste
    # épargné, les creux qui touchent une anse sont comblés
    eau_vraie = cv2.dilate(eau_vraie, np.ones((5, 5), np.uint8)) > 0
    cuvette = ~g8 & (height < BAS_CUVETTE) & (lit <= 0) & ~eau_vraie
    if cuvette.any():
        comble = remplir_lisse(height, ~cuvette)
        height = np.where(cuvette, np.maximum(comble, BAS_CUVETTE), height).astype(np.float32)
        sea = np.where(cuvette, np.minimum(sea, height - SOUS_TERRE_MER), sea).astype(np.float32)
    print(f"  cuvettes sous la mer comblées (hors WH1, loin de l'eau) : {int(cuvette.sum())} px")
    trou = ~g8 & (height < HAUTEUR_SUR_MER)
    height = np.where(trou, HAUTEUR_SUR_MER, height).astype(np.float32)
    sea = np.where(trou, np.minimum(sea, -0.3), sea).astype(np.float32)
    mer8 = (height <= 0.035).astype(np.uint8)
    dist = cv2.distanceTransform(1 - mer8, cv2.DIST_L2, 5)
    plafond = 0.06 + PENTE_COTE * dist
    monde = np.ones_like(g8)
    monde[(H - SUD) * f:] = False                                   # rangées < SUD : le Bois Rêveur
    trop = monde & ~g8 & (mer8 == 0) & (height > plafond)
    height = np.where(trop, plafond, height).astype(np.float32)
    sea = np.where(trop, np.minimum(sea, height - SOUS_TERRE_MER), sea).astype(np.float32)
    print(f"  surfaces sous la mer relevées : {int(trou.sum())} px ; murs côtiers adoucis : {int(trop.sum())} px")
    # (4.10.2026, controle_anomalies, gros plan (397, 232)) : des grains de terre de 2 à 3 px flottaient dans l'éther au nord
    # du Bois Rêveur (restes de la déchirure) ; hors de la zone gardée de WH1, toute terre de moins de GRAIN_MAX_PX px
    # entourée d'eau rentre sous la surface (les îles de l'Atlas, Landri comprise, font des centaines de px)
    n_c, lab_c, st_c, _ = cv2.connectedComponentsWithStats((height > 0.035).astype(np.uint8), connectivity=8)
    petits = np.flatnonzero(st_c[:, cv2.CC_STAT_AREA] < GRAIN_MAX_PX)
    grains = np.isin(lab_c, petits[petits > 0]) & ~g8
    height = np.where(grains, HAUTEUR_SUR_MER, height).astype(np.float32)
    sea = np.where(grains, np.minimum(sea, -0.3), sea).astype(np.float32)
    print(f"  grains de terre isolés rentrés sous l'eau : {int(grains.sum())} px")
    # (5.10.2026, fleuves en jeu : trou sans eau, terre de WH1 à 0,8 u et fond à −2,1 u sur le chenal) le chenal des
    # fleuves navigables et ses berges à la manière de CA (`chenaux_fleuves.py`), partout, zone gardée de WH1 comprise ;
    # la différence de relief recale ensuite les objets et les rubans de WH1 des berges
    import chenaux_fleuves
    height, sea, delta_ch, b_ch = chenaux_fleuves.relief(height, sea, f, reste, montagnes_gardees(f, reste))
    os.makedirs(os.path.dirname(chenaux_fleuves.DELTA), exist_ok=True)
    np.savez_compressed(chenaux_fleuves.DELTA, delta=delta_ch.astype(np.float16))
    print(f"  fleuves navigables : chenal {b_ch['chenal_hex']} hex (fond {chenaux_fleuves.FOND_CHENAL}) ; berges abaissées "
          f"{b_ch['berges_px']} px (jusqu'à {b_ch['abaissement_max_u']:.2f} u) ; embouchures {b_ch['embouchure_px']} px ; "
          f"épargné sous les montagnes de WH1 : {b_ch['epargne_px']} px")
    ecrits = {"height": height, "sea_height": sea}
    # autres rasters : la Saison dans le cadre, une valeur de l'extension autour
    for k, a in lus.items():
        if k in ecrits:
            continue
        if k == "patch_visibility_mask":
            # (3.10.2026) guide Terry : une case par parcelle de p pixels de la carte des tuiles, p = plafond(plus grand
            # côté / 128), (largeur // p) × (hauteur // p) cases ; Saison : 800 × 881, p = 7, 114 × 125 ; Expanded :
            # 1120 × 1811, p = 15, 74 × 120 (on écrivait 160 × 259, d'après des pavés de 28 px, faux hors de la Saison)
            lt, ht = W * 2, H * 2 + 1
            p = -(-max(lt, ht) // 128)
            ecrits[k] = np.full((ht // p, lt // p), 255, np.uint8)
            continue
        f_k = a.shape[1] // SW
        reste_k = a.shape[0] - SH * f_k
        g_k = garde_masque(f_k, reste_k)
        if g_k.ndim < a.ndim:
            g_k = g_k[..., None]
        if k == "height_shroud":
            ecrits[k] = np.where(g_k, agrandir(a, f_k, 1.0, reste_k), 1.0).astype(a.dtype)
        elif k in ("color_overlay", "color_overlay_sea"):
            # (3.10.2026) tissées depuis la Saison, type de sol par type de sol, fondues entre types (habillage_expanded)
            hab, cat = habillage_expanded.habiller(k, a, f_k, reste_k)
            hab = habillage_expanded.fondre_couleur(hab, cat, f_k)
            if k == "color_overlay_sea":
                # (aperçu du 3.10 : la mer tissée était tachetée en carrés) : la couleur de l'eau, lissée sur ~6 hex
                hab = cv2.GaussianBlur(hab.astype(np.float32), (0, 0), 6 * f_k).astype(a.dtype)
            # (4.10.2026, aperçus : LIGNE DROITE dans la mer à l'ouest du golfe du Bidouze, et le long du bord est du cadre
            # sur la terre : la couleur de WH1 coupée net au bord de la zone gardée) la couleur de WH1 se fond dans celle
            # de l'extension, à l'intérieur de la zone gardée : FONDU_EAU_HEX pour l'eau, FONDU_SOL_HEX pour le sol
            din = cv2.distanceTransform(g_k[..., 0].astype(np.uint8), cv2.DIST_L2, 5) / f_k
            wg = np.clip(din / (FONDU_EAU_HEX if k == "color_overlay_sea" else FONDU_SOL_HEX), 0, 1)
            wg = (wg * wg * (3 - 2 * wg))[..., None]
            ecrits[k] = (agrandir(a, f_k, 0, reste_k).astype(np.float32) * wg
                         + hab.astype(np.float32) * (1 - wg)).astype(a.dtype)
        elif k in ("snow_mask",):
            # (3.10.2026) neige des hauts sommets de l'extension (Voûtes, Grises de l'Atlas), au masque comme les Empires
            h_k = cv2.resize(height, (W * f_k, H * f_k + reste_k), interpolation=cv2.INTER_AREA)
            sommets = habillage_expanded.neige(h_k, f_k, np.random.default_rng(5))
            ecrits[k] = np.where(g_k, agrandir(a, f_k, 0, reste_k), sommets).astype(a.dtype)
        elif k == "corruption_mask":
            bas = int(np.percentile(a, 10))
            ecrits[k] = np.where(g_k, agrandir(a, f_k, bas, reste_k), bas).astype(a.dtype)
        elif k in ("blend", "tree"):
            # (3.10.2026) jusqu'ici : la valeur la plus fréquente de la Saison par type de sol (des aplats). Désormais
            # tissés depuis la matière de la Saison, type par type (habillage_expanded) ; éboulis sur les pentes des
            # montagnes, aucun arbre sur la roche ni sur les hauts sommets
            hab, cat = habillage_expanded.habiller(k, a, f_k, reste_k)
            sols_e = habillage_expanded._sols()[2]
            h_k = cv2.resize(height, (W * f_k, H * f_k + reste_k), interpolation=cv2.INTER_AREA)
            if k == "blend":
                hab, roc = habillage_expanded.montagnes(hab, h_k, f_k, cat, sols_e, np.random.default_rng(9))
                # (3.10.2026) la carte des textures de WH1 du MONDE ENTIER, pour la réécriture d'après BOB
                # (textures_sol_wh1.appliquer lit celle de WH1, 400 × 440) : la Saison à sa place, l'extension tissée
                # avec le même tirage que `blend` (mêmes fenêtres, mêmes cellules), 255 sur les éboulis (gardés tels que
                # BOB les compile) ; le Bois Rêveur est reflété plus bas, comme les autres rasters
                wh1 = np.fromfile(WH1_BLEND, np.uint8, count=a.shape[0] * a.shape[1], offset=128).reshape(a.shape)[::-1]
                # les textures que WH1 posait par ses tuiles (fonds de mer, plages, lits) : corrigées ICI, aux dimensions
                # de WH1 (textures_tuiles_wh1.corriger ne sait faire que 400 × 440 ; la chaîne d'après BOB d'Expanded
                # ne le refait pas)
                import textures_tuiles_wh1
                wh1_brut = wh1.copy()
                wh1, bilan_t = textures_tuiles_wh1.corriger(wh1)
                print(f"  textures des tuiles de WH1 corrigées : {bilan_t}")
                # (4.10.2026, aperçu du terrain compilé : 5 714 taches pâles de sable de berge (sand_a0) loin de toute eau
                # dans l'extension, les « taches orange-beige informes » relevées par Charles le 24.09) l'extension est
                # tissée depuis le mélange de WH1 SANS les corrections propres aux tuiles (fond de mer, plages, berges et
                # lits, posés là où WH1 avait de l'eau) : le climat de WH1, ses taches de carrefour retirées ; les
                # corrections ne valent que dans la zone gardée, où l'eau de WH1 est
                wh1_tissage = textures_tuiles_wh1._sans_taches_de_route(wh1_brut)[0]
                hab_w, _ = habillage_expanded.habiller(k, wh1_tissage, f_k, reste_k)
                # roche de l'extension en textures de WH1 (première chaîne d'après BOB : la Saison est en PARTOUT_WH1,
                # chaque pixel prend une texture de WH1, et 255 sur les grands massifs restait à plus de 64 px de toute
                # texture) : WH1 n'a pas d'éboulis (ses montagnes sont des maillages) ; en altitude snow3 (6, « roche et
                # neige sale »), sur les pentes mud_a0 (3, boue grise) et sand_b0 (11, sol brun sombre) en taches
                tache = habillage_expanded.bruit(h_k.shape, 6 * f_k, np.random.default_rng(13), 3)
                roche_wh1 = np.where(h_k > 9.5, 6, np.where(tache > 0, 3, 11)).astype(np.uint8)
                hab_w = np.where(roc, roche_wh1, hab_w)
                monde_wh1 = np.where(garde_masque(f_k, reste_k), agrandir(wh1, f_k, 255, reste_k), hab_w).astype(np.uint8)
            else:
                gy_, gx_ = np.gradient(cv2.GaussianBlur(h_k, (0, 0), 1.0))
                pente_k = np.hypot(gx_, gy_) * f_k
                mont_k = cat == sols_e.index("mountain")
                nu = mont_k & ((pente_k > 1.6) | (h_k > 9.5))
                mer_k = (cat >= habillage_expanded._sols()[3]) | (h_k <= 0.05)          # ni en mer ni sur l'eau
                nu |= mer_k
                # (5.10.2026) ni sous les montagnes de WH1 gardées (maillages) là où leur rectangle dépasse la zone gardée
                nu |= montagnes_gardees(f_k, reste_k)
                # (5.10.2026, Charles en jeu : « aux abords d'Athel Loren, il manque des arbres d'un coup dès qu'il y a
                # les montagnes ») la fenêtre « montagne » de WH1 est presque nue (ses montagnes sont des maillages sur un
                # sol plat), CA boise ses massifs (Voûtes des Empires : 0,53 arbre par u²) : forêt claire de WH1 sur la
                # montagne de l'extension, éclaircie par plaques avec l'altitude et la pente ; parois et neige restent nues
                hab_f, _ = habillage_expanded.habiller(k, a, f_k, reste_k, forcer={"mountain": "light_forest"})
                u_k = habillage_expanded.bruit(h_k.shape, 3 * f_k, np.random.default_rng(17), 3)
                u_k = (np.argsort(np.argsort(u_k.ravel())).reshape(u_k.shape) / u_k.size).astype(np.float32)
                dens = (np.clip((9.0 - h_k) / 5.0, 0, 1) * np.clip((1.4 - pente_k) / 0.8, 0, 1) * FORET_MONTAGNE)
                hab = np.where(mont_k & ~nu, np.where(u_k < dens, hab_f, 255), hab)
                # LISIÈRE de WH1 : sur LISIERE_HEX autour de la zone gardée, les arbres de WH1 (raster de la Saison au plus
                # près) se prolongent dans l'extension, de plus en plus clairsemés : pas de coupure nette au bord
                g_tree = garde_masque(f_k, reste_k)
                fond_t = agrandir(a, f_k, 255, reste_k)
                # plus proche pixel de la zone gardée (OpenCV, étiquette par pixel ; ordre des étiquettes vérifié sur les
                # pixels sources eux-mêmes)
                dist_t, lab_t = cv2.distanceTransformWithLabels((~g_tree).astype(np.uint8), cv2.DIST_L2, 5,
                                                                labelType=cv2.DIST_LABEL_PIXEL)
                zy, zx = np.nonzero(g_tree)
                vals = np.full(int(lab_t.max()) + 1, 255, np.uint8)
                vals[lab_t[zy, zx]] = fond_t[zy, zx]
                if not (vals[lab_t[zy, zx]] == fond_t[zy, zx]).all():
                    raise SystemExit("étiquettes de distanceTransformWithLabels inattendues")
                pres = vals[lab_t]
                p_lis = np.clip(1 - dist_t / (LISIERE_HEX * f_k), 0, 1) ** 1.5 * 0.9
                v_k = habillage_expanded.bruit(h_k.shape, 2 * f_k, np.random.default_rng(19), 3)
                v_k = (np.argsort(np.argsort(v_k.ravel())).reshape(v_k.shape) / v_k.size).astype(np.float32)
                prend = ~g_tree & (pres != 255) & (v_k < p_lis) & ~nu
                hab = np.where(prend, pres, hab)
                hab = np.where(nu, 255, hab)
                print(f"  arbres : montagne boisée {int((mont_k & ~nu & (hab != 255)).sum())} px ; lisière de WH1 prolongée "
                      f"{int(prend.sum())} px")
            fond_k = agrandir(a, f_k, 0, reste_k)
            ecrits[k] = np.where(garde_masque(f_k, reste_k), fond_k, hab).astype(np.uint8)
    # le Bois Rêveur dans les autres rasters : sols, arbres, neige (l'hiver d'Atylwyth), couleur teintée de Slaanesh ;
    # lisière du reflet et voile corrompus (masque de corruption au plus haut, teinte magenta)
    for k in list(ecrits):
        if k in ("height", "sea_height", "patch_visibility_mask", "height_shroud"):
            continue
        a = ecrits[k]
        f_k = a.shape[1] // W
        reste_k = a.shape[0] - H * f_k
        p_k, n_k, l_k, v_k = bois_reveur(f_k, reste_k)
        m = refleter(a, f_k)
        if k in ("blend", "tree", "snow_mask"):
            ecrits[k] = np.where(n_k, m, a).astype(a.dtype)
            if k == "blend":
                monde_wh1 = np.where(n_k, refleter(monde_wh1, f_k), monde_wh1).astype(np.uint8)
                os.makedirs(os.path.dirname(MONDE_WH1), exist_ok=True)
                np.save(MONDE_WH1, monde_wh1)
                print(f"  textures de WH1 du monde entier : {MONDE_WH1} {monde_wh1.shape}")
                # l'emprise des montagnes de WH1 (maillages), dans le monde, là seulement où ils sont gardés
                emp = np.load(os.path.join(ATELIER, r"04-projets\saison-des-revelations\relief-wh1\montagnes_wh1.npy"))
                # (bord STRICT, à l'hex : les maillages de montagne de WH1 ne sont gardés que dans les hex de la zone gardée,
                # pas dans la bande organique de garde_masque)
                g_strict = np.repeat(np.repeat(garde_wh1_hex()[::-1], f_k, 0), f_k, 1)
                g_strict = np.concatenate([g_strict, np.repeat(g_strict[-1:], reste_k, 0)]) if reste_k else g_strict
                emp_m = agrandir(emp, f_k, False, emp.shape[0] - SH * f_k) & g_strict
                np.save(MONTAGNES_MONDE, emp_m)
                print(f"  emprise des montagnes de WH1 dans le monde : {MONTAGNES_MONDE} ({int(emp_m.sum())} px)")
        elif k == "corruption_mask":
            base = np.where(n_k, m, a).astype(np.float32)
            bord = np.clip(l_k + v_k.astype(np.float32) * 0.8, 0, 1)
            ecrits[k] = np.maximum(base, bord * 220).astype(np.uint8)
        elif k in ("color_overlay", "color_overlay_sea"):
            rgb = np.broadcast_to(GRIS_ROYAUME_EAU if k == "color_overlay_sea" else GRIS_ROYAUME, m[..., :3].shape)
            out = a.astype(np.float32)
            out[..., :3] = out[..., :3] * (1 - p_k[..., None]) + rgb * p_k[..., None]
            # (4.10.2026) plus de brume lavande sur le voile : elle n'en teintait que les 26 rangées, une bande droite d'un
            # bord à l'autre de la carte, plus claire que l'éther (« bande rose en frontière », refusée le 3.10) ; le voile
            # est de l'éther depuis le 3.10 (la déchirure) et en prend la couleur
            e_k = ether_sud(f_k, reste_k, p_k, v_k)[..., None]
            out[..., :3] = out[..., :3] * (1 - e_k) + (ETHER_EAU if k == "color_overlay_sea" else ETHER_LIT) * e_k
            ecrits[k] = np.clip(out, 0, 255).astype(np.uint8)
    for k, a in ecrits.items():
        im = Image.fromarray(a, modes.get(k, "F" if a.dtype == np.float32 else "L")) if modes.get(k) != "P" else None
        if modes.get(k) == "P":
            im = Image.fromarray(a, "P")
            im.putpalette(palettes[k])
        chemin = os.path.join(DST, os.path.basename(tifs[k]).replace(SOURCE_CLE, CIBLE_CLE))
        im.save(chemin, compression="tiff_lzw")
        print(f"  {k:24s} {a.shape} ")
    # carte des tuiles : la Saison dans le cadre ; mer ou terre (generic) autour
    tm = np.asarray(Image.open(os.path.join(SRC, "tile_map.png")).convert("RGBA"))
    f_t = tm.shape[1] // SW
    reste_t = tm.shape[0] - SH * f_t
    gt_t, _ = sols_grille(f_t, reste_t)
    mer_t = np.array([n.startswith("sea") for n in sols] + [False])[np.where(gt_t < 0, len(sols), gt_t)]
    tuiles = np.where(mer_t[..., None], np.array((83, 141, 213, 255), np.uint8), np.array((223, 180, 145, 255), np.uint8))
    tuiles = np.where(garde_masque(f_t, reste_t)[..., None], agrandir(tm, f_t, 0, reste_t), tuiles).astype(np.uint8)
    p_t, n_t, _, v_t = bois_reveur(f_t, reste_t)
    tuiles = np.where(n_t[..., None], refleter(tuiles, f_t), tuiles).astype(np.uint8)
    tuiles = np.where((ether_sud(f_t, reste_t, p_t, v_t) > 0.5)[..., None], np.array((83, 141, 213, 255), np.uint8),
                      tuiles).astype(np.uint8)
    # (4.10.2026, guide Terry de l'Atlas : « exporter tile_map.png depuis CAIME, sans peinture ni retouche » ; les routes
    # sont des blocs 2 × 2 de la couleur roads) hors de la zone gardée de WH1, les ROUTES viennent de l'export CAIME de la
    # grille (verbe export-tilemap de notre CAIME, le code du menu Tools > Export > Baseline Tilemap ; image à l'envers,
    # rangée 0 au sud) : routes dessinées = routes de la grille (le reflet du Bois Rêveur dessinait 4 280 px de routes
    # absentes de la grille). Côtes : comme la Saison (generic et sea, sans cliff_gen ni sea_coast : côtes de WH1)
    # (4.10.2026, Charles : « ajoute les côtes de CA » ; guide Terry : tile_map = export CAIME sans retouche) toute la
    # carte des tuiles = l'export CAIME de la grille, côtes de CA comprises ; l'éther en mer sur l'infranchissable
    # (tuiles_expanded.py ; remplace la composition « Saison dans le cadre » et tuiles_de_caime)
    import tuiles_expanded
    tuiles = tuiles_expanded.composer((ether_sud(f_t, reste_t, p_t, v_t) > 0.5) | v_t)
    Image.fromarray(tuiles, "RGBA").save(os.path.join(DST, "tile_map.png"))
    # (4.10.2026, audit des guides : `.terry.user` absent, l'aperçu de Terry sans eau ni arbres) les réglages d'affichage
    # de Terry de la Saison (aucun nom propre à la carte dedans), sous le nom d'Expanded
    src_u = os.path.join(SRC, SOURCE_CLE + ".terry.user")
    if os.path.exists(src_u):
        shutil.copy2(src_u, os.path.join(DST, CIBLE_CLE + ".terry.user"))
    # (4.10.2026, audit des guides : 1 747 px de mer au fond ≥ 0, jusqu'à +4 ; guide Terry : « le fond marin doit rester
    # sous 0 là où il y a de la mer ») partout où la carte des tuiles met la mer, hors de la zone gardée de WH1, le fond
    # (sea_height) passe sous FOND_MER_MAX
    mer_t = (tuiles[..., :3] == np.array((83, 141, 213), np.uint8)).all(-1)
    # (5.10.2026) les lacs fermés sont de la terre dans la carte des tuiles (comme WH1) mais de l'EAU pour le relief : fond
    # sous l'eau, ni comblés comme fosses ni refermés comme creux
    mer_t = mer_t | tuiles_expanded.lacs_eau(tuiles.shape)
    p_sea = os.path.join(DST, os.path.basename(tifs["sea_height"]).replace(SOURCE_CLE, CIBLE_CLE))
    sea_im = np.asarray(Image.open(p_sea), np.float32).copy()
    mer8 = cv2.resize(mer_t.astype(np.uint8), (sea_im.shape[1], sea_im.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    mer8 &= ~garde_masque(f, reste)
    trop_haut = mer8 & (sea_im > FOND_MER_MAX)
    sea_im[trop_haut] = FOND_MER_MAX
    # (4.10.2026, classement des marches de relief : petites fosses en hex, en 8, au bout des chenaux de mer ; sous
    # BAS_CUVETTE alors que la carte des tuiles y dit TERRE, épargnées par le comblement des cuvettes, qui laisse tout ce qui
    # est à moins de 2 hex de l'eau) la mer qui compte est celle de la CARTE DES TUILES : hors de WH1 gardé, toute
    # cuvette sous BAS_CUVETTE que les tuiles disent terre (à un pixel près), hors des rivières de l'Atlas et de l'éther, est
    # comblée depuis ses bords
    mer_h =cv2.dilate((cv2.resize(mer_t.astype(np.uint8), (height.shape[1], height.shape[0]),
                                   interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    eth_h = ether_sud(f, reste, poids_r, voile_r) > 0.05
    # (deuxième passage : les fosses en 8 au bout des bras de mer du nord-ouest restaient, sous le champ d'une rivière de
    # l'Atlas qui part de là, champ ≥ 0,2 sur tout l'hex ; leur forme d'hex vient du masque de mer du relief, pas de la
    # rivière) seul le LIT même de la rivière (cœur du tracé, champ ≥ 0,5) est épargné
    fosses = (~garde_masque(f, reste) & ~montagnes_gardees(f, reste) & (height < BAS_CUVETTE) & ~mer_h & ~eth_h
              & (rivieres_atlas.champ(f, reste) < 0.5))
    if fosses.any():
        comble = remplir_lisse(height, ~fosses)
        height = np.where(fosses, np.maximum(comble, BAS_CUVETTE), height).astype(np.float32)
        sea_im = np.where(fosses, np.minimum(sea_im, height - SOUS_TERRE_MER), sea_im).astype(np.float32)
    # (4.10.2026, fosses en hex de (94, 821) et (95, 820), à 0,18 et 0,37 u entre des terres à 1 à 1,3 u, restées après
    # les deux comblements : ni lit, ni ville, ni mer de la grille) toute CREUX plus étroit que ~2 hex et plus profond que
    # CREUX_U, en plaine (fermeture < CREUX_PLAINE_U : les vallées de montagne restent), sur la terre des tuiles hors de WH1,
    # des lits, de l'éther et du trait de côte, est refermé (fermeture morphologique, fondue sur 2 px)
    noyau = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * f + 1, 2 * f + 1))
    ferme = cv2.morphologyEx(height, cv2.MORPH_CLOSE, noyau)
    cote2 = cv2.dilate((cv2.resize(mer_t.astype(np.uint8), (height.shape[1], height.shape[0]),
                                   interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    # (essai : 606 px du Bois Rêveur, des mares de WH1 reflétées : le reflet reste fidèle) hors du Bois Rêveur (`monde`)
    creux = ((ferme - height > CREUX_U) & (ferme < CREUX_PLAINE_U) & ~garde_masque(f, reste) & ~montagnes_gardees(f, reste) & ~cote2 & ~eth_h
             & (rivieres_atlas.champ(f, reste) < 0.2) & monde)
    # (premier passage : sillons de 4 à 7 cm d'un pixel sur l'ancien contour des fosses, là où un fondu mêlait relief et
    # fermeture) la fermeture n'est jamais sous le relief (elle ne fait que combler) : appliquée PLEINE sur l'amas élargi
    # de 4 px, sans fondu, elle ne laisse aucun bord
    creux = cv2.dilate(creux.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    if creux.any():
        height = np.where(creux, np.maximum(height, ferme), height).astype(np.float32)
        sea_im = np.where(creux, np.minimum(sea_im, height - SOUS_TERRE_MER), sea_im).astype(np.float32)
    print(f"  creux étroits en plaine refermés : {int(creux.sum())} px")
    # (5.10.2026, contrôle des marches : 690 px de l'Atlas à plus de 0,6 u d'un pixel au voisin, en lignes horizontales et
    # en escaliers le long des bords d'hex : les vallées de jeu de relief_alpin sont un masque par hex agrandi au plus
    # proche, sur une grille rectangulaire) chaque marche de plus de MARCHE_U, hors de WH1 gardé, du Bois Rêveur, de la
    # déchirure et du trait de côte, est fondue dans un relief lissé (zone élargie et fondue, deux passes)
    n_marches = 0
    for _passe in range(2):
        marche = np.zeros(height.shape, bool)
        marche[:-1] |= np.abs(np.diff(height, axis=0)) > MARCHE_U
        marche[:, :-1] |= np.abs(np.diff(height, axis=1)) > MARCHE_U
        marche &= ~garde_masque(f, reste) & ~montagnes_gardees(f, reste) & ~cote2 & ~eth_h & monde & (height > 0.06)
        if not marche.any():
            break
        n_marches += int(marche.sum())
        poids = np.clip(cv2.GaussianBlur(cv2.dilate(marche.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32),
                                         (0, 0), 2.0) * 1.5, 0, 1)
        poids[garde_masque(f, reste) | montagnes_gardees(f, reste) | cote2 | eth_h | ~monde] = 0
        height = (height * (1 - poids) + cv2.GaussianBlur(height, (0, 0), 2.5) * poids).astype(np.float32)
        sea_im = np.where(poids > 0, np.minimum(sea_im, height - SOUS_TERRE_MER), sea_im).astype(np.float32)
    print(f"  marches de relief adoucies (> {MARCHE_U} u d'un pixel au voisin, hors WH1, Bois Rêveur, côtes) : {n_marches} px")
    # (5.10.2026, Charles en jeu : « escaliers » sur les berges et les côtes ; guides CAIME et Terry, profil de CA mesuré)
    # le relief au trait des TUILES selon la tuile de côte (cotes_relief.py) : falaise = plateau de CA, plage = passage
    # sous l'eau en pente douce, mer voisine au fond de CA ; la différence s'ajoute à celle des chenaux (objets, rubans).
    # AVANT les berges des rivières de l'Atlas (premier passage, après : 7 bords d'eau en l'air près des côtes)
    import cotes_relief
    mer_c, fal_c, pla_c = cotes_relief.masques_tuiles(tuiles, height.shape, tuiles_expanded.lacs_eau(tuiles.shape))
    reves_c = np.zeros(height.shape, bool)
    reves_c[(H - SUD) * f:] = True
    # (5.10.2026, Charles : « les passages entre les montagnes… naturels… ne pas bloquer les armées ») les fonds de vallée
    # franchissables de l'extension sans versant (vallees_relief.py) ; avant les côtes, qui ont le dernier mot
    import vallees_relief
    S_v = os.path.join(ICI, r"couches-expanded\villes-sortie")
    imp_v = read_layer(os.path.join(S_v, "layer_impassable.hex_layer"))[1].reshape(H, W)
    gt_v = read_layer(os.path.join(S_v, "layer_groundtypes.hex_layer"))[1].reshape(H, W)
    n_terre_v = len(caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))[0].get("Land ground types", []))
    passe_v = chenaux_fleuves.px_nord((imp_v == 1) & (gt_v >= 0) & (gt_v < n_terre_v), f, reste)
    height, delta_v, b_v = vallees_relief.aplanir(height, passe_v,
                                                  garde_masque(f, reste) | montagnes_gardees(f, reste) | reves_c | mer_c)
    delta_ch = (delta_ch + delta_v).astype(np.float32)
    print(f"  fonds de vallée franchissables de l'extension : {b_v}")
    height, sea_im, delta_c, b_c = cotes_relief.raccorder(height, sea_im, mer_c, fal_c, pla_c, UX_PX,
                                                          montagnes_gardees(f, reste), reves_c)
    # (5.10.2026) le relief sous les tuiles de MER change aussi (continu avec la côte) : les objets posés sur l'eau
    # (rochers en mer, épaves) ne le suivent pas
    delta_c = np.where(mer_c, 0.0, delta_c)
    delta_ch = (delta_ch + delta_c).astype(np.float32)
    np.savez_compressed(chenaux_fleuves.DELTA, delta=delta_ch.astype(np.float16))
    print(f"  côtes au profil de CA : {b_c}")
    # (5.10.2026, Charles : « des rivières qui n'arrivent pas… pas bien dessinées » ; relevé `scratchpad\petites_rivieres.py`
    # : 188 hex de tracé de l'Atlas sans eau, 20 morceaux d'eau sans débouché, dont 7 arrêtés à 2-4 hex d'une plage) le
    # profil des côtes et l'adoucissement des marches aplanissaient le LIT des rivières de l'Atlas (l'eau ne se pose que
    # dans un lit plus bas que ses berges) : le lit est recreusé à la fin, PROFONDEUR_LIT sous ses berges (fermeture du
    # relief sur ~2 hex), jamais plus bas qu'avant ailleurs, jamais dans WH1 gardé ni sous ses montagnes
    k_lit = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * f + 1, 2 * f + 1))
    berges_lit = cv2.morphologyEx(height, cv2.MORPH_CLOSE, k_lit)
    lit_fin = rivieres_atlas.champ(f, reste) * (~garde_masque(f, reste)) * (~montagnes_gardees(f, reste)) * (~reves_c)
    cible_lit = np.maximum(berges_lit - PROFONDEUR_LIT * lit_fin, np.minimum(height, 0.06))
    recreuse = (lit_fin > 0) & (cible_lit < height - 0.005)
    height = np.where(recreuse, cible_lit, height).astype(np.float32)
    print(f"  lits des rivières de l'Atlas recreusés après les côtes : {int(recreuse.sum())} px")
    # (5.10.2026, controle_anomalies n° 6 : 31 px de bord d'eau des rivières de l'Atlas au-dessus de la berge, là où le lit
    # descend en marche) la berge juste hors du maillage d'eau, plus basse que l'eau voisine, est relevée au niveau de
    # l'eau (+1 cm) ; deux passes (le niveau se recalcule sur le relief retouché)
    import rivieres_atlas_eau as RE_
    n_berges = 0
    for _passe in range(2):
        ch_b, niv_b = RE_.champ_et_niveau(height)
        dedans_b = (ch_b >= 0.25) & np.isfinite(niv_b)
        if not dedans_b.any():
            break
        niv_v = cv2.dilate(np.where(dedans_b, niv_b, -99.0).astype(np.float32), np.ones((3, 3), np.uint8))
        dehors_b = ~dedans_b & (cv2.dilate(dedans_b.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        flotte_b = dehors_b & (niv_v > height + 0.02) & (height > 0.035) & ~garde_masque(f, reste) & ~montagnes_gardees(f, reste)
        if not flotte_b.any():
            break
        n_berges += int(flotte_b.sum())
        height = np.where(flotte_b, niv_v + 0.01, height).astype(np.float32)
    print(f"  berges relevées au niveau de l'eau des rivières de l'Atlas : {n_berges} px")
    n_marches += n_berges
    # (5.10.2026, Charles : « que les côtes soient vraiment parfaites, les plages vraiment belles ») les textures du rivage
    # de la recette de la Saison, sur la côte lissée de toute la carte (cotes_relief.textures_rivage) : réécrit la carte des
    # textures de WH1 du monde entier (lue par textures_sol_wh1 après BOB)
    ch_r, niv_r = RE_.champ_et_niveau(height)
    monde_t = np.load(MONDE_WH1)
    if monde_t.shape != height.shape:
        raise SystemExit(f"textures du monde {monde_t.shape} et relief {height.shape} de tailles différentes")
    monde_t, b_t = cotes_relief.textures_rivage(monde_t, mer_c, pla_c, UX_PX, reves_c,
                                                eau_riv=(ch_r >= 0.25) & np.isfinite(niv_r),
                                                garde=garde_masque(f, reste), chenal=chenaux_fleuves.eau_px(f, reste))
    np.save(MONDE_WH1, monde_t)
    print(f"  textures du rivage (recette de la Saison, côte lissée) : {b_t}")
    p_h = os.path.join(DST, os.path.basename(tifs["height"]).replace(SOURCE_CLE, CIBLE_CLE))
    Image.fromarray(height, "F").save(p_h, compression="tiff_lzw")
    Image.fromarray(sea_im, "F").save(p_sea, compression="tiff_lzw")
    print(f"  fond marin sous la mer de la carte des tuiles : {int(trop_haut.sum())} px ramenés à {FOND_MER_MAX} ; "
          f"fosses sous 0,05 que les tuiles disent terre, comblées : {int(fosses.sum())} px")
    # ---- calques d'objets : positions décalées, fichiers renommés
    n_pos = 0
    motif = re.compile(r'(<ECTransform position=")([-0-9.eE]+) ([-0-9.eE]+) ([-0-9.eE]+)(")')

    def decale(m):
        nonlocal n_pos
        n_pos += 1
        return f"{m.group(1)}{float(m.group(2)) + DX_U:.5f} {m.group(3)} {float(m.group(4)) + DZ_U:.5f}{m.group(5)}"
    # objets de WH1 posés dans la bordure remplacée par l'Atlas : retirés (falaises et montagnes drapées sur un relief
    # qui n'est plus là)
    garde = garde_wh1_hex()
    n_retires = 0
    pos = re.compile(r'<ECTransform position="([-0-9.eE]+) [-0-9.eE]+ ([-0-9.eE]+)"')
    # (5.10.2026, fleuves navigables) objets de WH1 posés SUR le chenal : retirés (maisons, roches, sons de l'ancienne
    # Brienne au-dessus de l'eau), sauf les rubans de rivière (rognés par rivieres_maillages_expanded) ; sur les berges
    # abaissées (chenaux_fleuves.relief), leur hauteur suit le relief (y + delta)
    chenal = chenaux_fleuves.chenal_hex()
    pos_y = re.compile(r'(<ECTransform position="[-0-9.eE]+ )([-0-9.eE]+)( [-0-9.eE]+")')
    n_chenal, n_recales, n_montagnes_ret = 0, 0, 0
    import montagnes_wh1_expanded

    def trie(m):
        nonlocal n_retires, n_chenal, n_recales, n_montagnes_ret
        if eau_expanded.est_mer_wh1(m.group(0)):
            return ""                 # (3.10.2026) remplacés par les plans d'eau d'Expanded (eau_expanded)
        p_ = pos.search(m.group(0))
        if not p_:
            return m.group(0)
        x_, z_ = float(p_.group(1)), float(p_.group(2))
        q = int(x_ / (LARGEUR_S / SW))
        r = int(z_ / (PROF_S / SH))
        if 0 <= q < SW and 0 <= r < SH and not garde[DY + r, DXH + q]:
            n_retires += 1
            return ""
        if "/models/river_wh1_" in m.group(0):
            return m.group(0)         # sommets recalés un à un par rivieres_maillages_expanded (pas le centre)
        # (5.10.2026, Charles : « montagnes cohérentes… les passages ne doivent pas bloquer les armées ») les montagnes de
        # bordure de WH1 surtout HORS de la zone gardée (pivot dedans, roche sur l'Atlas) : retirées (montagnes_wh1_expanded)
        if "_wh1/campaign/montagnes" in m.group(0) and montagnes_wh1_expanded.est_retiree(x_, z_):
            n_montagnes_ret += 1
            return ""
        if 0 <= q < SW and 0 <= r < SH and chenal[DY + r, DXH + q]:
            n_chenal += 1
            return ""
        cx, cy = ipx_de(x_ + DX_U, z_ + DZ_U, delta_ch.shape)
        dy = float(delta_ch[cy, cx])
        if abs(dy) > 0.005:          # (5.10.2026) le profil des côtes de CA lève aussi la terre des falaises
            n_recales += 1
            return pos_y.sub(lambda g: f"{g.group(1)}{float(g.group(2)) + dy:.5f}{g.group(3)}", m.group(0), count=1)
        return m.group(0)
    entite = re.compile(r'[ \t]*<entity id="[^"]*">.*?</entity>[ \t]*\r?\n', re.S)
    calques_decales = []
    for p in glob.glob(os.path.join(SRC, "*.layer")):
        t = open(p, encoding="utf-8").read()
        t = entite.sub(trie, t)
        t = eau_expanded.materiaux(motif.sub(decale, t).replace(SOURCE_CLE, CIBLE_CLE))
        calques_decales.append(t)
        with open(os.path.join(DST, os.path.basename(p).replace(SOURCE_CLE, CIBLE_CLE)), "w", encoding="utf-8",
                  newline="\n") as fh:
            fh.write(t)
    # ---- projet, règles, éclairage
    terry = open(os.path.join(SRC, f"{SOURCE_CLE}.terry"), encoding="utf-8").read().replace(SOURCE_CLE, CIBLE_CLE)
    terry = re.sub(r'world_width="[^"]*"', f'world_width="{LARGEUR_E:.3f}"', terry, count=1)
    terry = eau_expanded.materiaux(terry)          # (3.10.2026) water_plane_material d'Expanded
    # (3.10.2026, première compilation BOB d'Expanded : « Wrong size, expecting 3200x3524 », 9 actions sur 12 en échec) :
    # chaque `QTU::TerrainMap` du .terry déclare la taille de son raster ; elles restaient celles de la Saison. La taille
    # déclarée devient celle du fichier écrit (couche `base`, par son identifiant)
    tailles = {}
    for p in glob.glob(os.path.join(DST, f"{CIBLE_CLE}.*.tif")):
        tailles[os.path.basename(p).split(".")[-2]] = "{}x{}".format(*Image.open(p).size)

    def taille(m):
        t = tailles.get(m.group(3))
        if t is None:
            raise SystemExit(f"raster de la couche {m.group(3)} introuvable dans le projet")
        return f'{m.group(1)}{t}{m.group(2)}{m.group(3)}'
    terry, n_t = re.subn(r'(<data type="\w+" size=")\d+x\d+(" id="[0-9a-f]+"/>\s*<pc type="QTU::TerrainMapLayer">\s*'
                         r'<data id=")([0-9a-f]+)', taille, terry)
    # le masque des parcelles n'a pas de couche dans le .terry : sa taille se déclare seule
    pvm = glob.glob(os.path.join(DST, f"{CIBLE_CLE}.patch_visibility_mask.*.tif"))[0]
    terry = re.sub(r'(<data type="PatchVisibilityMask" size=")\d+x\d+', r"\g<1>" + "{}x{}".format(*Image.open(pvm).size),
                   terry, count=1)
    print(f"  .terry : {n_t} tailles de rasters mises à celles d'Expanded ; parcelles {Image.open(pvm).size}")
    # (3.10.2026) identifiant de projet propre : celui de la Saison était recopié tel quel (deux projets du kit au même id)
    terry = re.sub(r'(<project version="\d+" id=")[0-9a-f]+(")', r"\g<1>1e8a5d0e3c2b7f1\g<2>", terry, count=1)
    open(os.path.join(DST, f"{CIBLE_CLE}.terry"), "w", encoding="utf-8", newline="\n").write(terry)
    regles = open(os.path.join(SRC, "rules.bob"), encoding="utf-8").read().replace(SOURCE_CLE, CIBLE_CLE)
    open(os.path.join(DST, "rules.bob"), "w", encoding="utf-8", newline="\n").write(regles)
    if os.path.isdir(os.path.join(SRC, "lighting")):
        shutil.copytree(os.path.join(SRC, "lighting"), os.path.join(DST, "lighting"))
    # (3.10.2026) les plans d'eau de toutes les mers d'Expanded et de l'éther
    eau_expanded.poser(DST, CIBLE_CLE, calques_decales, DX_U, DZ_U, ether_plus=abime_hex()[0])
    # (4.10.2026) l'eau des rivières de l'Atlas dans leurs lits (maillages drapés, comme celles de WH1)
    import rivieres_atlas_eau
    rivieres_atlas_eau.poser(DST, CIBLE_CLE, height)
    # (3.10.2026) la vie autour des villes neuves : fermes, cultures, clôtures… de leur ville modèle de WH1
    decors_expanded.declarer(DST, CIBLE_CLE, "abords_villes", decors_expanded.copier(SRC, h_s, height))
    # (4.10.2026, Charles : « tous les décors du royaume de Slaanesh ») le Bois Rêveur habillé des objets, décalques,
    # effets, lumières et sons du royaume de Slaanesh de CA (wh3_main_chaos_map_1), par morceaux translatés
    import royaume_slaanesh
    decors_expanded.declarer(DST, CIBLE_CLE, "royaume_slaanesh", royaume_slaanesh.poser(height)[0])
    # (4.10.2026, mesure : 0,470 maillage par hex de terre dans WH1, 0,006 sur l'Atlas) les objets naturels de WH1
    # (roches, buissons, herbes, roseaux, menhirs bretonniens), cellule par cellule, depuis la cellule de WH1 au même
    # mélange de sols ; avant la vie (dont le dégagement les lit)
    import nature_expanded
    decors_expanded.declarer(DST, CIBLE_CLE, "nature_expanded", nature_expanded.poser(height, tuiles)[0])
    # (4.10.2026, Charles : « des animaux, des créatures magiques, en lien avec le lore… comme dans la Saison ») la vie de
    # CA par région (recherche 05-journal\2026-10-04-vie-expanded, choix de Charles)
    import vie_expanded
    decors_expanded.declarer(DST, CIBLE_CLE, "vie_expanded", vie_expanded.poser(height, tuiles)[0])
    # (5.10.2026, Charles : « vas-y… et généralise à tout l'Atlas ») un camp des hommes-bêtes d'occupation de WH1 par
    # région neuve, posé selon la règle de WH1 (camps_expanded.py)
    import camps_expanded
    decors_expanded.declarer(DST, CIBLE_CLE, "camps_expanded", camps_expanded.poser(height, SRC, h_s, DST)[0])
    noms_e, _, _ = caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))
    decors_expanded.calques_regions(DST, CIBLE_CLE, flat_names(noms_e, "Regions"),
                                    {"wh_dlc05_carcassonne_summersfall_fort": "saison_glanborielle_fort_solstice"})
    print(f"{n_pos} positions d'objets décalées de ({DX_U:.3f}, {DZ_U:.3f}) u ; {n_retires} objets de WH1 retirés de la "
          f"bordure remplacée ; projet : {DST}")
    print(f"  fleuves navigables : {n_chenal} objets de WH1 retirés du chenal, {n_recales} recalés sur les berges abaissées")
    print(f"  montagnes de bordure de WH1 surtout hors de la zone gardée, retirées : {n_montagnes_ret} "
          f"(poses à retirer : {len(montagnes_wh1_expanded.pivots_retires())})")
    # (5.10.2026) les rubans d'eau de WH1 d'Expanded : copiés de la Saison, rognés sur le chenal, recalés sur les berges
    import rivieres_maillages_expanded
    rivieres_maillages_expanded.ecrire()
    # aperçu de contrôle : relief ombré réduit, tuiles
    petit = cv2.resize(height, (W * 2, (H * 8 + reste) // 4), interpolation=cv2.INTER_AREA)
    gy, gx = np.gradient(petit * 0.6)
    omb = np.clip(128 + (-gx + gy) * 60, 0, 255).astype(np.uint8)
    Image.fromarray(omb).save(os.path.join(ICI, "apercus", "08-projet-expanded-relief.png"))
    Image.fromarray(tuiles).save(os.path.join(ICI, "apercus", "08-projet-expanded-tuiles.png"))


if __name__ == "__main__":
    main()
