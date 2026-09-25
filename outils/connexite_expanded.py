#!/usr/bin/env python3
"""connexite_expanded.py - contrôle de ChaosRobie (25.09.2026) : toutes les colonies d'Expanded sont-elles sur un seul
ensemble connexe de cases franchissables (terre ET mer franchissables, voisinage hex de CAIME) ? Les portails ne
comptent pas. Lecture seule ; liste les colonies hors de la composante principale."""
import os
import sys

import numpy as np

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names    # noqa: E402
from grow_town_slots import components                          # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
S = os.path.join(ICI, r"couches-expanded\villes-sortie")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    listes, W, H = caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))
    noms = flat_names(listes, "Regions")
    lire = lambda n: read_layer(os.path.join(S, f"layer_{n}.hex_layer"))[1].reshape(H, W)    # noqa: E731
    imp, slots, reg = lire("impassable"), lire("townslots"), lire("regions")
    ids, n = components(imp == 1, W, H)
    villes = {}
    for r, q in np.argwhere(slots == 0):
        villes.setdefault(int(reg[r, q]), set()).add(int(ids[r, q]))
    tailles = np.bincount(ids[ids >= 0])
    principale = int(np.argmax(tailles))
    hors = sorted(noms[k] for k, c in villes.items() if principale not in c)
    print(f"{n} composantes franchissables ; principale : {tailles[principale]} hex ; {len(villes)} colonies ; "
          f"hors de la principale : {len(hors)}")
    for h in hors:
        print("   ", h)
    if not hors or "--corriger" not in sys.argv:
        return 1 if hors else 0
    # --corriger : le plus court passage (hex infranchissables à ouvrir) de chaque colonie isolée vers la composante
    # principale ; les hex ouverts gardent leur région (celle de la poche), comme un col
    from collections import deque
    from grow_town_slots import neighbours
    from caime_layers import encode_flat
    import subprocess
    imp2 = imp.copy()
    for k, comps in villes.items():
        if principale in comps:
            continue
        depart = [(int(q), int(r)) for r, q in np.argwhere(np.isin(ids, list(comps)))]
        prec = {c: None for c in depart}
        file = deque(depart)
        fin = None
        while file:
            q, r = file.popleft()
            if ids[r, q] == principale:
                fin = (q, r)
                break
            for nq, nr in neighbours(q, r, W, H):
                if (nq, nr) not in prec:
                    prec[(nq, nr)] = (q, r)
                    file.append((nq, nr))
        n_ouv = 0
        c = fin
        while c is not None:
            q, r = c
            if imp2[r, q] == 0:
                imp2[r, q] = 1
                n_ouv += 1
            c = prec[c]
        print(f"  {noms[k]} : passage de {n_ouv} hex ouvert")
    chemin = os.path.join(S, "layer_impassable.hex_layer")
    with open(chemin, "wb") as fh:
        fh.write(encode_flat("Impassable", imp2.reshape(-1)))
    p = subprocess.run([CAIME, "import-layer", "--map", os.path.join(ICI, r"caime\saison_expanded_map\map.hex"),
                        "--layer", "Impassable", "--file", chemin], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    return 0


if __name__ == "__main__":
    sys.exit(main())
