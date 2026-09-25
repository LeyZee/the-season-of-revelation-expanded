#!/usr/bin/env python3
"""rivieres_atlas.py - les rivières de l'Atlas hors de la carte de WH1, en champ raster pour le relief d'Expanded.

Pourquoi (25.09.2026, 22 h 30) : les rivières de l'extension étaient dans la grille CAIME (couche Rivers, déplacements)
mais pas dans le relief : aucun lit hors de WH1. Source : `travail\\extension_rivieres.json` de la session « Extension »
(`geo_extension.py`) : `atlas` (morceaux de l'Atlas gardés parce qu'ils finissent en mer, hors du cadre ou sur une de nos
rivières, trois points par hex), `est` (cinq rivières dessinées dans leurs vallées : Teufel, Wut, Karak Norn, Grimhold,
Helmgart), `ponts` (raccords vers nos rivières). Repère : x vers l'est, y vers le nord, 1 = 1 hex, carte de WH1 en
(0..400, 0..440) ; Expanded : colonne = x + 120, rangée = y + 250 (ligne 0 = sud).

Le lit suit la convention de WH1 relevée par la chaîne de la Saison (`02-scripts\\rivieres_wh1.py`, GUIDE § 15 n° 149) :
lit à ~0,17 u sous les berges, berges basses ; l'eau (maillages drapés) viendra avec la chaîne d'Expanded.

Usage : module (`champ(f, reste)`) ; `python rivieres_atlas.py` imprime un bilan.
"""
import json
import os
import sys

import cv2
import numpy as np

ATELIER = r"C:\TotalWar-CampaignMap"
SOURCE = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\extension_rivieres.json")
H, W = 825, 560
DX, DY = 120, 250
DEMI_LARGEUR_HEX = {"atlas": 0.22, "est": 0.3, "ponts": 0.22}     # demi-largeur du lit (hex) ; WH1 : 0,1 à 0,75


def traces():
    """[(genre, [(x, y), ...])] dans le repère d'Expanded (colonne, rangée ; rangée 0 = sud)."""
    d = json.load(open(SOURCE, encoding="utf-8"))
    out = [("atlas", [(x + DX, y + DY) for x, y in t]) for t in d["atlas"]]
    out += [("est", [(x + DX, y + DY) for x, y in r["points"]]) for r in d["est"]]
    out += [("ponts", [(p["de"][0] + DX, p["de"][1] + DY), (p["a"][0] + DX, p["a"][1] + DY)]) for p in d["ponts"]]
    return out


def champ(f, reste=0):
    """Champ 0..1 des lits de l'Atlas à f px par hex, nord en haut, `reste` rangées de plus en bas : 1 au fil de l'eau,
    décroissant jusqu'au bord du lit (profil lisse)."""
    hauteur = H * f + reste
    d = np.full((hauteur, W * f), 255, np.uint8)
    m = np.zeros_like(d)
    larg = np.zeros((hauteur, W * f), np.float32)
    for genre, pts in traces():
        if len(pts) < 2:
            continue
        p = np.array([[x * f, (H - y) * f] for x, y in pts], np.float64)
        e = max(1, int(round(DEMI_LARGEUR_HEX[genre] * f)))
        un = np.zeros_like(m)
        cv2.polylines(un, [np.round(p * 4).astype(np.int32)], False, 255, 1, cv2.LINE_8, 2)
        m = np.maximum(m, un)
        larg = np.where(un > 0, np.maximum(larg, e), larg)
    # distance au fil (px), puis profil : 1 au fil, 0 à la demi-largeur (+1 px de berge adoucie)
    dist, lab = cv2.distanceTransformWithLabels((m == 0).astype(np.uint8), cv2.DIST_L2, 5,
                                                labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(m)
    largeur_pix = np.zeros(int(lab.max()) + 1, np.float32)
    largeur_pix[lab[ys, xs]] = larg[ys, xs]
    demi = largeur_pix[lab]
    t = np.clip(1 - dist / np.maximum(demi + 1, 1), 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tr = traces()
    for g in ("atlas", "est", "ponts"):
        n = [t for k, t in tr if k == g]
        print(f"  {g:6s} {len(n)} tracés, {sum(len(t) for t in n)} points")
    c = champ(2)
    print(f"  champ à 2 px par hex : {int((c > 0.5).sum())} px de lit (~{(c > 0.5).sum() / 4:.0f} hex)")


if __name__ == "__main__":
    main()
