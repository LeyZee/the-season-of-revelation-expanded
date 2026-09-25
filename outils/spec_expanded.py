#!/usr/bin/env python3
"""
spec_expanded.py - fiche de déclaration d'Expanded (phase 2), tirée de celle de la Saison.

Sortie : `04-projets/saison-expanded/map_spec_expanded.json`, lue par `02-scripts/declare_map.py` (rien n'est écrit dans
le kit ici). Principes (25.09.2026) :
- carte `saison_expanded_map` (560 × 825 hex), campagne `saison_expanded` ; clés neuves `saison_` (règle de Charles) ;
- les 61 régions de WH1 gardent leurs clés `wh_dlc05_` (contenu de WH1) : `campaign_map_regions` les relie à la nouvelle
  carte, et les scripts de la Saison, qui les nomment, restent valables ; les lignes `regions`, `provinces`, jonctions
  et colonies existent déjà (declare_map les laisse telles quelles) ;
- zone jouable = celle de la Saison, décalée de DECALAGE_HEX (le reste de la Bretonnie viendra région par région) ;
- routes à nous (`saison_expanded_road_lv_*`), la clé de route étant unique dans tout le jeu.
Le pack de la bêta n'en prend rien : `build_pack.py` filtre carte et campagne sur leurs clés exactes de la Saison.
"""
import json
import os
import sys

RACINE = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(RACINE, "02-scripts"))
os.environ["SAISON_CARTE"] = "expanded"
import carte_config as cc                                      # noqa: E402

SOURCE = os.path.join(RACINE, "04-projets", "saison-des-revelations", "map_spec.json")
SORTIE = os.path.join(RACINE, "04-projets", "saison-expanded", "map_spec_expanded.json")
INDEX_ZONE = 1758400003                                         # Saison : 1758400002 ; vérifié libre par verifier()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    s = json.load(open(SOURCE, encoding="utf-8"))
    dx, dy = cc.DECALAGE_HEX
    ux = cc.LARGEUR_MONDE_SOURCE / 400                          # u par colonne d'hex
    uz = cc.PROFONDEUR_MONDE_SOURCE / 440                       # u par rangée d'hex
    pa = dict(s["playable_area"])
    pa.update({
        "index": INDEX_ZONE,
        "onscreen": "The Season of Revelation: Expanded",
        "minx": round(pa["minx"] + dx * ux, 2), "maxx": round(pa["maxx"] + dx * ux, 2),
        "miny": round(pa["miny"] + dy * uz, 2), "maxy": round(pa["maxy"] + dy * uz, 2),
        "stem": cc.CAMPAGNE, "map_file": f"{cc.CAMPAGNE}_map.png",
    })
    spec = {
        "_commentaire": "Fiche générée par 04-projets/saison-expanded/outils/spec_expanded.py depuis la fiche de la "
                        "Saison. Régions de WH1 partagées (clés wh_dlc05_), carte, campagne, zone et routes à nous.",
        "map": dict(s["map"], name=cc.CARTE, maxx=560, maxy=825),
        "campaign": dict(s["campaign"], name=cc.CAMPAGNE, onscreen="The Season of Revelation: Expanded",
                         description="Bretonnia, from the Grey Mountains to the Sea of Claws",
                         script_path=f"script/campaign/{cc.CAMPAGNE}"),
        "provinces": s["provinces"],
        "regions": s["regions"],
        "roads": [dict(r, key=r["key"].replace("wh_dlc05_wood_elves", cc.CAMPAGNE)) for r in s["roads"]],
        "playable_area": pa,
        "areas_of_interest": [],
        "settlements": s["settlements"],
    }
    if "--lot2" in sys.argv:
        lot2(spec)
    json.dump(spec, open(SORTIE, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"{SORTIE}\n  carte {spec['map']}\n  zone x {pa['minx']}-{pa['maxx']}, z {pa['miny']}-{pa['maxy']}"
          f"\n  routes {[r['key'] for r in spec['roads']]}\n  régions {len(spec['regions'])}, provinces {len(spec['provinces'])}")
    verifier(spec)


DECLARATION = os.path.join(RACINE, r"05-journal\2026-09-23-extension-carte\travail\expanded_declaration.json")
KIT_DB = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit\raw_data\db"


def couleurs_ecartees(n, prises, graine=11):
    """n couleurs de région bien distinctes entre elles et de celles déjà prises (écart ≥ 40 en RVB) : la minicarte et
    les frontières se détourent mieux avec des couleurs franches (25.09.2026, contours lissés)."""
    import random
    rng = random.Random(graine)
    out = []
    essais = 0
    while len(out) < n:
        c = (rng.randrange(20, 250, 5), rng.randrange(20, 250, 5), rng.randrange(20, 250, 5))
        essais += 1
        seuil = 40 if essais < 200000 else 12
        if all(sum((a - b) ** 2 for a, b in zip(c, p)) >= seuil ** 2 for p in prises + out):
            out.append(c)
    return out


def lot2(spec):
    """Phase 2 bis (25.09.2026, 19 h 40 ; décisions de Charles : l'Atlas l'emporte, 11 maîtres validés) : les 75 régions
    et 21 provinces de expanded_declaration.json (session « Extension »). Les régions de WH1 gardent clé, couleur et
    province (la province d'une région est GLOBALE dans WH3 : changer celle d'une région de WH1 changerait la bêta ;
    Fort Solstice, que l'Atlas passe à Glanborielle, attend la décision de l'Atlas et reste à Carcassonne ici)."""
    d = json.load(open(DECLARATION, encoding="utf-8"))
    # régions de WH1 remplacées dans Expanded par une « reprise » à clé à nous (Fort Solstice, 19 h 25) : hors de la carte
    retirees = {t["cle_jeu"] for t in d.get("regions_wh1_touchees", []) if t.get("dans_expanded") == 0}
    spec["regions"] = [r for r in spec["regions"] if r["key"] not in retirees]
    spec["settlements"] = [s for s in spec["settlements"] if s["region"] not in retirees]
    print(f"  régions de WH1 remplacées par une reprise : {sorted(retirees)}")
    # couleurs : une région déjà déclarée dans le kit GARDE sa couleur (19 h 25 : un tirage dans l'ordre de la liste
    # décalait les couleurs quand une région s'insère) ; les nouvelles évitent toutes les couleurs du kit
    import re
    t = open(os.path.join(KIT_DB, "regions.xml"), encoding="utf-8", errors="replace").read()
    kit_rgb = {}
    for bloc in re.findall(r"<regions[ >](.*?)</regions>", t, re.S):
        k = re.search(r"<key>(.*?)</key>", bloc).group(1)
        kit_rgb[k] = tuple(int(re.search(f"<{c}>(\\d+)</{c}>", bloc).group(1)) for c in "rgb")
    prises = [tuple(r["rgb"]) for r in spec["regions"]] + [c for k, c in kit_rgb.items() if k.startswith("saison_")]
    neuves = [r for r in d["regions"]]
    terrestres = [r for r in neuves if not r["is_sea"]]
    a_tirer = [r for r in terrestres if r["cle_jeu"] not in kit_rgb]
    tirees = dict(zip((r["cle_jeu"] for r in a_tirer), couleurs_ecartees(len(a_tirer), prises)))
    rgbs = iter(kit_rgb.get(r["cle_jeu"]) or tirees[r["cle_jeu"]] for r in terrestres)
    # mers : une couleur propre aussi (20 h 10 : l'image de correspondance distingue chaque région, mers comprises,
    # comme chez CA ; déclarées d'abord en noir). Une mer déjà en couleur dans le kit la garde.
    mers = [r for r in neuves if r["is_sea"]]
    prises_mers = prises + list(tirees.values()) + [kit_rgb[r["cle_jeu"]] for r in terrestres if r["cle_jeu"] in kit_rgb]
    a_tirer_m = [r for r in mers if kit_rgb.get(r["cle_jeu"], (0, 0, 0)) == (0, 0, 0)]
    tirees_m = dict(zip((r["cle_jeu"] for r in a_tirer_m), couleurs_ecartees(len(a_tirer_m), prises_mers, graine=23)))
    couleur_mer = {r["cle_jeu"]: tirees_m.get(r["cle_jeu"]) or kit_rgb[r["cle_jeu"]] for r in mers}
    climat_peuple = {"nain": "climate_mountain", "peau-verte": "climate_mountain", "elfe": "climate_magicforest",
                     "ruine elfe": "climate_magicforest"}
    for r in neuves:
        entree = {"key": r["cle_jeu"], "onscreen": r["nom_en"], "battle_name": r["nom_en"], "in_encyclopedia": 1,
                  "is_sea": int(r["is_sea"])}
        if r["is_sea"]:
            entree["rgb"] = list(couleur_mer[r["cle_jeu"]])
        else:
            entree["rgb"] = list(next(rgbs))
            if r.get("province_jeu"):
                entree["province"] = r["province_jeu"]
                entree["is_capital"] = int(r.get("est_capitale", 0))
            climat = "climate_magicforest" if r["categorie"] == "bois_reveur" else climat_peuple.get(r.get("peuple"),
                                                                                                        "climate_temperate")
            spec["settlements"].append({"region": r["cle_jeu"], "climate_type": climat})
        spec["regions"].append(entree)
    spec["provinces"] += [{"key": p["cle_jeu"], "onscreen": p["nom_en"]} for p in d["provinces_neuves"]]
    # contrôles : clés uniques, couleurs terrestres uniques, provinces citées déclarées
    cles = [r["key"] for r in spec["regions"]]
    assert len(cles) == len(set(cles)), "clé de région en double"
    toutes = [tuple(r["rgb"]) for r in spec["regions"]]
    assert len(toutes) == len(set(toutes)), "couleur de région en double (mers comprises)"
    provs = {p["key"] for p in spec["provinces"]}
    orph = sorted({r["province"] for r in spec["regions"] if r.get("province") and r["province"] not in provs})
    print(f"  lot 2 : {len(neuves)} régions ({len(terrestres)} terrestres), {len(d['provinces_neuves'])} provinces ; "
          f"provinces citées non déclarées : {orph or 'aucune'}")


def verifier(spec):
    """Les clés neuves ne doivent exister nulle part dans le kit (ni chez CA ni chez nous)."""
    db = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit\raw_data\db"
    neuves = {"campaign_maps.xml": [spec["map"]["name"]], "campaigns.xml": [spec["campaign"]["name"]],
              "campaign_map_roads.xml": [r["key"] for r in spec["roads"]],
              "campaign_map_playable_areas.xml": [f"<index>{spec['playable_area']['index']}</index>"]}
    for f, cles in neuves.items():
        texte = open(os.path.join(db, f), encoding="utf-8", errors="replace").read()
        for c in cles:
            print(f"  {f:36} {c:45} {'DÉJÀ PRÉSENTE' if c in texte else 'libre'}")


if __name__ == "__main__":
    main()
