#!/usr/bin/env python3
r"""
relief_monde.py - le relief du monde entier de Saison Expanded (phase 3, prototype, lecture seule sur le kit).

Assemble, dans le repère des rasters du jeu (8 px par rangée d'hex, ligne 0 = NORD ; ici `--px` par hex) :
- au centre, le relief RÉEL de la carte de la Saison (height du projet Terry de la bêta, tel que la chaîne l'écrit),
  posé au décalage d'Expanded (x + 120 hex, 135 hex sous le haut : 825 − 250 − 440) ;
- autour, le relief modelé de l'Atlas (`relief_atlas.relief`, repère des rasters : ky = 1) ;
- au sud, la bande réservée au Bois des Rêves (plate, sous la brume, en attendant l'Atlas) ;
- un raccord progressif sur RACCORD_HEX le long du cadre de la Saison, seulement là où la Saison est de la bordure de
  décor (hors de sa partie jouable, qui reste exactement celle de WH1).
Sortie : `relief\relief_monde_<px>px.npy` et un aperçu ombré coloré par la grille CAIME (`captures-article\`).
Rappel : dans WH1 le sol est plat sous les montagnes, portées par des maillages ; l'aperçu les montre donc plates dans
la Saison (les maillages de WH1 seront posés par la chaîne).

Usage :
    python relief_monde.py [--px 4]
"""
import argparse
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relief_atlas                                                  # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names        # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
PROJET_SAISON = os.path.join(KIT, r"raw_data\terrain\campaigns\wh_dlc05_wood_elves_map_1")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
W, H = 560, 825
DX, DY_HAUT = 120, 825 - 250 - 440                 # colonnes à gauche, rangées au-dessus de la Saison (nord)
RACCORD_HEX = 6
CARTE_SAISON_HEX = os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex")
COUCHES_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots")
# les royaumes d'Athel Loren (session « Extension », bois_des_reves.DOMAINES)
ROYAUMES_AL = ("arranoc", "argwylon", "tirsyth", "atylwyth", "cythral", "modryn", "cavaroc", "torgovann", "anmyr",
               "fyr_darric", "wydrioth", "talsyn", "oak_of_ages")
COULEURS = relief_atlas and {
    "grassland": (138, 170, 96), "plains": (160, 176, 104), "hills": (150, 140, 96), "light_forest": (86, 128, 70),
    "dense_forest": (44, 86, 44), "hilly_light_forest": (96, 120, 72), "mountain": (128, 120, 112),
    "marsh": (96, 116, 94), "swamp": (84, 100, 80), "tundra": (190, 196, 200), "wasteland": (150, 130, 110),
    "chaotic_wasteland": (110, 70, 70), "desert": (214, 190, 130), "jungle": (60, 110, 60), "river": (70, 120, 170)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--px", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    px = a.px
    LW, LH = W * px, H * px
    monde = np.full((LH, LW), -0.25, np.float32)                  # bande du sud : basse, sous la brume
    # l'Atlas (575 rangées, nord en haut) occupe les rangées 0..575 du haut
    ha, _ = relief_atlas.relief(px, 7, 1.0)
    monde[:ha.shape[0], :ha.shape[1]] = ha
    # la Saison : height du projet Terry (3524 × 3200, 8 px par hex, nord en haut), ramenée à px par hex
    tif = glob.glob(os.path.join(PROJET_SAISON, "wh_dlc05_wood_elves_map_1.height.*.tif"))[0]
    s = np.asarray(Image.open(tif), np.float32)
    s = cv2.resize(s, (400 * px, 440 * px), interpolation=cv2.INTER_AREA)
    y0, x0 = DY_HAUT * px, DX * px
    # partie jouable de la Saison (couche Impassable de la grille : 1 = franchissable), nord en haut
    _, imp = read_layer(os.path.join(ICI, "couches-expanded", "layer_impassable.hex_layer"))
    imp = imp.reshape(H, W)[::-1]
    jouable = cv2.resize(imp.astype(np.float32), (LW, LH), interpolation=cv2.INTER_NEAREST) > 0.5
    # poids de la Saison : 1 dans le jouable ; dans la bordure de décor, 1 au cœur, 0 au bord du cadre (raccord)
    cadre = np.zeros((LH, LW), np.uint8)
    cadre[y0:y0 + 440 * px, x0:x0 + 400 * px] = 1
    d = cv2.distanceTransform(cadre, cv2.DIST_L2, 5) / px
    poids = np.clip(d / RACCORD_HEX, 0, 1)
    poids = np.where(jouable, 1.0, poids).astype(np.float32)
    saison = np.zeros_like(monde)
    saison[y0:y0 + 440 * px, x0:x0 + 400 * px] = s
    monde = monde * (1 - poids) + saison * poids
    # LE BOIS DES RÊVES (Charles, 25.09.2026 : « attaque aussi le miroir d'Athel Loren ») : définition de la session
    # « Extension » (bois_des_reves.py, DOMAINES ; réponse du 25.09) : les 18 régions d'Athel Loren de la Saison, en
    # MIROIR de haut en bas sous un voile d'environ 26 rangées : hex (x, y) de la Saison -> (x, 7 - y) de l'Atlas, soit la
    # rangée 257 - y de la grille ; dans le raster (nord en haut), rangée de pixel cible = 1142 px - 1 - rangée source.
    noms_s, _, _ = caime_names(CAIME, CARTE_SAISON_HEX)
    regions_s = flat_names(noms_s, "Regions")
    _, reg = read_layer(os.path.join(COUCHES_SAISON, "layer_regions.hex_layer"))
    reg = reg.reshape(440, 400)                                    # ligne 0 = sud
    ids_al = [i for i, n in enumerate(regions_s) if any(k in n for k in ROYAUMES_AL)]
    al = np.isin(reg, ids_al)
    m_src = np.zeros((LH, LW), bool)
    bloc = np.repeat(np.repeat(al[::-1], px, 0), px, 1)            # nord en haut
    m_src[y0:y0 + 440 * px, x0:x0 + 400 * px] = bloc
    rangs = np.arange(LH)
    cible = 1142 * px - 1 - rangs                                   # rangée cible de chaque rangée source
    ok = (cible >= 0) & (cible < LH)
    miroir = np.zeros((LH, LW), bool)
    miroir[cible[ok]] = m_src[rangs[ok]]
    monde_m = monde.copy()
    monde_m[cible[ok]] = monde[rangs[ok]]
    voile = np.zeros((LH, LW), bool)
    voile[575 * px:601 * px] = True
    ether = np.zeros((LH, LW), bool)
    ether[575 * px:] = True
    monde = np.where(miroir, monde_m, np.where(voile, 0.4, np.where(ether, -0.4, monde))).astype(np.float32)
    print(f"  Bois des Rêves : {len(ids_al)} régions d'Athel Loren reflétées ({int(al.sum())} hex)")
    os.makedirs(os.path.join(ICI, "relief"), exist_ok=True)
    np.save(os.path.join(ICI, "relief", f"relief_monde_{px}px.npy"), monde)
    # aperçu : couleur par sol de la grille CAIME, ombrage du relief
    noms, _, _ = caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))
    sols = flat_names(noms, "GroundTypes")
    _, gt = read_layer(os.path.join(ICI, "couches-expanded", "layer_groundtypes.hex_layer"))
    gt = cv2.resize(gt.reshape(H, W)[::-1].astype(np.float32), (LW, LH), interpolation=cv2.INTER_NEAREST).astype(int)
    pal = np.array([COULEURS.get(n, (60, 90, 130)) for n in sols] + [(22, 22, 28)], np.float32)
    c = pal[np.where(gt < 0, len(sols), gt)]
    gy, gx = np.gradient(cv2.GaussianBlur(monde, (0, 0), 0.8) * (12.0 / px) * 0.7)
    omb = np.clip(0.66 - gx * 0.6 + gy * 0.6, 0.3, 1.3)[..., None]
    mer = np.array([n.startswith("sea") for n in sols] + [False])[np.where(gt < 0, len(sols), gt)]
    prof = np.clip(-monde / 1.5, 0, 1)[..., None]
    # le reflet : les sols d'Athel Loren, reflétés, teintés aux couleurs de Slaanesh (violet, magenta, lilas)
    gt_m = gt.copy()
    gt_m[cible[ok]] = gt[rangs[ok]]
    c_m = pal[np.where(gt_m < 0, len(sols), gt_m)]
    lum = (c_m.mean(-1, keepdims=True) / 255.0)
    slaanesh = np.clip(np.array((46, 20, 78)) * (1 - lum) * 1.3 + np.array((196, 96, 200)) * lum * 1.6, 0, 255)
    c = np.where(miroir[..., None], c_m * 0.25 + slaanesh * 0.75, c)
    c = np.where((voile & ~miroir)[..., None], np.array((150, 140, 170)), c)
    c = np.where((ether & ~voile & ~miroir)[..., None], np.array((24, 16, 38)), c)
    mer = mer & ~ether
    c = np.where(mer[..., None], np.array((70, 110, 150)) * (1 - prof) + np.array((28, 52, 90)) * prof, c * omb)
    # brume du voile : fondu doux vers le haut et vers le bas
    brume = cv2.GaussianBlur(voile.astype(np.float32), (0, 0), 6 * px)[..., None]
    c = c * (1 - brume * 0.6) + np.array((175, 165, 195)) * brume * 0.6
    img = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype("georgia.ttf", 26)
    dr.rectangle((x0, y0, x0 + 400 * px, y0 + 440 * px), outline=(240, 200, 60), width=3)
    dr.text((x0 + 8, y0 + 6), "La Saison (relief réel de WH1)", font=f, fill=(250, 215, 90), stroke_width=2,
            stroke_fill=(0, 0, 0))
    dr.text((x0 + 8, (575 + 30) * px), "Le Bois des Rêves (reflet d'Athel Loren, en miroir)", font=f,
            fill=(225, 190, 245), stroke_width=2, stroke_fill=(20, 0, 30))
    dr.text((x0 + 8, 577 * px), "voile de brume", font=f, fill=(60, 50, 80))
    sortie = os.path.join(ICI, "captures-article", f"05_relief_monde_{px}px.jpg")
    img.save(sortie, quality=90)
    print(f"monde {monde.shape}, min {monde.min():.2f}, max {monde.max():.2f} ; Saison {s.min():.2f}..{s.max():.2f} ; "
          f"aperçu {sortie}")


if __name__ == "__main__":
    main()
