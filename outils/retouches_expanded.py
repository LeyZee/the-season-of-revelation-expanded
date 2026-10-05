#!/usr/bin/env python3
"""
retouches_expanded.py - corrections de la grille d'Expanded d'après la validation de CAIME (25.09.2026, 19 h 55 ;
`05-journal\\validation-expanded-1955.log`).

1. CLIMATS : 254 966 hex de l'extension sans climat. La Saison n'en emploie que deux : `mtn_pass` (montagnes) et
   `brt_moorlands` (tout le reste, mer comprise) ; même règle : sol `mountain` ou montagne de l'Atlas -> `mtn_pass`,
   sinon `brt_moorlands`.
2. PASSAGES DES COLS : les hex franchissables restés en terre sauvage (tracés des ouvertures) passent à la région neuve
   ou de WH1 la plus proche (« terre sauvage sans ville mais pas entièrement infranchissable »).
3. HEX INFRANCHISSABLES ISOLÉS (64) : un hex de terre infranchissable dont les six voisins sont franchissables devient
   franchissable.
Rien dans le kit. Import dans le map.hex de Climates, Regions, Impassable.

Usage :
    python retouches_expanded.py [--sans-import]
"""
import argparse
import os
import subprocess
import sys
from collections import Counter, deque

import numpy as np

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, encode_flat, caime_names, flat_names    # noqa: E402
from grow_town_slots import neighbours                                        # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE_EXP = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
COUCHES = os.path.join(ICI, "couches-expanded")
SORTIE = os.path.join(COUCHES, "villes-sortie")          # sortie de villes_expanded.py (couches à jour)
ATLAS = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
# (3.10.2026 : 560 × 905, WH1 en (x + 120, y + 330), Atlas dès la rangée 250, reflet R' = 587 − R : cadre_expanded.py)
from cadre_expanded import SUD, REFLET, RANG_ATLAS, DX, DY, SW, SH           # noqa: E402


def lire(nom, dossier=SORTIE):
    return read_layer(os.path.join(dossier, f"layer_{nom.lower()}.hex_layer"))[1]


def ecrire(nom, v):
    chemin = os.path.join(SORTIE, f"layer_{nom.lower()}.hex_layer")
    with open(chemin, "wb") as fh:
        fh.write(encode_flat(nom, np.asarray(v).reshape(-1)))
    return chemin


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-import", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    listes, W, H = caime_names(CAIME, CARTE_EXP)
    climats = flat_names(listes, "Climates")
    sols = flat_names(listes, "GroundTypes")
    noms = flat_names(listes, "Regions")
    reg = lire("Regions").reshape(H, W).copy()
    sol = lire("GroundTypes").reshape(H, W)
    imp = lire("Impassable").reshape(H, W).copy()
    clim = read_layer(os.path.join(COUCHES, "layer_climates.hex_layer"))[1].reshape(H, W).copy()
    n_terre = len(listes.get("Land ground types", []))
    terre = (sol >= 0) & (sol < n_terre)

    # 1. climats
    g = np.load(os.path.join(ATLAS, "extension_geo.npz"))
    mont = np.zeros((H, W), bool)
    mont[RANG_ATLAS:RANG_ATLAS + g["montagne"].shape[0], :W] = g["montagne"]
    vide = clim < 0
    choix = np.where((sol == sols.index("mountain")) | (mont & terre), climats.index("mtn_pass"),
                     climats.index("brt_moorlands"))
    clim = np.where(vide, choix, clim)
    print(f"  climats posés : {int(vide.sum())} hex (mtn_pass {int((vide & (choix == climats.index('mtn_pass'))).sum())})")

    # 2. hex franchissables restés en terre sauvage -> région la plus proche (terre, hors terre et mer sauvages)
    sauvage = {noms.index("wh_dlc05_wilderness_land"), noms.index("wh_dlc05_wilderness_sea")}
    a_rattacher = [(int(q), int(r)) for r, q in np.argwhere((imp == 1) & terre & np.isin(reg, list(sauvage)))]
    rattaches = 0
    for q0, r0 in a_rattacher:
        vus, file = {(q0, r0)}, deque([(q0, r0)])
        while file:
            q, r = file.popleft()
            if terre[r, q] and reg[r, q] not in sauvage:
                reg[r0, q0] = reg[r, q]
                rattaches += 1
                break
            for nq, nr in neighbours(q, r, W, H):
                if (nq, nr) not in vus and abs(nq - q0) + abs(nr - r0) <= 30:
                    vus.add((nq, nr))
                    file.append((nq, nr))
    print(f"  passages en terre sauvage : {len(a_rattacher)} hex, {rattaches} rattachés à une région")

    # 3. infranchissables isolés
    isoles, laisses = 0, 0
    for r, q in np.argwhere((imp == 0) & terre):
        vois = list(neighbours(int(q), int(r), W, H))
        if len(vois) == 6 and all(imp[nr, nq] == 1 for nq, nr in vois):
            # (3.10.2026 : deux cases de terre SAUVAGE ouvertes ainsi, au bord de la mer du nord, restaient franchissables
            # sans région ni ville) : une case sauvage prend la région de terre voisine la plus fréquente, sinon reste fermée
            if reg[r, q] in sauvage:
                c = Counter(int(reg[nr, nq]) for nq, nr in vois if terre[nr, nq] and reg[nr, nq] not in sauvage)
                if not c:
                    laisses += 1
                    continue
                reg[r, q] = c.most_common(1)[0][0]
            imp[r, q] = 1
            isoles += 1
    print(f"  infranchissables isolés rendus franchissables : {isoles} ; laissés fermés (terre sauvage seule) : {laisses}")
    # 3 bis (3.10.2026, validation CAIME : « passable hole fully enclosed by impassable hexes », 3 cases ; deux coupaient
    # Oisillon et le Camp des Orques de fer en deux morceaux) : une case de terre franchissable dont les six voisins sont
    # fermés se referme (jamais une case de ville)
    slots_ = lire("TownSlots").reshape(H, W)
    trous = 0
    for r, q in np.argwhere((imp == 1) & terre & (slots_ < 0)):
        vois = list(neighbours(int(q), int(r), W, H))
        if len(vois) == 6 and all(imp[nr, nq] != 1 and terre[nr, nq] for nq, nr in vois):
            imp[r, q] = 0
            trous += 1
    # (et une poche de quelques cases, sans ville, sans issue : 3 cases dans la forêt de Karak Bhufdar, 3.10.2026)
    from grow_town_slots import components
    ids, n = components((imp == 1), W, H)
    tailles = np.bincount(ids[ids >= 0])
    principale = int(np.argmax(tailles))
    for k in range(n):
        if k != principale and tailles[k] < 20 and not ((ids == k) & (slots_ >= 0)).any():
            imp[ids == k] = 0
            trous += int(tailles[k])
    print(f"  trous et poches franchissables enfermés, sans ville, refermés : {trous} cases")
    # 3 ter : une case de terre sans aucun voisin de sa région (région morcelée : « split into 2 disconnected areas ») prend
    # la région de terre voisine la plus fréquente, et son passage (jamais une case de ville ni de WH1 dans son cadre)
    isolees = 0
    regions_wh1 = {i for i, n in enumerate(noms) if n.startswith("wh_dlc05_")}
    for r, q in np.argwhere(terre & (slots_ < 0)):
        if reg[r, q] in sauvage or (DY <= r < DY + SH and DX <= q < DX + SW and reg[r, q] in regions_wh1):
            continue
        vois = list(neighbours(int(q), int(r), W, H))
        if any(reg[nr, nq] == reg[r, q] for nq, nr in vois):
            continue
        c = Counter(int(reg[nr, nq]) for nq, nr in vois if terre[nr, nq])
        if c:
            nouveau = c.most_common(1)[0][0]
            reg[r, q] = nouveau
            pas = [imp[nr, nq] for nq, nr in vois if reg[nr, nq] == nouveau]
            imp[r, q] = Counter(pas).most_common(1)[0][0]
            isolees += 1
    print(f"  cases de terre isolées de leur région, rattachées à la voisine : {isolees}")
    # 4. rivières du Bois Rêveur : (3.10.2026) reflétées désormais dans villes_expanded.py, AVANT la pose des villes
    # (reflétées ici, après, elles tombaient à 2 hex de l'étalement du palais d'Argwylon : Error de CAIME)
    riv = lire("Rivers").reshape(H, W).copy()
    rv = np.load(os.path.join(ATLAS, "reves_grilles.npz"))
    rterre = np.zeros((H, W), bool)
    rterre[0:rv["terre"].shape[0], :W] = rv["terre"] & ~rv["voile"]
    # 5. FIL DE RIVIÈRE CACHÉ (25.09.2026, 20 h 15 ; conseil de ChaosRobie, accord de Charles) : le Bois Rêveur ne
    # s'atteint que par les portails, mais le calcul des chemins du jeu veut une carte d'un seul tenant (les nœuds de
    # téléportation ne comptent pas) ; comme la Rivière des Échos de The Old World, une ligne de rivière d'un hex, cachée
    # sous le voile, relie la Porte d'hiver (Atylwyth) à son reflet. Chaque hex prend la région terrestre la plus proche.
    # (3.10.2026 : depuis les Voûtes, un fil de la porte à son reflet percerait leur massif sur 90 hex, un raccourci
    # infranchissable partout ailleurs ; il part donc du bas de la vallée des Voûtes la plus proche de la colonne de la
    # Porte d'hiver (la Route du Fleuve, de Karak Grom) et ne traverse que le voile, jusqu'à la première case du reflet)
    import json
    rj = json.load(open(os.path.join(ATLAS, "reves_grilles.json"), encoding="utf-8"))
    porte = next(p for p in rj["portes"] if p["cle"] == "hiver")
    q_porte = int(round(porte["hex"][0])) + 120
    bas_voutes = [q for q in range(W) if imp[SUD, q] == 1 and terre[SUD, q]]
    assert bas_voutes, "aucune case franchissable au pied des Voûtes"
    q_fil = min(bas_voutes, key=lambda q: abs(q - q_porte))
    r_haut = SUD - 1
    r_bas = next(r for r in range(SUD - 1, -1, -1) if rterre[r, q_fil])
    fil = [(q_fil, r) for r in range(r_bas, r_haut + 1)]
    ouverts = 0
    for q, r in fil:
        riv[r, q] = 1
        if imp[r, q] == 0:
            ouverts += 1
        imp[r, q] = 1
        if reg[r, q] in sauvage:
            vus, file = {(q, r)}, deque([(q, r)])
            while file:
                cq, cr = file.popleft()
                if terre[cr, cq] and reg[cr, cq] not in sauvage and (cq, cr) not in fil:
                    reg[r, q] = reg[cr, cq]
                    break
                for nq, nr in neighbours(cq, cr, W, H):
                    if (nq, nr) not in vus:
                        vus.add((nq, nr))
                        file.append((nq, nr))
    bout_nord = noms[reg[SUD, q_fil]]
    bout_sud = noms[reg[r_bas, q_fil]]
    print(f"  fil de rivière caché : colonne {q_fil} (porte d'hiver : {q_porte}), rangées {r_bas}-{r_haut} ({len(fil)} hex, "
          f"{ouverts} ouverts) ; de {bout_nord} (pied des Voûtes) à {bout_sud}")
    fichiers = {"Climates": ecrire("Climates", clim), "Regions": ecrire("Regions", reg),
                "Impassable": ecrire("Impassable", imp), "Rivers": ecrire("Rivers", riv)}
    with open(os.path.join(COUCHES, "layer_climates.hex_layer"), "wb") as fh:
        fh.write(encode_flat("Climates", clim.reshape(-1)))
    with open(os.path.join(COUCHES, "layer_regions.hex_layer"), "wb") as fh:
        fh.write(encode_flat("Regions", reg.reshape(-1)))
    if a.sans_import:
        return 0
    args = [CAIME, "import-layer", "--map", CARTE_EXP]
    for nom, chemin in fichiers.items():
        args += ["--layer", nom, "--file", chemin]
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
