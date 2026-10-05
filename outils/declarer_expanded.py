#!/usr/bin/env python3
"""
declarer_expanded.py - (re)déclare Expanded dans le kit depuis map_spec_expanded.json, sans jamais toucher une ligne de
la Saison.

Pourquoi (3.10.2026) : la grille passe à 560 × 905 (les Voûtes) et la déclaration compte 86 régions, 24 provinces ; or le
kit, restauré le 3.10 à 01 h 44 (session « Lakemen »), porte les lignes d'Expanded du 25.09 (560 × 825, 76 régions, zone
jouable de l'ancien décalage). `02-scripts\\declare_map.py` n'ajoute que les lignes absentes : il laisserait l'ancienne
taille, l'ancienne zone et des jonctions de province devenues fausses. Ce script reprend sa construction (`build`) et ses
tables (`Table`), et :
- REMPLACE en place les lignes d'Expanded qui changent : la carte, la campagne, la zone jouable, les routes (clés
  d'Expanded seulement : `saison_expanded*`, l'index de zone de la fiche) ;
- AJOUTE ce qui manque (provinces, régions, colonies, liens carte -> région, jonctions) ; une région de WH1 (`wh_dlc05_`)
  n'est jamais réécrite : seulement reliée à la carte d'Expanded ;
- RETIRE, pour les régions `saison_` de la fiche, les jonctions vers une AUTRE province que celle de la fiche, et les
  liens de la carte d'Expanded vers une région que la fiche n'a plus.
Essai à blanc par défaut ; `--apply` écrit (sauvegarde des XML touchés dans 05-journal\\db-backups\\<date>-expanded) :
PRÉAVIS DE 5 MINUTES avant, et un seul de nous à la fois dans le kit (Construction, 3.10.2026).

Usage :
    python declarer_expanded.py            # essai à blanc
    python declarer_expanded.py --apply
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
import declare_map as DM                                                     # noqa: E402

KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
SPEC = os.path.join(ATELIER, r"04-projets\saison-expanded\map_spec_expanded.json")
REMPLACER = ("campaign_maps", "campaigns", "campaign_map_playable_areas", "campaign_map_roads")


def a_nous(cle):
    return cle.startswith("saison_")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    # (5.10.2026, régions d'eau des fleuves) la zone jouable (kit_expanded : le monde entier) et la campagne (masque vidé
    # par la Construction) ont changé depuis la fiche : une redéclaration complète les défairait ; n'ajouter que le neuf
    ap.add_argument("--ajouts-seulement", action="store_true",
                    help="n'ajoute que les lignes absentes ; ne remplace ni ne retire rien")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    spec = json.load(open(SPEC, encoding="utf-8"))
    carte = spec["map"]["name"]
    assert carte == "saison_expanded_map" and spec["campaign"]["name"] == "saison_expanded", "fiche inattendue"
    index_zone = str(spec["playable_area"]["index"])
    plan = DM.build(spec)
    tables = {}
    for nom, recs in plan.items():
        if not recs:
            continue
        t = DM.Table(KIT, nom)
        for cle, champs in recs:
            if nom in REMPLACER and not a.ajouts_seulement:
                assert cle in (carte, spec["campaign"]["name"], index_zone) or cle.startswith("saison_expanded_road_"), cle
                if cle in t.keys:
                    t.replace(cle, champs)
                else:
                    t.add(cle, champs)
            else:
                t.add(cle, champs)               # (déjà là : laissée telle quelle, y compris toute ligne de la Saison)
        tables[nom] = t
    # jonctions de province : une région à nous dans une seule province, celle de la fiche
    prov = {r["key"]: r.get("province") for r in spec["regions"] if a_nous(r["key"])}
    j = tables["region_to_province_junctions"]
    for bloc in ([] if a.ajouts_seulement else
                 re.findall(r"<region_to_province_junctions [^>]*>.*?</region_to_province_junctions>", j.text, re.S)):
        cle = re.search(r'record_key="([^"]*)"', bloc).group(1)
        reg = re.search(r"<region>(.*?)</region>", bloc).group(1)
        pr = re.search(r"<province>(.*?)</province>", bloc).group(1)
        if reg in prov and prov[reg] and pr != prov[reg]:
            j.remove(cle)
    # liens de la carte d'Expanded vers des régions que la fiche n'a plus
    garde = {r["key"] for r in spec["regions"]}
    c = tables["campaign_map_regions"]
    for bloc in ([] if a.ajouts_seulement else
                 re.findall(r"<campaign_map_regions [^>]*>.*?</campaign_map_regions>", c.text, re.S)):
        if f"<campaign_map>{carte}</campaign_map>" not in bloc:
            continue
        reg = re.search(r"<region>(.*?)</region>", bloc).group(1)
        if reg not in garde:
            c.remove(re.search(r'record_key="([^"]*)"', bloc).group(1))
    for nom, t in tables.items():
        print(f"{nom:34} ajouté {len(t.added):3}  remplacé {len(t.updated):2}  retiré {len(t.removed):2}  "
              f"déjà là {len(t.skipped):3}")
        for k in t.added[:40]:
            print(f"    + {k}")
        for k in t.updated:
            print(f"    ~ {k}")
        for k in t.removed:
            print(f"    - {k}")
    touchees = [t for t in tables.values() if t.added or t.updated or t.removed]
    if not a.apply:
        print(f"\nEssai à blanc : rien n'a été écrit ({len(touchees)} tables à écrire). Relancer avec --apply après le "
              f"préavis.")
        return 0
    sauve = os.path.join(ATELIER, "05-journal", "db-backups", datetime.now().strftime("%Y%m%d-%H%M%S") + "-expanded")
    for t in touchees:
        t.save(sauve)
    print(f"\nÉcrit : {len(touchees)} tables. Sauvegardes des XML d'origine : {sauve}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
