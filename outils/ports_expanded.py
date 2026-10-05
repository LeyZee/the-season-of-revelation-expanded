#!/usr/bin/env python3
"""
ports_expanded.py - toutes les colonies d'Expanded au modèle de CA (disque de 19 hex ; port = 16 principal + 3 port),
4.10.2026.

Pourquoi : plantage au chargement +0x2613117 (liste vide), nommé par la Construction sur `saison_tor_soleil` après
Bordeleaux (erreur 334) : 9 ports neufs de l'Atlas n'ont pas leur emplacement en disque parfait (16 + 3 mais pas en
disque, ou 16 + 2, 16 + 1). Le modèle et l'outil existent depuis le 21.09 pour la Saison (ERREURS-ET-LECONS n° 45,
`02-scripts\\recentrer_emplacements.py`) ; on l'applique à Expanded. Une précaution d'abord : l'outil rattache une case
de port à une colonie si elle est à 2 hex au plus de ses cases principales ; un port déclaré dont la case de port est
plus loin (L'Anguille : 16 + 0) deviendrait une ville intérieure. Pour chaque région déclarée `port` sans case de port
proche, la case égarée (à moins de 6 hex) est retirée et une case de mer de région de mer voisine de ses cases
principales devient le port ; `recentrer_emplacements` pose ensuite le disque.

Contrôle final : chaque région déclarée port a 16 + 3 en disque, ses cases de mer en région de mer ; chaque colonie de
WH1 est restée identique à la Saison.
Usage : python ports_expanded.py [--apply]     (grille du chantier ; le kit, ensuite, par kit_expanded sous préavis)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
import villes_expanded as V                                                   # noqa: E402
from caime_layers import read_layer, encode_flat, caime_names, flat_names     # noqa: E402
from grow_town_slots import neighbours                                        # noqa: E402
from cadre_expanded import W, H                                               # noqa: E402

ENTREE = os.path.join(V.COUCHES, "ports-entree")
SORTIE = os.path.join(V.COUCHES, "ports-sortie")
RECENTRER = os.path.join(V.ATELIER, r"02-scripts\recentrer_emplacements.py")
SAUVEGARDES = os.path.join(V.ATELIER, r"05-journal\terrain-backups")


def lire(dossier, nom):
    return read_layer(os.path.join(dossier, f"layer_{nom}.hex_layer"))[1].reshape(H, W).copy()


def composantes_risque(imp, riv, terre):
    """Composantes connexes (voisinage d'hex) du terrain à risque : infranchissable, rivière, côte (terre voisine de la
    mer). Rend un tableau (H, W) d'identifiants, -1 hors risque."""
    from collections import deque
    cote = np.zeros((H, W), bool)
    for r, q in np.argwhere(terre):
        if any(not terre[nr, nq] for nq, nr in neighbours(int(q), int(r), W, H)):
            cote[r, q] = True
    risque = (imp != 1) | (riv != 0) | cote
    comp = np.full((H, W), -1, np.int64)
    n = 0
    for r0, q0 in np.argwhere(risque):
        if comp[r0, q0] >= 0:
            continue
        comp[r0, q0] = n
        file_ = deque([(int(q0), int(r0))])
        while file_:
            q, r = file_.popleft()
            for nq, nr in neighbours(q, r, W, H):
                if risque[nr, nq] and comp[nr, nq] < 0:
                    comp[nr, nq] = n
                    file_.append((nq, nr))
        n += 1
    return comp


def risque_ok(d, comp):
    """Règles de SprawlValidator pour l'étendue `d` : toute zone à risque à 2 hex au plus la touche ; une seule touche."""
    touche, pres = set(), set()
    anneau = set()
    for q, r in d:
        anneau |= set(neighbours(q, r, W, H))
    anneau -= d
    anneau2 = set()
    for q, r in anneau:
        anneau2 |= set(neighbours(q, r, W, H))
    anneau2 -= d | anneau
    for q, r in anneau:
        if comp[r, q] >= 0:
            touche.add(int(comp[r, q]))
    for q, r in anneau2:
        if comp[r, q] >= 0:
            pres.add(int(comp[r, q]))
    return len(touche) <= 1 and pres <= touche


def placer_ports(slots, sprawl, reg, gt, imp, riv, rids, noms, n_terre, n_land_reg, plages):
    """Repeint en place chaque port de `rids` hors des règles du guide ; rend (nombre repeint, échecs)."""
    import math
    sys.path.insert(0, os.path.dirname(RECENTRER))
    from recentrer_emplacements import disque
    terre = (gt >= 0) & (gt < n_terre)
    comp = composantes_risque(imp, riv, terre)
    n_rep, echecs = 0, []
    for rid in rids:
        prin = {(int(q), int(r)) for r, q in np.argwhere((reg == rid) & (slots == 0))}
        if not prin:
            continue
        port = {(int(q), int(r)) for r, q in np.argwhere(slots == 1)
                if min(abs(q - a) + abs(r - b) for a, b in prin) <= 2}
        union = prin | port
        mer_u = [c for c in union if not terre[c[1], c[0]]]
        terre_port = [c for c in port if terre[c[1], c[0]]]
        if len(prin) == 16 and len(port) == 3 and len(mer_u) == 2 and all(terre[c[1], c[0]] for c in prin) \
                and all(plages[c[1], c[0]] for c in terre_port) and risque_ok(union, comp):
            continue
        cx = sum(q for q, _ in union) / len(union)
        cy = sum(r for _, r in union) / len(union)
        autre = slots >= 0
        for q, r in union:
            autre[r, q] = False
        meilleurs = []
        # CA (mesure de la session des fleuves sur 290 ports : _map_1, _map_7, chaos_map_4) : 3 hex de Port consécutifs
        # de l'anneau 2 en [mer, mer, terre] (127 sur 130), la terre sur la PLAGE (126 sur 127) ; en repli seulement,
        # [mer, mer, mer] (3 sur 130 chez CA)
        for n_mer in (2, 3):
            for q in range(max(0, int(cx) - 8), min(W, int(cx) + 9)):
                for r in range(max(0, int(cy) - 8), min(H, int(cy) + 9)):
                    d, ordre = disque(q, r, W, H)
                    if len(d) != 19 or len(ordre) != 12 or any(autre[c[1], c[0]] for c in d):
                        continue
                    mers = [c for c in d if not terre[c[1], c[0]]]
                    terres = [c for c in d if terre[c[1], c[0]]]
                    if len(mers) != n_mer or any(reg[c[1], c[0]] < n_land_reg or c not in ordre for c in mers):
                        continue
                    idx_m = sorted(ordre.index(c) for c in mers)
                    debut = next((k for k in idx_m if all(((k + t) % 12) in idx_m for t in range(n_mer))), None)
                    if debut is None:
                        continue                      # les hex de mer doivent se suivre sur l'anneau
                    if any(reg[c[1], c[0]] != rid or imp[c[1], c[0]] != 1 for c in terres):
                        continue
                    if not risque_ok(d, comp):
                        continue
                    suite = [ordre[(debut + t) % 12] for t in range(n_mer)]
                    if n_mer == 3:
                        meilleurs.append(((q - cx) ** 2 + (r - cy) ** 2, d, suite))
                        continue
                    for bout, arc in ((ordre[(debut + 2) % 12], suite + [ordre[(debut + 2) % 12]]),
                                      (ordre[(debut - 1) % 12], [ordre[(debut - 1) % 12]] + suite)):
                        if terre[bout[1], bout[0]]:
                            meilleurs.append(((q - cx) ** 2 + (r - cy) ** 2, d, arc))
                            break
            if meilleurs:
                break
        if not meilleurs:
            echecs.append(noms[rid])
            continue
        dist, d, arc = min(meilleurs, key=lambda m: m[0])
        for q, r in union:
            slots[r, q] = -1
            sprawl[r, q] = 0
        for q, r in d:
            slots[r, q] = 1 if (q, r) in arc else 0
            sprawl[r, q] = 1
        for q, r in arc:
            if terre[r, q]:
                plages[r, q] = 1                      # le hex de port à terre sur la plage, comme chez CA
        print(f"    {noms[rid]:42} : disque à la CA (port [mer, mer, plage]), déplacé de {math.sqrt(dist):.1f} hex")
        n_rep += 1
    return n_rep, echecs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for d in (ENTREE, SORTIE):
        shutil.rmtree(d, ignore_errors=True)
    subprocess.run([V.CAIME, "export-layer", "--map", V.CARTE_EXP, "--out", ENTREE, "--all", "--format", "binary"],
                   capture_output=True)
    le = caime_names(V.CAIME, V.CARTE_EXP)[0]
    noms = flat_names(le, "Regions")
    n_land_reg = len(le.get("Land regions", []))
    n_terre = len(le.get("Land ground types", []))
    slots, reg, gt = lire(ENTREE, "town_slots"), lire(ENTREE, "regions"), lire(ENTREE, "ground_types")
    decl = json.load(open(os.path.join(V.ATLAS, "expanded_declaration.json"), encoding="utf-8"))
    ports_voulus = [e["cle_jeu"] for e in decl["regions"] if e.get("port") and not e.get("is_sea")]
    idx = {n: i for i, n in enumerate(noms)}
    # 1. ports déclarés sans case de port à 2 hex de leurs cases principales
    poses = []
    for cle in ports_voulus:
        if cle not in idx:
            continue
        prin = [(int(q), int(r)) for r, q in np.argwhere((reg == idx[cle]) & (slots == 0))]
        if not prin:
            continue
        pres = lambda p, lim: min(abs(p[0] - q) + abs(p[1] - r) for q, r in prin) <= lim      # noqa: E731
        ports = [(int(q), int(r)) for r, q in np.argwhere(slots == 1)]
        if any(pres(p, 2) for p in ports):
            continue
        egares = [p for p in ports if pres(p, 6)]
        for q, r in egares:
            slots[r, q] = -1
        cands = sorted({(nq, nr) for q, r in prin for nq, nr in neighbours(q, r, W, H)
                        if gt[nr, nq] >= n_terre and reg[nr, nq] >= n_land_reg and slots[nr, nq] < 0})
        if not cands:
            # ville à l'intérieur des terres : une case de port sur la terre de la région voisine de la ville, la plus
            # proche de la mer ; recentrer_emplacements cherche ensuite (jusqu'à 8 hex) le disque portuaire de la région
            mer = np.argwhere((gt >= n_terre) & (reg >= n_land_reg))
            cands = sorted({(nq, nr) for q, r in prin for nq, nr in neighbours(q, r, W, H)
                            if reg[nr, nq] == idx[cle] and slots[nr, nq] < 0 and gt[nr, nq] < n_terre},
                           key=lambda c: np.min(np.abs(mer[:, 1] - c[0]) + np.abs(mer[:, 0] - c[1])))
            if not cands:
                print(f"  !! {cle} : port déclaré sans case libre autour de la ville")
                continue
        q, r = cands[0] if gt[cands[0][1], cands[0][0]] < n_terre else cands[len(cands) // 2]
        slots[r, q] = 1
        poses.append(f"{cle} (case égarée retirée : {egares}, port posé en {(q, r)})")
    print(f"  ports déclarés : {len(ports_voulus)} ; rattachés à nouveau : {poses or 'aucun'}")
    with open(os.path.join(ENTREE, "layer_town_slots.hex_layer"), "wb") as fh:
        fh.write(encode_flat("TownSlots", slots.reshape(-1)))
    # 2. le modèle de CA
    p = subprocess.run([sys.executable, RECENTRER, "--layers", ENTREE, "--out", SORTIE, "--noms-carte", V.CARTE_EXP,
                        "--caime", V.CAIME], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("  " + "\n  ".join((p.stdout + p.stderr).strip().splitlines()[-14:]))
    if p.returncode:
        return p.returncode
    # 2 bis. les ports neufs de l'Atlas COMME CHEZ CA (4.10.2026) : disque de 19, 16 principaux sur la terre, 3 hex de
    # Port consécutifs de l'anneau 2 en [mer, mer, terre], la terre sur la plage (mesure de la session des fleuves sur
    # 290 ports de CA : 127 sur 130 et 131 sur 134 ; banc-fleuve, conformite_guide.md § 1.1 ; le guide CAIME de l'Atlas,
    # « dont un en mer », ne décrivait que le minimum du validateur) ; étendue = les 19 ; terrain à risque (SprawlValidator
    # .cs : IsImpassable || IsRiver || IsCoast) au contact ou à 3 hex, une seule zone au contact
    sl2, sp2 = lire(SORTIE, "town_slots"), lire(SORTIE, "town_sprawl")
    pl2 = lire(ENTREE, "beaches")
    pl_avant = pl2.copy()
    n_rep, echecs = placer_ports(sl2, sp2, reg, gt, lire(ENTREE, "impassable"), lire(ENTREE, "rivers"),
                                 [idx[c] for c in ports_voulus if c in idx], noms, n_terre, n_land_reg, pl2)
    print(f"  ports repeints à la CA ([mer, mer, plage]) : {n_rep} ; sans disque conforme : {echecs or 'aucun'} ; "
          f"plages ajoutées : {int(((pl2 > 0) & (pl_avant == 0)).sum())}")
    for nom, v in (("TownSlots", sl2), ("TownSprawl", sp2)):
        with open(os.path.join(SORTIE, f"layer_{nom.lower().replace('town', 'town_')}.hex_layer"), "wb") as fh:
            fh.write(encode_flat(nom, v.reshape(-1)))
    with open(os.path.join(SORTIE, "layer_beaches.hex_layer"), "wb") as fh:
        fh.write(encode_flat("Beaches", pl2.reshape(-1)))
    # 3. contrôles
    ennuis = []
    for cle in ports_voulus:
        if cle not in idx:
            continue
        prin = (reg == idx[cle]) & (sl2 == 0)
        pq = [(int(q), int(r)) for r, q in np.argwhere(sl2 == 1)
              if min(abs(q - a_) + abs(r - b_) for b_, a_ in np.argwhere(prin)) <= 2]
        mer_hors = [c for c in pq if gt[c[1], c[0]] >= n_terre and reg[c[1], c[0]] < n_land_reg]
        n_mer = sum(1 for c in pq if gt[c[1], c[0]] >= n_terre)
        sans_plage = [c for c in pq if gt[c[1], c[0]] < n_terre and not pl2[c[1], c[0]]]
        if prin.sum() != 16 or len(pq) != 3 or mer_hors or n_mer not in (2, 3) or sans_plage:
            ennuis.append(f"{cle} : {int(prin.sum())} + {len(pq)} ; {n_mer} en mer ; mer hors région de mer {mer_hors} ; "
                          f"port à terre sans plage {sans_plage}")
    s_sl = read_layer(os.path.join(V.COUCHES_SAISON, "layer_town_slots.hex_layer"))[1].reshape(440, 400)
    s_slk = lire(ENTREE, "town_slots")[V.DY:V.DY + 440, V.DX:V.DX + 400]
    wh1_change = int(((sl2[V.DY:V.DY + 440, V.DX:V.DX + 400] != s_slk) & (s_sl >= 0)).sum())
    print(f"  ports hors 16 + 3 après coup : {ennuis or 'aucun'} ; cases de colonies de WH1 changées : {wh1_change}")
    if not a.apply:
        print("  à blanc : rien d'écrit dans la grille")
        return 0
    if ennuis or wh1_change:
        print("  !! contrôle en échec : rien d'écrit")
        return 2
    os.makedirs(SAUVEGARDES, exist_ok=True)
    sauve = os.path.join(SAUVEGARDES, time.strftime("%Y%m%d-%H%M%S") + "-map.hex-expanded-avant-ports")
    shutil.copy2(V.CARTE_EXP, sauve)
    args = [V.CAIME, "import-layer", "--map", V.CARTE_EXP]
    for nom, f in (("TownSlots", "town_slots"), ("TownSprawl", "town_sprawl"), ("Beaches", "beaches")):
        args += ["--layer", nom, "--file", os.path.join(SORTIE, f"layer_{f}.hex_layer")]
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    p = subprocess.run([V.CAIME, "validate", "--map", V.CARTE_EXP, "--town-slots", "--town-sprawl", "--beaches"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if ": OK" in l or "rror" in l or "arning" in l))
    print(f"  sauvegarde : {sauve}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
