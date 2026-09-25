#!/usr/bin/env python3
"""rendu_grille.py - rendu lisible de la grille CAIME de Saison Expanded (types de sol, franchissabilité, rivières),
couleurs naturelles et légende ; hex décalés comme dans CAIME (colonnes impaires relevées d'un demi-hex). Lecture seule."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names       # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
C = os.path.join(ICI, "couches-expanded")
W, H = 560, 825
COULEURS = {"grassland": (138, 170, 96), "plains": (160, 176, 104), "hills": (150, 140, 96), "light_forest": (86, 128, 70),
            "dense_forest": (44, 86, 44), "hilly_light_forest": (96, 120, 72), "mountain": (128, 120, 112), "marsh": (96, 116, 94),
            "swamp": (84, 100, 80), "tundra": (190, 196, 200), "wasteland": (150, 130, 110), "chaotic_wasteland": (110, 70, 70),
            "desert": (214, 190, 130), "jungle": (60, 110, 60), "river": (70, 120, 170), "sea_coast": (70, 110, 150),
            "sea_ocean": (40, 70, 110), "sea_lake": (80, 130, 170), "sea_river": (70, 120, 170), "sea_reef": (90, 140, 150),
            "sea_maelstrom": (60, 40, 90)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    noms, _, _ = caime_names(CAIME, CARTE)
    sols = flat_names(noms, "GroundTypes")
    _, gt = read_layer(os.path.join(C, "layer_groundtypes.hex_layer"))
    _, imp = read_layer(os.path.join(C, "layer_impassable.hex_layer"))
    _, riv = read_layer(os.path.join(C, "layer_rivers.hex_layer"))
    gt, imp, riv = (x.reshape(H, W) for x in (gt, imp, riv))
    S = 4
    img = np.zeros((H * S + S // 2 + 1, W * S, 3), np.uint8)
    for y in range(H):
        for x in range(W):
            i = gt[y, x]
            col = (18, 18, 22) if i < 0 else COULEURS.get(sols[i], (255, 0, 255))
            if i >= 0 and imp[y, x] == 0 and not sols[i].startswith("sea"):
                col = tuple(int(c * 0.72) for c in col)          # hors jeu : assombri
            if riv[y, x] and i >= 0 and not sols[i].startswith("sea"):
                col = (70, 125, 180)
            yy = (H - 1 - y) * S + (S // 2 if x % 2 == 0 else 0)   # ligne 0 = sud ; colonnes paires descendues
            img[yy:yy + S, x * S:(x + 1) * S] = col
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("georgia.ttf", 30)
    x0, x1 = 120 * S, 520 * S
    y0, y1 = (H - 690) * S, (H - 250) * S
    d.rectangle((x0, y0, x1, y1), outline=(240, 200, 60), width=4)
    d.text((x0 + 10, y0 + 8), "La Saison (WH1), jouable", font=f, fill=(250, 215, 90), stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((20, (H - 125) * S), "Réservé au Bois des Rêves (reflet d'Athel Loren, en miroir)", font=f,
           fill=(200, 200, 210), stroke_width=2, stroke_fill=(0, 0, 0))
    sortie = os.path.join(ICI, "captures-article", "04_grille_caime_560x825.jpg")
    im.save(sortie, quality=90)
    print(im.size, sortie)


if __name__ == "__main__":
    main()
