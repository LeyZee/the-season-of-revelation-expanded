#!/usr/bin/env python3
"""apercu_regions.py - aperçu des régions d'Expanded (couche CAIME posée par regions_expanded.py), nord en haut : une
couleur par région (celle déclarée), frontières sombres, mers en bleu, terres sauvages en gris, cadre de la Saison en or.
Lecture seule. Sortie : captures-article/11-regions-expanded.png"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import caime_names, flat_names    # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
F = 2


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    reg = np.load(os.path.join(ICI, "couches-expanded", "regions_expanded.npy")).astype(np.int64)
    noms = flat_names(caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))[0], "Regions")
    spec = json.load(open(os.path.join(ICI, "map_spec_expanded.json"), encoding="utf-8"))
    info = {r["key"]: r for r in spec["regions"]}
    pal = np.zeros((len(noms), 3), np.float32)
    for i, n in enumerate(noms):
        r = info.get(n)
        if n.endswith("wilderness_land"):
            pal[i] = (150, 146, 138)
        elif n.endswith("wilderness_sea") or (r and r.get("is_sea")) or "_sea_" in n:
            pal[i] = (58, 86, 128)
        elif r:
            c = np.array(r["rgb"], np.float32)
            pal[i] = c * 0.55 + np.array((215, 200, 170)) * 0.45       # couleur déclarée, adoucie pour la lecture
        else:
            pal[i] = (255, 0, 255)
    img = pal[reg[::-1]]
    img = np.repeat(np.repeat(img, F, 0), F, 1)
    r2 = np.repeat(np.repeat(reg[::-1], F, 0), F, 1)
    bord = np.zeros(r2.shape, bool)
    bord[:, 1:] |= r2[:, 1:] != r2[:, :-1]
    bord[1:, :] |= r2[1:, :] != r2[:-1, :]
    img[bord] = (40, 30, 25)
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    H = reg.shape[0]
    d.rectangle((120 * F, (H - 690) * F, 520 * F, (H - 250) * F), outline=(240, 200, 60), width=3)
    f = ImageFont.truetype("georgia.ttf", 22)
    d.text((10, 8), f"Saison Expanded : {len(noms)} régions (cadre or = carte de WH1)", font=f, fill=(255, 255, 255),
           stroke_width=2, stroke_fill=(0, 0, 0))
    sortie = os.path.join(ICI, "captures-article", "11-regions-expanded.png")
    out.save(sortie)
    print(sortie, out.size)


if __name__ == "__main__":
    main()
