#!/usr/bin/env python3
"""
mer_tuiles.py - OÙ EST LA MER, selon la carte des tuiles (5.10.2026) : une seule source pour les outils du chantier.

Pourquoi (Charles, 5.10.2026 : « encore des hachures, des escaliers par-ci par-là ») : CA (Empires Immortels, relief du
kit ombré au pixel, `scratchpad\\relief_ombre_ca.py`) garde un relief CONTINU au trait de côte : la terre se prolonge sous
les tuiles de mer (relief médian 0,64 près des falaises), les chenaux ne sont pas creusés dans le relief ; seuls les
tuiles (côte en hex) et le fond marin disent la mer. Notre convention de WH1 (relief à 0,02 sur la mer) dessinait au
contraire une marche nette au bord de chaque tuile de mer, que l'éclairage du jeu montre en escalier. Le relief n'étant
plus à 0,02 près des côtes, les outils qui en déduisaient la mer (eau_materiau, rivieres_atlas_eau, arbres_expanded,
decors_expanded, controle_anomalies) la lisent ici : tuiles `sea` de `tile_map.png` du projet (export CAIME) et lacs
fermés de la grille (`tuiles_expanded.lacs_eau`), à la résolution demandée.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded"
TUILES = os.path.join(ICI, r"terry\saison_expanded_map\tile_map.png")
MER = (83, 141, 213)
_CACHE = {}


def mer_px(forme, tuiles=None):
    """Booléens (forme du raster, nord en haut) : tuile de mer ou lac fermé, au plus proche."""
    cle = (tuple(forme), id(tuiles) if tuiles is not None else os.path.getmtime(TUILES))
    if cle in _CACHE:
        return _CACHE[cle]
    if tuiles is None:
        from PIL import Image
        tuiles = np.asarray(Image.open(TUILES).convert("RGBA"))
    import tuiles_expanded
    m = (tuiles[..., :3] == MER).all(-1) | tuiles_expanded.lacs_eau(tuiles.shape)
    out = cv2.resize(m.astype(np.uint8), (forme[1], forme[0]), interpolation=cv2.INTER_NEAREST) > 0
    _CACHE.clear()
    _CACHE[cle] = out
    return out
