#!/usr/bin/env python3
"""
textes_atlas.py - les noms des régions et provinces de l'Atlas en anglais ET en français pour le pack d'Expanded
(3.10.2026).

Pourquoi : la Construction (`construction-pack-expanded.md`, « Reste » n° 4) injecte pour les régions et provinces
`saison_*` les noms anglais du kit, recopiés tels quels dans le .loc français. Les noms français existent : la déclaration
de l'Atlas (`expanded_declaration.json`, `regions[].nom_fr` et `provinces_neuves[].nom_fr`, formes de GW vérifiées par la
session « Extension »). Clés au format des textes de la Saison (`regions_onscreen_*`, `regions_battle_name_*`,
`provinces_onscreen_*`) ; fichier au format de `textes_gameplay.json`, que `injecter_textes.py` lit dans
`04-projets\\saison-expanded\\textes\\` (profil expanded).

Sortie : `04-projets\\saison-expanded\\textes\\regions_atlas.json`. Usage : python textes_atlas.py
"""
import json
import os
import sys

ATELIER = r"C:\TotalWar-CampaignMap"
DECL = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\expanded_declaration.json")
SORTIE = os.path.join(ATELIER, r"04-projets\saison-expanded\textes\regions_atlas.json")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.load(open(DECL, encoding="utf-8"))
    out = {}
    for r in d["regions"]:
        k = r["cle_jeu"]
        if not k.startswith("saison_"):
            continue                      # régions de WH1 : leurs noms restent ceux de la Saison
        nom = {"en": r["nom_en"], "fr": r["nom_fr"]}
        out[f"regions_onscreen_{k}"] = nom
        out[f"regions_battle_name_{k}"] = nom
    for p in d["provinces_neuves"]:
        out[f"provinces_onscreen_{p['cle_jeu']}"] = {"en": p["nom_en"], "fr": p["nom_fr"]}
    vides = [k for k, v in out.items() if not (v["en"] and v["fr"])]
    if vides:
        raise SystemExit(f"noms vides : {vides[:5]}")
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    diff = sum(1 for v in out.values() if v["en"] != v["fr"])
    print(f"  {len(out)} textes ({diff} où le français diffère de l'anglais) -> {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
