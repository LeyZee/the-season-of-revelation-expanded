#!/usr/bin/env python3
"""
releve_constantes.py - relevé des constantes de module de la chaîne (Saison Expanded, phase 1).

Pourquoi (25.09.2026) : la chaîne va être paramétrée par carte (`carte_config`). Contrôle de non-régression : avec la carte
par défaut (la bêta), chaque constante de chaque module doit garder EXACTEMENT sa valeur. Ce script importe les modules de
la chaîne et écrit leurs constantes simples (chaînes, nombres, booléens, tuples et listes de ces types, chemins) en JSON.

Usage :
    python releve_constantes.py --sortie avant.json
    python releve_constantes.py --sortie apres.json --comparer avant.json
"""
import argparse
import importlib
import json
import os
import sys

SCRIPTS = r"C:\TotalWar-CampaignMap\02-scripts"
MODULES = ("terrain_wh1_vers_terry", "masques_eau_carte", "compiler_terrain_bob", "shroud_heights", "camera_heightmap",
           "textures_sol_wh1", "lf_normal_depuis_relief", "modeles_wh1", "tuiles_wh1", "eclairage_wh1", "arbres_wh1",
           "montagnes_wh1", "rivieres_wh1", "entites_wh1", "eau_carte", "ajouts_carte_wh3", "props_wh1_vers_layers",
           "lire_props_wh1", "relief_maillages_wh1", "cotes_wh1", "champs_bretons", "decors_carte_wh3", "vie_carte_wh3",
           "textures_tuiles_wh1", "fichiers_wh1", "etangs_wh1", "deltas_wh1", "build_pack", "donnees_campagne",
           "tables_gameplay")


def simple(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return True
    if isinstance(v, (tuple, list, frozenset, set)):
        return all(simple(x) for x in v)
    if isinstance(v, dict):
        return all(isinstance(k, (str, int)) and simple(x) for k, x in v.items())
    return False


def normal(v):
    if isinstance(v, (set, frozenset)):
        return sorted(normal(x) for x in v)
    if isinstance(v, (tuple, list)):
        return [normal(x) for x in v]
    if isinstance(v, dict):
        return {str(k): normal(x) for k, x in v.items()}
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--comparer")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, SCRIPTS)
    releve, echecs = {}, {}
    for m in MODULES:
        try:
            mod = importlib.import_module(m)
        except Exception as e:                       # noqa: BLE001
            echecs[m] = f"{type(e).__name__}: {e}"
            continue
        releve[m] = {k: normal(v) for k, v in vars(mod).items()
                     if not k.startswith("_") and not callable(v) and simple(v)}
    with open(a.sortie, "w", encoding="utf-8") as f:
        json.dump({"constantes": releve, "echecs": echecs}, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{sum(len(v) for v in releve.values())} constantes dans {len(releve)} modules ; échecs d'import : {echecs}")
    if a.comparer:
        ref = json.load(open(a.comparer, encoding="utf-8"))["constantes"]
        diff = 0
        for m, cs in ref.items():
            for k, v in cs.items():
                w = releve.get(m, {}).get(k, "<absente>")
                if w != v:
                    diff += 1
                    print(f"  DIFFÉRENT {m}.{k} : {str(v)[:120]} -> {str(w)[:120]}")
        print(f"{diff} constante(s) différente(s)")
        return 1 if diff else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
