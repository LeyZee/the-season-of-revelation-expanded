#!/usr/bin/env python3
"""
routes_expanded.py - les ROUTES de l'Atlas dans la grille d'Expanded (couche Roads de CAIME), 4.10.2026.

Pourquoi (Charles : « que ça grouille de vie », étude de The Old World : des routes partout entre les villes) : la grille
d'Expanded n'avait de routes que dans le cadre de WH1 (3 147 cases, celles de la Saison) ; aucune dans l'extension, où
l'Atlas trace pourtant 84 routes entre ses villes (`extension_routes.json`, clé `routes`, session « Extension »).

Codage relevé sur le map.hex de la Saison (kit, 4.10.2026) : chaque case de route porte un masque de 6 bits, le bit k
allumé si la route continue vers le voisin de la direction k de `grow_town_slots.DIRS` (sommet plat, colonnes impaires
décalées) ; le voisin porte le bit (k + 3) mod 6 (concordance de 100 % sur les 3 147 cases). Pas de couche Bridges dans
la Saison (une route passe sur 15 cases de rivière sans pont déclaré).

Règles : une route de l'Atlas ne se pose que sur la terre franchissable, hors de la zone gardée de WH1 (WH1 à 100 % :
ses routes restent les siennes) ; là où elle touche une case de route de WH1, elle s'y branche (bit ajouté des deux
côtés) ; deux points successifs non voisins sont reliés par la ligne d'hex la plus droite.

Source : la copie FIGÉE d'avant-20261004 (05-journal\\2026-10-04-fleuves-navigables-atlas\\avant-20261004\\). Le feu
vert de Charles pour le fichier vivant est donné (4.10.2026, 19 h 15) ; il passe avec le lot des fleuves (villes
déplacées), voir SOURCE plus bas.
Usage : python routes_expanded.py [--apply]     (à blanc : bilan et image ; --apply : grille du chantier, sauvegardée)
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
from grow_town_slots import DIRS, cube                                        # noqa: E402
from cadre_expanded import W, H, DX, DY                                       # noqa: E402

SOURCE_VIVANTE = os.path.join(V.ATLAS, "extension_routes.json")
SOURCE_FIGEE = os.path.join(V.ATELIER, r"05-journal\2026-10-04-fleuves-navigables-atlas\avant-20261004\extension_routes.json")
# (4.10.2026, 20 h 45) le fichier vivant mène déjà les routes aux 7 villes DÉPLACÉES par la v3 des fleuves ; tant que la
# grille ne les a pas déplacées (lot des fleuves, après le démarrage de référence validé par Charles, CLAUDE.md § 2), il
# laisserait des culs-de-sac à 1 à 4 hex de ces villes : la copie figée reste la source jusqu'à ce lot
SOURCE = SOURCE_FIGEE
TRAVAIL = os.path.join(V.COUCHES, "routes")
APERCU = os.path.join(V.ICI, r"apercus\routes-expanded.png")
SAUVEGARDES = os.path.join(V.ATELIER, r"05-journal\terrain-backups")


def offset(x, y, z):
    return x, z + (x - (x & 1)) // 2


def ligne_hex(a, b):
    """Cases (colonne, rangée) de a à b, la ligne d'hex la plus droite (interpolation en coordonnées cubiques)."""
    ca, cb = np.array(cube(*a), float), np.array(cube(*b), float)
    n = int(max(abs(ca - cb)))
    out = []
    for i in range(n + 1):
        p = ca + (cb - ca) * (i / max(n, 1)) + 1e-6
        r = np.round(p)
        d = np.abs(r - p)
        if d[0] > d[1] and d[0] > d[2]:
            r[0] = -r[1] - r[2]
        elif d[1] > d[2]:
            r[1] = -r[0] - r[2]
        else:
            r[2] = -r[0] - r[1]
        q = offset(int(r[0]), int(r[1]), int(r[2]))
        if not out or out[-1] != q:
            out.append(q)
    return out


# (premier aperçu, 4.10.2026 : les routes de l'Atlas filaient en longues lignes droites, celles de WH1 serpentent ;
# plusieurs finissaient en cul-de-sac au bord de la zone gardée de WH1)
COURBE_HEX = 1.3                 # écart latéral au plus (hex), nul aux deux bouts du tracé (villes, carrefours)
RACCORD_MAX_HEX = 40             # au plus (le long du tracé de l'Atlas), pour rejoindre une route ou une ville de WH1


def courbes(pts):
    """Le tracé (x, y) avec des courbes douces (deux ondes de 9 à 20 hex), nulles aux bouts ; stable (graine = tracé)."""
    p = np.asarray(pts, np.float64)
    if len(p) < 3:
        return [tuple(x) for x in p]
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    L = s[-1]
    if L < 6:
        return [tuple(x) for x in p]
    t = np.linspace(0, L, max(3, int(L / 0.5) + 1))
    x, y = np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])
    k = 4
    xs = np.convolve(np.pad(x, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    ys = np.convolve(np.pad(y, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    dx, dy = np.gradient(xs), np.gradient(ys)
    n = np.maximum(np.hypot(dx, dy), 1e-9)
    g = np.random.default_rng(int(abs(p[0, 0] * 7919 + p[0, 1] * 104729 + L * 31)) % (2 ** 32))
    l1, l2 = g.uniform(9, 13), g.uniform(14, 20)
    f1, f2 = g.uniform(0, 2 * np.pi, 2)
    onde = 0.6 * np.sin(2 * np.pi * t / l1 + f1) + 0.4 * np.sin(2 * np.pi * t / l2 + f2)
    bouts = np.clip(np.minimum(t, L - t) / 4.0, 0, 1)
    a = COURBE_HEX * onde * bouts * bouts * (3 - 2 * bouts)
    return list(zip(x - a * dy / n, y + a * dx / n))


def raccord(depart, wh1, passe):
    """Chemin d'hex le plus court (sur la terre franchissable) de `depart` à la route de WH1 la plus proche, au plus
    RACCORD_MAX_HEX ; None sinon."""
    from collections import deque
    prev = {depart: None}
    file_ = deque([(depart, 0)])
    while file_:
        c, d = file_.popleft()
        if wh1[c[1], c[0]] and c != depart:
            chemin = [c]
            while prev[chemin[-1]] is not None:
                chemin.append(prev[chemin[-1]])
            return chemin[::-1]
        if d >= RACCORD_MAX_HEX:
            continue
        for dq, dr in DIRS[c[0] & 1]:
            n_ = (c[0] + dq, c[1] + dr)
            if 0 <= n_[0] < W and 0 <= n_[1] < H and n_ not in prev and passe[n_[1], n_[0]]:
                prev[n_] = c
                file_.append((n_, d + 1))
    return None


def direction(a, b):
    for k, (dq, dr) in enumerate(DIRS[a[0] & 1]):
        if (a[0] + dq, a[1] + dr) == b:
            return k
    return None


def neighbours_(q, r):
    for dq, dr in DIRS[q & 1]:
        if 0 <= q + dq < W and 0 <= r + dr < H:
            yield q + dq, r + dr


def routes_reves(roads, passe_route, terre, plages):
    """Bits de route du Bois Rêveur : les routes d'Athel Loren (cases de route de WH1 de la grille) reflétées comme tout
    le reste (cadre_expanded : rangée R' = REFLET − R), sur la terre franchissable du reflet. (4.10.2026, comparaison de
    tile_map.png à l'export CAIME : 4 280 px de routes reflétées dans la carte des tuiles, aucune dans la grille ; le
    guide Terry veut tile_map = export CAIME, donc routes de la grille = routes dessinées.) Le reflet décale d'un
    demi-hex les colonnes de parité opposée : deux cases voisines dans Athel Loren peuvent ne plus l'être ; elles sont
    alors reliées par la ligne d'hex la plus droite."""
    from cadre_expanded import REFLET, SUD
    rv = np.load(projet_expanded_reves())
    terre_r = np.zeros((H, W), bool)
    terre_r[:rv["terre"].shape[0], :W] = rv["terre"] & ~rv["voile"]
    # (validate --roads, premier passage : « Hex(288, 162) is both a road and cliff or beach, and is not leading to a
    # bridge ») jamais sur la côte (terre voisine de la mer) ni sur une plage
    cote = np.zeros((H, W), bool)
    for r, q in np.argwhere(passe_route[:SUD]):
        if any(not terre[nr, nq] for nq, nr in neighbours_(int(q), int(r))):
            cote[r, q] = True
    ok = passe_route & terre_r & ~cote & ~plages
    # (4.10.2026, CAIME process BLOQUÉ dans l'export Pathfinding, isolé sur ces routes ; premier essai par R' = REFLET −
    # R et raccords en ligne d'hex : 331 carrefours à 3, 55 à 4, 3 à 5, des routes soudées côte à côte ; WH1 : des fils,
    # 55 carrefours) MIROIR EXACT de la grille d'hex : colonne paire R -> REFLET − R, colonne impaire R -> REFLET − R − 1 ;
    # directions nord <-> sud, nord-est <-> sud-est, nord-ouest <-> sud-ouest (DIRS : 0 <-> 3, 1 <-> 2, 4 <-> 5). Une
    # isométrie : le réseau garde exactement la forme de celui de WH1 ; un lien n'est gardé que si ses deux bouts sont
    # sur la terre franchissable du reflet
    miroir_dir = (3, 2, 1, 0, 5, 4)
    bits = np.zeros((H, W), np.int64)
    for r, q in np.argwhere(roads > 0):
        q, r = int(q), int(r)
        r2 = REFLET - r - (q & 1)
        if not (0 <= r2 < SUD) or not ok[r2, q]:
            continue
        v = int(roads[r, q])
        for k in range(6):
            if v >> k & 1:
                bits[r2, q] |= 1 << miroir_dir[k]
    # liens réciproques seulement (un bout hors de la terre franchissable du reflet coupe le lien)
    n = 0
    for r, q in np.argwhere(bits > 0):
        for k in range(6):
            if not bits[r, q] >> k & 1:
                continue
            dq, dr = DIRS[q & 1][k]
            nq, nr = int(q) + dq, int(r) + dr
            if not (0 <= nq < W and 0 <= nr < H) or not (bits[nr, nq] >> ((k + 3) % 6) & 1):
                bits[r, q] &= ~(1 << k)
            else:
                n += 1
    return bits, n // 2


COULOIR_HEX = 3                  # écart au tracé de l'Atlas au plus
COUT_SUIVRE = 0.3                # suivre un lien de route déjà posé
COUT_ECART = 0.8                 # par hex d'écart au tracé
COUT_LONGER = 6.0                # par route voisine non reliée (deux routes côte à côte)
BRANCHES_MAX = 3
# (4.10.2026, BOB du 23 h 46 : 32 « Failed to find tile » TileSet_roads, 25 sur 26 à 1 hex d'un nœud que la Saison n'a
# jamais) BOB n'a de tuile de route que pour les formes que WH1 emploie : formes canoniques (6 bits à une rotation près)
# 1 (bout), 5 (virage de 120°), 9 (droit), 11, 13, 21 (fourches) ; jamais 3 (virage de 60°), 7, 23 ; et jamais deux
# carrefours voisins (Saison : 0, Expanded : 21). COUT_LONGER passe de 1,5 à 6 (routes côte à côte sans lien : 62 dans
# la Saison, 189 dans Expanded)
FORMES_CA = (1, 5, 9, 11, 13, 21)


def forme(m):
    """Forme canonique d'un masque de route de 6 bits (plus petit masque parmi ses 6 rotations)."""
    return min(sum(1 << ((k + s) % 6) for k in range(6) if m >> k & 1) for s in range(6))


def ok_noeud(c, m, deg, complet):
    """Le nœud c au masque m a-t-il une forme de CA, et, carrefour, aucun carrefour voisin ? `complet` : m est le masque
    final de c (sinon seule la forme partielle est jugée : un masque à deux liens collés y est déjà refusé)."""
    n = bin(m).count("1")
    if n == 2 and forme(m) == 3:
        return False                                   # virage de 60°, jamais complété en forme de CA sans fourche
    if n >= 3 and forme(m) not in FORMES_CA:
        return False
    if complet and n == 2 and forme(m) not in FORMES_CA:
        return False
    if n >= 3:
        for w in neighbours_(*c):
            if deg[w[1], w[0]] >= 3:
                return False
    return True


def defauts_reseau(neuf):
    """(formes hors de CA, carrefours voisins, routes voisines non reliées) du réseau `neuf`."""
    formes, carref, contact = 0, 0, 0
    deg = np.zeros((H, W), np.int64)
    for k in range(6):
        deg += (neuf >> k) & 1
    for r, q in np.argwhere(neuf > 0):
        m = int(neuf[r, q])
        if forme(m) not in FORMES_CA:
            formes += 1
        for k in range(6):
            dq, dr = DIRS[q & 1][k]
            a, b = q + dq, r + dr
            if not (0 <= a < W and 0 <= b < H) or neuf[b, a] <= 0:
                continue
            if not (m >> k & 1):
                contact += 1
            if deg[r, q] >= 3 and deg[b, a] >= 3:
                carref += 1
    return formes, carref // 2, contact // 2


ZIGZAG_MAX = 8                   # longueur au plus d'une boucle coupée


def couper_zigzags(neuf, fixes):
    """Deux cases de route NEUVES voisines non reliées, à deux branches chacune, qui sont sur la même route à moins de
    ZIGZAG_MAX liens l'une de l'autre (zigzag de la recherche de chemin contre sa propre trace, que BOB ne sait pas
    dessiner) : reliées directement, et les cases de la boucle entre elles retirées, si les formes restent celles de CA.
    `fixes` : cases jamais retirées (routes de WH1, villes). Rend le nombre de boucles coupées."""
    from collections import deque
    n = 0
    change = True
    while change:
        change = False
        deg = sum((neuf >> k) & 1 for k in range(6))
        for r, q in np.argwhere((neuf > 0) & ~fixes):
            x = (int(q), int(r))
            if deg[x[1], x[0]] != 2 or not neuf[x[1], x[0]]:
                continue
            for k in range(6):
                if neuf[x[1], x[0]] >> k & 1:
                    continue
                dq, dr = DIRS[x[0] & 1][k]
                y = (x[0] + dq, x[1] + dr)
                if not (0 <= y[0] < W and 0 <= y[1] < H) or fixes[y[1], y[0]] or deg[y[1], y[0]] != 2:
                    continue
                # chemin de x à y par les liens, cases intermédiaires à deux branches et non fixes
                prec = {x: None}
                file_ = deque([(x, 0)])
                trouve = False
                while file_ and not trouve:
                    c, d = file_.popleft()
                    if d >= ZIGZAG_MAX:
                        continue
                    for j in range(6):
                        if not neuf[c[1], c[0]] >> j & 1:
                            continue
                        a, b = c[0] + DIRS[c[0] & 1][j][0], c[1] + DIRS[c[0] & 1][j][1]
                        s = (a, b)
                        if s in prec:
                            continue
                        if s == y:
                            prec[s] = c
                            trouve = True
                            break
                        if fixes[b, a] or deg[b, a] != 2:
                            continue
                        prec[s] = c
                        file_.append((s, d + 1))
                if not trouve:
                    continue
                boucle = [y]
                while prec[boucle[-1]] is not None:
                    boucle.append(prec[boucle[-1]])
                boucle = boucle[::-1]                          # x … y
                if len(boucle) < 3:                            # x, c, y : virage de 60° en c, coupé aussi
                    continue
                # masques après la coupe : x garde son lien hors boucle et prend y ; y de même
                kx_out = [j for j in range(6) if neuf[x[1], x[0]] >> j & 1 and j != direction(x, boucle[1])]
                ky_out = [j for j in range(6) if neuf[y[1], y[0]] >> j & 1 and j != direction(y, boucle[-2])]
                mx = sum(1 << j for j in kx_out) | (1 << k)
                my = sum(1 << j for j in ky_out) | (1 << ((k + 3) % 6))
                if forme(mx) not in FORMES_CA or forme(my) not in FORMES_CA:
                    continue
                for c in boucle[1:-1]:
                    neuf[c[1], c[0]] = 0
                neuf[x[1], x[0]] = mx
                neuf[y[1], y[0]] = my
                n += 1
                change = True
                break
            if change:
                break
    return n


def elaguer_bouts(neuf, fixes, villes):
    """Bouts de route neufs (une seule liaison) hors d'une ville qui frôlent une autre route sans la rejoindre (nœud des
    passages étroits : BOB n'a pas de tuile pour deux routes côte à côte) : retirés case par case tant qu'ils la
    frôlent. Rend le nombre de cases retirées."""
    n = 0
    change = True
    while change:
        change = False
        deg = sum((neuf >> k) & 1 for k in range(6))
        for r, q in np.argwhere((deg == 1) & ~fixes):
            c = (int(q), int(r))
            if bin(int(neuf[r, q])).count("1") != 1:
                continue                                       # changé depuis le relevé (case voisine retirée)
            if any(villes[w[1], w[0]] for w in neighbours_(*c)) or villes[c[1], c[0]]:
                continue
            frole = [w for w in neighbours_(*c) if neuf[w[1], w[0]] > 0 and not (neuf[c[1], c[0]] >> direction(c, w) & 1)]
            if not frole:
                continue
            k = [j for j in range(6) if neuf[c[1], c[0]] >> j & 1][0]
            a, b = c[0] + DIRS[c[0] & 1][k][0], c[1] + DIRS[c[0] & 1][k][1]
            neuf[c[1], c[0]] = 0
            neuf[b, a] &= ~(1 << ((k + 3) % 6))
            n += 1
            change = True
    return n


LIAISON_MAX = 40                 # hex au plus pour souder un bout mort au morceau de réseau voisin


def morceaux_reseau(neuf):
    """Étiquette (H, W) du morceau de réseau de chaque case de route (−1 ailleurs)."""
    from collections import deque
    lab = -np.ones((H, W), np.int64)
    i = 0
    for r, q in np.argwhere(neuf > 0):
        if lab[r, q] >= 0:
            continue
        f = deque([(int(q), int(r))])
        lab[r, q] = i
        while f:
            c = f.popleft()
            for k in range(6):
                if neuf[c[1], c[0]] >> k & 1:
                    a, b = c[0] + DIRS[c[0] & 1][k][0], c[1] + DIRS[c[0] & 1][k][1]
                    if lab[b, a] < 0:
                        lab[b, a] = i
                        f.append((a, b))
        i += 1
    return lab


def souder_bouts(neuf, permis, fixes, villes):
    """(4.10.2026, contrôle des routes : 12 morceaux de réseau ; dans les vallées étroites des Voûtes, le tracé de l'Atlas
    coupe un éperon rocheux et la route était posée en deux morceaux jamais rejoints) chaque bout mort hors d'une ville
    est relié, par la terre franchissable hors de la zone gardée (`permis`), à la case la plus proche d'un AUTRE morceau,
    à LIAISON_MAX hex au plus, en formes de CA (ok_noeud) et sans longer d'autre route. Rend (soudures, cases ajoutées)."""
    from collections import deque
    n_s, n_c = 0, 0
    change = True
    while change:
        change = False
        lab = morceaux_reseau(neuf)
        deg = sum((neuf >> k) & 1 for k in range(6))
        for r, q in np.argwhere((deg == 1) & ~villes):
            x = (int(q), int(r))
            if any(villes[w[1], w[0]] for w in neighbours_(*x)):
                continue
            moi = lab[x[1], x[0]]
            if fixes[x[1], x[0]]:
                continue
            prec = {x: None}
            file_ = deque([(x, 0)])
            cible = None
            while file_ and cible is None:
                c, d = file_.popleft()
                if d >= LIAISON_MAX:
                    continue
                for v in neighbours_(*c):
                    if v in prec:
                        continue
                    if neuf[v[1], v[0]] > 0:
                        if lab[v[1], v[0]] != moi and c != x:
                            prec[v] = c
                            cible = v
                            break
                        continue
                    if not permis[v[1], v[0]]:
                        continue
                    # une case neuve ne touche que son prédécesseur ou la cible (pas de route côte à côte)
                    if any(neuf[w[1], w[0]] > 0 and w != c and lab[w[1], w[0]] == moi for w in neighbours_(*v)):
                        continue
                    prec[v] = c
                    file_.append((v, d + 1))
            if cible is None:
                continue
            ch = [cible]
            while prec[ch[-1]] is not None:
                ch.append(prec[ch[-1]])
            ch = ch[::-1]                                   # x … cible
            # formes : x (bout + départ), cases neuves (deux liens), cible (un lien de plus)
            essai = neuf.copy()
            for c0, c1 in zip(ch, ch[1:]):
                kk = direction(c0, c1)
                essai[c0[1], c0[0]] |= 1 << kk
                essai[c1[1], c1[0]] |= 1 << ((kk + 3) % 6)
            deg2 = sum((essai >> k) & 1 for k in range(6))
            if not all(ok_noeud(c, int(essai[c[1], c[0]]), deg2, True) for c in ch):
                continue
            neuf[:] = essai
            n_s += 1
            n_c += len(ch) - 2
            change = True
            break
    return n_s, n_c


LIAISON_MORCEAU_MAX = 260        # coût au plus d'une liaison entre morceaux (120 : 3 petits morceaux restaient seuls)
COUT_GARDE = 3                   # une case de route neuve dans la zone gardée de WH1 coûte plus (WH1 touché au minimum)
# (5.10.2026) l'accord de Charles porte sur l'ouest (33, 51 et 34 cases dans WH1) ; une liaison qui traverserait plus
# de cases de WH1 (le morceau de l'est : 86) attend sa décision
GARDE_MAX_LIAISON = 60


def relier_morceaux(neuf, passe, garde, villes, sud):
    """(5.10.2026, accord de Charles : « relie l'ouest au grand réseau » ; exception à « WH1 à 100 % », pour Expanded
    SEULEMENT : quelques cases de route dans la zone gardée) chaque morceau du réseau hors du plus grand et hors du Bois
    Rêveur (rangées < sud, à part : accès par les portails) est relié au plus grand par le chemin le moins coûteux sur la
    terre franchissable `passe` (case de la zone gardée : COUT_GARDE), sans longer d'autre route, en formes de CA ; la
    case d'arrivée qui ferait une forme hors de CA est écartée et la recherche reprend. Rend [(taille, cases, dans WH1)]."""
    import heapq
    faits = []
    for _ in range(40):
        lab = morceaux_reseau(neuf)
        n_lab = int(lab.max()) + 1
        tailles = np.bincount(lab[lab >= 0], minlength=n_lab)
        haut = np.zeros(n_lab, bool)
        for i in np.unique(lab[:sud][lab[:sud] >= 0]):
            haut[i] = True                                  # morceaux du Bois Rêveur
        cand = [i for i in np.argsort(-tailles) if not haut[i]]
        if len(cand) < 2:
            break
        principal = cand[0]
        cible = lab == principal
        relie = False
        for i in cand[1:]:
            src = [(int(q), int(r)) for r, q in np.argwhere(lab == i)]
            refus = set()
            for _essai in range(12):
                dist = {s: 0 for s in src}
                prec = {}
                tas = [(0, s) for s in src]
                fin = None
                while tas:
                    d, c = heapq.heappop(tas)
                    if d > dist.get(c, 1e9) or d > LIAISON_MORCEAU_MAX:
                        continue
                    if cible[c[1], c[0]] and c not in refus:
                        fin = c
                        break
                    for v in neighbours_(*c):
                        if cible[v[1], v[0]]:
                            if v in refus:
                                continue
                            d2 = d + 1
                        else:
                            if neuf[v[1], v[0]] > 0 or not passe[v[1], v[0]] or villes[v[1], v[0]]:
                                continue
                            if any(neuf[w[1], w[0]] > 0 and w != c and not cible[w[1], w[0]] and lab[w[1], w[0]] != i
                                   for w in neighbours_(*v)):
                                continue                   # ne longe pas un troisième morceau
                            d2 = d + (COUT_GARDE if garde[v[1], v[0]] else 1)
                        if d2 < dist.get(v, 1e9):
                            dist[v] = d2
                            prec[v] = c
                            heapq.heappush(tas, (d2, v))
                if fin is None:
                    break
                ch = [fin]
                while ch[-1] in prec:
                    ch.append(prec[ch[-1]])
                ch = ch[::-1]                               # départ (case du morceau) … arrivée (principal)
                essai = neuf.copy()
                for c0, c1 in zip(ch, ch[1:]):
                    kk = direction(c0, c1)
                    essai[c0[1], c0[0]] |= 1 << kk
                    essai[c1[1], c1[0]] |= 1 << ((kk + 3) % 6)
                deg2 = sum((essai >> k) & 1 for k in range(6))
                if sum(1 for c in ch[1:-1] if garde[c[1], c[0]]) > GARDE_MAX_LIAISON:
                    break                                   # trop de WH1 traversé : décision de Charles
                mauvais = [c for c in (ch[0], ch[-1]) if not ok_noeud(c, int(essai[c[1], c[0]]), deg2, True)]
                mauvais += [c for c in ch[1:-1] if not ok_noeud(c, int(essai[c[1], c[0]]), deg2, True)]
                if mauvais:
                    refus.add(ch[-1])
                    if ch[0] in mauvais:
                        src = [s for s in src if s != ch[0]]
                    continue
                neuf[:] = essai
                faits.append((int(tailles[i]), len(ch) - 2, sum(1 for c in ch[1:-1] if garde[c[1], c[0]])))
                relie = True
                break
            if relie:
                break
        if not relie:
            break
    return faits


DOUBLON_HEX = 2


def retirer_doublons(neuf, fixes, villes):
    """(4.10.2026, image des Voûtes : deux routes de l'Atlas qui partagent une vallée étroite y laissaient un second fil
    collé au premier, en morceau à part) un morceau de réseau sans case fixe (WH1, Bois Rêveur, ville) dont TOUTES les
    cases sont à DOUBLON_HEX au plus d'un autre morceau est retiré. Rend (morceaux, cases) retirés."""
    import cv2
    lab = morceaux_reseau(neuf)
    n_m, n_c = 0, 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * DOUBLON_HEX + 1, 2 * DOUBLON_HEX + 1))
    for i in range(int(lab.max()) + 1):
        moi = lab == i
        if not moi.any() or (moi & (fixes | villes)).any():
            continue
        autres = cv2.dilate(((lab >= 0) & ~moi).astype(np.uint8), k) > 0
        if (moi & ~autres).any():
            continue
        # liens des voisins vers ce morceau retirés aussi
        for r, q in np.argwhere(moi):
            for j in range(6):
                if neuf[r, q] >> j & 1:
                    a, b = q + DIRS[q & 1][j][0], r + DIRS[q & 1][j][1]
                    neuf[b, a] &= ~(1 << ((j + 3) % 6))
        neuf[moi] = 0
        n_m += 1
        n_c += int(moi.sum())
    return n_m, n_c


def chemin_couloir(m, neuf, deg, permis, wh1, ok_cases, interdit=None):
    """Chemin de cases de m[0] à m[-1] dans le couloir de COULOIR_HEX autour du morceau m (A*), ou None. Cases permises :
    terre franchissable hors WH1 gardé (`permis`), routes existantes, cases de raccord (`ok_cases`) ; un lien neuf a au
    moins un bout qui n'est pas une route de WH1 ; aucune case ne dépasse BRANCHES_MAX liens."""
    import heapq
    from collections import deque
    ecart = {c: 0 for c in m}
    file_ = deque(m)
    while file_:
        c = file_.popleft()
        if ecart[c] >= COULOIR_HEX:
            continue
        for n_ in neighbours_(*c):
            if n_ not in ecart:
                ecart[n_] = ecart[c] + 1
                file_.append(n_)

    def permise(c):
        if c not in ecart:
            return False
        if wh1[c[1], c[0]]:
            return True
        return bool(permis[c[1], c[0]]) or (c in ok_cases and not (interdit is not None and interdit[c[1], c[0]]))

    def lie(u, k):
        return bool(neuf[u[1], u[0]] >> k & 1)

    def hd(a, b):
        ca, cb = cube(*a), cube(*b)
        return max(abs(ca[0] - cb[0]), abs(ca[1] - cb[1]), abs(ca[2] - cb[2]))

    def proche_permise(c):
        """c, ou la case permise la plus proche dans le couloir (bout de tracé sur la côte : ville de port)."""
        if permise(c):
            return c
        vus, file2 = {c}, deque([c])
        while file2:
            x = file2.popleft()
            for n_ in neighbours_(*x):
                if n_ in vus or n_ not in ecart:
                    continue
                if permise(n_):
                    return n_
                vus.add(n_)
                file2.append(n_)
        return None

    dep, but = proche_permise(m[0]), proche_permise(m[-1])
    if dep is None or but is None or dep == but:
        return None
    tas = [(0.0, 0.0, dep, False)]
    # (premier essai : MemoryError, le départ sans coût connu recevait un prédécesseur : cycle) départ à 0, états fermés
    vu = {(dep, False): 0.0}
    prec = {}
    fermes = set()
    while tas:
        _, g, u, arrive_neuf = heapq.heappop(tas)
        if (u, arrive_neuf) in fermes:
            continue
        fermes.add((u, arrive_neuf))
        if u == but:
            p = [(u, arrive_neuf)]
            while p[-1] in prec:
                p.append(prec[p[-1]])
            return [c for c, _ in reversed(p)]
        for k in range(6):
            dq, dr = DIRS[u[0] & 1][k]
            v = (u[0] + dq, u[1] + dr)
            if not (0 <= v[0] < W and 0 <= v[1] < H) or not permise(v):
                continue
            existe = lie(u, k)
            if not existe and wh1[u[1], u[0]] and wh1[v[1], v[0]] and u not in ok_cases and v not in ok_cases:
                continue
            neuf_lien = not existe
            if deg[u[1], u[0]] + int(arrive_neuf) + int(neuf_lien) > BRANCHES_MAX:
                continue
            if v == but and deg[v[1], v[0]] + int(neuf_lien) > BRANCHES_MAX:
                continue
            # formes de CA seulement (FORMES_CA), carrefours jamais voisins : en u (liens posés + arrivée + départ) et en v
            # (liens posés + arrivée ; complet si v est le but)
            pu = prec.get((u, arrive_neuf))
            m_u = int(neuf[u[1], u[0]]) | (1 << k)
            if pu is not None:
                m_u |= 1 << direction(u, pu[0])
            m_v = int(neuf[v[1], v[0]]) | (1 << ((k + 3) % 6))
            if not ok_noeud(u, m_u, deg, True) or not ok_noeud(v, m_v, deg, v == but):
                continue
            if existe:
                cout = COUT_SUIVRE
            else:
                cout = 1.0 + COUT_ECART * ecart[v]
                # (essai d'une interdiction stricte des contacts, 4.10.2026 : 59 morceaux sans chemin, 1 200 cases de
                # route perdues ; refusé) coût seulement ; les zigzags d'une route contre elle-même sont coupés ensuite
                # (couper_zigzags)
                longe = sum(1 for w in neighbours_(*v) if w != u and deg[w[1], w[0]] > 0
                            and not lie(v, direction(v, w)))
                cout += COUT_LONGER * longe
            g2 = g + cout
            cle = (v, neuf_lien)
            if cle not in fermes and g2 < vu.get(cle, 1e18) - 1e-9:
                vu[cle] = g2
                prec[cle] = (u, arrive_neuf)
                heapq.heappush(tas, (g2 + COUT_SUIVRE * hd(v, but), g2, v, neuf_lien))
    return None


def projet_expanded_reves():
    import projet_expanded
    return projet_expanded.REVES


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--seulement-reves", action="store_true",
                    help="seulement les routes reflétées du Bois Rêveur (pas les routes de l'Atlas, en attente du feu "
                         "vert des Voûtes)")
    ap.add_argument("--base", help="map.hex d'où lire les couches (grille SANS les routes de l'Atlas) ; défaut : la "
                                   "grille du chantier. --apply écrit toujours dans la grille du chantier")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    shutil.rmtree(TRAVAIL, ignore_errors=True)
    os.makedirs(TRAVAIL)
    p = subprocess.run([V.CAIME, "export-layer", "--map", a.base or V.CARTE_EXP, "--out", TRAVAIL, "--format", "binary",
                        "--layer", "Roads", "--layer", "Impassable", "--layer", "GroundTypes", "--layer", "TownSlots",
                        "--layer", "Beaches", "--layer", "Bridges"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise SystemExit(p.stdout + p.stderr)
    lire = lambda n: read_layer(os.path.join(TRAVAIL, f"layer_{n}.hex_layer"))[1].reshape(H, W).copy()  # noqa: E731
    roads, imp, gt, slots = lire("roads"), lire("impassable"), lire("ground_types"), lire("town_slots")
    plages = lire("beaches")
    n_terre = len(caime_names(V.CAIME, V.CARTE_EXP)[0].get("Land ground types", []))
    import projet_expanded
    garde = projet_expanded.garde_wh1_hex()
    wh1 = roads > 0
    passe_route = (gt >= 0) & (gt < n_terre) & (imp == 1)
    permis = passe_route & ~garde
    from cadre_expanded import SUD
    # la bande du Bois Rêveur ne porte que les routes reflétées : refaite à neuf à chaque passage
    roads = roads.copy()
    roads[:SUD] = 0
    wh1 = roads > 0
    neuf = roads.astype(np.int64).copy()
    b_reves, n_reves = routes_reves(roads, passe_route, (gt >= 0) & (gt < n_terre), plages > 0)
    neuf |= b_reves
    print(f"  Bois Rêveur : {n_reves} liens de route reflétés d'Athel Loren, {int(((b_reves > 0) & ~wh1).sum())} cases")
    wh1 = wh1 | (b_reves > 0)                    # les routes reflétées comptent comme réseau existant
    routes = [] if a.seulement_reves else json.load(open(SOURCE, encoding="utf-8"))["routes"]
    n_liens, n_branches, coupees = 0, 0, 0
    sans_trace = 0
    morceaux, ok_cases = [], set()
    for rt in routes:
        if not rt.get("points"):
            sans_trace += 1                      # paire de villes sans tracé dans l'Atlas (route impossible par terre)
            continue
        orig = [(int(np.floor(x)) + DX, int(np.floor(y)) + DY) for x, y in rt["points"]]
        cases = []
        for x, y in courbes(rt["points"]):
            c = (int(np.floor(x)) + DX, int(np.floor(y)) + DY)
            if 0 <= c[0] < W and 0 <= c[1] < H and (permis[c[1], c[0]] or wh1[c[1], c[0]]):
                cases.append(c)
        # la courbe ne quitte jamais la terre franchissable : là où elle en sortait, ses points sont sautés
        cases = [orig[0]] + cases + [orig[-1]] if len(cases) >= 2 else orig
        chemin = []
        for c0, c1 in zip(cases, cases[1:]):
            seg = ligne_hex(c0, c1)
            chemin += seg if not chemin else seg[1:]
        # raccord au réseau de WH1 par le tracé même de l'Atlas : dans chaque passage du tracé dans la zone gardée, les
        # cases depuis le bord jusqu'à la première route de WH1 (RACCORD_MAX_HEX au plus, terre franchissable) sont
        # permises ; au-delà, la route de WH1 prend le relais
        chemin = [c for c in chemin if 0 <= c[0] < W and 0 <= c[1] < H]
        ok_ici = [bool(permis[c[1], c[0]]) for c in chemin]
        dans = [bool(garde[c[1], c[0]]) for c in chemin]
        for sens in (1, -1):
            idxs = list(range(len(chemin)))[::sens]
            for j, i in enumerate(idxs[:-1]):
                if ok_ici[i] and dans[idxs[j + 1]]:
                    for t in range(1, RACCORD_MAX_HEX + 1):
                        if j + t >= len(idxs):
                            break
                        c = chemin[idxs[j + t]]
                        if not passe_route[c[1], c[0]]:
                            break
                        if wh1[c[1], c[0]] or slots[c[1], c[0]] >= 0:
                            for u in range(1, t + 1):
                                ok_ici[idxs[j + u]] = True
                            break
        # morceaux du tracé où la route est permise (suites de liens permis) : chacun sera tracé par recherche de chemin
        run = []
        for i0 in range(len(chemin) - 1):
            c0, c1 = chemin[i0], chemin[i0 + 1]
            if direction(c0, c1) is None:
                continue
            ok0, ok1 = ok_ici[i0], ok_ici[i0 + 1]
            r0, r1 = wh1[c0[1], c0[0]], wh1[c1[1], c1[0]]
            if (ok0 and ok1) or (ok0 and r1) or (r0 and ok1):
                if not run:
                    run = [c0]
                run.append(c1)
                for c, ok in ((c0, ok0), (c1, ok1)):
                    if ok:
                        ok_cases.add(c)
            else:
                if ok0 or ok1:
                    coupees += 1
                if len(run) >= 2:
                    morceaux.append(run)
                run = []
        if len(run) >= 2:
            morceaux.append(run)
    # (4.10.2026, données vivantes de l'Atlas : 389 carrefours à 3 branches et 102 à 4 ou plus, contre 55 et 0 dans WH1 ;
    # deux routes de l'Atlas qui partagent un couloir y étaient tracées côte à côte, à un hex l'une de l'autre, au lieu de
    # se rejoindre) chaque morceau est tracé par RECHERCHE DE CHEMIN dans un couloir de COULOIR_HEX autour du tracé de
    # l'Atlas : suivre une route déjà posée coûte peu (les routes se rejoignent), s'écarter du tracé coûte, longer une route
    # sans la rejoindre coûte ; jamais plus de 3 branches à un carrefour (comme WH1). Les plus longs morceaux d'abord.
    morceaux.sort(key=len, reverse=True)
    # (premier --apply, validate --roads de CAIME : 11 « Hex is both a road and cliff or beach, and is not leading to a
    # bridge ») comme les routes du Bois Rêveur : jamais une route neuve sur la côte (terre voisine de la mer) ni sur une
    # plage ; les routes de WH1 qui y passent restent les leurs
    terre_g = (gt >= 0) & (gt < n_terre)
    cote = np.zeros((H, W), bool)
    for r_, q_ in np.argwhere(terre_g):
        if any(not terre_g[nr, nq] for nq, nr in neighbours_(int(q_), int(r_))):
            cote[r_, q_] = True
    permis = permis & ~cote & ~(plages > 0)
    # (5.10.2026, fleuves navigables) une route franchit un fleuve sur ses PONTS (cases d'eau de la couche Bridges, posées
    # par creuser_fleuve aux points de l'Atlas) ; la case de berge qui y mène est permise (validate --roads : « is both a
    # road and cliff or beach, and is not leading to a bridge » ne vise que les berges sans pont)
    p_ponts = os.path.join(TRAVAIL, "layer_bridges.hex_layer")
    if os.path.exists(p_ponts):
        ponts = read_layer(p_ponts)[1].reshape(H, W) > 0
        approche = np.zeros((H, W), bool)
        for r_, q_ in np.argwhere(ponts):
            for nq, nr in neighbours_(int(q_), int(r_)):
                approche[nr, nq] = True
        permis = permis | ponts | (approche & terre_g & (imp == 1))
        print(f"  ponts des fleuves : {int(ponts.sum())} cases, {int((approche & terre_g).sum())} cases d'approche permises")
    deg = np.zeros((H, W), np.int64)
    for k in range(6):
        deg += (neuf >> k) & 1
    sans_chemin = 0
    for m in morceaux:
        p = chemin_couloir(m, neuf, deg, permis, wh1, ok_cases, interdit=cote | (plages > 0))
        if p is None:
            sans_chemin += 1
            continue
        for c0, c1 in zip(p, p[1:]):
            k = direction(c0, c1)
            if neuf[c0[1], c0[0]] >> k & 1:
                continue
            neuf[c0[1], c0[0]] |= 1 << k
            neuf[c1[1], c1[0]] |= 1 << ((k + 3) % 6)
            deg[c0[1], c0[0]] += 1
            deg[c1[1], c1[0]] += 1
            n_liens += 1
            n_branches += int(wh1[c0[1], c0[0]] or wh1[c1[1], c1[0]])
    print(f"  morceaux de tracé : {len(morceaux)} ; sans chemin dans leur couloir (non posés) : {sans_chemin}")
    # bouts de route (une seule liaison) hors d'une ville, à moins de 3 hex de la zone gardée : raccordés à la route de
    # WH1 la plus proche par la terre franchissable (quelques cases de route ajoutées dans la zone gardée, au plus
    # RACCORD_MAX_HEX ; « une seule vraie carte » plutôt qu'un cul-de-sac au raccord)
    passe = (gt >= 0) & (gt < n_terre) & (imp == 1)
    import cv2
    pres_garde = cv2.dilate(garde.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    degre = np.zeros((H, W), np.int64)
    for k in range(6):
        degre += (neuf >> k) & 1
    n_racc, n_racc_cases = 0, 0
    for r, q in np.argwhere((degre == 1) & ~wh1 & (slots < 0) & pres_garde):
        ch = raccord((int(q), int(r)), wh1, passe)
        if not ch:
            continue
        for c0, c1 in zip(ch, ch[1:]):
            k = direction(c0, c1)
            neuf[c0[1], c0[0]] |= 1 << k
            neuf[c1[1], c1[0]] |= 1 << ((k + 3) % 6)
        n_racc += 1
        n_racc_cases += len(ch) - 2
    print(f"  bouts raccordés au réseau de WH1 : {n_racc} ({n_racc_cases} cases de route ajoutées pour cela)")
    n_zz = couper_zigzags(neuf, wh1 | (slots >= 0))
    n_el = elaguer_bouts(neuf, wh1 | (slots >= 0), slots >= 0)
    n_zz += couper_zigzags(neuf, wh1 | (slots >= 0))
    print(f"  BOB n'a pas de tuile pour deux routes côte à côte : zigzags coupés {n_zz}, cases de bouts morts retirées {n_el}")
    n_s, n_c = souder_bouts(neuf, permis, wh1 | (slots >= 0), slots >= 0)
    n_zz2 = couper_zigzags(neuf, wh1 | (slots >= 0))
    print(f"  bouts morts soudés au morceau de réseau voisin : {n_s} ({n_c} cases ajoutées) ; zigzags coupés ensuite {n_zz2}")
    n_dm, n_dc = retirer_doublons(neuf, wh1 | (slots >= 0), slots >= 0)
    n_el2 = elaguer_bouts(neuf, wh1 | (slots >= 0), slots >= 0)
    print(f"  doublons collés à une autre route retirés : {n_dm} morceaux ({n_dc} cases) ; bouts élagués ensuite {n_el2}")
    passe_liaison = passe_route & ~cote & ~(plages > 0)
    faits = relier_morceaux(neuf, passe_liaison, garde, slots >= 0, SUD)
    print(f"  morceaux reliés au grand réseau (accord de Charles du 5.10, WH1 touché au minimum) : {len(faits)} ; "
          + " ; ".join(f"{t} cases reliées par {n} cases neuves dont {g} dans WH1" for t, n, g in faits))
    lab_ = morceaux_reseau(neuf)
    print(f"  morceaux du réseau : {int(lab_.max()) + 1} (Bois Rêveur, à part : voulu, accès par les portails)")
    ajout = (neuf > 0) & ~wh1
    print(f"  routes de l'Atlas : {len(routes)} paires, {sans_trace} sans tracé ; {n_liens} liens posés ({n_branches} branchés sur une route de "
          f"WH1) ; {int(ajout.sum())} cases de route neuves ; {coupees} liens écartés (infranchissable, mer ou WH1 gardé)")
    print(f"  cases de route de WH1 modifiées (branchement) : {int(((neuf != roads) & (roads > 0)).sum())}")
    try:
        from PIL import Image
        img = np.zeros((H, W, 3), np.uint8)
        img[(gt >= 0) & (gt < n_terre)] = (60, 70, 50)
        img[garde] = (70, 70, 95)
        img[wh1] = (200, 180, 120)
        img[ajout] = (255, 120, 40)
        os.makedirs(os.path.dirname(APERCU), exist_ok=True)
        Image.fromarray(img[::-1]).resize((W * 2, H * 2), Image.NEAREST).save(APERCU)
        print(f"  aperçu : {APERCU}")
    except Exception as e:                                              # noqa: BLE001
        print(f"  aperçu impossible : {e}")
    # (4.10.2026 : un réseau soudé, validé « OK » par validate --roads, a bloqué l'export Pathfinding de CAIME) forme du
    # réseau : des fils, comme WH1 (55 carrefours à 3 branches, aucun à 4 ou plus) ; refus d'écrire sinon
    deg = np.zeros((H, W), np.int64)
    for k in range(6):
        deg += (neuf >> k) & 1
    n4 = int((deg >= 4).sum())
    print(f"  forme du réseau : carrefours à 3 branches {int((deg == 3).sum())}, à 4 ou plus {n4}, bouts {int((deg == 1).sum())}")
    f_, c_, t_ = defauts_reseau(neuf)
    f0, c0, t0 = defauts_reseau(roads.astype(np.int64))
    print(f"  nœuds sans tuile de CA (BOB) : formes hors de CA {f_} (avant les routes neuves : {f0}), carrefours voisins "
          f"{c_} ({c0}), routes voisines non reliées {t_} ({t0})")
    np.save(os.path.join(TRAVAIL, "neuf_roads.npy"), neuf)          # contrôle (à blanc compris)
    np.save(os.path.join(TRAVAIL, "base_roads.npy"), roads)
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    # (5.10.2026, fleuves : 1 carrefour à 4 branches DANS LE RÉSEAU DE DÉPART, raccord d'une route de WH1 à un pont posé
    # par creuser_fleuve, en (153, 494)) seuls les carrefours à 4 que NOUS créons arrêtent l'écriture (le blocage de
    # Pathfinding venait d'un réseau soudé de dizaines de carrefours à 4)
    deg0 = np.zeros((H, W), np.int64)
    for k in range(6):
        deg0 += (roads.astype(np.int64) >> k) & 1
    n4_base = int((deg0 >= 4).sum())
    if n4 > n4_base:
        print(f"  !! réseau soudé ({n4 - n4_base} carrefour(s) à 4 branches ou plus ajoutés) : rien d'écrit")
        return 2
    if n4:
        print(f"  carrefours à 4 branches : {n4}, tous dans le réseau de départ (raccords des ponts) : écriture permise")
    os.makedirs(SAUVEGARDES, exist_ok=True)
    sauve = os.path.join(SAUVEGARDES, time.strftime("%Y%m%d-%H%M%S") + "-map.hex-expanded-avant-routes")
    shutil.copy2(V.CARTE_EXP, sauve)
    f = os.path.join(TRAVAIL, "neuf_roads.hex_layer")
    with open(f, "wb") as fh:
        fh.write(encode_flat("Roads", neuf.reshape(-1)))
    p = subprocess.run([V.CAIME, "import-layer", "--map", V.CARTE_EXP, "--layer", "Roads", "--file", f],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "Saved:" in l or "rror" in l))
    p = subprocess.run([V.CAIME, "validate", "--map", V.CARTE_EXP, "--roads"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("\n".join(l for l in (p.stdout + p.stderr).splitlines() if "roads" in l.lower() or "rror" in l))
    print(f"  sauvegarde : {sauve}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
