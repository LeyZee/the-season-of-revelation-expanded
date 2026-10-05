#!/usr/bin/env python3
"""carte_grille_expanded.py - rendu de contrôle de la grille CAIME d'Expanded (3.10.2026), lecture seule : sols aux
couleurs naturelles, hors jeu assombri, rivières, frontières des régions, villes (rouge) et ports (bleu), cadre de la
Saison en pointillé d'or ; plus des gros plans par zone, pour montrer à Charles chaque zone avant d'avancer.

Usage :
    python carte_grille_expanded.py [--dossier <couches>] [--suffixe <texte>]
Sorties : `apercus\\grille-<suffixe>-entiere.jpg` et `apercus\\grille-<suffixe>-<zone>.png`.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from caime_layers import read_layer, caime_names, flat_names        # noqa: E402
from cadre_expanded import W, H, DX, DY, SW, SH, SUD                 # noqa: E402
from cotes_expanded import voisins                                   # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
COULEURS = {"grassland": (150, 172, 98), "plains": (170, 178, 108), "hills": (160, 146, 100), "light_forest": (92, 132, 70),
            "dense_forest": (46, 88, 46), "hilly_light_forest": (104, 124, 74), "mountain": (138, 128, 118),
            "marsh": (104, 122, 98), "swamp": (88, 104, 82), "tundra": (196, 200, 204), "wasteland": (156, 136, 114),
            "chaotic_wasteland": (116, 74, 74), "desert": (216, 192, 132), "jungle": (62, 112, 62),
            "sea_coast": (76, 118, 160), "sea_ocean": (44, 74, 116), "sea_lake": (86, 136, 176),
            "sea_river": (76, 126, 176), "sea_reef": (96, 146, 156), "sea_maelstrom": (66, 44, 96)}
# gros plans : (colonne min, colonne max, rangée min, rangée max) en hex de la grille
ZONES = {
    "nord-bretonnie-lyonesse": (0, 300, 700, 905),
    "nord-est-reikland": (280, 560, 640, 905),
    "ouest-cote-atlantique": (0, 200, 380, 760),
    "est-grises-raccord": (420, 560, 380, 780),
    "sud-voutes": (180, 560, 230, 420),
    "bois-reveur": (150, 560, 0, 260),
    "jonction-grises-voutes": (300, 560, 250, 480),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(ICI, r"couches-expanded\villes-sortie"))
    ap.add_argument("--suffixe", default="v1")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    listes, _, _ = caime_names(CAIME, CARTE)
    sols = flat_names(listes, "GroundTypes")
    nt = len(listes.get("Land ground types", []))

    def L(n):
        p = os.path.join(a.dossier, f"layer_{n}.hex_layer")
        if not os.path.exists(p):
            p = os.path.join(ICI, "couches-expanded", f"layer_{n}.hex_layer")
        return read_layer(p)[1].reshape(H, W)
    gt, imp, riv, reg, sl = (L(n) for n in ("groundtypes", "impassable", "rivers", "regions", "townslots"))
    pal = np.array([COULEURS.get(s, (255, 0, 255)) for s in sols] + [(18, 18, 22)], np.float32)
    col = pal[np.where(gt < 0, len(sols), gt)]
    terre = (gt >= 0) & (gt < nt)
    col[terre & (imp != 1)] *= 0.62                                   # infranchissable (montagnes, hors jeu)
    col[terre & (riv > 0)] = (70, 128, 186)
    v = voisins(reg)
    bord = ((v != reg[None]) & (v >= 0)).any(0)
    col[bord & terre] *= 0.45
    col[sl == 0] = (200, 40, 30)
    col[sl == 1] = (40, 90, 220)
    S = 4
    img = np.zeros((H * S + S // 2, W * S, 3), np.uint8)
    for x in range(W):
        off = S // 2 if x % 2 == 0 else 0                              # colonnes impaires relevées
        bloc = np.repeat(col[::-1, x], S, 0).astype(np.uint8)
        img[off:off + H * S, x * S:(x + 1) * S] = bloc[:, None, :]
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    x0, x1 = DX * S, (DX + SW) * S
    y0, y1 = (H - DY - SH) * S, (H - DY) * S
    for i in range(x0, x1, 24):
        d.line((i, y0, i + 12, y0), fill=(240, 200, 60), width=3)
        d.line((i, y1, i + 12, y1), fill=(240, 200, 60), width=3)
    for j in range(y0, y1, 24):
        d.line((x0, j, x0, j + 12), fill=(240, 200, 60), width=3)
        d.line((x1, j, x1, j + 12), fill=(240, 200, 60), width=3)
    os.makedirs(os.path.join(ICI, "apercus"), exist_ok=True)
    entiere = os.path.join(ICI, "apercus", f"grille-{a.suffixe}-entiere.jpg")
    im.convert("RGB").resize((W * 2, (H * S + S // 2) // 2), Image.LANCZOS).save(entiere, quality=90)
    print(entiere)
    for nom, (q0, q1, r0, r1) in ZONES.items():
        boite = (q0 * S, (H - r1) * S, q1 * S, (H - r0) * S + S // 2)
        z = im.crop(boite)
        z = z.resize((z.width * 2, z.height * 2), Image.NEAREST)
        p = os.path.join(ICI, "apercus", f"grille-{a.suffixe}-{nom}.png")
        z.save(p)
        print(p, z.size)


if __name__ == "__main__":
    main()
