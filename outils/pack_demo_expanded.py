#!/usr/bin/env python3
"""
pack_demo_expanded.py - pack de démonstration minuscule `saison_expanded.pack` et sa vignette, pour créer la page
Workshop PRIVÉE d'Expanded (demande de Charles à la session « Extension », 25.09.2026, 20 h 15 : le lanceur de CA ne crée
une page qu'à partir d'un pack et de sa vignette).

Contenu : UN fichier texte (`text/saison_expanded_lisez_moi.txt`), aucun script, aucune table, rien de WH1 ; le jeu
l'ignore. Vignette : un carré de la minicarte parchemin de l'Atlas (session « Extension »), 512 × 512.
rpfm_server doit tourner ; ne pas lancer pendant un essai en jeu (le pilote fabrique aussi ses packs avec rpfm_server).

Usage :
    python pack_demo_expanded.py
"""
import json
import os
import sys

from PIL import Image

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from essai_tours_auto import session, call, text      # noqa: E402

DATA = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data"
PACK = os.path.join(DATA, "saison_expanded.pack")
VIGNETTE = os.path.join(DATA, "saison_expanded.png")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
LISEZ_MOI = os.path.join(ICI, "demo", "saison_expanded_lisez_moi.txt")
VIGNETTE_EXTENSION = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\vignette-lanceur",
                                  "vignette_expanded_fr_512.png")
PARCHEMIN = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\minicarte_expanded",
                         "saison_expanded_minimap_1120x1905.png")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(os.path.dirname(LISEZ_MOI), exist_ok=True)
    with open(LISEZ_MOI, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("The Season of Revelation: Expanded - work in progress.\n"
                 "This placeholder pack holds no game content yet. See the project page.\n")
    if os.path.exists(PACK):
        sys.exit(f"{PACK} existe déjà : rien n'est écrasé")
    sid = session()
    call(sid, "set_game_selected", {"game_name": "warhammer_3", "rebuild_dependencies": False}, 2)
    call(sid, "close_all_packs", {}, 3)
    call(sid, "new_pack", {}, 4)
    lst = json.loads(text(call(sid, "list_open_packs", {}, 5)))
    cle = [e[0] if isinstance(e, list) else e for v in lst.values() for e in v][0]
    call(sid, "save_pack_as", {"pack_key": cle, "path": PACK}, 6)
    call(sid, "close_all_packs", {}, 7)
    call(sid, "open_packfiles", {"paths": [PACK]}, 8)
    call(sid, "add_packed_files", {"pack_key": PACK, "source_paths": [LISEZ_MOI],
                                   "destination_paths": json.dumps([{"File": "text/saison_expanded_lisez_moi.txt"}])}, 9)
    res = text(call(sid, "save_packfile", {"pack_key": PACK}, 10))
    call(sid, "close_all_packs", {}, 11)
    if '"Error"' in res or not os.path.exists(PACK):
        sys.exit(f"!! pack non enregistré : {res[:300]}")
    # vignette : celle de la session « Extension » (25.09.2026, 21 h 12, assortie à celle de la Saison, demande de Charles),
    # recopiée telle quelle ; le recadrage de la minicarte ne sert que si elle manque
    if os.path.exists(VIGNETTE_EXTENSION):
        Image.open(VIGNETTE_EXTENSION).save(VIGNETTE)
    else:
        im = Image.open(PARCHEMIN).convert("RGB")
        w, h = im.size
        haut = int(h * 0.30)
        im.crop((0, haut, w, haut + w)).resize((512, 512), Image.LANCZOS).save(VIGNETTE)
    print(f"pack : {PACK} ({os.path.getsize(PACK)} octets) ; vignette : {VIGNETTE}")


if __name__ == "__main__":
    main()
