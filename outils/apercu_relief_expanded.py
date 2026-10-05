#!/usr/bin/env python3
"""apercu_relief_expanded.py - relief du projet Terry d'Expanded en couleurs d'altitude, ombré (lumière du nord-ouest),
mer d'après le fond (`sea_height`) et la surface ; vue entière réduite et gros plans par zone (mêmes zones que
`carte_grille_expanded.ZONES`). Lecture seule. Ce n'est pas le jeu (erreur 223) : c'est pour voir coutures et formes.

Usage : python apercu_relief_expanded.py [--suffixe v1] [--px 4]
"""
import argparse
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, DX, DY, SW, SH, DY_HAUT                 # noqa: E402
from carte_grille_expanded import ZONES                                  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded"
TERRY = os.path.join(ICI, r"terry\saison_expanded_map")
# rampe d'altitude (u) : plaines vertes, collines ocre, montagnes grises, sommets clairs
RAMPE = [(-0.05, (70, 112, 92)), (0.3, (118, 150, 92)), (1.5, (150, 166, 104)), (3.0, (176, 160, 112)),
         (6.0, (150, 128, 104)), (10.0, (132, 124, 120)), (16.0, (214, 212, 210))]


def coloriser(h):
    xs = np.array([a for a, _ in RAMPE], np.float32)
    out = np.zeros(h.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(h, xs, np.array([b[c] for _, b in RAMPE], np.float32))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffixe", default="v1")
    ap.add_argument("--px", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    h = np.asarray(Image.open(glob.glob(os.path.join(TERRY, "*.height.*.tif"))[0]), np.float32)
    s = np.asarray(Image.open(glob.glob(os.path.join(TERRY, "*.sea_height.*.tif"))[0]), np.float32)
    f = h.shape[1] // W
    k = f // a.px
    h = cv2.resize(h, (h.shape[1] // k, h.shape[0] // k), interpolation=cv2.INTER_AREA)
    s = cv2.resize(s, (s.shape[1] // k, s.shape[0] // k), interpolation=cv2.INTER_AREA)
    mer = h <= 0.035
    col = coloriser(h)
    prof = np.clip(-s, 0, 3) / 3
    eau = np.array((96, 140, 170), np.float32) * (1 - prof[..., None]) + np.array((30, 56, 92), np.float32) * prof[..., None]
    col[mer] = eau[mer]
    # ombrage : relief exagéré, lumière du nord-ouest
    gy, gx = np.gradient(np.where(mer, 0, h) * (a.px / 1.2))
    omb = np.clip(1.0 + (-gx - gy) * 0.55, 0.45, 1.45)
    col = np.clip(col * omb[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(col)
    sortie = os.path.join(ICI, "apercus", f"relief-{a.suffixe}-entier.jpg")
    im.resize((im.width // max(1, a.px // 2), im.height // max(1, a.px // 2)), Image.LANCZOS).save(sortie, quality=90)
    print(sortie, im.size)
    for nom, (q0, q1, r0, r1) in ZONES.items():
        boite = (q0 * a.px, (H - r1) * a.px, q1 * a.px, (H - r0) * a.px)
        p = os.path.join(ICI, "apercus", f"relief-{a.suffixe}-{nom}.jpg")
        im.crop(boite).save(p, quality=92)
        print(p)


if __name__ == "__main__":
    main()
