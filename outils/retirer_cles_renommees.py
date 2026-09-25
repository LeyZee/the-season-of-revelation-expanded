#!/usr/bin/env python3
"""
retirer_cles_renommees.py - retire du kit les lignes d'Expanded écrites sous des clés de région RENOMMÉES depuis.

Pourquoi (25.09.2026, 19 h 20) : la déclaration de 19 h 14 a écrit 75 régions ; la session « Extension » a renommé 9 clés
juste après (noms abandonnés : Thurin -> Barfleur, etc. ; règle de Charles, CLAUDE.md § 2). `declare_map.py --undo`
retirerait aussi la carte et la campagne : cet outil ne retire QUE les lignes des anciennes clés, dans les quatre tables
où `declare_map.build` les a mises (mêmes clés d'enregistrement), avec sauvegarde. Ensuite, `spec_expanded.py --lot2`
puis `declare_map.py --apply` ajoutent les nouvelles clés (les autres lignes sont déjà là : idempotent).

Usage :
    python retirer_cles_renommees.py            # essai à blanc
    python retirer_cles_renommees.py --apply    # écrit (préavis du kit d'abord)
"""
import os
import sys
from datetime import datetime

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
import declare_map as dm                                            # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
CARTE = "saison_expanded_map"
# ancienne clé -> province déclarée à 19 h 14 (map_spec_expanded.json de 19 h 14)
ANCIENNES = {
    "saison_lyonesse_thurin": "saison_province_lyonesse",
    "saison_lyonesse_portsall": "saison_province_lyonesse",
    "saison_marches_saint_lambert": "saison_province_marches",
    "saison_marches_euresbourg": "saison_province_marches",
    "saison_artois_venin_rouge": "saison_province_artois",
    "saison_irrana_pics_sanglants": "saison_province_irrana",
    "saison_irrana_capuches_tordues": "saison_province_irrana",
    "saison_dame_grise_col_de_wut": "saison_province_dame_grise",
    "saison_grises_sud_yeux_jaunes": "saison_province_grises_sud",
}


# régions de WH1 remplacées dans Expanded par une « reprise » à clé à nous (19 h 25, Fort Solstice) : on ne retire QUE leur
# lien avec la carte d'Expanded ; la région, sa province et sa colonie restent (la Saison s'en sert)
HORS_DE_LA_CARTE = ["wh_dlc05_carcassonne_summersfall_fort"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    apply = "--apply" in sys.argv
    cles = {
        "regions": list(ANCIENNES),
        "campaign_map_regions": [CARTE + k for k in list(ANCIENNES) + HORS_DE_LA_CARTE],
        "region_to_province_junctions": [k + p for k, p in ANCIENNES.items()],
        "campaign_map_settlements": [f"settlement:{k}" for k in ANCIENNES],
    }
    tables = {}
    for nom, liste in cles.items():
        t = dm.Table(KIT, nom)
        for k in liste:
            t.remove(k)
        tables[nom] = t
        print(f"{nom:32} retiré {len(t.removed):2} / {len(liste)} ; {t.removed}")
    if not apply:
        print("essai à blanc : rien d'écrit")
        return
    dossier = os.path.join(ATELIER, "05-journal", "db-backups", datetime.now().strftime("%Y%m%d-%H%M%S"))
    for t in tables.values():
        t.save(dossier)
    print(f"écrit ; sauvegardes dans {dossier}")


if __name__ == "__main__":
    main()
