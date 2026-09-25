#!/usr/bin/env python3
"""
grille_expanded.py - la grille hex de Saison Expanded dans CAIME (phase 2), dans le bac à sable du chantier.

Pourquoi (25.09.2026, Charles : « attaque la phase 2 aujourd'hui ») : la carte agrandie (560 × 825 hex, `carte_config`
profil « expanded ») a besoin de sa grille CAIME : la Saison au centre, telle quelle, et la terre de l'extension autour,
hors jeu et infranchissable (première étape : décor), d'après l'Atlas (source unique ; session « Extension »).

Ce que fait le script (rien dans le kit : la carte vit dans `04-projets\\saison-expanded\\caime\\`) :
1. lit les couches de la Saison (`04-projets\\saison-des-revelations\\couches-slots\\`, 400 × 440, indices du map.hex de
   la Saison) et les renumérote par NOM vers les listes de la carte Expanded (CAIME `info --names`) ;
2. les pose dans la grille 560 × 825 au décalage (x + 120, y + 250) (ligne 0 = sud, comme CAIME et l'Atlas) ;
3. hors du cadre de la Saison : types de sol de l'Atlas (`extension_regions.npz`, `biome` = index CAIME à plat, terre
   puis mer), rivières de l'Atlas, tout infranchissable ; la bande du sud (Bois des Rêves) reste vide en attendant les
   grilles de la session « Extension » ;
4. écrit les couches (`couches-expanded\\`) et les importe dans la carte (CAIME `import-layer`), puis exporte des PNG
   de contrôle (`export-layer --format png`).
Régions, emplacements de colonie et routes commerciales ne sont pas encore posés (les régions de la carte Expanded ne
sont pas déclarées dans la base).

Usage :
    python grille_expanded.py [--sans-import]
"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, encode_flat, caime_names, flat_names    # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
CARTE_SAISON = os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex")
COUCHES_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE_EXP = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
SORTIE = os.path.join(ICI, "couches-expanded")
ATLAS = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
W, H = 560, 825
DX, DY = 120, 250                  # place de la Saison (400 × 440) dans la grille
SW, SH = 400, 440
Y0_ATLAS = 250                     # la ligne 0 de l'Atlas (y = 0) est la ligne 250 de la grille
COUCHES = ("GroundTypes", "Climates", "Attritions", "Impassable", "Rivers", "Roads", "Beaches", "Bridges")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-import", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    src, sw, sh = caime_names(CAIME, CARTE_SAISON)
    dst, dw, dh = caime_names(CAIME, CARTE_EXP)
    assert (sw, sh) == (SW, SH) and (dw, dh) == (W, H), ((sw, sh), (dw, dh))
    g = np.load(os.path.join(ATLAS, "extension_geo.npz"))
    r = np.load(os.path.join(ATLAS, "extension_regions.npz"))
    ha, wa = r["biome"].shape                                      # 575, 560 ; ligne 0 = y 0 (sud), colonne = x + 120
    cadre = np.zeros((H, W), bool)
    cadre[DY:DY + SH, DX:DX + SW] = True
    atlas = np.zeros((H, W), bool)
    atlas[Y0_ATLAS:Y0_ATLAS + ha, :wa] = True
    hors = atlas & ~cadre                                          # l'extension dessinée par l'Atlas
    couches = {}
    for f in sorted(os.listdir(COUCHES_SAISON)):
        nom, v = read_layer(os.path.join(COUCHES_SAISON, f))
        if nom not in COUCHES:
            continue
        v = v.reshape(SH, SW)
        if nom in ("GroundTypes", "Climates", "Attritions"):
            s_noms = flat_names(src, nom)
            d_index = {n: i for i, n in enumerate(flat_names(dst, nom))}
            table = np.array([d_index.get(n, -1) for n in s_noms] + [-1])
            absents = sorted({s_noms[i] for i in np.unique(v) if i >= 0 and s_noms[i] not in d_index})
            v = np.where(v < 0, -1, table[np.clip(v, 0, None)])
            if absents:
                print(f"  {nom} : noms absents de la carte Expanded : {absents}")
        grille = np.full((H, W), -1 if nom in ("GroundTypes", "Climates", "Attritions") else 0, np.int64)
        grille[DY:DY + SH, DX:DX + SW] = v
        couches[nom] = grille
    # l'extension, d'après l'Atlas. (25.09.2026, 17 h 25, mesure `accord_saison_atlas.py`) : sur la partie JOUABLE de la
    # Saison, l'Atlas reprend nos couches à 98,5 % (on garde la Saison, WH1 à 100 %) ; sur sa bordure non jouable (décor
    # uniforme de WH1), à 61 % seulement : l'Atlas y a dessiné 25 680 hex de régions neuves (Artois, Grung Zint,
    # Helmgart...). L'Atlas vaut donc partout hors de la partie jouable de la Saison.
    jouable = cadre & (couches["Impassable"] == 1)
    hors = atlas & ~jouable
    biome = np.full((H, W), -1, np.int64)
    biome[Y0_ATLAS:Y0_ATLAS + ha, :wa] = r["biome"].astype(np.int64)
    couches["GroundTypes"] = np.where(hors, biome, couches["GroundTypes"])
    riv = np.zeros((H, W), np.int64)
    riv[Y0_ATLAS:Y0_ATLAS + ha, :wa] = g["riv_ext"].astype(np.int64)
    couches["Rivers"] = np.where(hors, riv, couches["Rivers"])
    couches["Impassable"] = np.where(cadre, couches["Impassable"], 0)      # 1 = franchissable ; hors Saison : non
    for nom in ("Roads", "Beaches", "Bridges"):
        couches[nom] = np.where(cadre, couches[nom], 0)
    os.makedirs(SORTIE, exist_ok=True)
    args = [CAIME, "import-layer", "--map", CARTE_EXP]
    for nom, grille in couches.items():
        chemin = os.path.join(SORTIE, f"layer_{nom.lower()}.hex_layer")
        with open(chemin, "wb") as fh:
            fh.write(encode_flat(nom, grille.reshape(-1)))
        args += ["--layer", nom, "--file", chemin]
        pose = int((grille >= 0).sum()) if nom in ("GroundTypes", "Climates", "Attritions") else int((grille != 0).sum())
        print(f"  {nom:12s} {pose:7d} hex posés")
    sols = flat_names(dst, "GroundTypes")
    comptes = np.bincount(couches["GroundTypes"][hors & (couches["GroundTypes"] >= 0)], minlength=len(sols))
    print("  extension (hors Saison) : " + ", ".join(f"{sols[i]} {c}" for i, c in enumerate(comptes) if c))
    print(f"  bande du sud (Bois des Rêves, lignes 0-{Y0_ATLAS - 1}) : vide, en attente de l'Atlas")
    if a.sans_import:
        return 0
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved" in l or "rror" in l))
    png = os.path.join(ICI, "caime", "export-png")
    shutil.rmtree(png, ignore_errors=True)
    p = subprocess.run([CAIME, "export-layer", "--map", CARTE_EXP, "--out", png, "--layer", "GroundTypes",
                        "--layer", "Impassable", "--layer", "Rivers", "--format", "png"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "xport" in l or "rror" in l))
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
