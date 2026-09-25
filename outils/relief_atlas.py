#!/usr/bin/env python3
"""
relief_atlas.py - prototype du relief d'Expanded depuis l'Atlas (phase 3, lecture seule : rien n'est écrit dans le kit).

Pourquoi (25.09.2026, Charles : « je ne veux pas une map plate : les reliefs, les plaines, les forêts… conforme à
l'Atlas »). L'Atlas donne une pseudo-altitude par hex (`alt`, 0 mer, 1 plaine … ~10 sommets ; infranchissable > 5,3) et
des masques (montagne, colline, forêt, rivières, mer). Un relief de jeu demande une surface continue à 8 px par hex.
Méthode :
- base : `alt` lissée (écart-type 1,5 hex), agrandie en bicubique, convertie en hauteur par une courbe par classe
  (plaine basse, collines douces, montagnes hautes) ;
- détail : bruit fractal (fBm) partout, faible en plaine ; bruit à crêtes (« ridged ») sur les montagnes, pour des arêtes
  et des vallons plutôt que des bosses ;
- rivières : vallées creusées le long des rivières de l'Atlas (profil en V adouci) ;
- mer : sous l'eau, de plus en plus profonde loin des côtes.
Sortie : `relief.npy` (float32, unités de jeu approximatives) et un aperçu ombré. Le cadre de la Saison n'est pas
touché ici (le relief de WH1 y sera repris tel quel).

Usage :
    python relief_atlas.py [--px 4] [--graine 7]
"""
import argparse
import os
import sys

import numpy as np
import cv2

T = r"C:\TotalWar-CampaignMap\05-journal\2026-09-23-extension-carte\travail"
ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KY = 1.1547                                           # hauteur / largeur d'un hex


def bruit(forme, echelle, rng, octaves=5, persistance=0.5):
    """fBm par sommes de grilles aléatoires agrandies (bruit de valeur), dans [-1, 1] environ."""
    h, w = forme
    tot = np.zeros(forme, np.float32)
    amp, norme = 1.0, 0.0
    e = echelle
    for _ in range(octaves):
        gh, gw = max(2, int(h / e) + 2), max(2, int(w / e) + 2)
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        tot += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        norme += amp
        amp *= persistance
        e /= 2
    return tot / norme


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--px", type=int, default=4, help="px par hex (8 pour la chaîne, 4 pour l'aperçu)")
    ap.add_argument("--graine", type=int, default=7)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    h, (g, r, grand, mont, riv, mer, LW, LH, px_hex) = relief(a.px, a.graine, KY)
    np.save(os.path.join(ICI, "relief", "relief_atlas.npy"), h)
    apercu(h, g, r, grand, mont, riv, mer, LW, LH, px_hex)


def relief(px, graine, ky):
    """Relief modelé de l'Atlas, nord en haut ; `ky` = étirement vertical (1,1547 pour un aperçu aux proportions des
    hex, 1 pour le repère des rasters du jeu, où les rangées d'hex sont déjà à 8 px)."""
    rng = np.random.default_rng(graine)
    g = np.load(os.path.join(T, "extension_geo.npz"))
    r = np.load(os.path.join(T, "extension_regions.npz"))
    H, W = g["alt"].shape
    LW, LH = W * px, int(round(H * px * ky))

    def grand(x, interp=cv2.INTER_CUBIC):
        return cv2.resize(np.ascontiguousarray(x[::-1]).astype(np.float32), (LW, LH), interpolation=interp)  # nord en haut

    class A:                                                       # compatibilité avec le corps d'origine
        pass
    a = A()
    a.px = px
    alt = grand(cv2.GaussianBlur(g["alt"].astype(np.float32), (0, 0), 1.5))
    mer = grand(g["mer"].astype(np.float32)) > 0.5
    # v2 : piémonts larges (flou de 4 hex) ; la hauteur suit `alt`, pas le bord du masque
    mont = cv2.GaussianBlur(grand(g["montagne"].astype(np.float32)), (0, 0), a.px * 4.0)
    coll = cv2.GaussianBlur(grand(g["colline"].astype(np.float32)), (0, 0), a.px * 2.5)
    alt = cv2.GaussianBlur(alt, (0, 0), a.px * 2.5)
    riv = grand((g["riv_ext"] | g["nous_riv"]).astype(np.float32), cv2.INTER_LINEAR) > 0.3
    px_hex = a.px
    # base (v3, 25.09.2026 17 h 30) : calée sur les hauteurs de WH1 dans la Saison jouable (relief_maillages, p10/p50/p90 ;
    # session « Extension », reponse_construction.md § 4) : prairie 0,56/1,61/3,47, collines boisées 2,37/3,55/6,87,
    # montagne 3,24/6,78/10,47, maximum 13,8 ; `alt` : plaines 1-2, collines 3-4, Montagnes Grises 5-7, Voûtes 8-10
    base = np.interp(alt, [0, 1, 2, 3, 4, 5.3, 7, 10], [0.0, 0.6, 1.6, 2.6, 3.6, 6.0, 9.5, 13.5])
    # détail
    fbm = bruit((LH, LW), 30 * px_hex, rng, octaves=6)
    ondul = bruit((LH, LW), 9 * px_hex, rng, octaves=4)                      # collines et plaines qui ondulent
    # crêtes : bruit à crêtes sur un domaine déformé (pas de « bulles »), étiré le long d'un axe par massif
    dx = bruit((LH, LW), 40 * px_hex, rng, octaves=3) * 18 * px_hex
    dy = bruit((LH, LW), 40 * px_hex, rng, octaves=3) * 18 * px_hex
    gx_, gy_ = np.meshgrid(np.arange(LW, dtype=np.float32), np.arange(LH, dtype=np.float32))
    brut = bruit((LH, LW), 22 * px_hex, rng, octaves=6, persistance=0.52)
    brut = cv2.remap(brut, gx_ + dx, gy_ + dy * 0.45, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    crete = np.clip(1.0 - np.abs(brut) * 1.6, 0, 1) ** 2.0
    h = (base + fbm * 0.35 + ondul * (0.25 + 0.8 * coll)
         + mont * crete * (1.2 + 0.7 * np.clip(alt - 3, 0, 7)))
    # ÉROSION (25.09.2026, 18 h ; raccord avec WH1, dont le relief porte de fines ravines) : sur les pentes, un bruit à
    # crêtes fin (~2,5 hex), étiré par un domaine déformé, d'amplitude proportionnelle à la pente locale
    gyp, gxp = np.gradient(cv2.GaussianBlur(h.astype(np.float32), (0, 0), 2 * px_hex))
    pente = np.clip(np.hypot(gxp, gyp) * px_hex, 0, 2.0)
    fin = bruit((LH, LW), 2.5 * px_hex, rng, octaves=3, persistance=0.5)
    fin = cv2.remap(fin, gx_ + dx * 0.25, gy_ + dy * 0.25, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ravines = 1.0 - np.abs(fin) * 2.0
    h = h - np.clip(ravines, 0, 1) ** 3 * pente * 0.35 + fbm * 0.05
    # vallées des rivières (profil adouci, largeur ~1,5 hex)
    d = cv2.distanceTransform((~riv).astype(np.uint8), cv2.DIST_L2, 5) / px_hex
    h = h - np.exp(-(d / 1.5) ** 2) * (0.3 + 2.0 * mont + 0.5 * coll)
    # mer : profondeur croissante loin des côtes (jusqu'à -1,5 u à 20 hex)
    dm = cv2.distanceTransform(mer.astype(np.uint8), cv2.DIST_L2, 5) / px_hex
    h = np.where(mer, -0.05 - 1.45 * (1 - np.exp(-dm / 8)) + fbm * 0.05, np.maximum(h, 0.02))
    h = h.astype(np.float32)
    return h, (g, r, grand, mont, riv, mer, LW, LH, px_hex)


def apercu(h, g, r, grand, mont, riv, mer, LW, LH, px_hex):
    # aperçu ombré, couleurs par sol
    gy, gx = np.gradient(h * (12.0 / px_hex) * 0.9)
    omb = np.clip(0.62 - gx * 0.55 + gy * 0.55, 0.28, 1.3)[..., None]
    biome = cv2.resize(np.ascontiguousarray(r["biome"][::-1]).astype(np.float32), (LW, LH),
                       interpolation=cv2.INTER_NEAREST).astype(int)
    foret = grand(g["foret"].astype(np.float32)) > 0.5
    c = np.empty((LH, LW, 3), np.float32)
    c[:] = (104, 170, 128)                                                   # BGR prairie
    c[biome == 8] = (90, 118, 100)
    c[foret] = (48, 92, 52)
    roc = (mont > 0.5) & (h > 5.5)
    c[roc] = (132, 138, 142)
    c[(mont > 0.5) & (h > 10.5)] = (232, 232, 236)
    c = c * omb
    prof = np.clip(-h / 1.5, 0, 1)[..., None]
    c = np.where(mer[..., None], (150, 118, 70) * (1 - prof) + (95, 60, 30) * prof, c)
    c[riv & ~mer] = (170, 125, 70)
    # cadre de la Saison
    x0, x1 = 120 * px_hex, 520 * px_hex
    y1 = LH
    y0 = LH - int(round(440 * px_hex * KY))
    img = np.ascontiguousarray(np.clip(c, 0, 255).astype(np.uint8))
    cv2.rectangle(img, (x0, y0), (x1, y1 - 1), (60, 200, 245), 3)
    sortie = os.path.join(ICI, "apercus", "03-relief-modele.jpg")
    cv2.imwrite(sortie, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"relief {h.shape}, min {h.min():.2f}, max {h.max():.2f} ; aperçu {sortie}")


if __name__ == "__main__":
    main()
