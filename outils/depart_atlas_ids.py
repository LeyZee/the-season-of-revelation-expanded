#!/usr/bin/env python3
"""
depart_atlas_ids.py - les identifiants des lignes de départ écrites par depart_atlas.py, rangés par catégorie, pour une
dichotomie du plantage au chargement d'Expanded (4.10.2026, 13 h 27, Warhammer3.exe+0x2602213, pile « port, primary »,
« SAVED_CHARACTERS_SYSTEM »).

Catégories : factions neuves (de CA / à nous), hordes (chef avec start_pos_horde_details), régions neuves (maître de CA,
à nous, ruine), personnages (chefs ; Kemmler et les siens, déplacés), Aislinn (horde de CA à qui la déclaration donne
3 régions), unités. Lecture seule. Sortie : 05-journal\\2026-10-03-expanded-suite\\depart-atlas-ids.json
Usage : python depart_atlas_ids.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import depart_atlas as DA                                                 # noqa: E402
import factions_atlas as FA                                               # noqa: E402
from donnees_campagne import TableKit                                     # noqa: E402

v = TableKit.valeurs
SORTIE = os.path.join(DA.ATELIER, r"05-journal\2026-10-03-expanded-suite\depart-atlas-ids.json")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    corr = json.load(open(DA.CORR, encoding="utf-8"))
    recopiees = {d["neuf"] for d in corr["factions"].values()}
    F, P, RG = TableKit("start_pos_factions"), TableKit("start_pos_characters"), TableKit("start_pos_regions")
    HD, U = TableKit("start_pos_horde_details"), TableKit("start_pos_land_units")
    fac = {v(c)["ID"]: v(c)["faction"] for _, c in F.ou(campaign=DA.CAMP)}
    neuves = {i: k for i, k in fac.items() if i not in recopiees}
    persos = {v(c)["ID"]: v(c) for _, c in P.lignes if v(c)["faction"] in neuves}
    hordes = {i for i in persos if HD.ou(general=i)}
    regions_recopiees = set(corr["regions"].values())
    regs = [v(c) for _, c in RG.ou(campaign=DA.CAMP) if v(c)["id"] not in regions_recopiees]
    out = {
        "factions_neuves_de_CA": {i: k for i, k in neuves.items() if k not in FA.FACTIONS},
        "factions_neuves_a_nous": {i: k for i, k in neuves.items() if k in FA.FACTIONS},
        "chefs_hordes": {i: f"{persos[i]['subtype']} ({neuves[persos[i]['faction']]})" for i in hordes},
        "chefs_armees": {i: f"{p['subtype']} ({neuves[p['faction']]})" for i, p in persos.items() if i not in hordes},
        "regions_neuves_maitre_CA": {r["id"]: r["region"] for r in regs if r["owning_faction"] in neuves
                                     and neuves[r["owning_faction"]] not in FA.FACTIONS},
        "regions_neuves_maitre_nous": {r["id"]: r["region"] for r in regs if r["owning_faction"] in neuves
                                       and neuves[r["owning_faction"]] in FA.FACTIONS},
        "regions_neuves_maitre_saison": {r["id"]: r["region"] for r in regs if r["owning_faction"]
                                         and r["owning_faction"] not in neuves},
        "regions_neuves_ruines": {r["id"]: r["region"] for r in regs if not r["owning_faction"]},
        "aislinn": {"faction": [i for i, k in neuves.items() if k == "wh3_dlc27_hef_aislinn"],
                    "regions": [r["region"] for r in regs
                                if neuves.get(r["owning_faction"]) == "wh3_dlc27_hef_aislinn"]},
        "unites_des_chefs": len([1 for _, c in U.lignes if v(c)["general"] in persos]),
    }
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for k, val in out.items():
        print(f"  {k} : {len(val) if hasattr(val, '__len__') else val}")
    print(f"  -> {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
