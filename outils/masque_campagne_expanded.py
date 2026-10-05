#!/usr/bin/env python3
"""
masque_campagne_expanded.py - vide le `mask` de la ligne `campaigns` de saison_expanded dans le kit (4.10.2026).

Pourquoi (Construction, 4.10.2026, 13 h 12, par essai) : avec `<mask>32</mask>` (masque des Elfes sylvains de WH1, que
`declare_map.py` recopiait de la fiche `map_spec_expanded.json`), la génération du startpos d'Expanded plante
(`Warhammer3.exe+0x2A588B2`) ; toutes les autres campagnes du kit, la Saison comprise, ont un masque VIDE. Masque vidé :
startpos écrit. La fiche est corrigée aussi (`"mask": ""`), sinon une nouvelle déclaration le remettrait.

Sauvegarde dans `05-journal\\db-backups\\<date>-masque-expanded\\` ; idempotent. PRÉAVIS DU KIT avant `--apply`.
Usage : python masque_campagne_expanded.py [--apply]
"""
import argparse
import os
import sys
from datetime import datetime

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from donnees_campagne import TableKit                                    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t = TableKit("campaigns")
    lignes = t.ou(campaign_name="saison_expanded")
    if len(lignes) != 1:
        raise SystemExit(f"campaigns : {len(lignes)} ligne(s) saison_expanded")
    k, c = lignes[0]
    print(f"  campaigns {k} : mask = {t.valeurs(c).get('mask')!r}")
    if not t.modifier(k, {"mask": ""}):
        print("  déjà vide : rien à faire")
        return 0
    if not a.apply:
        print("  à blanc : le masque serait vidé")
        return 0
    dossier = os.path.join(ATELIER, "05-journal", "db-backups", datetime.now().strftime("%Y%m%d-%H%M%S") + "-masque-expanded")
    t.ecrire(dossier)
    print(f"  écrit ; sauvegarde {dossier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
