#!/usr/bin/env python3
"""ombrage_expanded.py - relief ombré du projet Terry d'Expanded (bac à sable), sans couleurs : pour juger la topographie
(Charles : « pas une map plate »). Lumière du nord-ouest, relief exagéré ×3, eau en bleu. Lecture seule.
Sortie : captures-article/12-relief-ombre.jpg (moitié : 1120 × 1651)."""
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ICI, "terry", "saison_expanded_map")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    h = np.asarray(Image.open(glob.glob(os.path.join(D, "*.height.*.tif"))[0]), np.float32)
    s = np.asarray(Image.open(glob.glob(os.path.join(D, "*.sea_height.*.tif"))[0]), np.float32)
    petit = cv2.resize(h, (h.shape[1] // 4, h.shape[0] // 4), interpolation=cv2.INTER_AREA)
    eau = cv2.resize(((h <= 0.03) | (s > h)).astype(np.uint8), (petit.shape[1], petit.shape[0]),
                     interpolation=cv2.INTER_NEAREST).astype(bool)
    gy, gx = np.gradient(petit * 3.0)                     # 4 px = 0,5 hex ; exagération ×3
    nx, ny = -gx, -gy
    l = np.array([-1.0, -1.0, 1.4])
    l /= np.linalg.norm(l)
    n = np.dstack([nx, ny, np.ones_like(nx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    ombre = np.clip((n @ l) * 1.15, 0, 1)
    alt = np.clip(petit / 12.0, 0, 1)
    base = np.dstack([0.55 + 0.35 * alt, 0.58 + 0.3 * alt, 0.50 + 0.3 * alt])
    img = base * (0.35 + 0.75 * ombre[..., None])
    img[eau] = (0.25, 0.38, 0.55)
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    chemin = os.path.join(ICI, "captures-article", "12-relief-ombre.jpg")
    out.save(chemin, quality=88)
    print(chemin, out.size, f"relief min {h.min():.2f} max {h.max():.2f}")


if __name__ == "__main__":
    main()
