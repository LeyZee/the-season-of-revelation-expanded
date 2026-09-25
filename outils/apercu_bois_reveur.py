#!/usr/bin/env python3
"""
apercu_bois_reveur.py - aperçu de contrôle du projet Terry d'Expanded (bac à sable), vue du sud : relief ombré, couleur
(color_overlay), eau (sea_height > height), lisière corrompue (corruption_mask). Lecture seule.

Sortie : `04-projets/saison-expanded/captures-article/10-bois-reveur.jpg` (et une vue d'ensemble réduite).
"""
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(ICI, "terry", "saison_expanded_map")


def lire(cle):
    return np.asarray(Image.open(glob.glob(os.path.join(DST, f"saison_expanded_map.{cle}.*.tif"))[0]))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    h = lire("height").astype(np.float32)
    s = lire("sea_height").astype(np.float32)
    col = lire("color_overlay")[..., :3].astype(np.float32)
    cor = cv2.resize(lire("corruption_mask").astype(np.float32), (h.shape[1], h.shape[0]))
    gy, gx = np.gradient(cv2.GaussianBlur(h, (0, 0), 1.0) * 1.2)
    omb = np.clip(0.75 - gx * 0.9 + gy * 0.9, 0.35, 1.35)[..., None]
    # couleur : overlay (~115 neutre) ramené autour d'un vert de forêt, pour lire la teinte
    base = np.array((92, 120, 78), np.float32)
    c = base * (col / 115.0) * omb
    eau = (s > h + 0.01)[..., None]
    c = np.where(eau, np.array((60, 90, 130), np.float32) * (col / 115.0) * 0.9, c)
    c = c * (1 - 0.35 * (cor[..., None] / 255.0)) + np.array((200, 40, 160)) * 0.35 * (cor[..., None] / 255.0)
    img = np.clip(c, 0, 255).astype(np.uint8)
    H, W = img.shape[:2]
    y0 = int(H * (825 - 250 - 40) / 825)                       # un peu de la Saison, le voile, tout le sud
    sud = img[y0:, :]
    sortie = os.path.join(ICI, "captures-article", "10-bois-reveur.jpg")
    Image.fromarray(cv2.resize(sud, (sud.shape[1] // 2, sud.shape[0] // 2), interpolation=cv2.INTER_AREA)).save(
        sortie, quality=88)
    tout = os.path.join(ICI, "captures-article", "10-expanded-ensemble.jpg")
    Image.fromarray(cv2.resize(img, (W // 5, H // 5), interpolation=cv2.INTER_AREA)).save(tout, quality=88)
    print(sortie, sud.shape, "\n", tout)


if __name__ == "__main__":
    main()
