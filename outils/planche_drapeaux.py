#!/usr/bin/env python3
"""planche_drapeaux.py - planche des drapeaux de jeu des 16 factions de l'Atlas (factions_atlas.py --drapeaux), pour
Charles, et contrôle du format DDS de mon_banner contre celui de CA. Lecture seule. Usage : python planche_drapeaux.py"""
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import factions_atlas as FA                                              # noqa: E402

sys.path.insert(0, os.path.join(FA.ATELIER, "02-scripts"))
from contenu_pack import SourcePacks                                     # noqa: E402


def entete(b):
    four = b[84:88]
    dxgi = struct.unpack("<I", b[128:132])[0] if four == b"DX10" else None
    return four, dxgi, struct.unpack("<II", b[12:20])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ca = SourcePacks(FA.DATA).lire("ui/flags/wh_main_dwf_karak_ziflin/mon_banner.dds")
    print("CA mon_banner :", entete(ca), len(ca))
    f = ImageFont.truetype("georgia.ttf", 18)
    cles = list(FA.FACTIONS)
    cw, ch = 300, 330
    out = Image.new("RGB", (cw * 4, ch * 4 + 60), (24, 20, 16))
    d = ImageDraw.Draw(out)
    d.text((14, 14), "Les 16 factions de l'Atlas : drapeaux de jeu (256, 64, 24 px et petite bannière inclinée)",
           font=ImageFont.truetype("georgia.ttf", 26), fill=(245, 228, 190))
    for i, cle in enumerate(cles):
        dd = os.path.join(FA.SORTIE_DRAPEAUX, "ui", "flags", cle)
        b = open(os.path.join(dd, "mon_banner.dds"), "rb").read()
        if i == 0:
            print("nous mon_banner :", entete(b), len(b))
        x, y = (i % 4) * cw, 60 + (i // 4) * ch
        g = Image.open(os.path.join(dd, "mon_256.png")).convert("RGBA").resize((200, 200))
        out.paste(g, (x + 10, y + 10), g)
        for k, (n, s) in enumerate((("mon_64.png", 64), ("mon_24.png", 24))):
            im = Image.open(os.path.join(dd, n)).convert("RGBA")
            out.paste(im, (x + 220, y + 10 + k * 80), im)
        r = Image.open(os.path.join(dd, "mon_rotated.png")).convert("RGBA")
        out.paste(r, (x + 180, y + 215), r)
        d.text((x + 10, y + 300), FA.FACTIONS[cle][2][:30], font=f, fill=(238, 222, 188))
    p = os.path.join(FA.ICI, "apercus", "drapeaux-factions-atlas.jpg")
    out.save(p, quality=90)
    print(p)


if __name__ == "__main__":
    main()
