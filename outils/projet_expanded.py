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
import relief_atlas                                                  # noqa: E402
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
W, H, SW, SH = 560, 825, 400, 440
DXH, DYH_HAUT = 120, 825 - 250 - 440          # hex à gauche, hex au-dessus (nord) de la Saison
LARGEUR_S, PROF_S = 266.53, 338.9
DX_U = DXH * LARGEUR_S / SW                    # 79,959 u vers l'est
DZ_U = 250 * PROF_S / SH                       # 192,557 u vers le nord (z croît vers le nord)
LARGEUR_E = LARGEUR_S * W / SW                 # 373,142
RACCORD_HEX = 12
PENTE_MAX_RACCORD = 0.5                       # u d'altitude par hex, au plus, dans le raccord
HAUTEUR_SUR_MER, SOUS_TERRE_MER = 0.02, 1.0
PROFONDEUR_LIT = 0.17                          # lit des rivières de l'Atlas sous les berges (WH1 : ~0,17 u, GUIDE n° 149)


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
MARGE_WH1_HEX = 4
REBORD_WH1_HEX = 8
_GARDE = {}


def garde_wh1_hex():
    """Hex (825 × 560, ligne 0 = sud) où le terrain de WH1 est gardé."""
    if "hex" in _GARDE:
        return _GARDE["hex"]
    # la carte de WH1 proprement dite = les cases de ses régions (tout sauf terre et mer sauvages), massifs infranchissables
    # intérieurs compris (20 h 20 : la couche de passage seule en excluait les sommets du Massif Orcal et des Grises)
    noms_s, _, _ = caime_names(CAIME, os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex"))
    regions_s = flat_names(noms_s, "Regions")
    sauvages = [i for i, n in enumerate(regions_s) if "wilderness" in n]
    _, rg = read_layer(os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots\layer_regions.hex_layer"))
    jouable = np.zeros((H, W), np.uint8)
    jouable[250:250 + SH, DXH:DXH + SW] = ~np.isin(rg.reshape(SH, SW), sauvages) & (rg.reshape(SH, SW) >= 0)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * MARGE_WH1_HEX + 1, 2 * MARGE_WH1_HEX + 1))
    proche = cv2.dilate(jouable, k).astype(bool)
    r = np.load(REGIONS_ATLAS)
    neuf = np.zeros((H, W), bool)
    neuf[250:250 + r["lab"].shape[0], :W] = (r["lab"] >= 0) | (r["labm"] >= 0)
    cadre = np.zeros((H, W), bool)
    cadre[250:250 + SH, DXH:DXH + SW] = True
    # 20 h 15 : d'abord gardée partout où l'Atlas n'avait rien de neuf, la bordure décorative laissait un cadre visible
    # à l'est et au sud (terre sauvage de l'Atlas contre montagnes de WH1). Désormais : WH1 sur sa partie jouable et la
    # marge seulement ; partout ailleurs, l'Atlas, raccordé (Charles : « sans bordure »).
    garde = cadre & proche
    # 21 h 05 (relief ombré, `captures-article\12-relief-ombre.jpg`) : le relief de WH1 plonge vers 0 sur ses derniers hex
    # (rebord de carte) ; gardé, il faisait une falaise droite le long du bord est. Sur une bande de REBORD_WH1_HEX hex au
    # bord du cadre, on ne garde WH1 que sur ses cases franchissables (couche Impassable de la Saison) ; le rebord
    # infranchissable passe au raccord vers l'Atlas.
    _, imp = read_layer(os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots\layer_impassable.hex_layer"))
    passe = np.zeros((H, W), np.uint8)
    passe[250:250 + SH, DXH:DXH + SW] = imp.reshape(SH, SW) == 1
    passe = cv2.dilate(passe, np.ones((5, 5), np.uint8)).astype(bool)
    interieur = np.zeros((H, W), np.uint8)
    interieur[250 + REBORD_WH1_HEX:250 + SH - REBORD_WH1_HEX, DXH + REBORD_WH1_HEX:DXH + SW - REBORD_WH1_HEX] = 1
    mers_s = [i for i, n in enumerate(regions_s) if "sea" in n]
    mer_wh1 = np.zeros((H, W), bool)
    mer_wh1[250:250 + SH, DXH:DXH + SW] = np.isin(rg.reshape(SH, SW), mers_s)
    # 21 h 30 (bande de terre verticale dans la mer, à l'ouest du golfe) : dans la bande du bord, seules les TERRES
    # franchissables de WH1 sont gardées ; ses mers y cèdent à celle de l'Atlas
    garde &= interieur.astype(bool) | (passe & ~mer_wh1)
    # 21 h 20 : une région TERRESTRE neuve posée sur une mer de WH1 (l'Île Silencieuse sur le golfe du Bidouze) prend le
    # relief de l'Atlas, même si le golfe est une région de WH1
    terre_neuve = np.zeros((H, W), bool)
    terre_neuve[250:250 + r["lab"].shape[0], :W] = r["lab"] >= 0
    garde &= ~(terre_neuve & mer_wh1)
    _GARDE["hex"] = garde
    print(f"  terrain de WH1 gardé sur {int(garde.sum())} hex du cadre ; remplacé par l'Atlas sur "
          f"{int((cadre & ~garde).sum())} hex (bordure décorative sous des régions ou mers neuves)")
    return garde


def garde_masque(f, reste):
    """La zone gardée de WH1, à f px par hex, nord en haut, `reste` rangées de plus en bas."""
    g = np.repeat(np.repeat(garde_wh1_hex()[::-1], f, 0), f, 1)
    if reste:
        g = np.concatenate([g, np.repeat(g[-1:], reste, 0)])
    return g


# LE BOIS RÊVEUR (Charles, 25.09.2026 : « le bois au sud, en reflet miroir », « effets démoniaques sur les contours du
# miroir et sur la séparation ») : grilles de la session « Extension » (bois_des_reves.py, exporter_grilles), 250 × 560,
# ligne 0 = sud, colonne = x + 120 : `terre` (les 18 régions d'Athel Loren reflétées), `voile` (26 rangées contre la
# Saison), `riviere`, `region`, `domaine`. Reflet : hex (x, y) de la Saison -> (x, 7 − y), soit la rangée de grille
# R' = 507 − R ; dans les rasters (nord en haut, f px par hex) : rangée de pixel p' <- 1142·f − 1 − p. Le reflet prend
# TOUT de WH1 (relief, eau, sols, arbres, neige d'hiver), sous une teinte de Slaanesh ; la lisière est corrompue.
# (Rangées de parité opposée : le reflet est décalé d'un demi-hex en x par rapport aux hex de la grille, 4 px à 8 px par
# hex ; invisible à l'œil, sans effet sur les régions, qui viennent de la grille.)
REVES = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\reves_grilles.npz")
SUD = 250                                       # rangées d'hex du Bois Rêveur, sous la Saison
TEINTE_SLAANESH = np.array((168, 96, 190), np.float32)      # lilas-magenta (RVB)
LISIERE_SLAANESH = np.array((214, 60, 170), np.float32)     # magenta vif de la lisière
TEINTE, TEINTE_LISIERE = 0.35, 0.45


def grille_sud(g, f, reste):
    """Grille du sud (250 × 560, ligne 0 = sud) posée dans la toile à f px par hex, nord en haut (float 0/1)."""
    m = np.zeros((H * f + reste, W * f), np.float32)
    b = np.repeat(np.repeat(g[::-1].astype(np.float32), f, 0), f, 1)
    m[(H - SUD) * f:H * f] = b
    if reste:
        m[H * f:] = b[-1:]
    return m


def refleter(a, f):
    """Reflet d'Athel Loren dans la bande du sud : rangée p' <- 1142·f − 1 − p (le reste de `a` est inchangé)."""
    out = a.copy()
    p2 = np.arange((H - SUD) * f, a.shape[0])
    p = (2 * H - 508) * f - 1 - p2
    ok = (p >= 0) & (p < a.shape[0])
    out[p2[ok]] = a[p[ok]]
    return out


def bois_reveur(f, reste):
    """(poids du reflet, reflet net, lisière 0..1, voile) à f px par hex."""
    g = np.load(REVES)
    terre = grille_sud(g["terre"] & ~g["voile"], f, reste)
    net = terre > 0.5
    poids = np.clip(cv2.GaussianBlur(terre, (0, 0), 0.75 * f) * 1.3 - 0.15, 0, 1)
    b = cv2.GaussianBlur(terre, (0, 0), 1.5 * f)
    lisiere = np.clip(b * (1 - b) * 4, 0, 1)
    voile = grille_sud(g["voile"], f, reste) > 0.5
    return poids.astype(np.float32), net, lisiere.astype(np.float32), voile


def ether_sud(f, reste, poids, voile):
    """Poids de l'éther (18 h 35, premier aperçu : l'éther en plaine verte se lisait comme une terre vide) : dans la bande
    du sud, hors du reflet et du voile, une mer d'éther sombre et violette, où le reflet flotte comme une île."""
    sud = grille_sud(np.ones((SUD, W), bool), f, reste)
    return (sud * (1 - poids) * (~voile)).astype(np.float32)


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
    lever = np.zeros((575, W), bool)
    creuser = np.zeros((575, W), bool)
    for c in d["conflits_terre_mer_wh1"]:
        gr = next(x for x in d["regions"] if x["cle_jeu"] == c["cle_jeu"])["grille"]
        m = r[gr["couche"]] == gr["valeur"]
        (lever if c["atlas"] == "terre" else creuser)[...] |= m
    toile = []
    for m in (lever, creuser):
        t = np.zeros((H * f + reste, W * f), np.float32)
        t[:575 * f] = np.repeat(np.repeat(m[::-1].astype(np.float32), f, 0), f, 1)
        t = cv2.GaussianBlur(t, (0, 0), 0.6 * f)
        toile.append(t * cadre_masque(f, reste))
    return toile


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
    # ---- rasters
    tifs = {os.path.basename(p).split(".")[1]: p for p in glob.glob(os.path.join(SRC, f"{SOURCE_CLE}.*.tif"))}
    lus = {k: np.asarray(Image.open(p)) for k, p in tifs.items()}
    modes = {k: Image.open(p).mode for k, p in tifs.items()}
    palettes = {k: Image.open(p).getpalette() for k, p in tifs.items() if modes[k] == "P"}
    # relief : Saison telle quelle dans le cadre ; Atlas dehors, raccordé hors du cadre vers le bord de la Saison
    h_s = lus["height"].astype(np.float32)
    f, reste = 8, h_s.shape[0] - SH * 8
    atlas, _ = relief_atlas.relief(8, 7, 1.0)                            # 575·8 rangées, nord en haut
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
    # 22 h 10 (trait droit dans les Grises de l'est, rangée 532 : bord de la zone gardée, relief fin de WH1 d'un côté,
    # remplissage lisse de l'autre) : dans le cadre de WH1, hors de la zone gardée, le DÉTAIL de WH1 (relief moins sa
    # version floutée sur 2 hex) est rendu au raccord, et s'efface à mesure que l'Atlas l'emporte (1 − w) ; pas sur le
    # rebord de carte de WH1 (REBORD_WH1_HEX), dont le détail est la chute vers le bord
    detail = np.clip(h_bord - cv2.GaussianBlur(h_bord, (0, 0), 2 * f), -1.5, 1.5)
    dedans = np.zeros_like(cadre)
    y0, x0, b = DYH_HAUT * f, DXH * f, REBORD_WH1_HEX * f
    dedans[y0 + b:y0 + SH * f - b, x0 + b:x0 + SW * f - b] = True
    dedans = cv2.GaussianBlur(dedans.astype(np.float32), (0, 0), 2 * f)
    height = np.where(cadre, height, height + detail * (1 - w) * dedans).astype(np.float32)
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
    sea = (sea * (1 - eth) + ETHER_SURFACE * eth).astype(np.float32)
    # coutures de l'Atlas dans le cadre : l'île levée (relief de l'Atlas, au moins 0,15), les baies creusées (surface 0,02,
    # fond jusqu'à −1, rivage adouci sur la moitié extérieure du fondu)
    w_terre, w_mer = coutures(f, reste)
    ile = np.maximum(h_a, 0.15)
    height = np.where(w_terre > 0, height * (1 - w_terre) + ile * w_terre, height)
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
    ecrits = {"height": height, "sea_height": sea}
    # autres rasters : la Saison dans le cadre, une valeur de l'extension autour
    for k, a in lus.items():
        if k in ecrits:
            continue
        if k == "patch_visibility_mask":
            n_w, n_h = -(-W * 8 // 28), -(-(H * 8 + 4) // 28)
            ecrits[k] = np.full((n_h, n_w), 255, np.uint8)
            continue
        f_k = a.shape[1] // SW
        reste_k = a.shape[0] - SH * f_k
        g_k = garde_masque(f_k, reste_k)
        if g_k.ndim < a.ndim:
            g_k = g_k[..., None]
        if k == "height_shroud":
            ecrits[k] = np.where(g_k, agrandir(a, f_k, 1.0, reste_k), 1.0).astype(a.dtype)
        elif k in ("color_overlay", "color_overlay_sea"):
            med = np.median(a.reshape(-1, a.shape[-1]), 0).astype(a.dtype)
            ecrits[k] = np.where(g_k, agrandir(a, f_k, med, reste_k), med).astype(a.dtype)
        elif k in ("snow_mask",):
            ecrits[k] = np.where(g_k, agrandir(a, f_k, 0, reste_k), 0).astype(a.dtype)
        elif k == "corruption_mask":
            bas = int(np.percentile(a, 10))
            ecrits[k] = np.where(g_k, agrandir(a, f_k, bas, reste_k), bas).astype(a.dtype)
        elif k in ("blend", "tree"):
            # la valeur la plus fréquente de la Saison pour chaque type de sol, appliquée aux sols de l'extension
            gt_k, _ = sols_grille(f_k, reste_k)
            saison_gt = gt_k[DYH_HAUT * f_k:DYH_HAUT * f_k + a.shape[0], DXH * f_k:DXH * f_k + a.shape[1]]
            table = {}
            for t in np.unique(saison_gt[saison_gt >= 0]):
                v = a[saison_gt == t]
                table[int(t)] = int(np.bincount(v.reshape(-1)).argmax())
            defaut = int(np.bincount(a.reshape(-1)).argmax())
            ext = np.vectorize(lambda t: table.get(int(t), defaut), otypes=[np.uint8])(gt_k)
            fond_k = agrandir(a, f_k, 0, reste_k)
            ecrits[k] = np.where(garde_masque(f_k, reste_k), fond_k, ext).astype(np.uint8)
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
        elif k == "corruption_mask":
            base = np.where(n_k, m, a).astype(np.float32)
            bord = np.clip(l_k + v_k.astype(np.float32) * 0.8, 0, 1)
            ecrits[k] = np.maximum(base, bord * 220).astype(np.uint8)
        elif k in ("color_overlay", "color_overlay_sea"):
            rgb = m[..., :3].astype(np.float32)
            t = (TEINTE + TEINTE_LISIERE * l_k)[..., None]
            cible = TEINTE_SLAANESH * (1 - l_k[..., None]) + LISIERE_SLAANESH * l_k[..., None]
            rgb = rgb * (1 - t) + cible * t
            out = a.astype(np.float32)
            out[..., :3] = out[..., :3] * (1 - p_k[..., None]) + rgb * p_k[..., None]
            brume = cv2.GaussianBlur(v_k.astype(np.float32), (0, 0), 2 * f_k)[..., None] * 0.5
            out[..., :3] = out[..., :3] * (1 - brume) + np.array((150, 128, 176), np.float32) * brume
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
    Image.fromarray(tuiles, "RGBA").save(os.path.join(DST, "tile_map.png"))
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

    def trie(m):
        nonlocal n_retires
        p_ = pos.search(m.group(0))
        if not p_:
            return m.group(0)
        q = int(float(p_.group(1)) / (LARGEUR_S / SW))
        r = int(float(p_.group(2)) / (PROF_S / SH))
        if 0 <= q < SW and 0 <= r < SH and not garde[250 + r, DXH + q]:
            n_retires += 1
            return ""
        return m.group(0)
    entite = re.compile(r'[ \t]*<entity id="[^"]*">.*?</entity>[ \t]*\r?\n', re.S)
    for p in glob.glob(os.path.join(SRC, "*.layer")):
        t = open(p, encoding="utf-8").read()
        t = entite.sub(trie, t)
        t = motif.sub(decale, t).replace(SOURCE_CLE, CIBLE_CLE)
        with open(os.path.join(DST, os.path.basename(p).replace(SOURCE_CLE, CIBLE_CLE)), "w", encoding="utf-8",
                  newline="\n") as fh:
            fh.write(t)
    # ---- projet, règles, éclairage
    terry = open(os.path.join(SRC, f"{SOURCE_CLE}.terry"), encoding="utf-8").read().replace(SOURCE_CLE, CIBLE_CLE)
    terry = re.sub(r'world_width="[^"]*"', f'world_width="{LARGEUR_E:.3f}"', terry, count=1)
    open(os.path.join(DST, f"{CIBLE_CLE}.terry"), "w", encoding="utf-8", newline="\n").write(terry)
    regles = open(os.path.join(SRC, "rules.bob"), encoding="utf-8").read().replace(SOURCE_CLE, CIBLE_CLE)
    open(os.path.join(DST, "rules.bob"), "w", encoding="utf-8", newline="\n").write(regles)
    if os.path.isdir(os.path.join(SRC, "lighting")):
        shutil.copytree(os.path.join(SRC, "lighting"), os.path.join(DST, "lighting"))
    print(f"{n_pos} positions d'objets décalées de ({DX_U:.3f}, {DZ_U:.3f}) u ; {n_retires} objets de WH1 retirés de la "
          f"bordure remplacée ; projet : {DST}")
    # aperçu de contrôle : relief ombré réduit, tuiles
    petit = cv2.resize(height, (W * 2, (H * 8 + reste) // 4), interpolation=cv2.INTER_AREA)
    gy, gx = np.gradient(petit * 0.6)
    omb = np.clip(128 + (-gx + gy) * 60, 0, 255).astype(np.uint8)
    Image.fromarray(omb).save(os.path.join(ICI, "apercus", "08-projet-expanded-relief.png"))
    Image.fromarray(tuiles).save(os.path.join(ICI, "apercus", "08-projet-expanded-tuiles.png"))


if __name__ == "__main__":
    main()
