#!/usr/bin/env python3
"""
images_campagne_expanded.py - les images que la ligne de zone jouable d'Expanded déclare et que personne ne produisait
(3.10.2026, question de la Construction à 22 h 13) : la carte stratégique (`map_file` = saison_expanded_map.png) et la
vignette de l'écran Nouvelle campagne (`frontend_image` = ui/frontend UI/campaign_images/saison_expanded.png, et ses
variantes `_button` et `_vertical` que la mise en page de CA accole au nom).

PROVISOIRES, faites de la minicarte parchemin de l'Atlas (`images-carte\\saison_expanded_minimap_en|fr.png`,
`minicarte_parchemin.py`, session « Expanded map avec vaults et détails sud ») : la carte stratégique à la taille de
celle de la Saison (2500 px de large, WH1 : 2500 × 3175), langue par langue comme la Saison (`affichage-carte-en` dans le
pack principal, `affichage-carte` dans la traduction) ; la vignette aux tailles de celle de la Saison (1600 × 900,
278 × 128, 380 × 735), cadrée sur la Bretonnie. À remplacer par de vraies images quand la session de la minicarte ou
celle des illustrations en fera.

Sorties : `04-projets\\saison-expanded\\affichage-carte(-en)\\campaign_maps\\saison_expanded_map\\saison_expanded_map.png`,
`04-projets\\saison-expanded\\images-campagne\\saison_expanded(_button|_vertical).png`. Usage : python
images_campagne_expanded.py
"""
import os
import sys

from PIL import Image

ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded"
MINI = os.path.join(ICI, "images-carte", "saison_expanded_minimap_{}.png")
CARTE = "saison_expanded_map"
LARGEUR_CARTE = 2500
# vignette : (nom, taille, centre relatif (x, y) du cadrage dans la minicarte : la Bretonnie, au nord de la Saison)
VIGNETTES = [("saison_expanded.png", (1600, 900), (0.42, 0.40)),
             ("saison_expanded_button.png", (278, 128), (0.42, 0.40)),
             ("saison_expanded_vertical.png", (380, 735), (0.45, 0.45))]


def cadrer(im, taille, centre):
    """Recadre `im` au rapport de `taille` autour de `centre` (relatif), au plus large possible, puis redimensionne."""
    w, h = im.size
    tw, th = taille
    r = tw / th
    cw, ch = (w, w / r) if w / r <= h else (h * r, h)
    cw, ch = cw * 0.8, ch * 0.8
    x0 = min(max(centre[0] * w - cw / 2, 0), w - cw)
    y0 = min(max(centre[1] * h - ch / 2, 0), h - ch)
    return im.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize(taille, Image.LANCZOS)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for langue, dossier in (("en", "affichage-carte-en"), ("fr", "affichage-carte")):
        im = Image.open(MINI.format(langue)).convert("RGB")
        g = im.resize((LARGEUR_CARTE, round(im.height * LARGEUR_CARTE / im.width)), Image.LANCZOS)
        d = os.path.join(ICI, dossier, "campaign_maps", CARTE)
        os.makedirs(d, exist_ok=True)
        g.save(os.path.join(d, CARTE + ".png"))
        print(f"  carte stratégique ({langue}) : {g.size} -> {d}")
    im = Image.open(MINI.format("en")).convert("RGB")
    d = os.path.join(ICI, "images-campagne")
    os.makedirs(d, exist_ok=True)
    for nom, taille, centre in VIGNETTES:
        cadrer(im, taille, centre).save(os.path.join(d, nom))
        print(f"  vignette {nom} {taille}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
