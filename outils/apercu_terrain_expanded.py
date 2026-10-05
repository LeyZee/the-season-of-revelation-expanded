#!/usr/bin/env python3
"""apercu_terrain_expanded.py - aperçu « vue de campagne » du projet Terry d'Expanded (3.10.2026), lecture seule : couleur
du sol (`color_overlay`), teinte des textures (éboulis gris), ombrage du relief, forêts (`tree` : touffes sombres), neige
(`snow_mask`), mer d'après le fond. Pas le jeu (erreur 223) : pour juger formes, lisières et raccords avant BOB.

Usage : python apercu_terrain_expanded.py [--suffixe v1] [--px 4]
Sorties : apercus\\terrain-<suffixe>-entier.jpg et apercus\\terrain-<suffixe>-<zone>.jpg (zones de carte_grille_expanded).
"""
import argparse
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H                                          # noqa: E402
from carte_grille_expanded import ZONES                                  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded"
TERRY = os.path.join(ICI, r"terry\saison_expanded_map")
EBOULIS = (110, 111, 112, 113)


def lire(nom):
    return np.asarray(Image.open(glob.glob(os.path.join(TERRY, f"*.{nom}.*.tif"))[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffixe", default="v1")
    ap.add_argument("--px", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    px = a.px
    taille = (W * px, H * px)
    h = cv2.resize(lire("height").astype(np.float32), taille, interpolation=cv2.INTER_AREA)
    s = cv2.resize(lire("sea_height").astype(np.float32), taille, interpolation=cv2.INTER_AREA)
    col = cv2.resize(lire("color_overlay")[..., :3].astype(np.float32), taille, interpolation=cv2.INTER_AREA)
    cms = cv2.resize(lire("color_overlay_sea")[..., :3].astype(np.float32), taille, interpolation=cv2.INTER_AREA)
    bl = cv2.resize(lire("blend"), taille, interpolation=cv2.INTER_NEAREST)
    tr = cv2.resize(lire("tree"), taille, interpolation=cv2.INTER_NEAREST)
    sn = cv2.resize(lire("snow_mask").astype(np.float32), taille, interpolation=cv2.INTER_LINEAR) / 255.0
    # sol : la couleur, un peu désaturée vers un vert-brun de campagne
    sol = col * 0.85 + np.array((92, 96, 70), np.float32) * 0.15
    roc = np.isin(bl, EBOULIS)
    sol[roc] = sol[roc] * 0.35 + np.array((128, 122, 114), np.float32) * 0.65
    # forêts : touffes sombres (densité lissée)
    foret = cv2.GaussianBlur((tr != 255).astype(np.float32), (0, 0), 0.6)
    sol = sol * (1 - 0.45 * foret[..., None]) + np.array((38, 58, 34), np.float32) * 0.45 * foret[..., None]
    # neige
    sol = sol * (1 - sn[..., None]) + np.array((236, 238, 242), np.float32) * sn[..., None]
    # ombrage (lumière du nord-ouest)
    mer = h <= 0.035
    gy, gx = np.gradient(cv2.GaussianBlur(np.where(mer, 0, h), (0, 0), 0.8) * (px / 1.6))
    omb = np.clip(1.0 + (-gx - gy) * 0.5, 0.5, 1.4)
    sol = sol * omb[..., None]
    # mer : couleur de l'eau, plus sombre au large
    prof = np.clip(-s, 0, 2.5) / 2.5
    eau = cms * 0.5 + np.array((52, 82, 104), np.float32) * 0.5
    eau = eau * (1 - 0.45 * prof[..., None])
    img = np.clip(np.where(mer[..., None], eau, sol), 0, 255).astype(np.uint8)
    im = Image.fromarray(img)
    sortie = os.path.join(ICI, "apercus", f"terrain-{a.suffixe}-entier.jpg")
    im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(sortie, quality=90)
    print(sortie)
    for nom, (q0, q1, r0, r1) in ZONES.items():
        p = os.path.join(ICI, "apercus", f"terrain-{a.suffixe}-{nom}.jpg")
        im.crop((q0 * px, (H - r1) * px, q1 * px, (H - r0) * px)).save(p, quality=92)
    print("zones :", ", ".join(ZONES))


if __name__ == "__main__":
    main()
