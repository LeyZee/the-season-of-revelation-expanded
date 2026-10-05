#!/usr/bin/env python3
"""
cotes_expanded.py - le trait de côte d'Expanded à l'échelle de l'hex, avant la pose des villes (appelé par
`villes_expanded.py`, étape 0 bis ; seul, il ne fait que mesurer).

Pourquoi (3.10.2026, validation CAIME de la grille au cadre 560 × 905 ; Charles : « que les côtes rentrent bien ») : la
carte de la Saison n'a AUCUN avertissement de côte ; celle d'Expanded en avait ~700, tous hors de la Saison :
- des langues de terre d'un hex (une case de terre qui touche 4, 5 ou 6 cases de mer) et des cases de mer enfermées dans
  la terre : la côte de l'Atlas, dessinée au trait, tombe en dents de scie sur la grille ; le reflet d'Athel Loren fait de
  sa lisière (terre contre terre dans WH1) une côte contre l'éther, tout aussi dentelée ;
- 262 cases de mer dans des régions de terre (lacs de l'Atlas sur la bordure de WH1, bords de l'Île Silencieuse…).
Le jeu en tire des côtes en escalier et des débarquements absurdes ; le relief de Terry suit cette grille.

Règles (comme un lissage majoritaire, jusqu'à stabilité) :
1. une case de terre qui touche au moins SEUIL cases de mer devient mer, une case de mer qui touche au moins SEUIL
   cases de terre devient terre ; la case prend la région, le sol et le climat les plus fréquents chez ses voisins de son
   nouveau côté ;
2. une case de mer dans une région de terre passe à la région de mer voisine la plus fréquente (sinon la mer sauvage) ;
   une case de terre dans une région de mer, à la région de terre voisine (sinon la terre sauvage) ;
3. rivières effacées en mer ; plages effacées hors de la terre côtière.
Jamais touchés : les régions de WH1 dans son cadre (WH1 à 100 %), le voile, et toute région nommée qui perdrait plus de
PERTE_MAX de ses cases (les îles restent des îles).
"""
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, DX, DY, SW, SH                       # noqa: E402

SEUIL = 4
PERTE_MAX = 0.15
DIRS = (
    ((0, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0)),
    ((0, 1), (1, 1), (1, 0), (0, -1), (-1, 0), (-1, 1)),
)


def voisins(a, hors=-9):
    """(6, H, W) : la valeur de chacun des six voisins (hors de la carte : `hors`)."""
    out = np.full((6,) + a.shape, hors, a.dtype)
    q = np.arange(W)[None, :].repeat(H, 0)
    r = np.arange(H)[:, None].repeat(W, 1)
    for k in range(6):
        for par in (0, 1):
            dq, dr = DIRS[par][k]
            m = (q % 2 == par)
            nq, nr = q + dq, r + dr
            ok = m & (nq >= 0) & (nq < W) & (nr >= 0) & (nr < H)
            out[k][ok] = a[nr[ok], nq[ok]]
    return out


def majorite(vois, choix, defaut):
    """Valeur la plus fréquente de `vois` (6 valeurs) parmi celles où `choix` est vrai ; sinon `defaut`."""
    c = Counter(int(v) for v, ok in zip(vois, choix) if ok and v >= 0)
    return c.most_common(1)[0][0] if c else defaut


def lisser(reg, sol, climat, rivieres, plages, n_sols_terre, regions_mer, i_terre_sauvage, i_mer_sauvage, protege,
           log=print):
    """Lisse le trait de côte. Tableaux (H, W), ligne 0 = sud ; modifiés en place. Rend un bilan (dict)."""
    taille0 = np.bincount(reg[reg >= 0], minlength=int(reg.max()) + 1)
    est_mer_reg = np.zeros(int(reg.max()) + 2, bool)
    est_mer_reg[list(regions_mer)] = True
    nommee = np.ones_like(est_mer_reg)
    nommee[[i_terre_sauvage, i_mer_sauvage]] = False
    bilan = Counter()
    for tour in range(12):
        changes = 0
        for vers_mer in (True, False):
            terre = (sol >= 0) & (sol < n_sols_terre)
            v_terre = voisins(terre.astype(np.int8), -1)
            n_mer = (v_terre == 0).sum(0)
            n_terre = (v_terre == 1).sum(0)
            cand = (terre & (n_mer >= SEUIL)) if vers_mer else ((~terre) & (sol >= 0) & (n_terre >= SEUIL))
            cand &= ~protege
            if not cand.any():
                continue
            v_reg, v_sol, v_cli = voisins(reg), voisins(sol), voisins(climat)
            taille = np.bincount(reg[reg >= 0], minlength=len(taille0))
            for r, q in np.argwhere(cand):
                cote = (v_terre[:, r, q] == 0) if vers_mer else (v_terre[:, r, q] == 1)
                ancien = int(reg[r, q])
                if vers_mer and ancien >= 0 and nommee[ancien] and not est_mer_reg[ancien] and \
                        taille[ancien] - 1 < (1 - PERTE_MAX) * taille0[ancien]:
                    bilan["gardées (île ou région nommée)"] += 1
                    continue
                reg[r, q] = majorite(v_reg[:, r, q], cote, i_mer_sauvage if vers_mer else i_terre_sauvage)
                sol[r, q] = majorite(v_sol[:, r, q], cote, sol[r, q])
                climat[r, q] = majorite(v_cli[:, r, q], cote, climat[r, q])
                if ancien >= 0:
                    taille[ancien] -= 1
                bilan["terre -> mer" if vers_mer else "mer -> terre"] += 1
                changes += 1
        if not changes:
            break
    # 2. régions en accord avec le sol
    terre = (sol >= 0) & (sol < n_sols_terre)
    v_reg = voisins(reg)
    v_terre = voisins(terre.astype(np.int8), -1)
    mauvais = ((~terre) & (sol >= 0) & (reg >= 0) & ~est_mer_reg[np.clip(reg, 0, None)]) | \
              (terre & (reg >= 0) & est_mer_reg[np.clip(reg, 0, None)])
    mauvais &= ~protege
    for r, q in np.argwhere(mauvais):
        mer = not terre[r, q]
        bons = [(v >= 0) and (est_mer_reg[v] == mer) for v in v_reg[:, r, q]]
        reg[r, q] = majorite(v_reg[:, r, q], bons, i_mer_sauvage if mer else i_terre_sauvage)
        bilan["région remise d'accord avec le sol"] += 1
    # 3. rivières et plages
    terre = (sol >= 0) & (sol < n_sols_terre)
    n_mer = (voisins(terre.astype(np.int8), -1) == 0).sum(0)
    bilan["rivières effacées en mer"] = int(((rivieres > 0) & ~terre).sum())
    rivieres[~terre] = 0
    pl = (plages > 0) & ~(terre & (n_mer > 0))
    bilan["plages effacées"] = int(pl.sum())
    plages[pl] = 0
    taille = np.bincount(reg[reg >= 0], minlength=len(taille0))
    perdues = [i for i in range(len(taille0)) if taille0[i] and not taille[i]]
    bilan["régions vidées"] = len(perdues)
    log("  côtes : " + ", ".join(f"{k} {v}" for k, v in bilan.items()))
    return bilan, perdues


def protege_wh1(reg_saison_dans_cadre, sauvages_saison):
    """Les régions de WH1 dans leur cadre (hors terre et mer sauvages) : jamais touchées."""
    p = np.zeros((H, W), bool)
    p[DY:DY + SH, DX:DX + SW] = (reg_saison_dans_cadre >= 0) & ~np.isin(reg_saison_dans_cadre, sauvages_saison)
    return p
