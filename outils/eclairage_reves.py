#!/usr/bin/env python3
"""
eclairage_reves.py - l'AMBIANCE du royaume de Slaanesh de CA sur le Bois Rêveur (4.10.2026) : PROPOSITION, à montrer en
image puis à essayer en jeu avant toute adoption (décision de Charles du 25.09.2026, éclairage zone par zone ; erreur 251).

Pourquoi (Charles, 4.10.2026 : « prépare l'ambiance [de Slaanesh] pour le Bois Rêveur ») : sur sa carte des Royaumes du
Chaos (`wh3_main_chaos_map_1`, environment_collection.xml des packs), CA pose sur son royaume de Slaanesh UN cylindre
d'environnement (x 491,3, z 473,0 ; rayon intérieur 70, extérieur 90) qui cite son fichier
`Weather/campaign/chaos/slaanesh.environment` : sans LUT, brouillard violet (0,247 ; 0,055 ; 0,384), densité 0,5, ciel
`skyboxes/tex/campaign_sky_slaanesh_01_base_colour.dds`, soleil à 45 000. On fait de même : des cylindres qui citent CE
fichier de CA, tel quel (rien copié, rien modifié, aucun fichier à nous à un chemin de CA), centrés sur l'île du Bois
Rêveur, avec la transition de CA (20 u entre rayons intérieur et extérieur). Hors des cylindres, l'éclairage global
d'Expanded ne change pas.

Mise en place : la collection d'Expanded est écrite par `build_pack.produits_eclairage` (session « Construction ») ; il
lui suffit d'y ajouter `lignes_cylindres()` et d'en tenir compte dans son contrôle des cylindres (erreur 109).

Usage : python eclairage_reves.py     (bilan, lignes de la collection, aperçu apercus\\eclairage-reves.png)
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H, SUD, UX, UZ                                     # noqa: E402

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APERCU = os.path.join(ICI, "apercus", "eclairage-reves.png")
FICHIER_CA = "Weather/campaign/chaos/slaanesh.environment"
CIEL_CA = "skyboxes/tex/campaign_sky_slaanesh_01_base_colour.dds"
BROUILLARD_CA = (0.247, 0.055, 0.384)
TRANSITION_U = 20.0                   # CA : 90 − 70
COUVERTURE = 0.99                     # part des hex de chaque tranche à l'intérieur de son rayon intérieur
TRANCHES = 5
Z_MAX = SUD * UZ                     # la transition peut couvrir le voile (éther), jamais les Voûtes ni la Saison au nord


def ile():
    """(x, z) Terry des hex de l'île du Bois Rêveur (terre reflétée, hors voile)."""
    import projet_expanded as P
    g = np.load(P.REVES)
    r, q = np.nonzero(g["terre"] & ~g["voile"])
    return np.stack([(q + 0.5) * UX, (r + 0.5) * UZ], 1)


def cylindres():
    """[(x, z, rayon intérieur, rayon extérieur)] : TRANCHES cylindres sur des tranches nord-sud de l'île, comme CA
    couvre une région allongée de plusieurs cylindres ; rayon intérieur = COUVERTURE des hex de la tranche. (Premier
    aperçu, deux cylindres : les coins nord et le bloc nord-est de l'île hors des rayons intérieurs.)"""
    import cv2
    cv2.setRNGSeed(20261004)          # (remarque de la Construction : kmeans++ sans graine, cylindres différents à chaque fois)
    p = ile()
    # (deuxième aperçu, tranches nord-sud : l'île est large, les rayons aussi, les coins nord hors des rayons intérieurs)
    # groupes compacts (k-moyennes) : des cylindres plus petits, au plus près des bords
    _, lab, _ = cv2.kmeans(p.astype(np.float32), TRANCHES, None,
                           (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.01), 10, cv2.KMEANS_PP_CENTERS)
    lab = lab.ravel()
    out = []
    for i in range(TRANCHES):
        moitie = p[lab == i]
        c = moitie.mean(0)
        d = np.hypot(moitie[:, 0] - c[0], moitie[:, 1] - c[1])
        ri = float(np.quantile(d, COUVERTURE))
        ro = ri + TRANSITION_U
        # ne pas déborder au nord du voile : le cylindre s'éloigne vers le sud s'il le faut
        cz = min(float(c[1]), Z_MAX - ro)
        out.append((float(c[0]), cz, ri, ro))
    return out, p


# LES CYLINDRES FIGÉS (x, z, rayon intérieur, rayon extérieur), ceux de l'aperçu approuvé par Charles le 4.10.2026 vers
# 18 h 30 (remarque de la Construction : reproductibilité d'une construction à l'autre). `cylindres()` ne sert plus qu'à
# les recalculer si la grille du Bois Rêveur change ; `main` compare.
CYLINDRES_FIGES = (
    (266.233, 137.661, 34.895, 54.895),
    (217.552, 135.742, 36.815, 56.815),
    (277.700, 89.775, 39.283, 59.283),
    (222.929, 75.658, 42.040, 62.040),
    (253.299, 31.779, 45.080, 65.080),
)


def lignes_cylindres():
    """Les lignes <CYLINDER .../> à ajouter dans <ENVIRONMENT_CYLINDERS> de la collection d'Expanded (format de CA ;
    y = 0 comme nos cylindres, eclairage_wh1) : CYLINDRES_FIGES."""
    return "".join(f"\t\t<CYLINDER serialise_version='1' lighting='{FICHIER_CA}' x='{x:.6f}' y='0.000000' z='{z:.6f}' "
                   f"inner_radius='{ri:.6f}' outer_radius='{ro:.6f}'/>\n" for x, z, ri, ro in CYLINDRES_FIGES)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import glob
    import cv2
    from PIL import Image, ImageDraw
    import projet_expanded as P
    Image.MAX_IMAGE_PIXELS = None
    recalc, p = cylindres()
    cyl = list(CYLINDRES_FIGES)
    ecart = max(abs(a - b) for c1, c2 in zip(sorted(recalc), sorted(cyl)) for a, b in zip(c1, c2))
    print(f"  cylindres figés : {len(cyl)} ; recalculés depuis la grille du Bois Rêveur : écart maximal {ecart:.3f} u"
          + ("" if ecart < 0.01 else " (LA GRILLE A CHANGÉ : refiger après accord de Charles)"))
    for x, z, ri, ro in cyl:
        print(f"  cylindre x {x:.1f} z {z:.1f} : rayons {ri:.1f} / {ro:.1f}")
    couv = np.zeros(len(p), bool)
    for x, z, ri, ro in cyl:
        couv |= np.hypot(p[:, 0] - x, p[:, 1] - z) <= ri
    print(f"  île : {len(p)} hex, {couv.mean() * 100:.1f} % dans un rayon intérieur ; nord au plus z = "
          f"{max(z + ro for x, z, ri, ro in cyl):.1f} (voile à {Z_MAX:.1f})")
    print("  lignes pour la collection d'Expanded :\n" + lignes_cylindres())
    # aperçu : relief ombré du sud, teinté du brouillard de CA dans les cylindres (fondu sur la transition), cercles ; ciel
    # relief du projet du bac à sable, sinon celui du kit (le bac à sable peut être en reconstruction)
    kit = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit\raw_data\terrain\campaigns\saison_expanded_map"
    reliefs = glob.glob(os.path.join(P.DST, "*.height.*.tif")) or glob.glob(os.path.join(kit, "*.height.*.tif"))
    h = np.asarray(Image.open(reliefs[0]), np.float32)
    f = h.shape[1] // W
    bas = h[(H - SUD - 40) * f:H * f]
    small = cv2.resize(bas, (bas.shape[1] // 2, bas.shape[0] // 2), interpolation=cv2.INTER_AREA)
    gy, gx = np.gradient(small)
    omb = np.clip(150 + (-gx + gy) * 140, 0, 255).astype(np.float32)
    rgb = np.stack([omb * 0.55, omb * 0.5, omb * 0.6], -1)
    sh, sw = small.shape
    ys, xs = np.mgrid[0:sh, 0:sw]
    xw = (xs + 0.5) / sw * W * UX
    z_haut = (SUD + 40) * UZ
    zw = z_haut - (ys + 0.5) / sh * z_haut
    poids = np.zeros((sh, sw), np.float32)
    for x, z, ri, ro in cyl:
        d = np.hypot(xw - x, zw - z)
        poids = np.maximum(poids, np.clip((ro - d) / (ro - ri), 0, 1))
    brou = np.array(BROUILLARD_CA) * 255
    rgb = rgb * (1 - 0.45 * poids[..., None]) + brou * 0.45 * poids[..., None]
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    for x, z, ri, ro in cyl:
        for rr, coul in ((ri, (255, 120, 220)), (ro, (180, 90, 160))):
            cx, cy = x / (W * UX) * sw, (z_haut - z) / z_haut * sh
            rx, ry = rr / (W * UX) * sw, rr / z_haut * sh
            dr.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=coul, width=2)
    sys.path.insert(0, os.path.join(P.ATELIER, "02-scripts"))
    try:
        from contenu_pack import SourcePacks
        sp = SourcePacks(r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data",
                         exclure=("saison_des_revelations", "zz_startpos_db", "saison_expanded", "!saison", "!!essai"))
        ciel = Image.open(io.BytesIO(sp.lire(CIEL_CA))).convert("RGB")
        ciel = ciel.resize((sw, max(1, sw // 4)))
        # le ciel de CA est très sombre (moyenne 14, 5, 11) : montré tel quel puis éclairci pour être lisible
        clair = Image.fromarray(np.clip(np.asarray(ciel, np.float32) * 6, 0, 255).astype(np.uint8))
        planche = Image.new("RGB", (sw, sh + 2 * ciel.size[1]), (0, 0, 0))
        planche.paste(img, (0, 0))
        planche.paste(ciel, (0, sh))
        planche.paste(clair, (0, sh + ciel.size[1]))
        img = planche
    except Exception as e:                                       # noqa: BLE001
        print(f"  ciel de CA non lu ({e}) : aperçu sans le ciel")
    img.save(APERCU)
    print(f"  aperçu : {APERCU}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
