#!/usr/bin/env python3
"""
lookup_expanded.py - images de correspondance des régions d'Expanded (minicarte et carte dézoomée), au format de CA, avec
le rendu validé par Charles pour la Saison (25.09.2026, 19 h : contours lissés, même teinte de parchemin).

Méthode : la grille hex de CAIME (colonnes à 4 px, rangées à 4,618 px, hex à sommet plat, colonnes impaires décalées
d'une demi-rangée) est tramée en pixels, chaque pixel prenant l'hex dont le centre est le plus proche. CONTRÔLE AVANT
USAGE : la même trame appliquée à la grille de la Saison doit redonner l'image de correspondance que CAIME a calculée
(`working_data\\...\\wh_dlc05_wood_elves_lookup.bmp`) : taux d'accord affiché ; en dessous de 98 %, rien n'est écrit.

Sorties (`04-projets\\saison-expanded\\images-carte\\`) : `saison_expanded_lookup.tga` (2240 × 3810),
`saison_expanded_lookup_minimap.tga` (quart), `saison_expanded_minimap.png` (parchemin de la session « Extension »,
1120 × 1905), `controle_regions.png`.

Usage :
    python lookup_expanded.py
"""
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names    # noqa: E402
import preparer_minicarte as pm                                 # noqa: E402

Image.MAX_IMAGE_PIXELS = None
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
SORTIE = os.path.join(ICI, "images-carte")
PARCHEMIN = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\minicarte_expanded",
                         "saison_expanded_minimap_1120x1905.png")
PX_COL = 4.0


def trame(grille, largeur_px, hauteur_px, decalage_impair):
    """Index de région par pixel (nord en haut) depuis une grille hex (H × W, ligne 0 = sud)."""
    H, W = grille.shape
    ph = hauteur_px / H
    ys, xs = np.mgrid[0:hauteur_px, 0:largeur_px].astype(np.float32)
    ys, xs = ys + 0.5, xs + 0.5
    q0 = np.floor(xs / PX_COL).astype(np.int64)
    meilleur = np.full(xs.shape, np.inf, np.float32)
    choix = np.zeros(xs.shape, np.int64)
    for dq in (-1, 0, 1):
        q = np.clip(q0 + dq, 0, W - 1)
        cx = (q + 0.5) * PX_COL
        dec = np.where(q % 2 == 1, decalage_impair, 0.0)
        # rangée r (0 = sud) : centre à y = hauteur − (r + 0,5 + dec) · ph
        rf = (hauteur_px - ys) / ph - 0.5 - dec
        for dr in (-1, 0, 1):
            r = np.clip(np.round(rf).astype(np.int64) + dr, 0, H - 1)
            cy = hauteur_px - (r + 0.5 + dec) * ph
            d = ((xs - cx) / 1.0) ** 2 + ((ys - cy) * (PX_COL * 1.5 / ph / 1.5)) ** 2
            plus = d < meilleur
            meilleur[plus] = d[plus]
            choix[plus] = grille[r[plus], q[plus]]
    return choix


def controle_saison():
    """Taux d'accord de la trame avec le lookup de CAIME de la Saison, pour les deux sens de décalage."""
    lk = np.asarray(Image.open(pm.LOOKUP_BMP).convert("RGB")).astype(np.int64)
    cle = lk[..., 0] * 65536 + lk[..., 1] * 256 + lk[..., 2]
    hp, wp = cle.shape
    src, _, _ = caime_names(CAIME, os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex"))
    noms = flat_names(src, "Regions")
    _, v = read_layer(os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots\layer_regions.hex_layer"))
    grille = v.reshape(440, 400)
    coul = pm.couleurs_regions()
    rgb = np.array([coul[n][0] * 65536 + coul[n][1] * 256 + coul[n][2] if n in coul else -1 for n in noms] + [-1])
    resultats = {}
    for dec in (0.5, -0.5):
        t = trame(grille, wp, hp, dec)
        resultats[dec] = float((rgb[t] == cle).mean())
    return resultats


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    acc = controle_saison()
    print("  contrôle sur la Saison (accord avec le lookup de CAIME) : " +
          ", ".join(f"décalage {k:+.1f} : {100 * v:.2f} %" for k, v in acc.items()))
    dec, taux = max(acc.items(), key=lambda kv: kv[1])
    if taux < 0.98:
        print("  !! accord insuffisant : rien n'est écrit")
        return 2
    # la grille d'Expanded (couche des régions de travail : ports rattachés, retouches faites)
    listes, W, H = caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))
    noms = flat_names(listes, "Regions")
    _, v = read_layer(os.path.join(ICI, r"couches-expanded\layer_regions.hex_layer"))
    grille = v.reshape(H, W)
    t = open(os.path.join(KIT, r"raw_data\db\regions.xml"), encoding="utf-8", errors="replace").read()
    kit = {}
    for bloc in re.findall(r"<regions[ >](.*?)</regions>", t, re.S):
        k = re.search(r"<key>(.*?)</key>", bloc).group(1)
        kit[k] = tuple(int(re.search(f"<{c}>(\\d+)</{c}>", bloc).group(1)) for c in "rgb")
    couleurs = [kit[n] for n in noms]
    doublons = len(couleurs) - len(set(couleurs))
    print(f"  {len(noms)} régions ; couleurs en double : {doublons}")
    if doublons:
        print("  !! couleurs en double (mers pas encore recolorées ?) : rien n'est écrit")
        return 3
    LW, LH = int(W * PX_COL), int(round(H * 2032 / 440))
    idx = trame(grille, LW, LH, dec)
    # contours lissés, comme la Saison (preparer_minicarte.SIGMA_CONTOURS)
    meilleur = np.full(idx.shape, -1.0, np.float32)
    lisse = np.zeros(idx.shape, np.int64)
    for i in np.unique(idx):
        m = cv2.GaussianBlur((idx == i).astype(np.float32), (0, 0), pm.SIGMA_CONTOURS)
        plus = m > meilleur
        meilleur[plus] = m[plus]
        lisse[plus] = i
    n_av = np.bincount(idx.ravel(), minlength=len(noms))
    n_ap = np.bincount(lisse.ravel(), minlength=len(noms))
    perdues = [noms[i] for i in range(len(noms)) if n_av[i] and not n_ap[i]]
    print(f"  contours lissés : {100 * (lisse != idx).mean():.2f} % des pixels ; régions perdues : {perdues or 'aucune'}")
    if perdues:
        return 4
    presentes = sorted(set(lisse.ravel().tolist()))
    pal_index = {r: i for i, r in enumerate(presentes)}
    palette = [(*couleurs[r], 255) for r in presentes]
    ind = np.vectorize(pal_index.get)(lisse).astype(np.uint16)
    os.makedirs(SORTIE, exist_ok=True)
    pm.ecrit_tga_palette(os.path.join(SORTIE, "saison_expanded_lookup.tga"), ind, palette)
    pm.ecrit_tga_palette(os.path.join(SORTIE, "saison_expanded_lookup_minimap.tga"), ind[::4, ::4], palette)
    # la minicarte : le parchemin de la session « Extension », au cadre exact (moitié de l'image de correspondance)
    par = Image.open(PARCHEMIN).convert("RGBA")
    if par.size != (LW // 2, LH // 2):
        par = par.resize((LW // 2, LH // 2), Image.LANCZOS)
    par.save(os.path.join(SORTIE, "saison_expanded_minimap.png"))
    # contrôle : frontières des régions sur le parchemin
    ctrl = np.asarray(par.convert("RGB")).copy()
    petit = lisse[::2, ::2][:ctrl.shape[0], :ctrl.shape[1]]
    bord = np.zeros(petit.shape, bool)
    bord[:, 1:] |= petit[:, 1:] != petit[:, :-1]
    bord[1:, :] |= petit[1:, :] != petit[:-1, :]
    ctrl[bord] = (90, 30, 20)
    Image.fromarray(ctrl).save(os.path.join(SORTIE, "controle_regions.png"))
    print(f"  écrit : lookup {LW} x {LH}, minicarte {par.size[0]} x {par.size[1]}, palette {len(palette)} couleurs ; "
          f"{SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
