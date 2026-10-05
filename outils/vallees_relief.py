#!/usr/bin/env python3
"""
vallees_relief.py - les FONDS DE VALLÉE franchissables de l'extension (5.10.2026) ; appelé par `projet_expanded`.

Pourquoi (Charles, 5.10.2026 : « les passages entre les montagnes doivent vraiment être naturels, vraiment rendre bien, ne
pas bloquer les armées… même si c'est très mineur ») : audit (`scratchpad\\audit_montagnes.py`) : dans la zone de WH1, un
hex franchissable a au plus 0,61 u de dénivelé intérieur (p99) ; dans l'extension, 4 275 hex franchissables le dépassent
(longs traits au pied des massifs, cols des Voûtes et des Grises de l'Atlas) : l'armée marche sur un versant, le col est
une tranchée.

Règle (à la manière de WH1 : la montagne commence où la grille dit infranchissable) : sur la terre franchissable de
l'extension (masque lissé, sans angle d'hex), le relief ne dépasse pas le FOND DE VALLÉE local (moyenne floutée du relief
de cette seule terre, sur FOND_HEX) de plus de MARGE_U ; fondu depuis le bord de la terre franchissable sur BORD_HEX
(la montée vers les sommets se fait sur l'infranchissable). Ne fait que descendre. Jamais dans la zone de WH1 gardée, sous
ses montagnes, dans le Bois Rêveur. Rend la différence (objets et rubans la suivent).
"""
import cv2
import numpy as np

FOND_HEX = 1.5
MARGE_U = 0.3
BORD_HEX = 0.6
LISSE_HEX = 0.5


def _lisse(m, s):
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), s)


def aplanir(height, passe_px, hors, px_hex=8.0):
    """(height, delta, bilan) ; `passe_px` : terre franchissable de l'extension (pixels, nord en haut) ; `hors` : jamais."""
    p = _lisse(passe_px & ~hors, LISSE_HEX * px_hex) > 0.5
    d = cv2.distanceTransform(p.astype(np.uint8), cv2.DIST_L2, 5) / px_hex          # hex depuis le bord, vers l'intérieur
    w = np.clip(d / BORD_HEX, 0, 1)
    w = w * w * (3 - 2 * w)
    poids = _lisse(p, FOND_HEX * px_hex)
    fond = _lisse(np.where(p, height, 0), FOND_HEX * px_hex) / np.maximum(poids, 1e-3)
    cible = np.minimum(height, fond + MARGE_U)
    avant = height.copy()
    height = np.where(p, height * (1 - w) + cible * w, height).astype(np.float32)
    delta = (height - avant).astype(np.float32)
    return height, delta, {"terre_franchissable_px": int(p.sum()), "abaissee_px": int((delta < -0.01).sum()),
                           "abaissement_max_u": float(-delta.min())}
