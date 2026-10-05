#!/usr/bin/env python3
"""planche_expanded.py - une planche titrée des vues d'Expanded pour Charles (3.10.2026) : la carte entière à gauche, les
zones à droite, chacune avec son titre. Lecture seule. Usage : python planche_expanded.py"""
import os

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
A = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded\apercus"
ENTIERE = ("terrain-v11-entier.jpg", "La carte entière (la Saison au centre)")
ZONES = [
    ("terrain-v11-nord-bretonnie-lyonesse.jpg", "Nord : Lyonesse et Couronne"),
    ("terrain-v11-nord-est-reikland.jpg", "Nord-est : vers le Reikland"),
    ("terrain-v11-jonction-grises-voutes.jpg", "Les Grises rejoignent les Voûtes (col Grimhold - Brise-Nuques)"),
    ("terrain-v11-sud-voutes.jpg", "Les Voûtes : vallées boisées, sommets enneigés, déchirure au sud"),
    ("terrain-v11-ouest-cote-atlantique.jpg", "Ouest : la côte atlantique"),
    ("terrain-v11-bois-reveur.jpg", "Le Bois Rêveur dans l'éther"),
]


def titre(im, texte, f):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 44), fill=(24, 20, 16))
    d.text((12, 8), texte, font=f, fill=(238, 222, 188))
    return im


def main():
    f = ImageFont.truetype("georgia.ttf", 26)
    g = Image.open(os.path.join(A, ENTIERE[0])).convert("RGB")
    hg = 2200
    g = g.resize((round(g.width * hg / g.height), hg), Image.LANCZOS)
    cw, ch = 760, 520
    tuiles = []
    for nom, t in ZONES:
        im = Image.open(os.path.join(A, nom)).convert("RGB")
        r = min(cw / im.width, (ch - 44) / im.height)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        c = Image.new("RGB", (cw, ch), (24, 20, 16))
        c.paste(im, ((cw - im.width) // 2, 44 + (ch - 44 - im.height) // 2))
        tuiles.append(titre(c, t, f))
    marge = 16
    largeur = g.width + 2 * cw + 4 * marge
    hauteur = max(hg + 44, 3 * ch + 2 * marge) + 2 * marge + 60
    out = Image.new("RGB", (largeur, hauteur), (24, 20, 16))
    d = ImageDraw.Draw(out)
    d.text((marge, 14), "Saison Expanded : le terrain au 3.10.2026 (vue calculée depuis le projet, pas encore le jeu)",
           font=ImageFont.truetype("georgia.ttf", 34), fill=(245, 228, 190))
    y0 = 70
    c = Image.new("RGB", (g.width, hg + 44), (24, 20, 16))
    c.paste(g, (0, 44))
    out.paste(titre(c, ENTIERE[1][:60], f), (marge, y0))
    for i, t in enumerate(tuiles):
        x = g.width + 2 * marge + (i % 2) * (cw + marge)
        y = y0 + (i // 2) * (ch + marge)
        out.paste(t, (x, y))
    sortie = os.path.join(A, "planche-expanded-20261003.jpg")
    out.save(sortie, quality=88)
    print(sortie, out.size)


if __name__ == "__main__":
    main()
