#!/usr/bin/env python3
"""
decors_expanded.py - les décors 3D de la vie autour des villes neuves d'Expanded (3.10.2026), appelé par
`projet_expanded.py`.

Pourquoi (Charles : « qu'il y ait de la vie sur cette map… que rien ne soit laissé au hasard ») : les villes neuves de
l'Atlas n'avaient autour d'elles aucun objet. Autour des villes bretonnes de WH1, la Saison a ses fermes, cultures,
clôtures, potagers, chemins boueux, sons d'ambiance, et les décors que le jeu n'affiche que selon l'état de la région
(traces de pillage, tertres de crânes, tombes, tumeurs du Chaos : drapeaux `visible_inside_destruction_region`…).

Ce que fait le module : pour chaque ville neuve d'un peuple qui cultive, les objets à moins de RAYON hex de SA ville
modèle de WH1 (la même que pour les textures, `habillage_expanded._abords`) sont recopiés, déplacés de la ville modèle à
la ville neuve, posés à la hauteur du nouveau terrain (même écart au sol que dans WH1) ; écartés : ce qui tomberait dans
l'eau ou sur une pente raide (> PENTE_MAX u par hex), et les polygones (eau, sons de zone). Identifiants neufs, stables.
"""
import glob
import hashlib
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, SW, SH, DX, DY                         # noqa: E402
import habillage_expanded                                                # noqa: E402

UX, UZ = 266.53 / 400, 338.9 / 440
RAYON = 7.0
PENTE_MAX = 1.4
ENT = re.compile(r'[ \t]*<entity id="[^"]*">.*?</entity>[ \t]*\r?\n', re.S)
POS = re.compile(r'(<ECTransform position=")([-0-9.eE]+) ([-0-9.eE]+) ([-0-9.eE]+)(")')


def hauteur(h, x, z, sh_hex):
    """Hauteur du raster `h` (nord en haut, étiré sur le monde de la carte : `sh_hex`·UZ de haut) au point du monde (x, z).
    (4.10.2026 : avant, (sh_hex − z/UZ)·8, jusqu'à 3 px d'écart au nord d'Expanded ; cadre_expanded.px_de)"""
    cols_hex = W if sh_hex == H else SW
    px = int(np.clip(round(x * h.shape[1] / (cols_hex * UX) - 0.5), 0, h.shape[1] - 1))
    py = int(np.clip(round((sh_hex * UZ - z) * h.shape[0] / (sh_hex * UZ) - 0.5), 0, h.shape[0] - 1))
    return float(h[py, px])


def pente(h, x, z, sh_hex):
    d = 0.5
    a = [hauteur(h, x + dx * UX, z + dz * UZ, sh_hex) for dx, dz in ((d, 0), (-d, 0), (0, d), (0, -d))]
    return max(abs(a[0] - a[1]), abs(a[2] - a[3])) / (2 * d)


def copier(src_dir, h_s, h_e):
    """Texte d'un calque `abords_villes` : les objets des abords des villes de WH1, recopiés autour des villes neuves."""
    objets = []
    for p in glob.glob(os.path.join(src_dir, "*.layer")):
        for e in ENT.findall(open(p, encoding="utf-8").read()):
            if "<ECPolyline" in e or "<ECPolygonMesh" in e:
                continue
            # (5.10.2026, Charles en jeu : « deux montagnes tout au nord de la Bretonnie qui n'ont rien à faire ici ») les
            # maillages de TERRAIN de WH1 (montagnes, falaises intérieures, ancres : `_wh1/campaign/montagnes`, drapés d'avance
            # sur le relief de LEUR place) ne se recopient pas : 31 posés autour des villes neuves (2 montagnes au nord, en
            # (232, 830) et (286, 804), 26 pans de falaise, 3 ancres), flottants ou enterrés
            if "_wh1/campaign/montagnes" in e:
                continue
            m = POS.search(e)
            if m:
                objets.append((float(m.group(2)), float(m.group(3)), float(m.group(4)), e))
    xs = np.array([o[0] for o in objets])
    zs = np.array([o[2] for o in objets])
    import mer_tuiles
    mer_px_e = cv2.dilate(mer_tuiles.mer_px(h_e.shape).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    sortie, n_pose, n_ecarte = [], 0, 0
    for k, ((rn, qn), (rs, qs)) in enumerate(habillage_expanded._abords()):
        # centres (monde) : ville modèle dans la Saison, ville neuve dans Expanded (rangées nord en haut -> depuis le sud)
        cxs, czs = (qs + 0.5) * UX, (SH - 1 - rs + 0.5) * UZ
        cxn, czn = (qn + 0.5) * UX, (H - 1 - rn + 0.5) * UZ
        proche = np.hypot((xs - cxs) / UX, (zs - czs) / UZ) < RAYON
        for i in np.flatnonzero(proche):
            x, y, z, e = objets[i]
            xn, zn = x - cxs + cxn, z - czs + czn
            sol_s = hauteur(h_s, x, z, SH)
            sol_n = hauteur(h_e, xn, zn, H)
            # (4.10.2026, controle_anomalies : 14 objets dans la mer) : le sol au point ET à un demi-hex autour, au-dessus
            # de la mer avec une marge
            autour = min(hauteur(h_e, xn + dx * UX, zn + dz * UZ, H)
                         for dx, dz in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)))
            # (5.10.2026) ni sur une tuile de mer (relief continu sous l'eau, cotes_relief : le relief seul ne suffit plus)
            mp = mer_px_e[min(max(int(round((H * UZ - zn) * h_e.shape[0] / (H * UZ) - 0.5)), 0), h_e.shape[0] - 1),
                          min(max(int(round(xn * h_e.shape[1] / (W * UX) - 0.5)), 0), h_e.shape[1] - 1)]
            if sol_n < 0.1 or autour < 0.06 or mp or pente(h_e, xn, zn, H) > PENTE_MAX:
                n_ecarte += 1
                continue
            yn = sol_n + (y - sol_s)
            nid = "1" + hashlib.sha1(f"abords/{k}/{i}".encode()).hexdigest()[:14]
            e2 = re.sub(r'<entity id="[^"]*">', f'<entity id="{nid}">', e, count=1)
            e2 = POS.sub(lambda m_: f"{m_.group(1)}{xn:.5f} {yn:.5f} {zn:.5f}{m_.group(5)}", e2, count=1)
            sortie.append(e2 if e2.endswith("\n") else e2 + "\n")
            n_pose += 1
    print(f"  abords des villes : {n_pose} objets de WH1 recopiés autour de {len(habillage_expanded._abords())} villes "
          f"neuves ; {n_ecarte} écartés (eau, pente)")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- abords_villes -->\n<layer version="41">\n\t<entities>\n'
            + "".join(sortie) + "\t</entities>\n\t<associations>\n\t\t<Logical/>\n\t\t<Transform/>\n\t</associations>\n"
            "</layer>\n")


def calques_regions(dst, cle, regions, renommer):
    """(Guide Terry : « le projet est lié à la liste des régions : une région de plus, c'est un File Layer de plus ») : un
    calque vide pour chaque région de la carte qui n'en a pas ; `renommer` {ancienne clé: nouvelle} pour une région de
    WH1 remplacée dans Expanded (Fort Solstice -> sa reprise)."""
    terry_p = os.path.join(dst, f"{cle}.terry")
    t = open(terry_p, encoding="utf-8").read()
    for a, b in renommer.items():
        t = t.replace(f'name="{a}"', f'name="{b}"')
    vide = ('<?xml version="1.0" encoding="UTF-8"?>\n<layer version="41">\n\t<entities>\n\t</entities>\n'
            "\t<associations>\n\t\t<Logical/>\n\t\t<Transform/>\n\t</associations>\n</layer>\n")
    ajoutes = 0
    for n in regions:
        if f'name="{n}"' in t:
            continue
        i = "1" + hashlib.sha1(f"saison_expanded/region/{n}".encode()).hexdigest()[:14]
        with open(os.path.join(dst, f"{cle}.{i}.layer"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(vide)
        t = t.replace("    </data>\n  </pc>", f'      <entity id="{i}" name="{n}">\n        <ECFileLayer export="true" '
                      f'bmd_export_type=""/>\n      </entity>\n    </data>\n  </pc>', 1)
        ajoutes += 1
    open(terry_p, "w", encoding="utf-8", newline="\n").write(t)
    print(f"  calques de régions : {ajoutes} ajoutés (vides) ; renommés : {renommer}")


def declarer(dst, cle, nom, texte):
    """Écrit le calque `nom` dans le projet et le déclare dans le `.terry` (comme eau_expanded)."""
    i = "1" + hashlib.sha1(f"saison_expanded/{nom}/calque".encode()).hexdigest()[:14]
    with open(os.path.join(dst, f"{cle}.{i}.layer"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texte)
    terry_p = os.path.join(dst, f"{cle}.terry")
    t = open(terry_p, encoding="utf-8").read()
    if f'name="{nom}"' not in t:
        t = t.replace("    </data>\n  </pc>", f'      <entity id="{i}" name="{nom}">\n        <ECFileLayer export="true" '
                      f'bmd_export_type=""/>\n      </entity>\n    </data>\n  </pc>', 1)
        open(terry_p, "w", encoding="utf-8", newline="\n").write(t)
