#!/usr/bin/env python3
"""
rivieres_atlas_eau.py - l'EAU des rivières de l'Atlas dans Expanded (4.10.2026) : jusque-là, des lits secs.

Pourquoi (Charles, 3.10.2026 : « de la vie… rien laissé au hasard » ; reste ouvert dans REPRISE.md) : `projet_expanded`
creuse les lits des rivières de l'Atlas (`rivieres_atlas.champ`, PROFONDEUR_LIT sous les berges, hors de la zone gardée
de WH1 et de la mer), mais aucune eau n'y coule ; celles de WH1 ont leurs maillages (`rivieres_wh1.py`, recopiés par
`rivieres_maillages_expanded.py`). Même méthode que l'eau lisse de WH1 (`rivieres_wh1.construire_lisse` : contour du
champ à SEUIL_MAILLAGE en marching squares, maillages de TUILE_EAU px au format des rivières des Empires, matériau d'eau de
la mer), avec :
- champ : celui des lits de l'Atlas, hors de la zone gardée de WH1 et de la mer (relief à 0,035 et moins) ;
- niveau : le fond du lit (relief du projet, déjà creusé), minimum sur une fenêtre puis lissé, + HAUTEUR_EAU : l'eau reste
  sous les berges (lit de 0,17), dans la convention de WH1 (eau sous la berge la plus basse) ;
- noms `river_atlas_cXX_YY` (jamais ceux de WH1), matériau d'eau d'Expanded (`eau_expanded.MATERIAU_MER`).
Sorties : calque `rivieres_atlas` dans le projet Terry d'Expanded (déclaré dans le .terry) et maillages dans
`04-projets\\saison-expanded\\rivieres-wh1\\terrain\\campaigns\\saison_expanded_map\\models\\` (embarqués avec ceux de WH1).
Les masques d'eau (`eau_materiau_expanded`) prennent ces rivières par le même champ.

Usage : python rivieres_atlas_eau.py [--apply]       (appelé aussi par projet_expanded)
"""
import argparse
import glob
import hashlib
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image

os.environ.setdefault("SAISON_CARTE", "expanded")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H                                            # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
Image.MAX_IMAGE_PIXELS = None
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CLE = "saison_expanded_map"
TERRY = os.path.join(ICI, "terry", CLE)
MODELES = os.path.join(ICI, r"rivieres-wh1\terrain\campaigns", CLE, "models")
F = 8                                        # px par hex des rasters du projet
PAS = F / (266.53 / 400)                     # px par unité du monde (12,006)
HAUTEUR_EAU = 0.10                           # au-dessus du fond du lit (lit de 0,17 sous les berges)
FENETRE_FOND = 9                             # px
NIVEAU_MER = 0.035


def champ_et_niveau(height):
    import rivieres_atlas
    import projet_expanded
    reste = height.shape[0] - H * F
    ch = rivieres_atlas.champ(F, reste)
    garde = projet_expanded.garde_masque(F, reste)
    # (5.10.2026) jamais sur une tuile de mer (le relief y est continu avec la côte, plus à 0,02 : mer_tuiles)
    import mer_tuiles
    sur_mer = mer_tuiles.mer_px(height.shape) if os.path.exists(mer_tuiles.TUILES) else np.zeros(height.shape, bool)
    ch = np.where(garde | (height <= NIVEAU_MER) | sur_mer, 0.0, ch).astype(np.float32)
    eau = ch >= 0.2
    fond = cv2.erode(np.where(eau, height, 99.0).astype(np.float32), np.ones((FENETRE_FOND, FENETRE_FOND), np.uint8))
    fond = np.where(eau, np.minimum(fond, height), np.nan)
    # lissé le long de l'eau (moyenne pondérée sur ~1 hex, sans déborder hors de l'eau)
    w = cv2.GaussianBlur(eau.astype(np.float32), (0, 0), F / 2)
    s = cv2.GaussianBlur(np.nan_to_num(fond).astype(np.float32), (0, 0), F / 2)
    niveau = np.where(eau, s / np.maximum(w, 1e-6) + HAUTEUR_EAU, np.nan)
    # (4.10.2026) jamais au-dessus de la berge la plus basse alentour (sol hors du lit à moins d'un hex) : sinon le bord
    # du maillage pend au-dessus d'une berge plus basse
    berge = cv2.erode(np.where(eau, 99.0, height).astype(np.float32), np.ones((F + 1, F + 1), np.uint8))
    # (5.10.2026, Charles : « des rivières pas bien dessinées » ; 188 hex de tracé sans eau, surtout des torrents de
    # montagne) sur une pente raide, la « berge la plus basse » à un hex est la pente AVAL, sous le lit lui-même : le
    # plafond vidait le torrent. Seule une vraie berge (au-dessus du fond du lit) plafonne le niveau
    vraie = (berge < 90) & (berge > fond + 0.02)
    niveau = np.where(eau & vraie, np.minimum(niveau, berge - 0.01), niveau)
    niveau = np.where(eau, np.maximum(niveau, NIVEAU_MER), np.nan)        # jamais sous la mer
    # (4.10.2026, controle_anomalies : 3 791 px de bord d'eau au-dessus de la berge) : le maillage ne couvre que le lit
    # EN EAU (sol sous le niveau) ; son bord tombe là où l'eau rencontre la berge, plus jamais en l'air
    ch = np.where(np.isfinite(niveau) & (niveau > height + 0.004), ch, 0.0).astype(np.float32)
    # (4.10.2026, essai rejeté : berge prise hors du maillage, deux passes -> 83 px en l'air au lieu de 41 et 22 % d'eau
    # en moins ; le contour se resserre et découvre d'autres bords. Les 41 px restants : marches où le lit descend)
    return ch, niveau.astype(np.float64)


def construire(height):
    import rivieres_wh1 as RW
    import eau_expanded
    ch, niveau = champ_et_niveau(height)
    # dossier provisoire : construire_lisse refuse un nom déjà présent dans le jeu, or le pack d'Expanded (data\) porte
    # les river_wh1_cXX_YY de WH1 au chemin d'Expanded ; on renomme ensuite en river_atlas_cXX_YY
    tmp = f"terrain/campaigns/{CLE}/models_atlas_tmp"
    RW.DOSSIER_MODELES = tmp
    entites, fichiers = RW.construire_lisse(niveau, ch.astype(np.float64), PAS, ecrire=False, mer=None)
    vrai = f"terrain/campaigns/{CLE}/models/river_atlas_c"
    renomme = {}
    for chemin, octets in fichiers.items():
        neuf = chemin.replace(tmp + "/river_wh1_c", vrai)
        if chemin.endswith(".wsmodel"):
            t = octets.decode("utf-8").replace(tmp + "/river_wh1_c", vrai)
            t = re.sub(r"(<material [^>]*>)[^<]*(</material>)", lambda m: m.group(1) + eau_expanded.MATERIAU_MER + m.group(2), t)
            octets = t.encode("utf-8")
        renomme[neuf] = octets
    entites = [e.replace(tmp + "/river_wh1_c", vrai) for e in entites]
    if any("models_atlas_tmp" in e for e in entites) or any("river_wh1" in k for k in renomme):
        raise SystemExit("rivières de l'Atlas : chemin provisoire resté")
    entites = [re.sub(r'<entity id="[^"]*">', lambda m, i=i: f'<entity id="1{hashlib.sha1(f"saison_expanded/rivieres_atlas/{i}".encode()).hexdigest()[:14]}">', e, count=1)
               for i, e in enumerate(entites)]
    entites = [recaler_z(e, height.shape[0]) for e in entites]
    return entites, renomme, int((ch >= 0.25).sum())


def recaler_z(entite, lignes):
    """(4.10.2026) construire_lisse place les maillages par la règle de la Saison (z = (lignes − 1,5 − i) / pas · 2/√3,
    juste pour 3 524 lignes / 338,9 u) ; le raster d'Expanded (7 244 lignes) est étiré sur Z_MONDE = 697,06 u
    (cadre_expanded.px_de) : sans recalage, l'eau était posée jusqu'à 0,45 u (un demi-hex) au sud de son lit au nord de
    la carte. Le centre du maillage est ramené à la ligne de pixel qu'il visait ; dans une tuile, l'écart d'échelle
    (0,05 %) reste sous le pixel."""
    from cadre_expanded import Z_MONDE

    def z_vrai(m):
        i = lignes - 1.5 - float(m.group(4)) * PAS * 3 ** 0.5 / 2
        return f"{m.group(1)}{m.group(2)} {m.group(3)} {Z_MONDE - (i + 0.5) * Z_MONDE / lignes:.5f}{m.group(5)}"
    return re.sub(r'(<ECTransform position=")([-0-9.eE]+) ([-0-9.eE]+) ([-0-9.eE]+)(")', z_vrai, entite, count=1)


def poser(dst, cle, height, ecrire_modeles=True):
    """Écrit le calque `rivieres_atlas` dans le projet `dst` et les maillages dans MODELES ; rend le nombre de maillages."""
    import decors_expanded
    entites, fichiers, n_px = construire(height)
    texte = ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- rivieres_atlas -->\n<layer version="41">\n\t<entities>\n'
             + "".join(entites) + "\t</entities>\n\t<associations>\n\t\t<Logical/>\n\t\t<Transform/>\n\t</associations>\n"
             "</layer>\n")
    decors_expanded.declarer(dst, cle, "rivieres_atlas", texte)
    if ecrire_modeles:
        for f in glob.glob(os.path.join(MODELES, "river_atlas_c*")):
            os.remove(f)                     # sortie générée, refaite à chaque fois (comme rivieres_wh1)
        for chemin, octets in fichiers.items():
            p = os.path.join(MODELES, os.path.basename(chemin))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(octets)
    print(f"  eau des rivières de l'Atlas : {len(entites)} maillages, {n_px} px d'eau ({n_px / F / F:.0f} hex)")
    return len(entites)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    height = np.asarray(Image.open(glob.glob(os.path.join(TERRY, "*.height.*.tif"))[0]), np.float32)
    if not a.apply:
        entites, fichiers, n_px = construire(height)
        print(f"  à blanc : {len(entites)} maillages, {n_px} px d'eau ; rien d'écrit")
        return 0
    poser(TERRY, CLE, height)
    return 0


if __name__ == "__main__":
    sys.exit(main())
