#!/usr/bin/env python3
"""
pose_au_sol.py - pose d'un grand objet translaté sur notre relief PAR SON EMPRISE, pas par son pivot (5.10.2026).

Pourquoi (Charles, en jeu, 5.10.2026 : « des montagnes flottantes un peu partout ») : mesure sur le projet du kit
(`scratchpad\\flottants_emprise.py`) : dessous en l'air de plus de 0,4 u pour 327 des 1 043 grands objets du royaume de
Slaanesh (portails, falaises, cornes, jusqu'à 9 u : morceaux d'un sol de CA plus plat que le Bois Rêveur, qui a le relief
de WH1) et 397 des 2 814 de la nature (aiguilles de roche, menhirs sur des pentes). Le pivot était au sol ; le flanc aval
pendait.

Règle : la boîte du modèle (de CA, ou de WH1 pour les modèles que nos packs embarquent : arbres_expanded._boite_ca),
orientée et mise à l'échelle comme l'objet ; sous les 9 points de son DESSOUS (coins, milieux, centre), le sol. L'objet
descend jusqu'à ce que son dessous ne soit nulle part à plus de TOLERANCE_U au-dessus du sol ; refusé si, pour cela, son
dessous s'enfonce de plus de ENFOUI_MAX de sa hauteur sous le sol au point le plus haut (un objet ne s'enterre pas à
moitié dans une pente pour cacher son flanc). Les objets plus bas que HAUT_MIN_U ne sont pas jugés (touffes, décalques).
"""
import math

import numpy as np

TOLERANCE_U = 0.2
ENFOUI_MAX = 0.5
HAUT_MIN_U = 0.8


def matrice_terry(rotation, echelle):
    """M (3 × 3) d'une entité de Terry : rotation (degrés, chaîne ou triplet), échelle ; monde = v · M + pos."""
    if isinstance(rotation, str):
        rotation = [float(v) for v in rotation.split()]
    if isinstance(echelle, str):
        echelle = [float(v) for v in echelle.split()]
    rx, ry, rz = (math.radians(-float(v)) for v in rotation)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    R = (np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
         @ np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]))
    return np.diag(np.asarray(echelle, float)) @ R


def _rot_y(deg):
    a = math.radians(-float(deg))
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def normale(x, z, sol, pas=0.5):
    """Normale du relief en (x, z) (espace de Terry), par différences centrées sur `pas` u."""
    hx = sol(np.array([x + pas, x - pas]), np.array([z, z]))
    hz = sol(np.array([x, x]), np.array([z + pas, z - pas]))
    n = np.array([-(hx[0] - hx[1]) / (2 * pas), 1.0, -(hz[0] - hz[1]) / (2 * pas)])
    return n / np.linalg.norm(n)


def orienter(rotation, echelle, n, part):
    """(rotation, M) : l'objet garde son lacet de départ (y), son axe vertical est penché vers la normale `n` du relief
    sur la fraction `part` (0 : debout, 1 : couché sur la pente). (5.10.2026 : les objets de WH1 étaient penchés pour la
    pente de LEUR place dans WH1 ; recopiés ailleurs, un côté flottait, l'autre s'enterrait)"""
    import royaume_slaanesh
    if isinstance(rotation, str):
        rotation = [float(v) for v in rotation.split()]
    if isinstance(echelle, str):
        echelle = [float(v) for v in echelle.split()]
    up = np.array([0.0, 1.0, 0.0])
    cible = up * (1 - part) + np.asarray(n, float) * part
    cible /= np.linalg.norm(cible)
    axe = np.cross(up, cible)
    s, c = float(np.linalg.norm(axe)), float(np.dot(up, cible))
    if s < 1e-9:
        T = np.eye(3)
    else:
        k = axe / s
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        T = np.eye(3) + K * s + K @ K * (1 - c)              # rotation (colonnes) qui porte up sur cible
    R = _rot_y(rotation[1]) @ T.T                            # lignes : v · R ; lacet puis inclinaison
    M = np.diag(np.asarray(echelle, float)) @ R
    ang, ech = royaume_slaanesh.rotation_terry(M)
    M2 = matrice_terry(ang, ech)
    if np.abs(M2 - M).max() > 1e-3:
        return rotation, matrice_terry(rotation, echelle)  # décomposition douteuse : on garde l'orientation d'origine
    return ang, M2


def ajuster(x, y, z, M, boite, sol, haut_min=HAUT_MIN_U):
    """(y ajusté, verdict) : verdict 'ok', 'abaissé', 'petit', 'sans boîte' ou 'refusé' (alors y = None). `sol(xs, zs)`
    rend le relief sous des positions du monde (tableaux)."""
    if boite is None:
        return y, "sans boîte"
    haut, ecart = ecarts(x, y, z, M, boite, sol)
    if haut < haut_min:
        return y, "petit"
    d = float(ecart.max()) - TOLERANCE_U
    if d <= 0:
        return y, "ok"
    if float((ecart - d).min()) < -ENFOUI_MAX * haut:
        return None, "refusé"
    return y - d, "abaissé"


def ecarts(x, y, z, M, boite, sol):
    """(hauteur verticale de l'objet, écarts du dessous au sol aux 9 points de sa face basse : > 0 en l'air, < 0 enfoui)."""
    lo, hi = np.asarray(boite[0], float), np.asarray(boite[1], float)
    # (5.10.2026, 57 objets du royaume encore en l'air : griffes et barbelés de CA COUCHÉS, dont l'axe y du modèle est
    # horizontal) hauteur = étendue verticale réelle de la boîte tournée ; dessous = la face de l'axe du modèle le plus
    # proche de la verticale du monde
    haut = float(np.sum(np.abs(M[:, 1]) * (hi - lo)))
    ax = int(np.argmax(np.abs(M[:, 1])))
    bas_ax = lo[ax] if M[ax, 1] > 0 else hi[ax]
    autres = [i for i in range(3) if i != ax]
    pts = []
    for a in (lo[autres[0]], (lo[autres[0]] + hi[autres[0]]) / 2, hi[autres[0]]):
        for c in (lo[autres[1]], (lo[autres[1]] + hi[autres[1]]) / 2, hi[autres[1]]):
            p = np.zeros(3)
            p[ax], p[autres[0]], p[autres[1]] = bas_ax, a, c
            pts.append(p)
    w = np.array(pts) @ M
    g = sol(x + w[:, 0], z + w[:, 2])
    return haut, (y + w[:, 1]) - g
