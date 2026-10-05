#!/usr/bin/env python3
"""
cadre_expanded.py - le cadre de la grille d'Expanded, en un seul endroit, pour tous les outils du chantier.

Pourquoi (3.10.2026, Charles : « repousser le miroir… côté jeu, CAIME, Terry ») : les Voûtes de l'Atlas descendent de
80 rangées sous la carte de Warhammer I (geo_extension.VOUTES_SUD) ; la grille passe de 560 × 825 à 560 × 905, la carte de
WH1 de (x + 120, y + 250) à (x + 120, y + 330), et le Bois Rêveur garde ses 250 rangées du bas. Jusque-là, chaque outil
portait ses constantes en dur (825, 250, 507, 1142…) : elles se lisent ici, et `carte_config` (profil « expanded ») dit
la même chose (contrôle à l'import).

Repères (ligne 0 = sud, comme CAIME et l'Atlas) :
- grille : W × H hex ; colonne = x + DX, rangée = y + DY, (x, y) en hex de l'Atlas (y = 0 : bas de la carte de WH1) ;
- l'Atlas (grilles de geo_extension / regions_extension, NH_ATLAS × W) : sa ligne 0 est y = Y0_ATLAS_Y, rangée
  RANG_ATLAS de la grille ;
- le Bois Rêveur : rangées 0 à SUD − 1 de la grille (grilles reves_grilles.npz : ligne 0 au sud), le voile en haut de la
  bande (VOILE rangées) ; reflet d'une rangée R d'Athel Loren : R' = REFLET − R ;
- rasters de Terry (nord en haut, f px par hex) : rangée de pixel p' <- REFLET_PX · f − 1 − p, avec
  REFLET_PX = 2 H − 1 − REFLET ; la carte de WH1 sous DY_HAUT hex de bord nord.
"""
import os
import sys

import numpy as np

W, H = 560, 905
SW, SH = 400, 440                      # la carte de WH1
DX, DY = 120, 330                      # sa place dans la grille
DY_HAUT = H - DY - SH                  # rangées au-dessus (nord) de la carte de WH1 : 135, comme avant
SUD = 250                              # rangées du Bois Rêveur, en bas de la grille
VOILE = 26                             # rangées du voile, en haut de la bande du Bois Rêveur
VOUTES = DY - SUD                      # rangées des Voûtes, entre le voile et la carte de WH1 : 80
Y0_ATLAS_Y = -VOUTES                   # y de la ligne 0 des grilles de l'Atlas
RANG_ATLAS = SUD                       # rangée de la grille de la ligne 0 de l'Atlas
NH_ATLAS = H - SUD                     # rangées des grilles de l'Atlas : 655
# reflet d'Athel Loren (bois_des_reves : (x, y) -> (x, RANG0 − VOILE + Y0 − y), RANG0 = 33) : en rangées de la grille
REFLET = (33 - VOILE + Y0_ATLAS_Y) + 2 * DY      # 587 (507 avant les Voûtes)
REFLET_PX = 2 * H - 1 - REFLET                   # 1222 (1142 avant)


def grille(x, y):
    """Hex de l'Atlas (x, y) -> (colonne, rangée) de la grille."""
    return x + DX, y + DY


# monde (unités des listes d'arbres et des calques : x vers l'est, z vers le nord) : W·UX × H·UZ, comme la Saison
# (266,53 × 338,9 pour 400 × 440 hex) ; en-têtes de BOB : z max = H·UZ + 0,88 dans les deux cartes
UX, UZ = 266.53 / 400, 338.9 / 440
X_MONDE, Z_MONDE = W * UX, H * UZ                # 373,14 × 697,06


def px_de(x, z, forme):
    """Points du monde (x, z) -> (colonne, ligne) de pixel, flottantes, d'un raster de Terry de taille `forme` (lignes,
    colonnes ; nord en haut). (4.10.2026 : Terry fait 8 H + 4 lignes, étirées sur Z_MONDE ; la règle de la Saison,
    z · √3/2 · 12,006 px, vaut 10,398 px par unité, juste pour 3 524 lignes / 338,9 u, mais pas pour 7 244 / 697,06 u
    (10,392) : 5 px d'écart au nord d'Expanded, assez pour poser un arbre dans l'eau.)"""
    return (np.asarray(x) * (forme[1] / X_MONDE) - 0.5,
            (Z_MONDE - np.asarray(z)) * (forme[0] / Z_MONDE) - 0.5)


def ipx_de(x, z, forme):
    """Comme px_de, en indices entiers bornés au raster."""
    px, py = px_de(x, z, forme)
    return (np.clip(np.rint(px).astype(int), 0, forme[1] - 1), np.clip(np.rint(py).astype(int), 0, forme[0] - 1))


def _controle():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "02-scripts"))
    os.environ.setdefault("SAISON_CARTE", "expanded")
    if os.environ["SAISON_CARTE"] != "expanded":
        return
    import carte_config as cc
    assert (cc.HEX_L, cc.HEX_H) == (W, H) and tuple(cc.DECALAGE_HEX) == (DX, DY), \
        f"carte_config (expanded) {cc.HEX_L}×{cc.HEX_H} {cc.DECALAGE_HEX} ≠ cadre_expanded {W}×{H} {(DX, DY)}"


_controle()

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"grille {W} × {H} ; WH1 en (x + {DX}, y + {DY}) ; Voûtes {VOUTES} rangées ; Bois Rêveur 0-{SUD - 1} "
          f"(voile {SUD - VOILE}-{SUD - 1}) ; Atlas {NH_ATLAS} rangées dès la rangée {RANG_ATLAS} (y = {Y0_ATLAS_Y}) ; "
          f"reflet R' = {REFLET} − R ; rasters p' = {REFLET_PX}·f − 1 − p")
