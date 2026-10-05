#!/usr/bin/env python3
"""
controle_anomalies.py - chasse aux bizarreries du terrain d'Expanded, sur le projet du bac à sable (4.10.2026).

Charles : « continue à faire du peaufinage… qu'il n'y ait pas de bugs, anomalies ou bizarreries ». Contrôles, en
lecture seule, avec un compte et les premières positions (colonne, rangée de la grille, rangée 0 au sud) :
1. MARCHES : saut de relief entre deux pixels voisins plus fort que SAUT_MAX (u), hors falaises de WH1 gardées ;
2. LIGNES DROITES : le long des quatre bords du cadre de WH1, rupture de pente concentrée sur la ligne (moyenne de la
   dérivée seconde du relief sur la ligne même, comparée aux lignes voisines) ;
3. ÎLOTS ET TROUS : terre de moins de ILOT_MIN px isolée dans la mer, mer de moins de ILOT_MIN px isolée dans la terre
   (hors lacs de WH1) ;
4. ARBRES DANS L'EAU : arbres de la liste finale posés sous le niveau de la mer ou dans l'eau des rivières de l'Atlas ;
5. OBJETS DANS L'EAU OU EN L'AIR : objets des abords des villes sous l'eau ;
6. EAU QUI FLOTTE : eau des rivières de l'Atlas au-dessus du sol voisin hors du lit (bord du maillage au-dessus de la
   berge) ;
7. NEIGE BASSE : neige au-dessous de NEIGE_ALT_MIN.
Usage : python controle_anomalies.py
"""
import glob
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image

os.environ.setdefault("SAISON_CARTE", "expanded")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, DX, DY, SW, SH, ipx_de                  # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
Image.MAX_IMAGE_PIXELS = None
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
TERRY = os.path.join(ICI, r"terry\saison_expanded_map")
F = 8
UX, UZ = 266.53 / 400, 338.9 / 440
SAUT_MAX = 0.6
ILOT_MIN = 40
NEIGE_ALT_MIN = 6.0


def lire(nom):
    return np.asarray(Image.open(glob.glob(os.path.join(TERRY, f"*.{nom}.*.tif"))[0]))


def case(y, x, reste):
    return int(x // F), int(H - 1 - (y - 0) // F) if y < H * F else 0


def positions(m, reste, n=6):
    ys, xs = np.nonzero(m)
    if not len(ys):
        return []
    i = np.linspace(0, len(ys) - 1, min(n, len(ys))).astype(int)
    return [(int(xs[k] // F), int(H - 1 - ys[k] // F)) for k in i]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    h = lire("height").astype(np.float32)
    reste = h.shape[0] - H * F
    import projet_expanded as P
    garde = P.garde_masque(F, reste)
    # (5.10.2026) la mer = les tuiles de mer (le relief y est continu avec la côte, comme CA : cotes_relief, mer_tuiles)
    import mer_tuiles
    mer = mer_tuiles.mer_px(h.shape) | (h <= 0.035)
    bilan = {}
    # 1. marches
    dy = np.abs(np.diff(h, axis=0))
    dx = np.abs(np.diff(h, axis=1))
    saut = np.zeros_like(h, bool)
    saut[:-1] |= dy > SAUT_MAX
    saut[:, :-1] |= dx > SAUT_MAX
    saut &= ~garde
    bilan["1. marches de relief (> %.1f u entre pixels, hors WH1 gardé)" % SAUT_MAX] = (int(saut.sum()), positions(saut, reste))
    # 2. lignes droites au bord du cadre
    lisse = cv2.GaussianBlur(h, (0, 0), 1.0)
    lap = np.abs(cv2.Laplacian(lisse, cv2.CV_32F))
    y0, x0 = (H - (DY + SH)) * F, DX * F
    y1, x1 = (H - DY) * F, (DX + SW) * F
    lignes = []
    for nom, prof, sel in (("nord", lap[y0, x0:x1], lap[y0 - 6:y0 + 7, x0:x1]),
                           ("sud", lap[y1 - 1, x0:x1], lap[y1 - 7:y1 + 6, x0:x1]),
                           ("ouest", lap[y0:y1, x0], lap[y0:y1, x0 - 6:x0 + 7].T),
                           ("est", lap[y0:y1, x1 - 1], lap[y0:y1, x1 - 7:x1 + 6].T)):
        ratio = float(np.mean(prof) / max(np.mean(sel), 1e-6))
        lignes.append(f"{nom} {ratio:.2f}")
    bilan["2. rupture de pente SUR la ligne du cadre / autour (1 = rien de visible, > 1,5 = trait)"] = (", ".join(lignes), [])
    # 3. îlots et trous
    for nom, m in (("terre isolée dans la mer", ~mer), ("mer isolée dans la terre", mer)):
        n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
        petits = [i for i in range(1, n) if st[i][4] < ILOT_MIN]
        mm = np.isin(lab, petits)
        bilan[f"3. {nom} (< {ILOT_MIN} px)"] = (len(petits), positions(mm, reste))
    # 4. arbres dans l'eau
    import arbres_wh1 as A
    _, gs = A.lire_liste(open(os.path.join(ICI, r"arbres-wh1\trees.campaign_tree_list"), "rb").read())
    pas = F / UX
    import rivieres_atlas_eau as RE
    ch, _ = RE.champ_et_niveau(h)
    eau_riv = ch >= 0.3
    noye, riv = [], []
    for nom, recs in gs:
        xyz = recs[:, :12].copy().view("<f4").reshape(-1, 3)
        xs, ys = ipx_de(xyz[:, 0], xyz[:, 2], h.shape)
        noye += [(int(x // F), int(H - 1 - y // F)) for x, y in zip(xs, ys) if mer[y, x]]
        riv += [(int(x // F), int(H - 1 - y // F)) for x, y in zip(xs, ys) if eau_riv[y, x]]
    bilan["4a. arbres dans la mer"] = (len(noye), noye[:6])
    bilan["4b. arbres dans l'eau des rivières de l'Atlas"] = (len(riv), riv[:6])
    # 5. objets des abords sous l'eau
    sous = []
    for f in glob.glob(os.path.join(TERRY, "*.layer")):
        t = open(f, encoding="utf-8", errors="replace").read()
        if "<!-- abords_villes -->" not in t:
            continue
        for x, y, z in re.findall(r'<ECTransform position="([-0-9.eE]+) ([-0-9.eE]+) ([-0-9.eE]+)"', t):
            px_, py_ = (int(v) for v in ipx_de(float(x), float(z), h.shape))
            if mer[py_, px_]:
                sous.append((px_ // F, H - 1 - py_ // F))
    bilan["5. objets des abords des villes dans la mer"] = (len(sous), sous[:6])
    # 6. eau qui flotte : niveau de l'eau des rivières de l'Atlas au-dessus du sol au bord du maillage
    # l'eau pend si, juste HORS du maillage, le sol est plus bas que l'eau voisine (bord en l'air)
    _, niv = RE.champ_et_niveau(h)
    dedans = (ch >= 0.25) & np.isfinite(niv)
    niv_v = cv2.dilate(np.where(dedans, niv, -99.0).astype(np.float32), np.ones((3, 3), np.uint8))
    dehors = ~dedans & (cv2.dilate(dedans.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    flotte = dehors & (niv_v > h + 0.03) & (h > 0.035)
    bilan["6. bord d'eau de rivière en l'air (sol hors du maillage > 3 cm sous l'eau voisine)"] = (int(flotte.sum()),
                                                                                                  positions(flotte, reste))
    # 7. neige basse
    sn = lire("snow_mask")
    hs = cv2.resize(h, (sn.shape[1], sn.shape[0]), interpolation=cv2.INTER_AREA)
    basse = (sn > 128) & (hs < NEIGE_ALT_MIN)
    bilan[f"7. neige sous {NEIGE_ALT_MIN} u (px du masque)"] = (int(basse.sum()), [])
    for k, (n, pos) in bilan.items():
        print(f"  {k} : {n}" + (f" ; ex. {pos}" if pos else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
