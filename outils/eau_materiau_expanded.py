#!/usr/bin/env python3
"""
eau_materiau_expanded.py - les matériaux d'eau d'Expanded et leurs masques (3.10.2026), à la manière de la Saison.

Pourquoi (Charles : « attaque tout ça » ; liste « ce qui manque avant le jeu », point 2) : le matériau d'eau d'une campagne
de WH3 est propre à sa carte (masque A : mer en alpha, rivières et lacs en bleu ; masque de flux), et ses masques se lisent
à uv = (x / largeur, 1 − z / profondeur) du monde (`masques_eau_carte.py`, session « IA et modding 3D », hors ligne ce
jour). Expanded employait celui de la Saison : ses masques, faits pour un monde de 266,53 × 338,9, auraient été étirés sur
373,14 × 697,06 (mer et rivières décalées, rides de la mauvaise taille).

Ce module ne modifie pas `masques_eau_carte.py` : il en importe les fonctions et lui donne le monde d'Expanded :
- mer : la surface du relief d'Expanded à 0,02 (mers, éther et déchirure, `projet_expanded`) et ses plans de mer ;
- rivières : l'eau des rivières de WH1 de la Saison (`relief-wh1\\eau_rivieres.npy`) posée à sa place dans le monde, dans
  la zone de WH1 gardée ; leur courant (`flux_rivieres.npy`) de même ; les rivières de l'Atlas n'ont pas encore d'eau ;
- lacs : les plans de lac de WH1 recopiés dans le projet d'Expanded ;
- bruits de CA à l'échelle du monde d'Expanded.
Sorties (`04-projets\\saison-expanded\\eau-carte\\`, à embarquer par build_pack) : trois matériaux à clés à nous,
`saison_expanded_campaign_water_plane` (mer et rivières), `saison_expanded_campaign_lake_plane` (lacs),
`saison_expanded_ether_plane` (l'éther du Bois Rêveur : même eau, couleur violette de son calque de couleur, mais calme et
lisse, sans écume ni vagues de rivage) ; masques `sea/saison_expanded_a_mask.dds` et `..._combined_flow_mask.dds`.
`eau_expanded` et `projet_expanded` font pointer les plans d'eau d'Expanded sur ces matériaux.

Usage : python eau_materiau_expanded.py [--apply]
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, SW, SH, DX, DY, DY_HAUT                 # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
import masques_eau_carte as M                                            # noqa: E402
import bc7                                                               # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
TERRY = os.path.join(ICI, r"terry\saison_expanded_map")
SORTIE = os.path.join(ICI, "eau-carte")
RELIEF_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\relief-wh1")
CLE = "saison_expanded"
MATERIAU_MER = f"materials/environment/campaign_sea/{CLE}_campaign_water_plane.xml.material"
MATERIAU_LAC = f"materials/environment/campaign_sea/{CLE}_campaign_lake_plane.xml.material"
MATERIAU_ETHER = f"materials/environment/campaign_sea/{CLE}_ether_plane.xml.material"
MASQUE_A = f"sea/{CLE}_a_mask.dds"
FLUX = f"sea/{CLE}_combined_flow_mask.dds"
# l'éther : une eau d'un autre monde, immobile et lisse (le violet vient de son calque de couleur, projet_expanded)
PARAMETRES_ETHER = dict(M.PARAMETRES_EAU, foam_falloff="40", whitewater_strength_rivers="0.0")
REGLAGES_ETHER = {"foam_strength": "0.02", "foam_strength_storm": "0.02", "whitewater_strength_sea": "0.05",
                  "shore_wave_diffuse_strength": "0.1", "shore_wave_range": "0.1", "roughness": "0.01",
                  "wave_height_scale": "0.05", "wave_flow_speed_1": "0.01", "wave_flow_speed_2": "0.008",
                  "caustics_intensity_sea": "1.5", "darkness_at_min": "0.95"}

# le monde d'Expanded dans le module de la Saison (lecture seule de ses données)
M.LARGEUR = 266.53 * W / SW                     # 373,142
M.PROFONDEUR = 338.9 * H / SH                   # 697,06
M.PROJET = TERRY


def placer(a, remplissage):
    """Raster de la Saison (8 px par hex, nord en haut, 3524 × 3200) posé dans le monde d'Expanded (7244 × 4480)."""
    hh, ww = H * 8 + (a.shape[0] - SH * 8), W * 8
    out = np.empty((hh, ww) + a.shape[2:], a.dtype)
    out[...] = remplissage
    y0, x0 = DY_HAUT * 8, DX * 8
    out[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
    return out


def garde_px(forme):
    import projet_expanded
    g = projet_expanded.garde_masque(8, forme[0] - H * 8)
    return g


def donnees():
    hauteur = np.asarray(Image.open(glob.glob(os.path.join(TERRY, "*.height.*.tif"))[0]), np.float32)
    # (5.10.2026) la mer = les tuiles de mer (et lacs) : le relief n'est plus à 0,02 près des côtes (relief continu sous
    # l'eau, comme CA, cotes_relief) ; plus le relief sous l'eau (plages qui passent sous la surface)
    import mer_tuiles
    mer_px = mer_tuiles.mer_px(hauteur.shape) | (hauteur <= 0.035)
    riv_s = np.isfinite(np.load(os.path.join(RELIEF_SAISON, "eau_rivieres.npy")))
    riv = placer(riv_s, False) & garde_px(hauteur.shape)
    # (4.10.2026) les rivières de l'Atlas, qui ont maintenant leur eau (rivieres_atlas_eau.py, même champ)
    import rivieres_atlas_eau
    ch, _ = rivieres_atlas_eau.champ_et_niveau(hauteur)
    riv = riv | (ch >= 0.45)
    riv = M.adoucir(riv, 1.5)
    return mer_px, np.where(mer_px, 0.0, riv), ["mer : relief d'Expanded à 0,02",
                                                "rivières : WH1 de la Saison placées + Atlas"]


def flux_rivieres(Hh, Ll):
    f = np.load(os.path.join(RELIEF_SAISON, M.FLUX_RIVIERES))
    f = placer(f, np.nan)
    f[~garde_px(f.shape[:2])] = np.nan
    valide = np.isfinite(f).all(axis=2)
    e, n = M.vers_est_nord(np.where(valide, f[..., 0], 0), np.where(valide, -f[..., 1], 0))
    couv = M._reduire_f(valide.astype(np.float32), M.N)
    se, sn = M._reduire_f(np.where(valide, e, 0), M.N), M._reduire_f(np.where(valide, n, 0), M.N)
    l = np.hypot(se, sn)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(l > 0, se / l, 0.0), np.where(l > 0, sn / l, 0.0), couv


def plans(lac):
    """Polygones monde des plans d'eau du projet d'Expanded : de lac (lake_plane) ou de mer (tous les autres)."""
    out = []
    for f in glob.glob(os.path.join(TERRY, "*.layer")):
        s = open(f, encoding="utf-8", errors="replace").read()
        if "campaign_sea" not in s:
            continue
        for m in re.finditer(r'<entity id="[^"]*">(.*?)</entity>', s, re.S):
            b = m.group(1)
            mm = re.search(r'<ECPolygonMesh material="([^"]*campaign_sea[^"]*)"', b)
            if not mm or (("lake_plane" in mm.group(1)) != lac):
                continue
            p = re.search(r'<ECTransform position="([^ ]+) ([^ ]+) ([^ "]+)" rotation="[^ ]+ ([^ ]+) ', b)
            x, z, rot = float(p.group(1)), float(p.group(3)), np.radians(float(p.group(4)))
            pts = [(float(a), float(c)) for a, c in re.findall(r'<point x="([^"]+)" y="([^"]+)"/>', b)]
            out.append([(x + a * np.cos(rot) + c * np.sin(rot), z - a * np.sin(rot) + c * np.cos(rot)) for a, c in pts])
    return out


def renommer(octets, nom_interne):
    t = octets.decode("utf-8")
    t = re.sub(r"<name>[^<]*_plane\.xml</name>", f"<name>{nom_interne}</name>", t, count=1)
    t = t.replace("Sea/wh_dlc05_wood_elves_a_mask.dds", f"Sea/{CLE}_a_mask.dds")
    t = t.replace("Sea/wh_dlc05_wood_elves_combined_flow_mask.dds", f"Sea/{CLE}_combined_flow_mask.dds")
    assert f"Sea/{CLE}_a_mask.dds" in t and f"Sea/{CLE}_combined_flow_mask.dds" in t
    return t.encode("utf-8")


def ether(octets):
    t = octets.decode("utf-8")
    for nom, valeur in REGLAGES_ETHER.items():
        motif = re.compile(rf"(<name>{nom}</name>\s*<type>float</type>\s*<value>)([^<]*)(</value>)")
        if len(motif.findall(t)) != 1:
            raise SystemExit(f"matériau : {nom} introuvable ou en double")
        t = motif.sub(lambda m, v=valeur: m.group(1) + v + m.group(3), t)
    return t.encode("utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    M.donnees = donnees
    M.flux_rivieres = flux_rivieres
    M.lacs = lambda mer=False: plans(lac=not mer)
    masque_a, flux, bilan = M.construire()
    print(f"  monde {M.LARGEUR:.2f} × {M.PROFONDEUR:.2f} ; masque A {M.N} × {M.N} : mer {bilan['mer'] * 100:.1f} % ; "
          f"rivières et lacs {bilan['rivieres_lacs'] * 100:.2f} % ({bilan['lacs']} lacs) ; " + " ; ".join(bilan["sources"]))
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    fichiers = {
        MATERIAU_MER: renommer(M.materiau(), f"{CLE}_campaign_water_plane.xml"),
        MATERIAU_LAC: renommer(M.materiau(M.PARAMETRES_LAC), f"{CLE}_campaign_lake_plane.xml"),
        MATERIAU_ETHER: ether(renommer(M.materiau(PARAMETRES_ETHER), f"{CLE}_ether_plane.xml")),
        MASQUE_A: bc7.dds_bc7(bc7.chaine(masque_a), srgb=False),
        FLUX: bc7.dds_bc7(bc7.chaine(flux), srgb=False),
    }
    for chemin, octets in fichiers.items():
        dest = os.path.join(SORTIE, *chemin.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(octets)
        print(f"  écrit {dest} ({len(octets) / 1e6:.2f} Mo)")
    apercu = np.zeros((M.N, M.N, 3), np.uint8)
    apercu[..., 0] = masque_a[..., 3] // 2
    apercu[..., 1] = masque_a[..., 2]
    apercu[..., 2] = np.maximum(masque_a[..., 3], masque_a[..., 2])
    p = os.path.join(ICI, "apercus", "eau-masque-expanded.png")
    Image.fromarray(apercu).resize((M.N // 2, M.N // 2), Image.LANCZOS).save(p)
    print(f"  contrôle : {p} (violet = mer, cyan = rivières et lacs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
