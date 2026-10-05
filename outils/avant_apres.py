#!/usr/bin/env python3
"""avant_apres.py - deux aperçus côte à côte, titrés (pour montrer une étape à Charles). Lecture seule.

Usage : python avant_apres.py <avant.jpg> <après.jpg> <sortie.jpg> "<titre avant>" "<titre après>"
"""
import sys

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None


def main():
    a, b, sortie, ta, tb = sys.argv[1:6]
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    h = min(ia.height, ib.height, 1400)
    ia = ia.resize((round(ia.width * h / ia.height), h), Image.LANCZOS)
    ib = ib.resize((round(ib.width * h / ib.height), h), Image.LANCZOS)
    marge, bandeau = 16, 56
    out = Image.new("RGB", (ia.width + ib.width + 3 * marge, h + bandeau + marge), (28, 24, 20))
    out.paste(ia, (marge, bandeau))
    out.paste(ib, (2 * marge + ia.width, bandeau))
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype("georgia.ttf", 30)
    d.text((marge, 12), ta, font=f, fill=(235, 220, 190))
    d.text((2 * marge + ia.width, 12), tb, font=f, fill=(235, 220, 190))
    out.save(sortie, quality=90)
    print(sortie, out.size)


if __name__ == "__main__":
    main()
