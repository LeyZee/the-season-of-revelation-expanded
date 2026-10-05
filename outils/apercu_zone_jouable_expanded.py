#!/usr/bin/env python3
"""
apercu_zone_jouable_expanded.py - format de l'aperçu de la carte à l'écran de sélection de la campagne d'Expanded
(4.10.2026).

Pourquoi (Charles, essai d'Expanded du 4.10.2026 : « la carte de l'écran de sélection est déformée » ; cause trouvée par la
Construction) : la ligne `campaign_map_playable_areas` de saison_expanded_map a preview_width / preview_height = 256 / 256,
les valeurs par défaut de `declare_map.py` ; le jeu y étire la carte. La Saison a 472 / 600 (rapport de son monde,
266,53 / 338,9 = 0,786), CA 750 / 600. Expanded : 373,142 / 697,06 = 0,535, soit 321 / 600. La fiche
`map_spec_expanded.json` porte aussi ces valeurs (playable_area.preview_width / preview_height) ; `declare_map.py`, qui
écrit 256 en dur, est à la Construction.

Sauvegarde dans `05-journal\\db-backups\\<date>-apercu-expanded\\` ; idempotent. PRÉAVIS DU KIT avant `--apply`, et jamais
pendant que le jeu tient le pack. Usage : python apercu_zone_jouable_expanded.py [--apply]
"""
import argparse
import os
import sys
from datetime import datetime

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from donnees_campagne import TableKit                                    # noqa: E402

LARGEUR, PROFONDEUR = 373.142, 697.06
HAUTEUR_APERCU = 600
VALEURS = {"preview_width": str(round(HAUTEUR_APERCU * LARGEUR / PROFONDEUR)), "preview_height": str(HAUTEUR_APERCU)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t = TableKit("campaign_map_playable_areas")
    lignes = t.ou(map_file="saison_expanded_map.png")
    if len(lignes) != 1:
        raise SystemExit(f"campaign_map_playable_areas : {len(lignes)} ligne(s) d'Expanded")
    k, c = lignes[0]
    v = t.valeurs(c)
    print(f"  {k} : preview {v.get('preview_width')} × {v.get('preview_height')} -> "
          f"{VALEURS['preview_width']} × {VALEURS['preview_height']}")
    if not t.modifier(k, VALEURS):
        print("  déjà au bon format : rien à faire")
        return 0
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    dossier = os.path.join(ATELIER, "05-journal", "db-backups", datetime.now().strftime("%Y%m%d-%H%M%S") + "-apercu-expanded")
    t.ecrire(dossier)
    print(f"  écrit ; sauvegarde {dossier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
