#!/usr/bin/env python3
"""
vue_de_loin_expanded.py - la carte peinte que WH3 affiche au dézoom maximal, pour Expanded (4.10.2026).

Pourquoi : la zone jouable d'Expanded déclare `campaign_overlay_map` (saison_expanded.dds), `campaign_overlay_lookup`
(saison_expanded_lookup.dds) et `campaign_overlay_map_text` (saison_expanded_text.dds) ; ils manquaient (build_pack :
« texture absente, signalée seulement »). Sans eux, au dézoom, une carte grise (Charles, 23.09.2026, pour la Saison :
erreur réglée par `02-scripts\\vue_de_loin.py`). Même méthode, fonctions de ce module : carte peinte = la carte
stratégique d'Expanded (`images_campagne_expanded.py`, parchemin de l'Atlas, EN pour le pack principal, FR pour la
traduction) en BC7 avec ses mips, côtés complétés à un multiple de 4 ; lookup = les octets du `saison_expanded_lookup.tga`
(R16) ; calque des noms transparent (les noms sont peints), au rapport de la zone jouable.

Sorties : `04-projets\\saison-expanded\\affichage-carte(-en)\\campaign_maps\\saison_expanded_map\\`. Usage : python
vue_de_loin_expanded.py [--apply]
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
import vue_de_loin as V                                                  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CARTE, BASE = "saison_expanded_map", "saison_expanded"
DOSSIERS = {"fr": os.path.join(ICI, "affichage-carte", "campaign_maps", CARTE),
            "en": os.path.join(ICI, "affichage-carte-en", "campaign_maps", CARTE)}
LOOKUP_TGA = os.path.join(ICI, "images-carte", "saison_expanded_lookup.tga")
CALQUE_TEXTE = (624, 1164)                   # rapport de la zone jouable (373,14 × 697,06), côtés multiples de 4


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    w, h, px = V.lire_tga16(LOOKUP_TGA)
    sorties = {}
    lookup = V.dds_r16(w, h, px)
    w_t, h_t = CALQUE_TEXTE
    calque = V.dds_bc7_mips(V.niveaux_mips(np.zeros((h_t, w_t, 4), np.uint8)))
    for langue, d in DOSSIERS.items():
        img = V.multiple_de_4(np.array(Image.open(os.path.join(d, CARTE + ".png")).convert("RGBA")))
        sorties[os.path.join(d, BASE + ".dds")] = V.dds_bc7_mips(V.niveaux_mips(img))
        print(f"  carte peinte ({langue}) : {img.shape[1]} × {img.shape[0]}")
    # lookup et calque : pack principal (EN) ; la traduction ne remplace que la carte peinte
    sorties[os.path.join(DOSSIERS["en"], BASE + "_lookup.dds")] = lookup
    sorties[os.path.join(DOSSIERS["en"], BASE + "_text.dds")] = calque
    print(f"  lookup : {w} × {h} ; calque des noms transparent {w_t} × {h_t}")
    for p, o in sorties.items():
        print(f"  {'écrit' if a.apply else 'à écrire'} : {p} ({len(o) / 1e6:.1f} Mo)")
        if a.apply:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
