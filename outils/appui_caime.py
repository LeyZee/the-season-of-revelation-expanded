#!/usr/bin/env python3
"""
appui_caime.py - les quatre fichiers d'appui de la carte CAIME d'Expanded (3.10.2026), dans le bac à sable, à côté de
`caime\\saison_expanded_map\\map.hex`.

Pourquoi (guide CAIME, « Remplir, valider, exporter ») : sans `trees.png`, `tree_database.xml`, `dynamic_resources.png`
et `dynamic_resources_database.xml` à côté du `map.hex`, Map Data ou Dynamic Resources échouent ; les images ont la
taille de la carte (≈ 7,04 × 7,37 px par hex pour trees.png, 2,54 × 2,40 pour dynamic_resources.png). Ceux de la
Saison (copiés du prologue le 20.09) servent de modèle : XML recopiés, images agrandies à la grille d'Expanded, celle
de la Saison posée à sa place (x + 120, y + 330), le reste de la couleur de fond de la Saison.
Lecture seule dans le kit. Usage : python appui_caime.py
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, SW, SH, DX, DY                       # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
SRC = os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1")
DST = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded\caime\saison_expanded_map"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for x in ("tree_database.xml", "dynamic_resources_database.xml"):
        shutil.copy2(os.path.join(SRC, x), os.path.join(DST, x))
    for nom in ("trees.png", "dynamic_resources.png"):
        im = np.asarray(Image.open(os.path.join(SRC, nom)).convert("RGBA"))
        kx, ky = im.shape[1] / SW, im.shape[0] / SH                    # px par hex
        lw, lh = round(W * kx), round(H * ky)
        valeurs, comptes = np.unique(im.reshape(-1, 4), axis=0, return_counts=True)
        fond = valeurs[np.argmax(comptes)]
        out = np.empty((lh, lw, 4), np.uint8)
        out[:] = fond
        x0, y0 = round(DX * kx), round((H - DY - SH) * ky)            # nord en haut
        out[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im[:lh - y0, :lw - x0]
        Image.fromarray(out, "RGBA").save(os.path.join(DST, nom))
        print(f"  {nom} : {im.shape[1]}×{im.shape[0]} -> {lw}×{lh} ({kx:.3f} × {ky:.3f} px par hex) ; "
              f"fond {tuple(int(v) for v in fond)} ({100 * comptes.max() / comptes.sum():.1f} % de la Saison)")


if __name__ == "__main__":
    main()
