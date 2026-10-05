#!/usr/bin/env python3
"""
eclairage_arden.py - l'AMBIANCE de la forêt d'Arden (5.10.2026) : PROPOSITION, à montrer en image puis à essayer en jeu
avant toute adoption (décision de Charles du 25.09.2026, éclairage zone par zone « à la manière de CA » ; erreur 251).

Pourquoi (Charles, 5.10.2026 : « commence par l'Ardenne… la forêt d'Ardennes, on dirait vraiment une belle forêt » ;
proposition retenue : « ambiance plus sombre et brumeuse ») : CA n'a PAS de zone propre à l'Arden (Empires Immortels,
`terrain/campaigns/wh3_main_combi_map_1/environment_collection.xml` : la Bretonnie entière sous
`Weather/campaign/combi/bretonnia.environment`, 4 cylindres ; Athel Loren sous `Weather/campaign/combi/woodelf.environment`,
1 cylindre, rayons 30 / 42). L'ambiance de forêt de CA est celle de woodelf : brouillard 2,0 (Bretonnie 1,3), plus haut
(6 u contre 4,5), soleil à 30 000 (Bretonnie 60 000), LUT `campaign_ie_woodelves`. On cite CE fichier de CA, tel quel
(rien copié, rien modifié, aucun fichier à nous à un chemin de CA), dans des cylindres sur les régions de la forêt d'Arden
(Artois), transition de CA (12 u, celle de son cylindre d'Athel Loren). Hors des cylindres : l'éclairage global
d'Expanded ne change pas.

Mise en place (session « Construction », comme `eclairage_reves`) : `build_pack` ajoute `lignes_cylindres()` à la
collection d'Expanded et en tient compte dans son contrôle des cylindres (erreur 109) ; interrupteur proposé :
SAISON_ECLAIRAGE_ARDEN=1, éteint par défaut.

Usage : python eclairage_arden.py     (bilan, lignes de la collection, aperçu apercus\\eclairage-arden.png)
"""
import glob
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H, UX, UZ                                          # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names                     # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
APERCU = os.path.join(ICI, "apercus", "eclairage-arden.png")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
FICHIER_CA = "Weather/campaign/combi/woodelf.environment"
REGIONS = ("saison_artois_",)        # les régions de la forêt d'Arden (relevé du 5.10 : 81 à 98 % de sol forestier)
TRANSITION_U = 12.0                  # CA, cylindre d'Athel Loren : 42 − 30
COUVERTURE = 0.9                     # part des hex de chaque groupe dans son rayon intérieur
GROUPES = 2
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data"


def foret():
    """(x, z) Terry des hex des régions de l'Arden."""
    noms = flat_names(caime_names(CAIME, CARTE)[0], "Regions")
    idx = [i for i, n in enumerate(noms) if n.startswith(REGIONS)]
    reg = read_layer(os.path.join(ICI, r"couches-expanded\villes-sortie\layer_regions.hex_layer"))[1].reshape(H, W)
    r, q = np.nonzero(np.isin(reg, idx))
    return np.stack([(q + 0.5) * UX, (r + 0.5) * UZ], 1)


def cylindres():
    """[(x, z, rayon intérieur, rayon extérieur)] : GROUPES cylindres (k-moyennes à graine fixe) sur la forêt."""
    import cv2
    cv2.setRNGSeed(20261005)
    p = foret()
    _, lab, _ = cv2.kmeans(p.astype(np.float32), GROUPES, None,
                           (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.01), 10, cv2.KMEANS_PP_CENTERS)
    out = []
    for i in range(GROUPES):
        g = p[lab.ravel() == i]
        c = g.mean(0)
        ri = float(np.quantile(np.hypot(g[:, 0] - c[0], g[:, 1] - c[1]), COUVERTURE))
        out.append((round(float(c[0]), 3), round(float(c[1]), 3), round(ri, 3), round(ri + TRANSITION_U, 3)))
    return out, p


def lignes_cylindres():
    """Les lignes <CYLINDER .../> à ajouter dans <ENVIRONMENT_CYLINDERS> de la collection d'Expanded (format de CA)."""
    return "".join(f"\t\t<CYLINDER serialise_version='1' lighting='{FICHIER_CA}' x='{x:.6f}' y='0.000000' z='{z:.6f}' "
                   f"inner_radius='{ri:.6f}' outer_radius='{ro:.6f}'/>\n" for x, z, ri, ro in cylindres()[0])


def reglages_ca(fichier):
    """Brouillard (densité, sommet, couleur), soleil et LUT d'un fichier d'ambiance de CA."""
    from contenu_pack import SourcePacks
    t = SourcePacks(DATA).lire(fichier.lower()).decode("utf-8", errors="replace")
    fog = re.search(r'<fog [^>]*density="([0-9.]+)"[^>]*height_top="([0-9.]+)"', t)
    coul = re.search(r'<fog_colour r="([0-9.]+)" g="([0-9.]+)" b="([0-9.]+)"', t)
    return {"brouillard": float(fog.group(1)), "sommet": float(fog.group(2)),
            "couleur": tuple(float(v) for v in coul.groups()) if coul else (0.6, 0.65, 0.6),
            "soleil": float(re.search(r'sun_colour_scale="([0-9.]+)"', t).group(1)),
            "lut": re.search(r'lut_texture_file="([^"]+)"', t).group(1)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    import projet_expanded as P
    Image.MAX_IMAGE_PIXELS = None
    cyl, p = cylindres()
    couv = np.zeros(len(p), bool)
    for x, z, ri, ro in cyl:
        couv |= np.hypot(p[:, 0] - x, p[:, 1] - z) <= ri
        print(f"  cylindre x {x:.1f} z {z:.1f} : rayons {ri:.1f} / {ro:.1f}")
    print(f"  Arden : {len(p)} hex, {couv.mean() * 100:.1f} % dans un rayon intérieur")
    a, b = reglages_ca(FICHIER_CA), reglages_ca("Weather/campaign/combi/bretonnia.environment")
    print(f"  {FICHIER_CA} : {a}\n  bretonnia (CA, pour comparer) : {b}")
    print("  lignes pour la collection d'Expanded :\n" + lignes_cylindres())
    # aperçu : relief ombré de l'ouest, assombri et voilé du brouillard de CA dans les cylindres (fondu sur la transition)
    h = np.asarray(Image.open(glob.glob(os.path.join(P.DST, "*.height.*.tif"))[0]), np.float32)
    f = h.shape[1] // W
    q0, q1, r0, r1 = 95, 245, 655, 800                     # hex : la forêt et ses abords
    sub = h[(H - r1) * f:(H - r0) * f, q0 * f:q1 * f]
    small = cv2.resize(sub, (sub.shape[1] // 2, sub.shape[0] // 2), interpolation=cv2.INTER_AREA)
    gy, gx = np.gradient(small)
    omb = np.clip(150 + (-gx + gy) * 140, 0, 255).astype(np.float32)
    base = np.stack([omb * 0.55, omb * 0.62, omb * 0.45], -1)
    sh, sw = small.shape
    ys, xs = np.mgrid[0:sh, 0:sw]
    xw = q0 * UX + (xs + 0.5) / sw * (q1 - q0) * UX
    zw = r1 * UZ - (ys + 0.5) / sh * (r1 - r0) * UZ
    poids = np.zeros((sh, sw), np.float32)
    for x, z, ri, ro in cyl:
        poids = np.maximum(poids, np.clip((ro - np.hypot(xw - x, zw - z)) / (ro - ri), 0, 1))
    lum = a["soleil"] / b["soleil"]                          # 0,5 : soleil moitié moins fort
    brou = np.array(a["couleur"]) * 255
    voile = 0.18 * (a["brouillard"] / b["brouillard"] - 1) / 0.54          # brouillard plus dense
    # (premier aperçu : la forêt sortait PLUS CLAIRE, le voile clair l'emportait) soleil ½ : lumière directe ~ −40 %
    rgb = base * (1 - poids[..., None] * (1 - (0.35 + 0.5 * lum)))
    rgb = rgb * (1 - voile * poids[..., None]) + brou * voile * poids[..., None]
    img = Image.fromarray(np.clip(np.concatenate([base, rgb], 1), 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    for x, z, ri, ro in cyl:
        cx, cy = sw + (x - q0 * UX) / ((q1 - q0) * UX) * sw, (r1 * UZ - z) / ((r1 - r0) * UZ) * sh
        for rr, coul in ((ri, (230, 230, 160)), (ro, (150, 150, 110))):
            rx, ry = rr / ((q1 - q0) * UX) * sw, rr / ((r1 - r0) * UZ) * sh
            dr.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=coul, width=2)
    police = ImageFont.truetype("arial.ttf", 14)
    dr.text((8, 8), "aujourd'hui (éclairage global)", fill=(255, 255, 255), font=police)
    dr.text((sw + 8, 8), "proposé : woodelf.environment de CA (soleil ½, brouillard ×1,5)", fill=(255, 255, 255), font=police)
    img.save(APERCU)
    print(f"  aperçu (schéma, pas un rendu du jeu) : {APERCU}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
