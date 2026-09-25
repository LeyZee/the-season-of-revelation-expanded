#!/usr/bin/env python3
"""
maj_couleurs_mers.py - donne aux mers d'Expanded, déclarées en noir à 19 h 14, leur couleur propre dans `regions`.

Pourquoi (25.09.2026, 20 h 10) : l'image de correspondance des régions (minicarte, carte dézoomée) distingue chaque région
par sa couleur, mers comprises, comme chez CA ; nos 11 mers `saison_sea_*` étaient toutes (0, 0, 0). La fiche
(`spec_expanded.py --lot2`) leur donne des couleurs écartées ; cet outil réécrit SEULEMENT les enregistrements `regions`
des clés `saison_sea_*` dont la couleur diffère (Table.replace de declare_map : même uuid, horodatage renouvelé), avec
sauvegarde. Aucune autre ligne n'est touchée.

Usage :
    python maj_couleurs_mers.py            # essai à blanc
    python maj_couleurs_mers.py --apply    # écrit (préavis du kit d'abord)
"""
import json
import os
import sys
from datetime import datetime

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
import declare_map as dm                                            # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
SPEC = os.path.join(ATELIER, r"04-projets\saison-expanded\map_spec_expanded.json")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    spec = json.load(open(SPEC, encoding="utf-8"))
    plan = dm.build(spec)
    t = dm.Table(KIT, "regions")
    for cle, champs in plan["regions"]:
        if cle.startswith("saison_sea_"):
            t.replace(cle, champs)
    print(f"regions : {len(t.updated)} mer(s) recolorée(s) : {t.updated} ; inchangées : {len(t.skipped)}")
    if "--apply" not in sys.argv:
        print("essai à blanc : rien d'écrit")
        return
    dossier = os.path.join(ATELIER, "05-journal", "db-backups", datetime.now().strftime("%Y%m%d-%H%M%S"))
    t.save(dossier)
    print(f"écrit ; sauvegarde dans {dossier}")


if __name__ == "__main__":
    main()
