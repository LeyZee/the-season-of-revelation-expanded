#!/usr/bin/env python3
"""
villes_wh1_expanded.py - remet à l'identique de la Saison les colonies de WH1 dans la grille d'Expanded, sans refaire
toute la grille (4.10.2026).

Pourquoi : plantage au chargement d'Expanded (+0x2613117, session « Construction », débogueur : une liste vide d'un
objet de la colonie wh_dlc05_bordeleaux_bordeleaux, « port, primary » dans la pile). Comparaison des deux grilles du
kit : les trois ports de WH1 (Bordeleaux, Brionne, Mousillon) ont 19 cases principales + 3 de port dans Expanded, contre
16 + 3 dans la Saison, qui charge ; toutes les autres colonies de WH1 sont identiques. `grow_town_slots` les avait fait
repousser (villes_expanded, étape 4). La règle est maintenant dans `villes_expanded.villes_wh1_a_l_identique` ; cet outil
l'applique au map.hex du chantier (`04-projets\\saison-expanded\\caime\\`), couches TownSlots et TownSprawl seulement.
Le kit se met à jour ensuite par `kit_expanded.py` (préavis), puis CAIME process, zz et startpos (Construction).

Usage : python villes_wh1_expanded.py [--apply]
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import villes_expanded as V                                                # noqa: E402
from caime_layers import read_layer, encode_flat, caime_names, flat_names  # noqa: E402
from cadre_expanded import W, H                                            # noqa: E402

TRAVAIL = os.path.join(V.COUCHES, "villes-wh1")
SAUVEGARDES = os.path.join(V.ATELIER, r"05-journal\terrain-backups")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    shutil.rmtree(TRAVAIL, ignore_errors=True)
    os.makedirs(TRAVAIL)
    p = subprocess.run([V.CAIME, "export-layer", "--map", V.CARTE_EXP, "--out", TRAVAIL, "--format", "binary",
                        "--layer", "TownSlots", "--layer", "TownSprawl", "--layer", "Regions"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise SystemExit(p.stdout + p.stderr)
    lire = lambda n: read_layer(os.path.join(TRAVAIL, f"layer_{n}.hex_layer"))[1].reshape(H, W).copy()  # noqa: E731
    slots, sprawl, reg = lire("town_slots"), lire("town_sprawl"), lire("regions")
    noms = flat_names(caime_names(V.CAIME, V.CARTE_EXP)[0], "Regions")
    avant = slots.copy()
    n = V.villes_wh1_a_l_identique(slots, sprawl, reg, noms)
    ch = np.argwhere(avant != slots)
    par_region = {}
    for r, q in ch:
        k = noms[reg[r, q]] if 0 <= reg[r, q] < len(noms) else "-"
        par_region.setdefault(k, []).append((int(q - V.DX), int(r - V.DY), int(avant[r, q]), int(slots[r, q])))
    print(f"  cases changées : {n} (emplacement : {len(ch)})")
    for k, v in par_region.items():
        print(f"    {k} : {v}")
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    os.makedirs(SAUVEGARDES, exist_ok=True)
    sauve = os.path.join(SAUVEGARDES, time.strftime("%Y%m%d-%H%M%S") + "-map.hex-expanded-avant-villes-wh1")
    shutil.copy2(V.CARTE_EXP, sauve)
    args = [V.CAIME, "import-layer", "--map", V.CARTE_EXP]
    for nom, v in (("TownSlots", slots), ("TownSprawl", sprawl)):
        f = os.path.join(TRAVAIL, f"neuf_{nom.lower()}.hex_layer")
        with open(f, "wb") as fh:
            fh.write(encode_flat(nom, v.reshape(-1)))
        args += ["--layer", nom, "--file", f]
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    print(f"  sauvegarde : {sauve}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
