#!/usr/bin/env python3
"""apercu_compile_expanded.py - rendu d'Expanded depuis les fichiers COMPILÉS (3.10.2026), lecture seule : la carte des
textures que le jeu lira (`global_map\\global_blend.dds` réécrite par textures_sol_wh1, chaque pixel coloré par la couleur
moyenne de la texture de son groupe), les arbres de la liste finale (`arbres-wh1\\trees.campaign_tree_list`) posés un par
un, l'ombrage du relief du projet, la neige compilée et la mer (plans d'eau d'eau_expanded, d'après la grille).
Plus proche du jeu que `apercu_terrain_expanded`, mais pas le jeu (pas d'éclairage, de modèles ni de shaders).

Usage : python apercu_compile_expanded.py [--suffixe v1]
"""
import argparse
import glob
import os
import re
import struct
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H                                          # noqa: E402
from carte_grille_expanded import ZONES                                  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
GM = os.path.join(KIT, r"working_data\terrain\campaigns\saison_expanded_map\global_map")
ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded"
TEX = os.path.join(ICI, "textures-sol-wh1")
UX, UZ = 266.53 / 400, 338.9 / 440


def couleurs_groupes():
    """Couleur moyenne (RVB) de chaque groupe de la liste compilée, depuis sa texture de couleur de base."""
    t = open(os.path.join(GM, "texture_arrays.xml"), encoding="utf-8").read()
    bloc = re.search(r"<base_colour_array>(.*?)</base_colour_array>", t, re.S).group(1)
    chemins = re.findall(r"<texture>([^<]+)</texture>", bloc)
    out = []
    packs = None
    for c in chemins:
        rgb = None
        for base in (TEX, os.path.join(KIT, "working_data")):
            p = os.path.join(base, *c.split("/"))
            if os.path.exists(p):
                try:
                    im = Image.open(p).convert("RGB").resize((16, 16), Image.BOX)
                    rgb = tuple(np.asarray(im).reshape(-1, 3).mean(0))
                except Exception:
                    pass
                break
        # (4.10.2026 : le Bois Rêveur sortait gris uni) les groupes de CA absents du disque (royaume de Slaanesh…) : leur
        # texture lue dans les packs du jeu
        if rgb is None:
            try:
                import io
                if packs is None:
                    sys.path.insert(0, r"C:\TotalWar-CampaignMap\02-scripts")
                    from contenu_pack import SourcePacks
                    packs = SourcePacks(r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data",
                                        exclure=("saison_des_revelations", "zz_startpos_db", "saison_expanded",
                                                 "!saison", "!!essai"))
                o = packs.lire(c)
                if o:
                    im = Image.open(io.BytesIO(o)).convert("RGB").resize((16, 16), Image.BOX)
                    rgb = tuple(np.asarray(im).reshape(-1, 3).mean(0))
            except Exception:                                        # noqa: BLE001
                rgb = None
        out.append(rgb or (128, 128, 128))
    return np.array(out, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffixe", default="v1")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    b = open(os.path.join(GM, "global_blend.dds"), "rb").read()
    h, w = struct.unpack_from("<II", b, 12)
    blend = np.frombuffer(b[len(b) - h * w:], np.uint8).reshape(h, w)
    pal = couleurs_groupes()
    print(f"  global_blend {w} × {h} ; {len(pal)} groupes ; groupes employés {len(np.unique(blend))}")
    px = 4
    taille = (W * px, H * px)
    col = cv2.resize(pal[np.clip(blend, 0, len(pal) - 1)], taille, interpolation=cv2.INTER_AREA)
    hgt = np.asarray(Image.open(glob.glob(os.path.join(ICI, r"terry\saison_expanded_map\*.height.*.tif"))[0]), np.float32)
    hgt = cv2.resize(hgt, taille, interpolation=cv2.INTER_AREA)
    sn = np.asarray(Image.open(glob.glob(os.path.join(ICI, r"terry\saison_expanded_map\*.snow_mask.*.tif"))[0]))
    sn = cv2.resize(sn.astype(np.float32), taille, interpolation=cv2.INTER_LINEAR) / 255.0
    # arbres : chaque arbre de la liste finale, une touche sombre
    sys.path.insert(0, r"C:\TotalWar-CampaignMap\02-scripts")
    os.environ["SAISON_CARTE"] = "expanded"
    import arbres_wh1 as A
    _, gs = A.lire_liste(open(os.path.join(ICI, r"arbres-wh1\trees.campaign_tree_list"), "rb").read())
    dens = np.zeros((taille[1], taille[0]), np.float32)
    for nom, recs in gs:
        xyz = recs[:, :12].copy().view("<f4").reshape(-1, 3)
        q = np.clip((xyz[:, 0] / UX * px).astype(int), 0, taille[0] - 1)
        r = np.clip(((H - xyz[:, 2] / UZ) * px).astype(int), 0, taille[1] - 1)
        poids = 0.4 if nom.split("_")[1] in ("grass", "shrubs") else 1.0
        np.add.at(dens, (r, q), poids)
    dens = np.clip(cv2.GaussianBlur(dens, (0, 0), 0.8) * 1.2, 0, 1)
    col = col * (1 - 0.55 * dens[..., None]) + np.array((34, 52, 30), np.float32) * 0.55 * dens[..., None]
    col = col * (1 - sn[..., None]) + np.array((232, 236, 240), np.float32) * sn[..., None]
    mer = hgt <= 0.035
    gy, gx = np.gradient(cv2.GaussianBlur(np.where(mer, 0, hgt), (0, 0), 0.8) * (px / 1.6))
    col = col * np.clip(1.0 + (-gx - gy) * 0.5, 0.5, 1.4)[..., None]
    col = np.where(mer[..., None], np.array((50, 78, 98), np.float32), col)
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    sortie = os.path.join(ICI, "apercus", f"compile-{a.suffixe}-entier.jpg")
    img.resize((img.width // 2, img.height // 2), Image.LANCZOS).save(sortie, quality=90)
    print(" ", sortie)
    for nom, (q0, q1, r0, r1) in ZONES.items():
        img.crop((q0 * px, (H - r1) * px, q1 * px, (H - r0) * px)).save(
            os.path.join(ICI, "apercus", f"compile-{a.suffixe}-{nom}.jpg"), quality=92)


if __name__ == "__main__":
    main()
