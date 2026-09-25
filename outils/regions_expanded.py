#!/usr/bin/env python3
"""
regions_expanded.py - la couche des RÉGIONS de la grille CAIME d'Expanded, d'après l'Atlas (phase 2 bis).

Pourquoi (25.09.2026, 19 h 35 ; décisions de Charles : « l'Atlas l'emporte », partie jouable de WH1 redessinée d'après
l'Atlas) : les 76 régions et 21 provinces sont déclarées dans le kit (19 h 14, 19 h 21, 19 h 28) et CAIME les connaît
(`sync-names`). Il reste à dire, hex par hex, à quelle région appartient chaque case.

Ordre de priorité (du plus précis au plus général), ligne 0 = sud comme CAIME :
1. découpes de l'Atlas (`extension_regions.npz`, couche `split`) ;
2. régions neuves (`lab`) et reprise de Fort Solstice (couche `R` de `extension_geo.npz`, valeur de la déclaration,
   moins les cases déjà prises) ;
3. mers de l'Atlas (`labm`) ;
4. dans le cadre de la Saison : la couche des régions de la Saison (renumérotée par nom), sauf Fort Solstice de WH1,
   remplacé par sa reprise ;
5. bande du sud : régions du Bois Rêveur (`reves_grilles.npz`, couche `region`) ; voile = terre sauvage ; éther = mer
   sauvage ;
6. ailleurs : terre sauvage ou mer sauvage de WH1 (`wh_dlc05_wilderness_land` / `_sea`), selon l'Atlas.
Chaque entrée de `expanded_declaration.json` donne sa grille ({fichier, couche, valeur}) : aucune correspondance devinée.
Contrôles : toute région déclarée a des cases (sauf absence justifiée), aucune case de terre sans région.

Usage :
    python regions_expanded.py [--sans-import]
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, encode_flat, caime_names, flat_names    # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
KIT = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit"
CARTE_SAISON = os.path.join(KIT, r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex")
COUCHES_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE_EXP = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
SORTIE = os.path.join(ICI, "couches-expanded")
ATLAS = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
W, H, DX, DY, SW, SH, Y0 = 560, 825, 120, 250, 400, 440, 250
TERRE_SAUVAGE, MER_SAUVAGE = "wh_dlc05_wilderness_land", "wh_dlc05_wilderness_sea"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-import", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.load(open(os.path.join(ATLAS, "expanded_declaration.json"), encoding="utf-8"))
    grilles = {"extension_regions.npz": np.load(os.path.join(ATLAS, "extension_regions.npz")),
               "extension_geo.npz": np.load(os.path.join(ATLAS, "extension_geo.npz")),
               "reves_grilles.npz": np.load(os.path.join(ATLAS, "reves_grilles.npz"))}
    src, _, _ = caime_names(CAIME, CARTE_SAISON)
    dst, dw, dh = caime_names(CAIME, CARTE_EXP)
    assert (dw, dh) == (W, H)
    noms_exp = flat_names(dst, "Regions")
    index = {n: i for i, n in enumerate(noms_exp)}

    def masque(entree):
        """Cases de la grille d'Expanded (825 × 560, ligne 0 = sud) d'une entrée de la déclaration."""
        g = entree["grille"]
        m = grilles[g["fichier"]][g["couche"]] == g["valeur"]
        out = np.zeros((H, W), bool)
        if g["fichier"] == "reves_grilles.npz":
            out[0:m.shape[0], :m.shape[1]] = m
        else:
            out[Y0:Y0 + m.shape[0], :m.shape[1]] = m
        return out

    reg = np.full((H, W), -1, np.int64)
    # 4. la Saison dans son cadre (renumérotée par nom)
    _, v = read_layer(os.path.join(COUCHES_SAISON, "layer_regions.hex_layer"))
    s_noms = flat_names(src, "Regions")
    # une région de WH1 remplacée par une reprise (Fort Solstice) : ses cases de la Saison vont à la reprise
    remplace = {t["cle_jeu"]: t["remplacee_par"] for t in d.get("regions_wh1_touchees", [])
                if t.get("dans_expanded") == 0 and t.get("remplacee_par")}
    table = np.array([index.get(remplace.get(n, n), -1) for n in s_noms] + [-1])
    v = v.reshape(SH, SW)
    reg[DY:DY + SH, DX:DX + SW] = np.where(v < 0, -1, table[np.clip(v, 0, None)])
    absents = sorted({s_noms[i] for i in np.unique(v) if i >= 0 and s_noms[i] not in index})
    print(f"  Saison : {len(s_noms)} régions ; absentes de la carte Expanded (remplacées) : {absents}")
    # 6. hors du cadre, dans l'Atlas : terre / mer sauvages
    r = grilles["extension_regions.npz"]
    terre = np.zeros((H, W), bool)
    terre[Y0:Y0 + r["terre"].shape[0], :W] = r["terre"]
    mer = np.zeros((H, W), bool)
    mer[Y0:Y0 + r["mer"].shape[0], :W] = r["mer"]
    hors_cadre = np.ones((H, W), bool)
    hors_cadre[DY:DY + SH, DX:DX + SW] = False
    reg = np.where(hors_cadre & terre & (reg < 0), index[TERRE_SAUVAGE], reg)
    reg = np.where(hors_cadre & mer & (reg < 0), index[MER_SAUVAGE], reg)
    # 5. bande du sud : Bois Rêveur, voile, éther
    rv = grilles["reves_grilles.npz"]
    sud = np.zeros((H, W), bool)
    sud[0:Y0] = True
    voile = np.zeros((H, W), bool)
    voile[0:rv["voile"].shape[0], :W] = rv["voile"]
    reg = np.where(sud & (reg < 0), index[MER_SAUVAGE], reg)
    reg = np.where(voile, index[TERRE_SAUVAGE], reg)
    # 1-3 et 5 : les entrées de la déclaration, de la plus générale à la plus précise (la dernière écrite gagne)
    ordre = {"bois_reveur": 0, "mer": 1, "reprise": 2, "neuve": 3, "decoupe": 4}
    entrees = sorted(d["regions"], key=lambda e: ordre.get(e["categorie"], 9))
    vides = []
    for e in entrees:
        m = masque(e)
        if e["categorie"] == "reprise":
            # ses cases viennent déjà de la couche de la Saison (renumérotée) ; les découpes passent après
            m = reg == index[e["cle_jeu"]]
        if e["categorie"] == "bois_reveur":
            m &= ~voile
        if not m.any():
            vides.append(e["cle_jeu"])
        reg = np.where(m, index[e["cle_jeu"]], reg)
    # lacs de l'Atlas (ni terre ni mer : couche `lac` de extension_geo.npz, 405 cases le 25.09) : mer sauvage ; un reste
    # éventuel prend la région voisine la plus proche
    lac = np.zeros((H, W), bool)
    lg = grilles["extension_geo.npz"]["lac"]
    lac[Y0:Y0 + lg.shape[0], :lg.shape[1]] = lg
    print(f"  lacs de l'Atlas sans région : {int((lac & (reg < 0)).sum())} -> mer sauvage")
    reg = np.where(lac & (reg < 0), index[MER_SAUVAGE], reg)
    if (reg < 0).any():
        import cv2
        _, lab = cv2.distanceTransformWithLabels((reg < 0).astype(np.uint8), cv2.DIST_L2, 5,
                                                 labelType=cv2.DIST_LABEL_PIXEL)
        pts = np.argwhere(reg >= 0)
        valeur = np.zeros(lab.max() + 1, np.int64)
        valeur[lab[pts[:, 0], pts[:, 1]]] = reg[pts[:, 0], pts[:, 1]]
        n = int((reg < 0).sum())
        reg = np.where(reg < 0, valeur[lab], reg)
        print(f"  {n} case(s) restante(s) confiée(s) à la région voisine")
    # la clé de WH1 remplacée ne doit plus rester nulle part
    for t in d.get("regions_wh1_touchees", []):
        if t.get("dans_expanded") == 0 and t["cle_jeu"] in index:
            reste = int((reg == index[t["cle_jeu"]]).sum())
            print(f"  {t['cle_jeu']} : {reste} case(s) restante(s) (attendu 0)")
    comptes = np.bincount(reg[reg >= 0], minlength=len(noms_exp))
    sans = [noms_exp[i] for i in range(len(noms_exp)) if comptes[i] == 0]
    print(f"  cases sans région : {int((reg < 0).sum())} ; régions sans case : {sans}")
    print(f"  entrées de la déclaration sans case : {vides}")
    os.makedirs(SORTIE, exist_ok=True)
    chemin = os.path.join(SORTIE, "layer_regions.hex_layer")
    with open(chemin, "wb") as fh:
        fh.write(encode_flat("Regions", reg.reshape(-1)))
    np.save(os.path.join(SORTIE, "regions_expanded.npy"), reg.astype(np.int16))
    print(f"  couche écrite : {chemin}")
    if a.sans_import:
        return 0
    p = subprocess.run([CAIME, "import-layer", "--map", CARTE_EXP, "--layer", "Regions", "--file", chemin],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved" in l or "rror" in l))
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
