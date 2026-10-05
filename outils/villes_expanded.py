#!/usr/bin/env python3
"""
villes_expanded.py - emplacements de colonie (TownSlots, TownSprawl) et passage (Impassable) de la grille d'Expanded.

Pourquoi (25.09.2026, 19 h 45 ; Charles : « continue à travailler sur Expanded ») : les régions sont posées
(`regions_expanded.py`) ; chaque région terrestre neuve a besoin de sa ville, et l'extension doit devenir franchissable
selon l'Atlas (session « Extension », 18 h : franchissable = couche de WH1 dans le cadre + régions neuves + les cinq
ouvertures des cols ; terre sauvage infranchissable).

Étapes (rien dans le kit ; la carte vit dans `04-projets\\saison-expanded\\caime\\`) :
1. villes de la Saison recopiées dans le cadre, telles quelles (« aucune ville de WH1 ne bouge », Atlas) ; contrôle : la
   ville de chaque région de WH1 reste dans sa région après les découpes ;
2. passage : cadre = couche de WH1 ; hors cadre et découpes : les cases des régions neuves (terre) et des mers déclarées
   deviennent franchissables ; les ouvertures (`extension_routes.json`, `ouvertures[].points`, tracé d'un hex de large)
   aussi ; le voile reste infranchissable ;
3. une graine de ville par région terrestre neuve, au `hex_ville_expanded` de la déclaration (ou à la case de terre de la
   région la plus proche), plus 3 hex de port sur la mer voisine pour une région `port` ;
4. `02-scripts\\grow_town_slots.py` fait pousser chaque ville à 19 hex (16 pour un port) et l'étalement, d'abord à blanc ;
   puis les colonies de WH1 sont remises à l'identique de la Saison (`villes_wh1_a_l_identique`, 4.10.2026) ;
5. import dans le map.hex de TownSlots, TownSprawl et Impassable seulement (erreur de `grow_town_slots` : il écrit tout).

Usage :
    python villes_expanded.py [--sans-import]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, encode_flat, caime_names, flat_names    # noqa: E402
from grow_town_slots import neighbours, hex_distance, components              # noqa: E402
from collections import deque                                                 # noqa: E402

CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
COUCHES_SAISON = os.path.join(ATELIER, r"04-projets\saison-des-revelations\couches-slots")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE_EXP = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
COUCHES = os.path.join(ICI, "couches-expanded")
TRAVAIL = os.path.join(COUCHES, "villes-travail")
SORTIE = os.path.join(COUCHES, "villes-sortie")
ATLAS = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
GROW = os.path.join(ATELIER, r"02-scripts\grow_town_slots.py")
# (3.10.2026 : 560 × 905, WH1 en (x + 120, y + 330) ; reflet R' = 587 − R : cadre_expanded.py)
from cadre_expanded import W, H, DX, DY, SW, SH, SUD, REFLET, RANG_ATLAS     # noqa: E402
MAIN, PORT = 0, 1
# Ouvertures de jeu à nous, en plus de celles de l'Atlas (`extension_routes.json`), même repère (x, y de l'Atlas).
# (3.10.2026, Charles : « je voulais que les montagnes du sud soient connectées aux montagnes de l'est, avec les
# passages… une continuation ») : la vallée de Grimhold (Grises du sud) s'arrêtait à y ≈ +31, celle du Repaire des
# Brise-Nuques (Voûtes) commence à y ≈ +26, séparées par 8 cases de montagne fermée : un col les relie, et la route de
# montagne continue des Grises dans les Voûtes. Sans nom dans le jeu (aucune source n'en nomme un ici).
OUVERTURES_JEU = [
    {"nom": "Col des Grises aux Voûtes (Grimhold - Brise-Nuques)", "points": [[370, 31], [376, 30], [382, 28], [389, 26]]},
]
# Îles de l'Atlas gardées en terre malgré le lissage des côtes (cotes_expanded efface les langues d'un hex ; une île de
# terre sauvage, sans région à elle, n'y est pas protégée). (3.10.2026, session « Expanded map avec vaults et détails
# sud ») l'île de Landri, 12 cases, tête de pont possible de l'ost d'Egil Styrbjorn (05-journal\2026-10-03-factions-nord\
# pistes-pour-le-jeu.md, piste B). Cadre en INDICES des grilles de l'Atlas (`extension_regions.npz` : colonne = x + 120 =
# colonne de la grille, ligne = y + 80, ligne 0 au sud) ; rangée de la grille = RANG_ATLAS + ligne. Landri, Atlas
# (-67..-64, 483..488) -> indices (53..56, 563..568) -> grille (53..56, 813..818).
ILES_GARDEES = {"Île de Landri": (53, 56, 563, 568)}
ATLAS_REGIONS = r"C:\TotalWar-CampaignMap\05-journal\2026-09-23-extension-carte\travail\extension_regions.npz"


def villes_wh1_a_l_identique(slots, sprawl, reg, noms):
    """Remet dans le cadre les cases d'emplacement et d'étalement de la Saison, à l'identique, pour les colonies de WH1.
    Rend le nombre de cases changées. (4.10.2026, plantage au chargement d'Expanded, +0x2613117, colonie
    wh_dlc05_bordeleaux_bordeleaux, liste vide, session « Construction ») `grow_town_slots` avait fait repousser à 19 cases
    les trois ports de WH1 (Bordeleaux, Brionne, Mousillon), faits de 16 cases principales + 3 de port dans la Saison, qui
    charge : 22 cases au lieu de 19. Cases visées : celles où la Saison a un emplacement, et celles où la croissance en a
    mis un dans une région de WH1 (wh_dlc05_*, terre ou mer)."""
    s_slots = lire(COUCHES_SAISON, "layer_town_slots.hex_layer").reshape(SH, SW)
    s_sprawl = lire(COUCHES_SAISON, "layer_town_sprawl.hex_layer").reshape(SH, SW)
    de_wh1 = np.array([n.startswith("wh_dlc05_") for n in noms] + [False])
    c_slots, c_sprawl = slots[DY:DY + SH, DX:DX + SW], sprawl[DY:DY + SH, DX:DX + SW]
    c_reg = reg[DY:DY + SH, DX:DX + SW]
    vise = (s_slots >= 0) | ((c_slots >= 0) & de_wh1[np.where(c_reg < 0, len(noms), c_reg)])
    # (4.10.2026, Poste de la Pierre Noire : une case d'étendue sans emplacement en trop, sous la ville) l'étendue aussi
    vise |= (c_sprawl != s_sprawl) & ((s_sprawl > 0) | de_wh1[np.where(c_reg < 0, len(noms), c_reg)])
    change = vise & ((c_slots != s_slots) | (c_sprawl != s_sprawl))
    c_slots[vise] = s_slots[vise]
    c_sprawl[vise] = s_sprawl[vise]
    return int(change.sum())


def iles_gardees(sol, n_sols_terre):
    """Cases de la grille des îles d'ILES_GARDEES (terre de l'Atlas dans leur cadre), à protéger du lissage."""
    terre = np.load(ATLAS_REGIONS)["terre"] > 0
    m = np.zeros((H, W), bool)
    for nom, (c0, c1, l0, l1) in ILES_GARDEES.items():
        bloc = terre[l0:l1 + 1, c0:c1 + 1]
        m[RANG_ATLAS + l0:RANG_ATLAS + l1 + 1, c0:c1 + 1] |= bloc
        n_terre = int((sol[RANG_ATLAS + l0:RANG_ATLAS + l1 + 1, c0:c1 + 1][bloc] < n_sols_terre).sum())
        print(f"  {nom} : {int(bloc.sum())} cases gardées en terre ({n_terre} de terre avant lissage)")
    return m


def lire(dossier, fichier):
    return read_layer(os.path.join(dossier, fichier))[1]


def trace(points):
    """Hex traversés par une ligne brisée (coordonnées de l'Atlas -> grille : x + DX, y + DY)."""
    out = set()
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for t in np.linspace(0, 1, n):
            out.add((int(round(x0 + (x1 - x0) * t)) + DX, int(round(y0 + (y1 - y0) * t)) + DY))
    return out


def anneau(q, r, rayon):
    """Cases à distance hex exactement `rayon` de (q, r), et le disque jusqu'à `rayon` (parcours en largeur)."""
    vus, front = {(q, r)}, [(q, r)]
    couches = [[(q, r)]]
    for _ in range(rayon):
        nouv = []
        for cq, cr in front:
            for nq, nr in neighbours(cq, cr, W, H):
                if (nq, nr) not in vus:
                    vus.add((nq, nr))
                    nouv.append((nq, nr))
        couches.append(nouv)
        front = nouv
    return couches


def defauts_emplacement(q, r, rid, reg, terre, imp, riv):
    """Nombre de défauts d'une ville de 19 cases centrée en (q, r), au sens du validateur de CAIME (étalement) :
    disque hors région, fermé, en mer ou sur une rivière ; plus d'une zone à risque au contact ; risque à 2 cases sans
    contact. (Approché : zones à risque comptées dans les deux anneaux autour du disque.)"""
    c = anneau(q, r, 4)
    disque = c[0] + c[1] + c[2]
    d = 0
    for cq, cr in disque:
        if reg[cr, cq] != rid or not terre[cr, cq] or imp[cr, cq] != 1 or riv[cr, cq]:
            d += 10
    def risque(cq, cr):
        if not terre[cr, cq] or imp[cr, cq] != 1 or riv[cr, cq]:
            return True
        return any(not terre[nr, nq] for nq, nr in neighbours(cq, cr, W, H))
    r1 = {x for x in c[3] if risque(*x)}
    r2 = {x for x in c[4] if risque(*x)}
    zone = r1 | r2
    comp, vus = 0, set()
    for x in r1:
        if x in vus:
            continue
        comp += 1
        pile = [x]
        vus.add(x)
        while pile:
            a = pile.pop()
            for nb in neighbours(a[0], a[1], W, H):
                if nb in zone and nb not in vus:
                    vus.add(nb)
                    pile.append(nb)
    d += max(0, comp - 1) * 3 + len(r2 - vus)
    return d


def meilleur_emplacement(q0, r0, rid, reg, terre, imp, riv, places, portee=3):
    """(3.10.2026, Oisillon à cheval sur une rivière de l'Atlas : Error d'étalement) : la case à `portee` hex au plus de
    la position voulue qui donne le moins de défauts, la plus proche à égalité. Rend (r, q)."""
    meilleur = (defauts_emplacement(q0, r0, rid, reg, terre, imp, riv), 0, q0, r0)
    if meilleur[0] == 0:
        return r0, q0
    for k, couche in enumerate(anneau(q0, r0, portee)[1:], start=1):
        for q, r in couche:
            if reg[r, q] != rid:
                continue
            s = (defauts_emplacement(q, r, rid, reg, terre, imp, riv), k, q, r)
            if s < meilleur:
                meilleur = s
    if (meilleur[2], meilleur[3]) != (q0, r0):
        places.append(f"{(q0, r0)}->{(meilleur[2], meilleur[3])}")
    return meilleur[3], meilleur[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-import", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.load(open(os.path.join(ATLAS, "expanded_declaration.json"), encoding="utf-8"))
    # (4.10.2026, 17 h, second préavis des Voûtes : 13 routes refaites autour de Couronne et L'Anguille, Helmgart-Ubersreik,
    # selon les rivières du lore ; « n'y touche pas avant mon feu vert ») : copie figée d'avant la retouche, comme le SVG
    # des rivières (rivieres_svg_grille.SVG) ; revenir au fichier vivant au feu vert
    routes = json.load(open(os.path.join(ATELIER, r"05-journal\2026-10-04-fleuves-navigables-atlas\avant-20261004",
                                         "extension_routes.json"), encoding="utf-8"))
    rv = np.load(os.path.join(ATLAS, "reves_grilles.npz"))
    listes, w, h = caime_names(CAIME, CARTE_EXP)
    assert (w, h) == (W, H)
    noms = flat_names(listes, "Regions")
    idx = {n: i for i, n in enumerate(noms)}
    n_sols_terre = len(listes.get("Land ground types", []))
    reg = lire(COUCHES, "layer_regions.hex_layer").reshape(H, W)
    sol = lire(COUCHES, "layer_groundtypes.hex_layer").reshape(H, W)
    climat = lire(COUCHES, "layer_climates.hex_layer").reshape(H, W)
    # 0. la bande du sud (Bois Rêveur) : sols et climats REFLÉTÉS d'Athel Loren (rangée R' = REFLET − R, comme le relief
    # de projet_expanded.py) sur les cases du reflet ; éther = mer ; voile = montagne (infranchissable)
    rterre = np.zeros((H, W), bool)
    rterre[0:rv["terre"].shape[0], :W] = rv["terre"]
    rvoile = np.zeros((H, W), bool)
    rvoile[0:rv["voile"].shape[0], :W] = rv["voile"]
    sols_noms = flat_names(listes, "GroundTypes")
    mer_eth = sols_noms.index("sea_ocean") if "sea_ocean" in sols_noms else n_sols_terre
    montagne = sols_noms.index("mountain")
    miroir = lambda a: a[REFLET - np.arange(H)[:, None].clip(0, REFLET), np.arange(W)[None, :]]      # noqa: E731
    sud = np.zeros((H, W), bool)
    sud[0:SUD] = True
    sol = np.where(sud & rterre & ~rvoile, miroir(sol), sol)
    climat = np.where(sud & rterre & ~rvoile, miroir(climat), climat)
    sol = np.where(sud & ~rterre, mer_eth, sol)
    sol = np.where(rvoile, montagne, sol)
    # 0 bis (3.10.2026). LE TRAIT DE CÔTE (`cotes_expanded.py`) : langues de terre d'un hex, cases de mer enfermées, mer
    # dans des régions de terre, lissés avant la pose des villes, pour qu'elles poussent sur la côte définitive. Jamais
    # touchées : les cases où la région de WH1 est restée la sienne (WH1 à 100 %), et le voile.
    import cotes_expanded                                                       # noqa: E402
    s_noms0 = flat_names(caime_names(CAIME, os.path.join(
        r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit",
        r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex"))[0], "Regions")
    s_reg0 = lire(COUCHES_SAISON, "layer_regions.hex_layer").reshape(SH, SW)
    vers_exp = np.array([idx.get(n, -1) for n in s_noms0] + [-1])
    garde = np.zeros((H, W), bool)
    garde[DY:DY + SH, DX:DX + SW] = (s_reg0 >= 0) & ~np.isin(
        s_reg0, [i for i, n in enumerate(s_noms0) if "wilderness" in n]) & (reg[DY:DY + SH, DX:DX + SW] == vers_exp[s_reg0])
    rivieres = lire(COUCHES, "layer_rivers.hex_layer").reshape(H, W).copy()
    # rivières du Bois Rêveur reflétées d'Athel Loren ICI, avant la pose des villes (3.10.2026 ; jusque-là dans
    # retouches_expanded, après : le palais d'Argwylon reflété ne pouvait pas s'étendre jusqu'à sa rivière, Error de CAIME)
    n_riv = int((rivieres[0:SUD] != 0).sum())
    rivieres = np.where(sud & rterre & ~rvoile, miroir(rivieres), rivieres)
    print(f"  rivières du Bois Rêveur : {int((rivieres[0:SUD] != 0).sum()) - n_riv} hex reflétés")
    plages = lire(COUCHES, "layer_beaches.hex_layer").reshape(H, W).copy()
    regions_mer = range(len(listes.get("Land regions", [])), len(noms))
    _, videes = cotes_expanded.lisser(reg, sol, climat, rivieres, plages, n_sols_terre, regions_mer,
                                      idx["wh_dlc05_wilderness_land"], idx["wh_dlc05_wilderness_sea"],
                                      garde | rvoile | iles_gardees(sol, n_sols_terre))
    assert not [noms[i] for i in videes if "wilderness" not in noms[i]], [noms[i] for i in videes]
    for nom, v in (("Rivers", rivieres), ("Beaches", plages), ("Regions", reg)):
        with open(os.path.join(COUCHES, f"layer_{nom.lower()}.hex_layer"), "wb") as fh:
            fh.write(encode_flat(nom, v.reshape(-1)))
    with open(os.path.join(COUCHES, "layer_groundtypes.hex_layer"), "wb") as fh:
        fh.write(encode_flat("GroundTypes", sol.reshape(-1)))
    with open(os.path.join(COUCHES, "layer_climates.hex_layer"), "wb") as fh:
        fh.write(encode_flat("Climates", climat.reshape(-1)))
    terre = (sol >= 0) & (sol < n_sols_terre)
    print(f"  Bois Rêveur : {int((sud & terre).sum())} hex de terre reflétés")
    cadre = np.zeros((H, W), bool)
    cadre[DY:DY + SH, DX:DX + SW] = True

    # 1. villes de la Saison dans le cadre
    slots = np.full((H, W), -1, np.int64)
    sprawl = np.zeros((H, W), np.int64)
    slots[DY:DY + SH, DX:DX + SW] = lire(COUCHES_SAISON, "layer_town_slots.hex_layer").reshape(SH, SW)
    sprawl[DY:DY + SH, DX:DX + SW] = lire(COUCHES_SAISON, "layer_town_sprawl.hex_layer").reshape(SH, SW)
    s_reg = lire(COUCHES_SAISON, "layer_regions.hex_layer").reshape(SH, SW)
    s_noms = flat_names(caime_names(CAIME, os.path.join(
        r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\assembly_kit",
        r"raw_data\EmpireDesignData\campaign_maps\wh_dlc05_wood_elves_map_1\map.hex"))[0], "Regions")
    deplacees = []
    for i in np.unique(s_reg[lire(COUCHES_SAISON, "layer_town_slots.hex_layer").reshape(SH, SW) == MAIN]):
        m = np.zeros((H, W), bool)
        m[DY:DY + SH, DX:DX + SW] = (s_reg == i)
        m &= slots == MAIN
        dans = set(noms[k] for k in np.unique(reg[m]))
        if len(dans) != 1:
            deplacees.append((s_noms[i], sorted(dans)))
    print(f"  villes de WH1 recopiées ; villes coupées ou passées dans une autre région : {deplacees or 'aucune'}")

    # 2. passage
    imp = np.zeros((H, W), np.int64)
    imp[DY:DY + SH, DX:DX + SW] = lire(COUCHES_SAISON, "layer_impassable.hex_layer").reshape(SH, SW)
    terrestres = [e for e in d["regions"] if not e["is_sea"]]
    mers = [e for e in d["regions"] if e["is_sea"]]
    # (3.10.2026) les Voûtes : la haute montagne de leurs régions reste infranchissable, hors des vallées creusées, comme
    # sur la carte de l'Atlas (carte_papier_v2.INFRANCHISSABLE : altitude de l'Atlas ≥ geo_extension.SEUIL_INFRANCHISSABLE)
    sys.path.insert(0, ATLAS)
    import geo_extension as GE                                               # noqa: E402
    r_at = np.load(os.path.join(ATLAS, "extension_regions.npz"))
    haute = np.zeros((H, W), bool)
    haute[RANG_ATLAS:RANG_ATLAS + r_at["alt"].shape[0], :W] = r_at["alt"] >= GE.SEUIL_INFRANCHISSABLE
    for e in terrestres:
        m = (reg == idx[e["cle_jeu"]]) & terre
        if e.get("zone") == "voutes":
            m &= ~haute
        imp[m] = 1
    for e in mers:
        imp[(reg == idx[e["cle_jeu"]]) & ~terre] = 1
    # (3.10.2026, relevé de la session « Recherche or et rivières navigables ») les mers de WH1 (wh_dlc05_sea_*) gardaient
    # leur lisière NON JOUABLE fermée (Impassable = 0 dans la Saison, bord de l'ancienne carte) : 434 cases du Golfe du
    # Bidouze, colonnes 123-127, entre le golfe et les mers de l'Atlas ; CAIME la traite en mur pour les navires (aucun
    # validateur ne le dit) et les ports de Bordeleaux, Brionne et Mousillon restaient sur une mer fermée. Charles : « une
    # seule vraie carte, sans coupure au raccord ». Toute case de mer d'une région de mer de WH1 s'ouvre (la partie jouable
    # l'est déjà : rien n'y change) ; la terre de la lisière reste celle de l'Atlas. Lisière = hors du rectangle des cases
    # franchissables de la Saison (les lacs fermés de WH1, dans ce rectangle, restent comme dans WH1)
    s_imp = lire(COUCHES_SAISON, "layer_impassable.hex_layer").reshape(SH, SW) == 1
    rs, cs = np.nonzero(s_imp)
    lisiere = np.zeros((H, W), bool)
    lisiere[DY:DY + SH, DX:DX + SW] = True
    lisiere[DY + rs.min():DY + rs.max() + 1, DX + cs.min():DX + cs.max() + 1] = False
    mers_wh1 = np.isin(reg, [i for n, i in idx.items() if n.startswith("wh_dlc05_sea_")]) & ~terre & lisiere
    print(f"  lisière des mers de WH1 ouverte : {int((mers_wh1 & (imp != 1)).sum())} cases")
    imp[mers_wh1] = 1
    # (3.10.2026) enclaves de terre sauvage réparties par regions_expanded (la « province sans nom » du nord, le massif
    # intérieur des Grises de l'est…) : elles ont une région, mais leur haute montagne (altitude de l'Atlas au-dessus du
    # seuil, comme dans les Voûtes) reste fermée ; les terres basses s'ouvrent, comme l'Atlas les dessine
    p_enc = os.path.join(COUCHES, "enclaves.npy")
    if os.path.exists(p_enc):
        enclaves = np.load(p_enc)
        hautes_cases = np.zeros((H, W), bool)
        hautes_cases[RANG_ATLAS:RANG_ATLAS + r_at["alt"].shape[0], :W] = r_at["alt"] >= GE.SEUIL_INFRANCHISSABLE
        sols_m = sol == montagne
        fermer = enclaves & (hautes_cases | sols_m)
        imp[fermer] = 0
        imp[enclaves & ~fermer & terre] = 1
        print(f"  enclaves : {int(enclaves.sum())} cases, dont {int(fermer.sum())} de haute montagne restées fermées")
    ouv = set()
    for o in routes["ouvertures"] + OUVERTURES_JEU:
        ouv |= trace(o["points"])
    for q, r in ouv:
        if 0 <= q < W and 0 <= r < H:
            imp[r, q] = 1
    voile = np.zeros((H, W), bool)
    voile[0:rv["voile"].shape[0], :W] = rv["voile"]
    imp[voile] = 0
    # (3.10.2026, connexite_expanded : le Camp des Orques de fer hors de la composante principale) une ouverture de l'Atlas
    # tracée dans l'ancien cadre peut finir en cul-de-sac : la Brèche des Orques de fer s'arrête à 4 cases de la Gasconnie,
    # sur la bordure infranchissable de WH1. Chaque ouverture qui n'atteint pas la composante principale est prolongée,
    # par la terre et hors du voile, jusqu'à la case ouverte la plus proche de cette composante (le sens que lui donne
    # l'Atlas), plutôt qu'un passage au plus court ailleurs.
    ids, _ = components(imp == 1, W, H)
    principale = int(np.argmax(np.bincount(ids[ids >= 0])))
    prolongees = []
    for o in routes["ouvertures"] + OUVERTURES_JEU:
        cases = [(r, q) for q, r in trace(o["points"]) if 0 <= q < W and 0 <= r < H]
        if any(ids[r, q] == principale for r, q in cases):
            continue
        prev = {c: None for c in cases}
        file_, fin = deque(cases), None
        while file_:
            r, q = file_.popleft()
            if ids[r, q] == principale:
                fin = (r, q)
                break
            for nq, nr in neighbours(q, r, W, H):
                if (nr, nq) not in prev and terre[nr, nq] and not voile[nr, nq]:
                    prev[(nr, nq)] = (r, q)
                    file_.append((nr, nq))
        ajout = []
        while fin is not None and prev[fin] is not None:
            fin = prev[fin]
            if imp[fin] != 1:
                ajout.append(fin)
        for c in ajout:
            imp[c] = 1
        prolongees.append(f"{o['nom']} +{len(ajout)}")
    print(f"  passage : {int(imp.sum())} hex franchissables ; ouvertures : {len(ouv)} hex ; "
          f"prolongées jusqu'à la composante principale : {prolongees or 'aucune'}")

    # 3. graines des villes neuves
    graines, sans_ville, ports_mer = 0, [], []
    reg_avant_ports = reg.copy()
    rivieres_v, places = rivieres > 0, []
    for e in terrestres:
        rid = idx[e["cle_jeu"]]
        if (slots[reg == rid] == MAIN).any():
            continue                                   # reprise de Fort Solstice : ville de WH1 déjà là
        cible = e.get("hex_ville_expanded")
        if not cible and e.get("reflet_de") in idx:
            # ville reflétée : le reflet du centre de la ville de WH1 (rangée REFLET − R)
            m = (reg == idx[e["reflet_de"]]) & (slots == MAIN)
            if m.any():
                rr, qq = np.argwhere(m).mean(0)
                cible = [int(round(qq)), int(REFLET - round(rr))]
        # (une ville sur une case franchissable : dans les Voûtes, au fond de son bassin, jamais sur la haute montagne)
        cases = np.argwhere((reg == rid) & terre & (imp == 1))
        if not len(cases):
            cases = np.argwhere((reg == rid) & terre)
        if not len(cases):
            sans_ville.append(e["cle_jeu"])
            continue
        if cible:
            dist = [hex_distance((int(c[1]), int(c[0])), (int(cible[0]), int(cible[1]))) for c in cases]
            r0, q0 = cases[int(np.argmin(dist))]
            if not e.get("port"):
                r0, q0 = meilleur_emplacement(int(q0), int(r0), rid, reg, terre, imp, rivieres_v, places)
        else:
            r0, q0 = cases[len(cases) // 2]
            sans_ville.append(e["cle_jeu"] + " (centre pris au milieu)")
        slots[r0, q0] = MAIN
        for nq, nr in neighbours(int(q0), int(r0), W, H):
            if reg[nr, nq] == rid and terre[nr, nq]:
                slots[nr, nq] = MAIN
        if e.get("port"):
            mer_proche = [(nq, nr) for q, r in [(int(q0), int(r0))] + list(neighbours(int(q0), int(r0), W, H))
                          for nq, nr in neighbours(q, r, W, H) if not terre[nr, nq]]
            if not mer_proche:
                pts = np.argwhere(~terre)
                dist = [hex_distance((int(p[1]), int(p[0])), (int(q0), int(r0))) for p in pts]
                pr, pq = pts[int(np.argmin(dist))]
                mer_proche = [(int(pq), int(pr))]
            # (3.10.2026, mesuré sur la couche de la Saison, qui tourne en jeu : ses 9 cases de port sont en mer ET dans
            # leur région de mer ; les rattacher à la région de la ville, comme on le faisait, levait 25 avertissements
            # « sea ground type, yet it is a land region », que la Saison n'a pas)
            # (`grow_town_slots` reconnaît un port à la région de ses cases de port : rattachées à la ville le temps
            # de la croissance, cible 16, puis rendues à leur mer à l'étape 4)
            for nq, nr in mer_proche[:3]:
                slots[nr, nq] = PORT
                ports_mer.append((nr, nq, int(reg[nr, nq])))
                reg[nr, nq] = rid
        graines += 1
    print(f"  graines de villes neuves : {graines} ; remarques : {sans_ville or 'aucune'}")
    print(f"  villes neuves déplacées pour l'étalement (≤ 3 hex) : {len(places)} {places[:12]}")

    # 4. croissance (à blanc puis pour de bon)
    shutil.rmtree(TRAVAIL, ignore_errors=True)
    os.makedirs(TRAVAIL)
    couches = {"Regions": reg, "GroundTypes": sol, "TownSlots": slots, "TownSprawl": sprawl, "Impassable": imp,
               "Rivers": lire(COUCHES, "layer_rivers.hex_layer"), "Beaches": lire(COUCHES, "layer_beaches.hex_layer")}
    for nom, v in couches.items():
        with open(os.path.join(TRAVAIL, f"layer_{nom.lower()}.hex_layer"), "wb") as fh:
            fh.write(encode_flat(nom, np.asarray(v).reshape(-1)))
    base = [sys.executable, GROW, "--caime", CAIME, "--map", CARTE_EXP, "--layers", TRAVAIL, "--out", SORTIE]
    p = subprocess.run(base + ["--dry-run"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("  " + "\n  ".join((p.stdout + p.stderr).strip().splitlines()[-14:]))
    shutil.rmtree(SORTIE, ignore_errors=True)
    subprocess.run(base, capture_output=True, text=True, encoding="utf-8", errors="replace")
    # les cases de port rendues à leur région de mer (comme les 9 de la Saison, qui tourne en jeu) : celles qu'on a
    # rattachées, et celles que grow_town_slots ajoute lui-même au port pendant la croissance
    reg_s = lire(SORTIE, "layer_regions.hex_layer").reshape(H, W).copy()
    for nr, nq, mer in ports_mer:
        reg_s[nr, nq] = mer
    sol_s = lire(SORTIE, "layer_groundtypes.hex_layer").reshape(H, W)
    regions_mer_ = np.zeros(len(noms) + 1, bool)
    regions_mer_[len(listes.get("Land regions", [])):len(noms)] = True
    a_rendre = (sol_s >= n_sols_terre) & ~regions_mer_[np.where(reg_s < 0, len(noms), reg_s)] & (reg_s >= 0)
    reg_s[a_rendre] = reg_avant_ports[a_rendre]
    print(f"  cases de port ajoutées par la croissance et rendues à leur mer : {int(a_rendre.sum())}")
    with open(os.path.join(SORTIE, "layer_regions.hex_layer"), "wb") as fh:
        fh.write(encode_flat("Regions", reg_s.reshape(-1)))
    print(f"  cases de port rendues à leur mer : {len(ports_mer)}")
    # 4 bis. les colonies de WH1 telles que dans la Saison (la croissance ne touche que les villes neuves)
    sl_s = lire(SORTIE, "layer_townslots.hex_layer").reshape(H, W).copy()
    sp_s = lire(SORTIE, "layer_townsprawl.hex_layer").reshape(H, W).copy()
    n_id = villes_wh1_a_l_identique(sl_s, sp_s, reg_s, noms)
    for nom, v in (("TownSlots", sl_s), ("TownSprawl", sp_s)):
        with open(os.path.join(SORTIE, f"layer_{nom.lower()}.hex_layer"), "wb") as fh:
            fh.write(encode_flat(nom, v.reshape(-1)))
    print(f"  colonies de WH1 remises à l'identique de la Saison : {n_id} cases")
    if a.sans_import:
        return 0
    args = [CAIME, "import-layer", "--map", CARTE_EXP]
    for nom in ("TownSlots", "TownSprawl", "Impassable", "Regions", "GroundTypes"):
        args += ["--layer", nom, "--file", os.path.join(SORTIE, f"layer_{nom.lower()}.hex_layer")]
    args += ["--layer", "Climates", "--file", os.path.join(COUCHES, "layer_climates.hex_layer")]
    # la couche des régions avec les hex de port rattachés à leur ville devient la référence du chantier
    shutil.copy2(os.path.join(SORTIE, "layer_regions.hex_layer"), os.path.join(COUCHES, "layer_regions.hex_layer"))
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
