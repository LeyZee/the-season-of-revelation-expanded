#!/usr/bin/env python3
"""
rivieres_svg_grille.py - les rivières de la carte de l'Atlas (`travail\\carte_papier_v2.svg`), en cases de la grille
d'Expanded et en tracés (colonne, rangée), pour la couche Rivers de CAIME et pour les lits du relief.

Pourquoi (3.10.2026) : la grille prenait les rivières de l'extension dans `riv_ext` (extension_geo.npz), relevé brut de
l'Atlas en escaliers d'une case ; au Reikland jouable, un maillage si dense qu'Ubersreik ne passait plus la validation de
CAIME (étalement entre deux rivières), et que Charles l'avait déjà refusé sur la minicarte (« au Reikland, la rivière part
un peu de partout »). La carte de l'Atlas a ses rivières raccordées, triées et lissées (`carte_papier_v2.reseau_riviere`),
celles que la minicarte dessine (`minicarte_parchemin.rivieres_svg`) : le jeu prend les mêmes.

Repère des chemins (session « Extension », 3.10.2026 : carte_papier_v2.pt) : linéaire, x de 0 à 1120 pour les 560
colonnes, y de 0 à 2090 pour les 905 rangées, du nord au sud ; case = (floor(x / 2), floor(905 − y / 2,3094)), sans demi-
rangée des colonnes impaires, comme toutes les grilles .npz de l'Atlas (`case_lineaire`, par défaut). Contrôle :
`python rivieres_svg_grille.py` compare les rivières de WH1 du même fichier (classe « riviere ») à la couche Rivers de la
Saison : 79 % sur la même case, 100 % à une case au plus (l'autre convention, `case`, au centre d'hex, fait pareil).

Classes prises : « riviere neuve » et « riviere raccord ajout ». Laissées : « riviere » (celles de WH1 : la grille garde la
couche de la Saison), « rv-riviere » (le Bois Rêveur se reflète de WH1), « riviere souterraine » (la Bruissante coule sous
les Voûtes : aucun lit en surface).
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H                                      # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
SVG_VIVANT = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\carte_papier_v2.svg")
# (4.10.2026, 14 h 45, préavis de la session des Voûtes : la Brienne est redessinée selon le lore dans le SVG vivant, forme
# encore en retouche ; « ne relance pas tes rivières sur ce SVG avant mon feu vert ») : copie figée du 3.10 au soir, la
# dernière d'avant la retouche ; revenir à SVG_VIVANT au feu vert, et retirer alors de la grille les cases de rivière de
# WH1 de l'ancien cours (≈ (95, 153) à (181, 124), passé en « riviere saison-seule »)
SVG = os.path.join(ATELIER, r"05-journal\2026-10-04-fleuves-navigables-atlas\avant-20261004\carte_papier_v2.svg")
LARGEUR_SVG, HAUTEUR_SVG = 1120.0, 2090.0
DEC = 0.5
CLASSES = ("riviere neuve", "riviere raccord ajout")


def chemins(classes=CLASSES):
    """[[(x, y), ...]] en px du SVG."""
    t = open(SVG, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<path d="([^"]*)" class="(riviere[^"]*)"', t):
        if m.group(2) not in classes:
            continue
        jetons = re.findall(r"[MmLlHhVv]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", m.group(1))
        cmd, i, x, y, p = None, 0, 0.0, 0.0, []
        while i < len(jetons):
            j = jetons[i]
            if j.isalpha():
                cmd = j
                i += 1
                if cmd in "Mm":
                    if len(p) >= 2:
                        out.append(p)
                    a, b = float(jetons[i]), float(jetons[i + 1])
                    x, y = (x + a, y + b) if cmd == "m" else (a, b)
                    p = [(x, y)]
                    i += 2
                    cmd = "l" if cmd == "m" else "L"
                continue
            if cmd in "Hh":
                v = float(j)
                x = x + v if cmd == "h" else v
                i += 1
            elif cmd in "Vv":
                v = float(j)
                y = y + v if cmd == "v" else v
                i += 1
            else:
                a, b = float(j), float(jetons[i + 1])
                x, y = (x + a, y + b) if cmd == "l" else (a, b)
                i += 2
            p.append((x, y))
        if len(p) >= 2:
            out.append(p)
    return out


def vers_hex(x, y):
    """Point du SVG -> (colonne, rangée) continues (rangée 0 = sud), repère linéaire de l'Atlas : la case (q, r) couvre
    [q, q + 1) × [r, r + 1), son centre est à + 0,5 (comme les tracés de extension_rivieres.json)."""
    return x / (LARGEUR_SVG / W), H - y / (HAUTEUR_SVG / H)


def case(x, y):
    """La case (q, r) dont le centre est le plus proche du point du SVG."""
    ph = HAUTEUR_SVG / H
    q0 = int(np.floor(x / (LARGEUR_SVG / W)))
    best, choix = None, None
    for q in (q0 - 1, q0, q0 + 1):
        if not 0 <= q < W:
            continue
        d = DEC if q % 2 else 0.0
        cx = (q + 0.5) * LARGEUR_SVG / W
        r0 = int(round((HAUTEUR_SVG - y) / ph - 0.5 - d))
        for r in (r0 - 1, r0, r0 + 1):
            if not 0 <= r < H:
                continue
            cy = HAUTEUR_SVG - (r + 0.5 + d) * ph
            # hex à sommet plat : pas de colonne 1,5 rayon, pas de rangée √3 rayon ; on compare en rayons
            dd = ((x - cx) / (LARGEUR_SVG / W) * 1.5) ** 2 + ((y - cy) / ph * np.sqrt(3)) ** 2
            if best is None or dd < best:
                best, choix = dd, (q, r)
    return choix


def case_lineaire(x, y):
    """Convention des grilles de l'Atlas (session « Extension », 3.10.2026 : carte_papier_v2.pt, riv_ext) : linéaire,
    sans demi-rangée des colonnes impaires ; colonne = floor(x / 2), rangée = floor(905 − y / 2,3094)."""
    q = int(np.floor(x / (LARGEUR_SVG / W)))
    r = int(np.floor(H - y / (HAUTEUR_SVG / H)))
    return (q, r) if 0 <= q < W and 0 <= r < H else None


def cases(classes=CLASSES, pas=0.2, conv=None):
    """Grille (H, W) booléenne des cases traversées par les rivières (échantillonnées tous les `pas` px du SVG)."""
    conv = conv or case_lineaire
    g = np.zeros((H, W), bool)
    for p in chemins(classes):
        p = np.asarray(p, np.float64)
        seg = np.hypot(*np.diff(p, axis=0).T)
        L = np.concatenate([[0.0], np.cumsum(seg)])
        s = np.arange(0.0, L[-1] + 1e-9, pas)
        for x, y in zip(np.interp(s, L, p[:, 0]), np.interp(s, L, p[:, 1])):
            c = conv(x, y)
            if c:
                g[c[1], c[0]] = True
    return g


def traces(classes=CLASSES):
    """[[(colonne, rangée), ...]] continus, rangée 0 = sud (pour les lits du relief)."""
    return [[vers_hex(x, y) for x, y in p] for p in chemins(classes)]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
    from caime_layers import read_layer
    from cadre_expanded import DX, DY, SW, SH
    _, rv = read_layer(os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots\layer_rivers.hex_layer"))
    s = np.zeros((H, W), bool)
    s[DY:DY + SH, DX:DX + SW] = rv.reshape(SH, SW) > 0
    # accord : part des cases du SVG à 0 ou 1 case d'une rivière de la Saison
    from cotes_expanded import voisins
    pres = s | (voisins(s.astype(np.int8), 0) == 1).any(0)
    for nom, conv in (("linéaire (Atlas)", case_lineaire), ("centre d'hex", case)):
        wh1 = cases(("riviere",), conv=conv)
        print(f"contrôle du repère, {nom} : rivières de WH1 du SVG : {int(wh1.sum())} cases, dont "
              f"{100 * (wh1 & s).sum() / max(wh1.sum(), 1):.1f} % sur une rivière de la Saison et "
              f"{100 * (wh1 & pres).sum() / max(wh1.sum(), 1):.1f} % à une case au plus")
    neuves = cases()
    print(f"rivières neuves de l'Atlas : {len(chemins())} tracés, {int(neuves.sum())} cases")
