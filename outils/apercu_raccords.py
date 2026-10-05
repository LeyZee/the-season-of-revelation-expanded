#!/usr/bin/env python3
"""apercu_raccords.py - gros plans des RACCORDS entre la carte de WH1 (cadre colonnes 120-519, rangées 330-769) et
l'Atlas, sur le terrain compilé (même rendu que apercu_compile_expanded : textures que le jeu lira, arbres, neige,
ombrage, mer), à 6 px par hex ; à côté, le même gros plan avec le tracé du cadre en pointillés rouges pour situer la
couture. Lecture seule. Usage : python apercu_raccords.py"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apercu_compile_expanded as A                                     # noqa: E402
from cadre_expanded import H, DX, DY, SW, SH                            # noqa: E402

RACCORDS = {
    "raccord-nord-gisoreux": (180, 340, 720, 820),
    "raccord-nord-est-parravon": (400, 560, 690, 800),
    "raccord-ouest-bidouze": (60, 200, 470, 640),
    "raccord-est-grises": (460, 560, 420, 600),
    "raccord-sud-voutes": (260, 420, 280, 380),
    "raccord-sud-ouest-arden": (90, 260, 300, 420),
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    A.ZONES = RACCORDS
    sys.argv = [sys.argv[0], "--suffixe", "raccords"]
    A.main()
    px = 4
    for nom, (q0, q1, r0, r1) in RACCORDS.items():
        p = os.path.join(A.ICI, "apercus", f"compile-raccords-{nom}.jpg")
        im = Image.open(p).convert("RGB")
        trace = im.copy()
        d = ImageDraw.Draw(trace)
        x0, x1 = (DX - q0) * px, (DX + SW - q0) * px
        y0, y1 = (r1 - (DY + SH)) * px, (r1 - DY) * px
        for i in range(0, max(im.width, im.height), 12):
            for (a, b, c, e) in ((x0 + i, y0, x0 + i + 6, y0), (x0 + i, y1, x0 + i + 6, y1),
                                 (x0, y0 + i, x0, y0 + i + 6), (x1, y0 + i, x1, y0 + i + 6)):
                d.line((a, b, c, e), fill=(220, 30, 30), width=2)
        planche = Image.new("RGB", (im.width * 2 + 10, im.height), (24, 20, 16))
        planche.paste(im, (0, 0))
        planche.paste(trace, (im.width + 10, 0))
        planche.save(p, quality=90)
        print(" ", p)


if __name__ == "__main__":
    main()
