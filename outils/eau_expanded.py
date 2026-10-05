#!/usr/bin/env python3
"""
eau_expanded.py - les plans d'eau d'Expanded (3.10.2026) : les mers de l'Atlas n'avaient aucune surface d'eau.

Pourquoi : dans un projet Terry de campagne, la surface de la mer est faite de grands polygones d'eau posés comme objets
(`ECPolygonMesh`, matériau d'eau, hauteur 0) ; sans eux, pas d'eau (guide Terry, « Les conventions »). La Saison en a 3
(mer) et 24 (lacs), recopiés par `projet_expanded.py` ; les mers neuves de l'Atlas (Lyonesse, baies, Manaanspoort, golfes,
mer Tiléenne…) et l'éther du Bois Rêveur n'en avaient pas.

Ce que fait le module :
- les 3 polygones de MER de WH1 sont retirés (filtre `est_mer_wh1`, appelé par projet_expanded) et remplacés par des
  polygones qui couvrent TOUTES les mers de la grille d'Expanded, WH1 comprise : un seul réseau, sans recouvrement (deux
  plans d'eau superposés à la même hauteur scintillent) ; les 24 LACS de WH1 restent tels quels, et leurs cases sont ôtées ;
- débord d'un hex sous la terre (la terre, au-dessus de 0, cache l'eau : comme le polygone de WH1, qui couvre 98 % de sa
  mer et déborde de 16 % sous la côte) ;
- tracé lissé à 1/4 d'hex, découpé en pavés de PAVE hex (pivot de chaque polygone dans la carte : BOB écarte sinon
  l'objet, « Failed to find valid quadtree node ») ;
- repère vérifié sur les mers de la Saison : x = colonne · 266,53/400, z = rangée · 338,9/440 (rangée 0 au sud), le
  « y » des points local va vers le nord ;
- deux calques : `mer_expanded` (mers) et `ether_reves` (l'éther autour du Bois Rêveur, matériau d'éther à lui) ;
  matériaux et masques d'Expanded faits par `eau_materiau_expanded.py` (3.10.2026).
"""
import hashlib
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, SUD                                    # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names          # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
SOLS = os.path.join(ICI, r"couches-expanded\villes-sortie\layer_groundtypes.hex_layer")
REVES = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\reves_grilles.npz")
UX, UZ = 266.53 / 400, 338.9 / 440                  # unités du monde par colonne, par rangée
SUR = 4                                              # sur-échantillonnage du tracé (px par hex)
PAVE = 128                                           # hex
# (3.10.2026) matériaux d'eau d'Expanded (`eau_materiau_expanded.py` : masques à la taille du monde d'Expanded) ; ceux de
# la Saison, faits pour un monde de 266,53 × 338,9, auraient été étirés
MATERIAU_MER = "materials/environment/campaign_sea/saison_expanded_campaign_water_plane.xml.material"
MATERIAU_LAC = "materials/environment/campaign_sea/saison_expanded_campaign_lake_plane.xml.material"
MATERIAU_ETHER = "materials/environment/campaign_sea/saison_expanded_ether_plane.xml.material"
MATERIAUX_WH1 = {"materials/environment/campaign_sea/wh_dlc05_wood_elves_campaign_water_plane.xml.material": MATERIAU_MER,
                 "materials/environment/campaign_sea/wh_dlc05_wood_elves_campaign_lake_plane.xml.material": MATERIAU_LAC}


def materiaux(texte):
    """Texte d'un calque ou du .terry recopié de la Saison, ses matériaux d'eau remplacés par ceux d'Expanded."""
    for a, b in MATERIAUX_WH1.items():
        texte = texte.replace(a, b)
    return texte


def est_mer_wh1(entite):
    """Vrai pour une entité de polygone de MER de WH1 (pas un lac), à retirer du calque recopié."""
    return "<ECPolygonMesh" in entite and "campaign_water_plane" in entite


def lacs_wh1(calques, dx_u, dz_u):
    """Cases couvertes par les polygones de LAC de WH1 (déjà décalés de (dx_u, dz_u) dans Expanded)."""
    m = np.zeros((H, W), np.uint8)
    ent = re.compile(r'<entity id="[^"]*">(.*?)</entity>', re.S)
    for t in calques:
        for corps in ent.findall(t):
            if "<ECPolygonMesh" not in corps or "lake_plane" not in corps:
                continue
            x0, _, z0 = map(float, re.search(r'<ECTransform position="([^"]*)"', corps).group(1).split())
            pts = np.array([(float(a), float(b)) for a, b in re.findall(r'<point x="([-0-9.eE]+)" y="([-0-9.eE]+)"/>',
                                                                        corps)])
            q = (x0 + pts[:, 0]) / UX
            r = (z0 + pts[:, 1]) / UZ
            cv2.fillPoly(m, [np.round(np.stack([q, r], 1)).astype(np.int32)], 1)
    return cv2.dilate(m, np.ones((3, 3), np.uint8)).astype(bool)


def masques():
    """(mer, éther) en cases de la grille (rangée 0 = sud)."""
    le, _, _ = caime_names(CAIME, os.path.join(ICI, r"caime\saison_expanded_map\map.hex"))
    nt = len(le.get("Land ground types", []))
    gt = read_layer(SOLS)[1].reshape(H, W)
    mer = gt >= nt
    rv = np.load(REVES)
    terre_r = np.zeros((H, W), bool)
    terre_r[:rv["terre"].shape[0], :W] = rv["terre"]
    ether = np.zeros((H, W), bool)
    ether[:SUD] = True
    ether &= ~terre_r
    return mer & ~ether, mer & ether


def polygones(masque, terre):
    """Polygones (listes de points du monde x, z) couvrant `masque`, débordant d'un hex sur `terre`, par pavés."""
    # (3.10.2026, première version : chaque pavé tracé à part s'arrêtait à 1/8 d'hex de son bord, d'où une fente sans eau
    # d'un quart d'hex le long des coupures) : tracé sur toute la carte, puis intersection exacte avec les pavés
    from shapely.geometry import Polygon, box
    from shapely.validation import make_valid
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    plein = (masque | (cv2.dilate(masque.astype(np.uint8), k).astype(bool) & terre)).astype(np.uint8)
    fin = cv2.resize(plein * 255, (W * SUR, H * SUR), interpolation=cv2.INTER_LINEAR)
    fin = (cv2.GaussianBlur(fin, (0, 0), SUR * 0.6) > 127).astype(np.uint8)
    contours, _ = cv2.findContours(fin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in contours:
        if cv2.contourArea(c) < SUR * SUR * 2:
            continue
        c = cv2.approxPolyDP(c, SUR * 0.25, True)[:, 0, :].astype(np.float64)
        if len(c) < 3:
            continue
        poly = make_valid(Polygon((c + 0.5) / SUR))                       # en hex : (colonne, rangée)
        x0, y0, x1, y1 = poly.bounds
        for r0 in range(int(y0) // PAVE * PAVE, int(y1) + 1, PAVE):
            for q0 in range(int(x0) // PAVE * PAVE, int(x1) + 1, PAVE):
                morceau = poly.intersection(box(q0, r0, q0 + PAVE, r0 + PAVE))
                parts = getattr(morceau, "geoms", [morceau])
                for g in parts:
                    if g.geom_type != "Polygon" or g.area < 1.0:
                        continue
                    xy = np.array(g.exterior.coords)[:-1]
                    out.append(np.stack([xy[:, 0] * UX, xy[:, 1] * UZ], 1))
    return out


def ident(nom, i):
    return "1" + hashlib.sha1(f"saison_expanded/{nom}/{i}".encode()).hexdigest()[:14]


def calque(nom, polys, materiau=MATERIAU_MER):
    """Texte d'un calque `.layer` de polygones d'eau, au format de mer_wh1."""
    lignes = ['<?xml version="1.0" encoding="UTF-8"?>', f"<!-- {nom} -->", '<layer version="41">', "\t<entities>"]
    for i, p in enumerate(polys):
        cx, cz = p.mean(0)
        lignes += [f'\t\t<entity id="{ident(nom, i)}">',
                   f'\t\t\t<ECPolygonMesh material="{materiau}" affects_mesh_optimization="false"/>'
                   '<ECVisibilitySettingsCampaign visible_in_tactical_view="True" visible_in_tactical_view_only="False"/>',
                   '\t\t\t<ECCampaignProperties visible_in_shroud="True" no_culling="true" culture_mask=""/>',
                   f'\t\t\t<ECTransform position="{cx:.5f} 0.00000 {cz:.5f}" rotation="0. 0. 0." scale="1. 1. 1." '
                   'pivot="0 0 0"/>',
                   "\t\t\t<ECPolyline>", '\t\t\t\t<polyline closed="true">']
        lignes += [f'\t\t\t\t\t<point x="{x - cx:.5f}" y="{z - cz:.5f}"/>' for x, z in p]
        lignes += ["\t\t\t\t</polyline>", "\t\t\t</ECPolyline>", "\t\t</entity>"]
    lignes += ["\t</entities>", "\t<associations>", "\t\t<Logical/>", "\t\t<Transform/>", "\t</associations>",
               "</layer>", ""]
    return "\n".join(lignes)


def poser(dst, cle, calques_wh1, dx_u, dz_u, ether_plus=None):
    """Écrit les calques `mer_expanded` et `ether_reves` dans le projet `dst` et les déclare dans son `.terry`.
    `ether_plus` : cases de terre de la grille rendues en éther par le terrain (la déchirure du voile, projet_expanded)."""
    mer, ether = masques()
    if ether_plus is not None:
        ether = ether | ether_plus
        mer &= ~ether_plus
    lacs = lacs_wh1(calques_wh1, dx_u, dz_u)
    mer &= ~lacs
    terre = ~(mer | ether)
    terry_p = os.path.join(dst, f"{cle}.terry")
    t = open(terry_p, encoding="utf-8").read()
    bilan = []
    for nom, m, mat in (("mer_expanded", mer, MATERIAU_MER), ("ether_reves", ether, MATERIAU_ETHER)):
        polys = polygones(m, terre & ~lacs)
        i = ident(nom, "calque")
        with open(os.path.join(dst, f"{cle}.{i}.layer"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(calque(nom, polys, mat))
        if f'name="{nom}"' not in t:
            t = t.replace("    </data>\n  </pc>", f'      <entity id="{i}" name="{nom}">\n        <ECFileLayer export="true" '
                          f'bmd_export_type=""/>\n      </entity>\n    </data>\n  </pc>', 1)
        bilan.append(f"{nom} : {len(polys)} polygones, {int(m.sum())} cases d'eau")
    if "mer_expanded" not in t:
        raise SystemExit("eau_expanded : impossible de déclarer les calques dans le .terry (fin de QTU::Scene introuvable)")
    open(terry_p, "w", encoding="utf-8", newline="\n").write(t)
    print("  eau : " + " ; ".join(bilan) + f" ; cases des lacs de WH1 laissées à leurs polygones : {int(lacs.sum())}")
