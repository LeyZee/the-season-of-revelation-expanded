#!/usr/bin/env python3
"""
ports_fleuves_depart.py - gabarit d'emplacement de PORT des régions qui ont reçu un port avec le lot des fleuves (5.10.2026).

Pourquoi : le lot des fleuves v3 (Brienne, Grismerie + Ois, Sannez ; `04-projets\\banc-fleuve`) pose des emplacements de
port dans la grille d'Expanded (TownSlots == 1) ; 10 régions n'avaient pas de ligne `start_pos_region_slot_templates` de
type « port » dans la campagne saison_expanded (relevé du 5.10, 2 h). Une région à port de la grille sans gabarit de port
n'a pas d'emplacement de port en jeu.

Règle : celle de Brionne (port de WH1 dans la Saison, éprouvé en jeu) : une ligne « port » / « wh_main_port », le
gabarit principal et le secondaire de la région ne changent pas. Identifiants `ident_numerique` à graine
« expanded-fleuves:<région>:port ». Idempotent.

Essai à blanc par défaut ; `--apply` : préavis du kit d'abord ; sauvegarde dans `05-journal\\db-backups\\<date>-ports-fleuves\\`.

Usage : python ports_fleuves_depart.py [--apply]
"""
import argparse
import os
import sys
from datetime import datetime

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from donnees_campagne import TableKit, ident_numerique                   # noqa: E402

CAMP = "saison_expanded"
TABLE = "start_pos_region_slot_templates"
REGIONS = ("saison_couronne_couronne", "wh_dlc05_brionne_muret", "wh_dlc05_carcassonne_ferignac",
           "wh_dlc05_gisoreux_gisoreux", "wh_dlc05_montfort_montfort", "wh_dlc05_mousillon_yremy",
           "wh_dlc05_parravon_parravon", "wh_dlc05_quenelles_brusse", "wh_dlc05_quenelles_laguiller",
           "wh_dlc05_quenelles_quenelles")
v = TableKit.valeurs


def construire():
    t = TableKit(TABLE)
    pris = {v(c).get("id") for _, c in t.lignes}
    modele = next(iter(t.ou(campaign=CAMP, region="wh_dlc05_brionne_brionne", slot_type="port")))
    journal = []
    for reg in REGIONS:
        lignes = [v(c) for _, c in t.ou(campaign=CAMP, region=reg)]
        if not lignes:
            raise SystemExit(f"{reg} : aucune ligne de gabarit dans {CAMP}")
        if any(l["slot_type"] == "port" for l in lignes):
            continue
        n = ident_numerique(f"expanded-fleuves:{reg}:port", pris)
        pris.add(n)
        t.ajouter_sur_modele(modele[0], {"id": n, "region": reg})
        journal.append(f"{reg} : port / wh_main_port ({n}) ; déjà : "
                       + ", ".join(f"{l['slot_type']} {l['slot_template']}" for l in lignes))
    return t, journal


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t, journal = construire()
    for l in journal:
        print("  " + l)
    print(f"{len(t.neuves)} ligne(s) {'écrites' if a.apply else 'à écrire'}")
    if not a.apply or not t.neuves:
        return 0
    dossier = os.path.join(ATELIER, "05-journal", "db-backups",
                           datetime.now().strftime("%Y%m%d-%H%M%S") + "-ports-fleuves")
    t.ecrire(dossier)
    t2, _ = construire()
    if t2.neuves:
        print(f"!!! NON IDEMPOTENT : {len(t2.neuves)} (sauvegarde {dossier})")
        return 2
    print(f"écrit ; sauvegarde {dossier} ; nouvelle passe à 0 ligne")
    return 0


if __name__ == "__main__":
    sys.exit(main())
