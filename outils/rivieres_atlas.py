#!/usr/bin/env python3
"""rivieres_atlas.py - les rivières de l'Atlas hors de la carte de WH1, en champ raster pour le relief d'Expanded.

Pourquoi (25.09.2026, 22 h 30) : les rivières de l'extension étaient dans la grille CAIME (couche Rivers, déplacements)
mais pas dans le relief : aucun lit hors de WH1. Source : `travail\\extension_rivieres.json` de la session « Extension »
(`geo_extension.py`) : `atlas` (morceaux de l'Atlas gardés parce qu'ils finissent en mer, hors du cadre ou sur une de nos
rivières, trois points par hex), `est` (cinq rivières dessinées dans leurs vallées : Teufel, Wut, Karak Norn, Grimhold,
Helmgart), `ponts` (raccords vers nos rivières). Repère : x vers l'est, y vers le nord, 1 = 1 hex, carte de WH1 en
(0..400, 0..440) ; Expanded : colonne = x + 120, rangée = y + 330 (ligne 0 = sud ; y + 250 avant les Voûtes).

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
# (3.10.2026 : 560 × 905, WH1 en (x + 120, y + 330) ; les rivières des Voûtes, Arena et bras ouest du Skiros, sont
# dans extension_rivieres.json, sous y = 0 : cadre_expanded.py)
from cadre_expanded import H, W, DX, DY                                       # noqa: E402
DEMI_LARGEUR_HEX = {"atlas": 0.22, "est": 0.3, "ponts": 0.22}     # demi-largeur du lit (hex) ; WH1 : 0,1 à 0,75


def traces():
    """[(genre, [(x, y), ...])] dans le repère d'Expanded (colonne, rangée ; rangée 0 = sud)."""
    d = json.load(open(SOURCE, encoding="utf-8"))
    # (3.10.2026, n° 308 de la Construction, relayé par la session « Extension ») : les bouts « atlas » de
    # extension_rivieres.json sont troués (lits en pointillés) ; on prend les tronçons raccordés de la carte de l'Atlas,
    # les mêmes que la grille CAIME et la minicarte (`rivieres_svg_grille.traces`, déjà en colonne / rangée de la grille)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rivieres_svg_grille
    # (4.10.2026, liste des Voûtes) sur le SVG VIVANT, aucun méandre ajouté : les rivières du lore (Sannez et ses
    # ruisseaux, Teufel), les sept de l'est et la Brienne y ont les leurs, celles du relevé de l'Atlas leur tracé naturel,
    # et les « riviere raccord ajout » restent droites, voulues ; nos méandres ne servent que sur la copie figée
    figee = rivieres_svg_grille.SVG != rivieres_svg_grille.SVG_VIVANT
    # (4.10.2026, contrôle : les sept rivières de l'est du JSON sont AUSSI dans le SVG, à 0,3 hex en moyenne, la Teufel
    # à 1 hex : deux lits côte à côte) : elles ne viennent plus que du SVG (Voûtes : « les points du JSON sont les tracés
    # droits du 24.09, les méandres ne sont qu'au dessin ») ; un tracé du SVG à moins de 1,2 hex en moyenne d'une rivière
    # « est » du JSON en prend la largeur
    est = [np.asarray([(x + DX, y + DY) for x, y in r["points"]], float) for r in d["est"]]
    out = []
    for t in rivieres_svg_grille.traces():
        p = np.asarray(t, float)
        genre = "atlas"
        for e in est:
            if np.sqrt(((p[:, None, :] - e[None, :, :]) ** 2).sum(-1)).min(1).mean() < 1.2:
                genre = "est"
                break
        out.append((genre, meandres(t) if figee else t))
    out += [("ponts", [(p["de"][0] + DX, p["de"][1] + DY), (p["a"][0] + DX, p["a"][1] + DY)]) for p in d["ponts"]]
    return out


# (4.10.2026, l'eau des rivières de l'Atlas : plusieurs tracés de la carte papier sont presque droits sur des dizaines
# d'hex, « tirés à la règle » ; Charles : tout doit être naturel et lisse) : méandres doux, perpendiculaires au tracé,
# somme de deux ondes (longueurs 4 à 9 hex), amplitude MEANDRE_HEX, nulle aux deux bouts (confluents, embouchures et
# raccords gardés à leur place), stable (graine = le tracé). Lit et eau suivent le même tracé ; la grille CAIME garde le
# sien (écart sous l'hex)
MEANDRE_HEX = 0.38
MEANDRE_DROIT_HEX = 0.9
# (4.10.2026, préavis des Voûtes) les tracés du SVG vivant ont désormais leurs PROPRES méandres : `traces` n'en ajoute
# plus dès que rivieres_svg_grille.SVG redevient SVG_VIVANT. À vérifier au feu vert : les « est » de
# extension_rivieres.json (sept rivières de l'est) portent-ils aussi les méandres du SVG ? sinon, les y prendre
PAS_MEANDRE = 0.25


def meandres(pts):
    p = np.asarray(pts, np.float64)
    if len(p) < 2:
        return pts
    seg = np.hypot(*np.diff(p, axis=0).T)
    s = np.r_[0, np.cumsum(seg)]
    L = s[-1]
    if L < 3:
        return pts
    t = np.linspace(0, L, max(3, int(L / PAS_MEANDRE) + 1))
    x, y = np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])
    # direction lissée (sur ~1,5 hex) et normale
    k = max(1, int(1.5 / PAS_MEANDRE))
    xs = np.convolve(np.pad(x, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    ys = np.convolve(np.pad(y, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    dx, dy = np.gradient(xs), np.gradient(ys)
    n = np.maximum(np.hypot(dx, dy), 1e-9)
    nx, ny = -dy / n, dx / n
    g = np.random.default_rng(int(abs(p[0, 0] * 7919 + p[0, 1] * 104729 + L * 31)) % (2 ** 32))
    l1, l2 = g.uniform(4, 6), g.uniform(6.5, 9)
    f1, f2 = g.uniform(0, 2 * np.pi, 2)
    onde = 0.6 * np.sin(2 * np.pi * t / l1 + f1) + 0.4 * np.sin(2 * np.pi * t / l2 + f2)
    bouts = np.clip(np.minimum(t, L - t) / 2.0, 0, 1)
    bouts = bouts * bouts * (3 - 2 * bouts)
    # (4.10.2026, aperçu du nord : rainure de 30 hex à moins d'un hex de sa corde, « tirée à la règle » malgré les
    # méandres) les tracés presque droits (corde / longueur > 0,9) méandrent davantage, jusqu'à MEANDRE_DROIT_HEX
    droit = np.clip((np.hypot(*(p[-1] - p[0])) / max(L, 1e-6) - 0.9) / 0.08, 0, 1)
    a = (MEANDRE_HEX + (MEANDRE_DROIT_HEX - MEANDRE_HEX) * droit) * onde * bouts
    return list(zip(x + a * nx, y + a * ny))


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
