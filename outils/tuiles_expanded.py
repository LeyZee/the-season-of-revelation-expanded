#!/usr/bin/env python3
"""
tuiles_expanded.py - la carte des tuiles (tile_map.png) du projet Terry d'Expanded : l'export CAIME de la grille, côtes
de CA comprises (4.10.2026). Appelé par `projet_expanded.py` ; se lance aussi seul sur le projet déjà écrit.

Pourquoi : guide Terry de l'Atlas (§ Le terrain d'une carte de campagne) : « exportez tile_map.png depuis CAIME (Tools →
Export → Baseline Tilemap), sans peinture ni retouche » ; l'export donne cliff_gen (253, 3, 1) aux hex de terre qui
touchent la mer, cliff_gen_ends (84, 230, 84) aux transitions avec une plage, sea_coast (255, 255, 0) aux plages, roads
(93, 66, 24) aux routes, generic (223, 180, 145) au reste de la terre, sea (83, 141, 213) à la mer. Jusqu'ici, Expanded
reprenait la carte de la Saison (sans côtes : WH1 n'avait pas de falaises) et composait le reste ; l'audit des guides a
montré 699 hex de mer dessinés en terre et des routes sans route de jeu. Charles (4.10.2026) : « ajoute les côtes de CA,
ça peut être vraiment cool », sur le modèle de The Old World de ChaosRobie. Donc :
- toute la carte = l'export de notre CAIME (verbe export-tilemap, le code du menu ; image à l'envers, rangée 0 au sud,
  retournée ici) ;
- seule exception, l'éther et la déchirure du Bois Rêveur : mer sur des cases INFRANCHISSABLES (`projet_expanded.ether_sud`
  et le voile), sans effet de jeu ;
- le fond marin (sea_height) passe sous FOND_MER_MAX partout où la carte met la mer (guide : « le fond reste sous 0 là
  où il y a de la mer »).
Contrôle après BOB : 0 « Failed to find tile » (guide BOB) ; sinon corriger la GRILLE dans CAIME, jamais la carte.

Usage : python tuiles_expanded.py [--apply]     (sur le projet du bac à sable ; à blanc : bilan seulement)
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile
from collections import Counter

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H                                            # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer                                         # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ATELIER, r"04-projets\saison-expanded\caime\saison_expanded_map\map.hex")
DST = os.path.join(ATELIER, r"04-projets\saison-expanded\terry\saison_expanded_map")
MER = np.array((83, 141, 213, 255), np.uint8)
FOND_MER_MAX = -0.03          # juste sous 0 (−0,3 effaçait les hauts-fonds des côtes)
NOMS = {(83, 141, 213): "sea", (223, 180, 145): "generic", (93, 66, 24): "roads", (253, 3, 1): "cliff_gen",
        (84, 230, 84): "cliff_gen_ends", (255, 255, 0): "sea_coast"}


def export_caime():
    """(export RGBA nord en haut, cases franchissables (H, W) rangée 0 au sud)."""
    with tempfile.TemporaryDirectory() as d:
        sortie = os.path.join(d, "tile_map.png")
        p = subprocess.run([CAIME, "export-tilemap", "--map", CARTE, "--out", sortie], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if p.returncode or not os.path.exists(sortie):
            raise SystemExit(f"export-tilemap de CAIME en échec : {p.stdout} {p.stderr}")
        ex = np.asarray(Image.open(sortie).convert("RGBA"))[::-1].copy()
        subprocess.run([CAIME, "export-layer", "--map", CARTE, "--out", d, "--format", "binary", "--layer", "Impassable"],
                       capture_output=True)
        imp = read_layer(os.path.join(d, "layer_impassable.hex_layer"))[1].reshape(H, W)
    return ex, imp == 1


def defauts_cote():
    """(H, W) rangée 0 au sud : les hex de côte qu'aucune tuile de côte de CA ne couvre (terre : plus de 3 voisins de mer
    ou deux séries de mer ; mer : la même chose côté terre), avec leurs six voisins."""
    import villes_expanded as V
    from caime_layers import caime_names
    from grow_town_slots import DIRS
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([CAIME, "export-layer", "--map", CARTE, "--out", d, "--format", "binary", "--layer", "GroundTypes"],
                       capture_output=True)
        gt = read_layer(os.path.join(d, "layer_ground_types.hex_layer"))[1].reshape(H, W)
    mer = gt >= len(caime_names(V.CAIME, CARTE)[0].get("Land ground types", []))
    defaut = np.zeros((H, W), bool)
    for r in range(H):
        for q in range(W):
            v = []
            for dq, dr in DIRS[q & 1]:
                a, b = r + dr, q + dq
                v.append(bool(mer[a, b] != mer[r, q]) if 0 <= a < H and 0 <= b < W else False)
            n = sum(v)
            series = sum(1 for k in range(6) if v[k] and not v[k - 1])
            if n > 3 or series > 1:
                defaut[r, q] = True
    zone = defaut.copy()
    for r, q in np.argwhere(defaut):
        for dq, dr in DIRS[q & 1]:
            if 0 <= r + dr < H and 0 <= q + dq < W:
                zone[r + dr, q + dq] = True
    print(f"  formes de côte sans tuile de CA (règle n° 97, terre et mer) : {int(defaut.sum())} hex")
    return zone


LAC_MAX_HEX = 30
_LACS = {}


def lacs_hex():
    """(H, W) rangée 0 au sud : les petites étendues d'eau FERMÉES de la grille (au plus LAC_MAX_HEX hex, sans toucher le
    bord de la carte). (5.10.2026, 75 trous de côte : 23 autour de 14 étangs de 4 à 24 hex, dont les 8 lacs de WH1 que la
    grille de la Saison a aussi ; la carte des tuiles de WH1 les peint en terre ordinaire, l'eau vient de leur maillage et
    du creux du relief ; les anneaux de falaise de CAIME autour d'un étang n'ont pas de tuile de CA)"""
    if "hex" in _LACS:
        return _LACS["hex"]
    import villes_expanded as V
    from collections import deque
    from caime_layers import caime_names
    from grow_town_slots import DIRS
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([CAIME, "export-layer", "--map", CARTE, "--out", d, "--format", "binary", "--layer", "GroundTypes"],
                       capture_output=True)
        gt = read_layer(os.path.join(d, "layer_ground_types.hex_layer"))[1].reshape(H, W)
    mer = gt >= len(caime_names(V.CAIME, CARTE)[0].get("Land ground types", []))
    lab = -np.ones((H, W), int)
    lacs = np.zeros((H, W), bool)
    n = 0
    for r0, q0 in np.argwhere(mer):
        if lab[r0, q0] >= 0:
            continue
        f, cases = deque([(int(r0), int(q0))]), []
        lab[r0, q0] = 1
        while f:
            r, q = f.popleft()
            cases.append((r, q))
            for dq, dr in DIRS[q & 1]:
                a, b = r + dr, q + dq
                if 0 <= a < H and 0 <= b < W and mer[a, b] and lab[a, b] < 0:
                    lab[a, b] = 1
                    f.append((a, b))
        bord = any(r in (0, H - 1) or q in (0, W - 1) for r, q in cases)
        if len(cases) <= LAC_MAX_HEX and not bord:
            for r, q in cases:
                lacs[r, q] = True
            n += 1
    print(f"  étangs et lacs fermés de la grille (au plus {LAC_MAX_HEX} hex) : {n}, {int(lacs.sum())} hex")
    _LACS["hex"] = lacs
    return lacs


def lacs_eau(forme):
    """Les lacs fermés (lacs_hex) à la taille de la carte des tuiles `forme`, nord en haut : de l'EAU pour le relief et le
    fond (projet_expanded), de la terre ordinaire pour la carte des tuiles."""
    import projet_expanded as P
    m = P.double_caime(lacs_hex().astype(np.uint8))[::-1] > 0
    if m.shape != tuple(forme[:2]):
        m = cv2.resize(m.astype(np.uint8), (forme[1], forme[0]), interpolation=cv2.INTER_NEAREST) > 0
    return m


def mer_wh1(forme):
    """La mer de la carte des tuiles de la SAISON dans la zone gardée de WH1, à la taille de la carte d'Expanded : ses lacs
    et chenaux (≈ 490 hex franchissables que la grille dit terre), validés en jeu par Charles (eau « comme dans WH1 »)."""
    import projet_expanded as P
    tm = np.asarray(Image.open(os.path.join(P.SRC, "tile_map.png")).convert("RGB"))
    f_t = forme[1] // W
    reste_t = forme[0] - H * f_t
    m = (tm == MER[:3]).all(-1).astype(np.uint8)
    return (P.agrandir(m, f_t, 0, reste_t) > 0) & P.garde_masque(f_t, reste_t)


def composer(ether_px):
    """La carte des tuiles : l'export CAIME ; en mer en plus : l'éther (`ether_px`, booléen nord en haut, à la taille de
    la carte) sur les seules cases infranchissables, et l'eau de la Saison dans la zone gardée de WH1 (mer_wh1)."""
    import projet_expanded as P
    ex, passe = export_caime()
    passe_t = P.double_caime(passe.astype(np.uint8))[::-1] > 0
    ether = ether_px & ~passe_t
    eau_wh1 = mer_wh1(ex.shape[:2])
    out = ex.copy()
    out[ether | eau_wh1] = MER
    # (4.10.2026, première compilation aux côtes de CA : 280 « Failed to find tile », TileSet_cliff_gen, dont 234 à 2 px
    # au plus d'une retouche) la côte de CAIME est dessinée autour de SA terre et de SA mer ; là où l'éther ou les lacs de
    # WH1 ajoutent de la mer, les morceaux de falaise voisins n'ont plus la forme d'une tuile. Près d'une retouche, les
    # pixels de côte redeviennent de la terre ordinaire (generic contre la mer : la règle de la Saison, compilée sans trou) ;
    # partout ailleurs, l'export reste tel quel. (Le relief dessine toujours la falaise de la déchirure dans l'éther.)
    retouche = (out != ex).any(-1)
    pres = cv2.dilate(retouche.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    # Même chose autour des formes de côte qu'aucune tuile de CA ne couvre (GUIDE § 15 n° 97, et son pendant côté mer,
    # relevé le 4.10 sur les signatures des trous : un hex de mer à plus de 3 voisins de terre ou à deux séries de terre,
    # une anse ou un bras de mer d'un hex). 30 des 32 sont dans la zone gardée de WH1 (anses et embouchures de la mer
    # logique de WH1, qui reste celle de WH1) : la côte y prend la règle de la Saison, sur l'hex et ses voisins
    defauts = defauts_cote()
    pres |= P.double_caime(defauts.astype(np.uint8))[::-1] > 0
    cote = np.zeros(out.shape[:2], bool)
    for c in ((253, 3, 1), (84, 230, 84), (255, 255, 0)):
        cote |= (out[..., :3] == c).all(-1)
    rendus = pres & cote
    out[rendus] = (223, 180, 145, 255)
    print(f"  côtes de CA près d'une retouche (éther, lacs de WH1) rendues à la terre ordinaire : {int(rendus.sum())} px")
    # (5.10.2026) les lacs fermés comme dans la carte des tuiles de WH1 : eau et anneau de côte en terre ordinaire (les
    # routes restent) ; l'eau reste dessinée par les plans d'eau et le relief (projet_expanded les traite en eau)
    lac = cv2.dilate(lacs_eau(out.shape).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    lac_px = lac & (cote | (out[..., :3] == MER[:3]).all(-1))
    out[lac_px] = (223, 180, 145, 255)
    print(f"  lacs fermés peints en terre ordinaire, comme WH1 : {int(lac_px.sum())} px")
    # (5.10.2026, accord de Charles ; ÉCART AU GUIDE TERRY DE L'ATLAS, « export CAIME sans retouche », justifié par la mesure
    # sur les cartes de CA, `05-journal\2026-10-05-tuiles-cote\RAPPORT.md` § 3) RACCORD DIRECT PLAGE-FALAISE, comme CA :
    # 412 plages sur la carte des Empires et seulement 36 bouts de falaise (cliff_gen_ends) sur toute la carte ; CAIME en
    # pose un de chaque côté de chaque plage, et BOB les lie souvent à la plage, laissant un trou côté falaise. Les bouts
    # deviennent de la falaise (cliff_gen) ; prédicteur : 102 -> 43 boîtes sans pavage
    bouts = (out[..., :3] == np.array((84, 230, 84), np.uint8)).all(-1)
    out[bouts] = (253, 3, 1, 255)
    print(f"  bouts de falaise (cliff_gen_ends) peints en falaise, raccord plage-falaise de CA : {int(bouts.sum())} px")
    print(f"  eau de la Saison gardée dans WH1 (lacs, chenaux) : {int((eau_wh1 & ~(ex[..., :3] == MER[:3]).all(-1)).sum())} px")
    c = Counter(NOMS.get(tuple(x), str(tuple(x))) for x in out[..., :3].reshape(-1, 3)[::7])
    print(f"  carte des tuiles = export CAIME (côtes de CA) ; éther en mer sur l'infranchissable : {int(ether.sum())} px ; "
          f"part (1 px sur 7) : {dict(c.most_common())}")
    return out


def fond_marin(tuiles):
    """sea_height du projet ramené sous FOND_MER_MAX partout où `tuiles` met la mer."""
    p_sea = glob.glob(os.path.join(DST, "*.sea_height.*.tif"))[0]
    sea = np.asarray(Image.open(p_sea), np.float32).copy()
    mer_t = (tuiles[..., :3] == MER[:3]).all(-1)
    mer8 = cv2.resize(mer_t.astype(np.uint8), (sea.shape[1], sea.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    trop = mer8 & (sea > FOND_MER_MAX)
    sea[trop] = FOND_MER_MAX
    print(f"  fond marin sous la mer de la carte des tuiles : {int(trop.sum())} px ramenés à {FOND_MER_MAX}")
    return p_sea, sea


def ether_du_projet(forme):
    """L'éther et le voile du Bois Rêveur, comme projet_expanded les pose, à la taille de la carte des tuiles."""
    import projet_expanded as P
    f_t = forme[1] // W
    reste_t = forme[0] - H * f_t
    p_t, n_t, _, v_t = P.bois_reveur(f_t, reste_t)
    return (P.ether_sud(f_t, reste_t, p_t, v_t) > 0.5) | v_t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    p_tm = os.path.join(DST, "tile_map.png")
    avant = np.asarray(Image.open(p_tm).convert("RGBA"))
    tuiles = composer(ether_du_projet(avant.shape[:2]))
    print(f"  pixels changés par rapport à la carte du projet : {int((tuiles != avant).any(-1).sum())}")
    p_sea, sea = fond_marin(tuiles)
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    Image.fromarray(tuiles, "RGBA").save(p_tm)
    Image.fromarray(sea, "F").save(p_sea, compression="tiff_lzw")
    print(f"  écrit : {p_tm} ; {p_sea}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
