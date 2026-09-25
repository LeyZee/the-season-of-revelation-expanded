"""controle_raccord.py - gros plans ombrés du relief du projet Expanded sur les bords du cadre de la Saison (nord-ouest,
nord-est, sud-ouest), pour juger le raccord. Lecture seule ; images dans apercus\\."""
import glob, os
import cv2
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded"
h = np.asarray(Image.open(glob.glob(os.path.join(ICI, r"terry\saison_expanded_map\*.height.*.tif"))[0]), np.float32)
f = 8
x0, x1, y0, y1 = 120 * f, 520 * f, 135 * f, 575 * f          # cadre de la Saison (nord en haut)
coins = {"nord_ouest": (x0, y0), "nord_est": (x1, y0), "sud_ouest": (x0, y1), "ouest_milieu": (x0, (y0 + y1) // 2)}
R = 600
for nom, (cx, cy) in coins.items():
    a = h[max(0, cy - R):cy + R, max(0, cx - R):cx + R]
    gy, gx = np.gradient(cv2.GaussianBlur(a, (0, 0), 1.0) * 1.6)
    omb = np.clip(150 + (-gx + gy) * 90, 0, 255)
    teinte = np.clip(a / 12, 0, 1)
    rgb = np.stack([omb * (0.75 + 0.25 * teinte), omb * (0.85 - 0.1 * teinte), omb * (0.7 - 0.1 * teinte)], -1)
    img = np.ascontiguousarray(np.clip(rgb, 0, 255).astype(np.uint8))
    # cadre en pointillés jaunes
    for i in range(0, img.shape[0], 12):
        for j in (cx - max(0, cx - R),):
            if 0 <= j < img.shape[1]:
                img[i:i + 6, j:j + 2] = (240, 200, 60)
    for j in range(0, img.shape[1], 12):
        i = cy - max(0, cy - R)
        if 0 <= i < img.shape[0]:
            img[i:i + 2, j:j + 6] = (240, 200, 60)
    Image.fromarray(img).save(os.path.join(ICI, "apercus", f"09-raccord-{nom}.png"))
    print(nom, img.shape)
