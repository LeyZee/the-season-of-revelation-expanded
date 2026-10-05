#!/usr/bin/env python3
"""
textures_reves.py - le sol du BOIS RÊVEUR aux textures du royaume de Slaanesh de CA (4.10.2026), après
`textures_sol_wh1.py` dans la chaîne d'après BOB d'Expanded.

Pourquoi (Charles, 4.10.2026) : « que le miroir d'Athel Loren ce soit vraiment les textures du monde du chaos de
Slaanesh qu'il y a dans la campagne des Royaumes du Chaos… comme c'est le monde démoniaque de Slaanesh, c'est cohérent ».
Relevé dans les packs du jeu : la carte des Royaumes du Chaos (`wh3_main_chaos_map_1`) emploie les groupes de CA
`chaos_relm_slaanesh0..3` (sol du royaume, sombre, bordeaux et prune : veiné, fleuri), DÉJÀ dans la liste compilée
d'Expanded (texture_arrays.xml de BOB, index 12 à 15 au 4.10), donc dans la base de variantes de CA : il suffit que le
mélange (`global_blend.dds`, un index de groupe par pixel, nord en haut) les désigne. Aucun fichier de CA copié ni
remplacé.

Règle : sur la TERRE reflétée du Bois Rêveur (`projet_expanded.bois_reveur`, hors voile, au-dessus de l'eau), chaque
pixel prend une variante du royaume selon le sol qu'il portait (la variété d'Athel Loren gardée) : prairies -> fleuri
(3), forêt, herbe morte, marais -> veiné sombre (0), sable, boue -> rougeâtre (2), neige, glace, roche -> (1). Pas de
corruption rampante : l'inventaire de wh3_main_chaos_map_1 (4.10.2026) montre que le royaume de CA n'emploie que
chaos_relm_slaanesh0..3, aucun creep_slaanesh (premier jet : creep sur la lisière, retiré). La marque de
textures_sol_wh1 est complétée (le contrôle de build_pack compare son âge à celui du mélange).

Usage : python textures_reves.py [--apply]     (SAISON_CARTE=expanded)
"""
import argparse
import glob
import os
import re
import shutil
import struct
import sys
import time

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H                                            # noqa: E402

Image.MAX_IMAGE_PIXELS = None
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
COMPILE = os.path.join(KIT, r"working_data\terrain\campaigns\saison_expanded_map\global_map")
ATELIER = r"C:\TotalWar-CampaignMap"
TERRY = os.path.join(KIT, r"raw_data\terrain\campaigns\saison_expanded_map")      # le projet posé, celui que BOB a compilé
SAUVEGARDES = os.path.join(ATELIER, r"05-journal\terrain-backups")
MARQUE = "saison_textures_wh1.txt"
# variante (0..3) selon le nom du groupe porté avant
REGLES = ((r"grass_a", 3), (r"grass_b|grass_dead|marsh|forest", 0), (r"sand|mud|dirt", 2), (r"snow|ice|scree|rock", 1))


def variante(nom):
    for motif, v in REGLES:
        if re.search(motif, nom):
            return v
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import projet_expanded as P
    xml = os.path.join(COMPILE, "texture_arrays.xml")
    blend = os.path.join(COMPILE, "global_blend.dds")
    groupes = re.findall(r"<group>([^<]+)</group>", open(xml, encoding="utf-8").read())
    roy = [groupes.index(f"chaos_relm_slaanesh{i}") for i in range(4)]
    creep = [groupes.index(f"creep_slaanesh{i}") for i in range(4)]
    b = bytearray(open(blend, "rb").read())
    h, w = struct.unpack_from("<II", b, 12)
    ent = len(b) - h * w
    mel = np.frombuffer(bytes(b[ent:]), np.uint8).reshape(h, w).copy()
    f = w // W
    reste = h - H * f
    _, net, _, voile = P.bois_reveur(f, reste)
    haut = np.asarray(Image.open(glob.glob(os.path.join(TERRY, "*.height.*.tif"))[0]), np.float32)
    haut = cv2.resize(haut, (w, h), interpolation=cv2.INTER_AREA) if haut.shape != (h, w) else haut
    terre = net & ~voile & (haut > 0.05)
    table_roy = np.array([roy[variante(g)] for g in groupes] + [roy[0]] * (256 - len(groupes)), np.uint8)
    neuf = mel.copy()
    # (un passage déjà fait : un pixel déjà au royaume garde sa variante ; un pixel en corruption rampante du premier
    # jet reprend la variante correspondante du royaume)
    for i, c in enumerate(creep):
        table_roy[c] = roy[i]
    for c in roy:
        table_roy[c] = c
    neuf[terre] = table_roy[mel[terre]]
    deja = int(np.isin(mel[terre], roy).mean() * 100) if terre.any() else 0
    print(f"  groupes du royaume de Slaanesh dans la liste : {roy}")
    print(f"  Bois Rêveur : {int(terre.sum())} px au sol du royaume ; déjà au royaume avant : {deja} % ; "
          f"pixels changés : {int((neuf != mel).sum())}")
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(blend, os.path.join(SAUVEGARDES, f"global_blend-avant-reves-{stamp}.dds"))
    b[ent:] = neuf.tobytes()
    with open(blend, "wb") as fh:
        fh.write(bytes(b))
    with open(os.path.join(COMPILE, MARQUE), "a", encoding="utf-8") as fh:
        fh.write(f"Bois Rêveur aux groupes de Slaanesh de CA (textures_reves.py) {stamp}\n")
    print(f"  écrit : {blend} (sauvegarde global_blend-avant-reves-{stamp}.dds) ; marque complétée")
    return 0


if __name__ == "__main__":
    sys.exit(main())
