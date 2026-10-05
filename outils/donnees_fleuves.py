#!/usr/bin/env python3
"""
donnees_fleuves.py - le reste du lot de données des fleuves navigables d'Expanded (5.10.2026), d'après
`04-projets\\banc-fleuve\\DONNEES-A-DECLARER.md` §§ 2 et 3 (les régions d'eau elles-mêmes : `spec_expanded.lot_fleuves` et
`declarer_expanded --ajouts-seulement`) :
- § 2, TEMPÊTES : `campaign_storms_excluded_regions`, une ligne par région d'eau (CA fait de même pour ses fleuves, ex.
  `wh3_dlc20_chaos_region_river_reik` ; sans cela une tempête marine, 4 à 20 % d'attrition, peut passer dans le fleuve) ;
- § 3, COMBAT NAVAL : `battle_catchment_override_battle_mappings` pour la carte `saison_expanded_map` : les deux lignes
  `Gatekeeper` de CA (`naval_normal` -> `wh2_southlands_grassland`, `naval_breakout` -> `wh2_ulthuan_grassland`, comme pour
  `wh3_main_combi_map`). Valable pour toutes les mers d'Expanded. Le reste des cartes de bataille d'Expanded (la Saison en
  a 124 lignes) relève du captage des batailles, pas de ce lot.
Ajouts seulement (clés à nous ou clé de carte à nous ; aucune ligne de CA modifiée) ; à blanc par défaut ; --apply écrit
avec sauvegarde des XML dans `05-journal\\db-backups\\<date>-fleuves-donnees` (PRÉAVIS DE 5 MINUTES avant).

Usage : python donnees_fleuves.py [--apply]
"""
import argparse
import os
import sys
from datetime import datetime

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import declare_map as DM                                                     # noqa: E402
from spec_expanded import FLEUVES                                            # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
CARTE = "saison_expanded_map"
NAVAL = (("naval_breakout", "wh2_ulthuan_grassland"), ("naval_normal", "wh2_southlands_grassland"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    regions = DM.Table(KIT, "regions")
    manquent = [k for k, _ in FLEUVES if k not in regions.keys]
    if manquent:
        raise SystemExit(f"régions d'eau non déclarées dans le kit : {manquent} (declarer_expanded --ajouts-seulement)")
    t1 = DM.Table(KIT, "campaign_storms_excluded_regions")
    for k, _ in FLEUVES:
        t1.add(k, [f"<region>{k}</region>"])
    t2 = DM.Table(KIT, "battle_catchment_override_battle_mappings")
    for typ, groupe in NAVAL:
        t2.add(f"Gatekeeper**{typ}{CARTE}", ["<area>Gatekeeper</area>", "<attacker>*</attacker>", "<defender>*</defender>",
                                              f"<battle_type>{typ}</battle_type>", f"<battle_path>{CARTE}</battle_path>",
                                              f"<battle_group>{groupe}</battle_group>",
                                              "<required_tile_upgrades></required_tile_upgrades>"])
    for t in (t1, t2):
        print(f"{t.name:44} ajouté {len(t.added)} ; déjà là {len(t.skipped)}")
        for k in t.added:
            print(f"    + {k}")
    if not a.apply:
        print("à blanc : rien d'écrit")
        return 0
    sauve = os.path.join(ATELIER, "05-journal", "db-backups", datetime.now().strftime("%Y%m%d-%H%M%S") + "-fleuves-donnees")
    for t in (t1, t2):
        if t.added:
            t.save(sauve)
    print(f"écrit ; sauvegardes : {sauve}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
