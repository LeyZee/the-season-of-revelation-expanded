#!/usr/bin/env python3
"""
kit_expanded.py - pose d'Expanded dans l'Assembly Kit (3.10.2026), sous préavis, avec sauvegardes. À blanc par défaut.

Étapes (`--apply` pour écrire) :
1. `raw_data\\db\\campaign_map_playable_areas.xml` (sauvegarde `05-journal\\db-backups\\<horodatage>-avant-ligne-expanded\\`) :
   - la ligne de `saison_expanded_map` ne doit pas être la DERNIÈRE du fichier (guide CAIME, « le piège de la dernière
     ligne » : l'export Map Data plante) : elle passe avant celle de `ile_claude_map` ;
   - sa zone jouable couvrait encore la Saison décalée (x 79,96 à 346,49 ; z 254,17 à 593,07) : la caméra n'aurait pas
     atteint la Bretonnie du nord, les Voûtes ni le Bois Rêveur ; elle couvre désormais le monde entier
     (0 à world_width = 373,142 ; 0 à 905 rangées × 338,9/440 = 697,07) ;
2. la grille CAIME et ses fichiers d'appui -> `raw_data\\EmpireDesignData\\campaign_maps\\saison_expanded_map\\` ;
3. le projet Terry -> `raw_data\\terrain\\campaigns\\saison_expanded_map\\`.
Un dossier de destination existant est d'abord rangé dans `05-journal\\terrain-backups\\`.
Usage : python kit_expanded.py [--apply]
"""
import argparse
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H                                        # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
ATELIER = r"C:\TotalWar-CampaignMap"
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE = "saison_expanded_map"
ZONES = os.path.join(KIT, r"raw_data\db\campaign_map_playable_areas.xml")
LARGEUR, PROFONDEUR = 266.53 * W / 400, 338.9 * H / 440


def zones(texte):
    """Le fichier de la base, la ligne d'Expanded déplacée avant celle d'ile_claude_map, sa zone élargie."""
    blocs = list(re.finditer(r"<campaign_map_playable_areas\b.*?</campaign_map_playable_areas>\r?\n", texte, re.S))
    exp = next(b for b in blocs if f"<mapname>{CARTE}</mapname>" in b.group(0))
    ile = next(b for b in blocs if "<mapname>ile_claude_map</mapname>" in b.group(0))
    ligne = exp.group(0)
    for cle, val in (("minx", 0.0), ("maxx", LARGEUR), ("miny", 0.0), ("maxy", PROFONDEUR)):
        ligne = re.sub(rf"<{cle}>[^<]*</{cle}>", f"<{cle}>{val:.2f}</{cle}>", ligne, count=1)
    sans = texte[:exp.start()] + texte[exp.end():]
    pos = sans.index(ile.group(0))
    return sans[:pos] + ligne + sans[pos:], ligne


def ranger(dossier, etiquette):
    if os.path.exists(dossier):
        dst = os.path.join(ATELIER, r"05-journal\terrain-backups", f"{time.strftime('%Y%m%d-%H%M%S')}-{etiquette}")
        shutil.move(dossier, dst)
        print(f"  rangé : {dossier} -> {dst}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t = open(ZONES, encoding="utf-8", newline="").read()
    neuf, ligne = zones(t)
    ordre = re.findall(r"<mapname>([^<]*)</mapname>", neuf)
    print(f"  1. zones jouables : ordre {ordre} ; Expanded : x 0 à {LARGEUR:.2f}, z 0 à {PROFONDEUR:.2f} ; "
          f"dernière ligne : {ordre[-1]}")
    assert ordre[-1] != CARTE and len(ordre) == len(re.findall(r"<mapname>", t))
    src_c = os.path.join(ICI, "caime", CARTE)
    dst_c = os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps", CARTE)
    src_t = os.path.join(ICI, "terry", CARTE)
    dst_t = os.path.join(KIT, r"raw_data\terrain\campaigns", CARTE)
    print(f"  2. {len(os.listdir(src_c))} fichiers -> {dst_c} (existe : {os.path.exists(dst_c)})")
    print(f"  3. {len(os.listdir(src_t))} fichiers -> {dst_t} (existe : {os.path.exists(dst_t)})")
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    # (5.10.2026, Construction : une date qui bouge sans changement fausse les contrôles d'après une mise à jour du jeu,
    # instantane_jeu, erreur 290) le fichier de la base n'est réécrit que si son contenu change
    if neuf == t:
        print("  1. zones jouables déjà à jour : rien d'écrit")
    else:
        sauve = os.path.join(ATELIER, r"05-journal\db-backups", f"{time.strftime('%Y%m%d-%H%M%S')}-avant-ligne-expanded")
        os.makedirs(sauve)
        shutil.copy2(ZONES, sauve)
        open(ZONES, "w", encoding="utf-8", newline="").write(neuf)
        print(f"  1. écrit (sauvegarde {sauve})")
    ranger(dst_c, "campaign_maps-saison_expanded_map")
    shutil.copytree(src_c, dst_c)
    print(f"  2. écrit : {dst_c}")
    ranger(dst_t, "terrain-saison_expanded_map")
    shutil.copytree(src_t, dst_t)
    print(f"  3. écrit : {dst_t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
