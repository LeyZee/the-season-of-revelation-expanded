#!/usr/bin/env python3
"""
vie_expanded.py - la VIE d'Expanded : animaux, créatures et effets de CA, selon le lore de chaque région (4.10.2026),
appelé par `projet_expanded.py` (calque `vie_expanded`) ; seul, il fait un essai à blanc.

Pourquoi (Charles, 4.10.2026) : « ajouter des animaux, des créatures magiques, en lien avec le lore… de la vie par-ci
par-là, comme ce qu'on avait fait avec la Saison des Révélations ». Même recette que la Saison (`02-scripts\\vie_carte_wh3.py`,
rapport `05-journal\\2026-09-23-rendu-carte\\gabarits-ca\\rapport-vie-ambiante-wh3.md`) : seulement des ressources que CA
pose lui-même en campagne dans WH3, avec SES réglages (échelle, hauteur au-dessus du relief, masque de culture, paires).
Recherche du 4.10 (lore par zone, poses de CA relevées) : `05-journal\\2026-10-04-vie-expanded\\` (rapport-vie-expanded.md,
vie-expanded.json). Choix de Charles (4.10.2026) : le groupe sûr, les destriers elfes de Tor Soleil (et étincelles sur
l'eau), sabretusks et vouivres, la brume pourpre du Bois Rêveur. Le cadre de WH1 garde la vie de la Saison (calques
recopiés) : rien n'est posé dans la zone gardée.

Pose : chaque ancre de la recherche (hex de la grille, choisi sur l'Atlas) est recalée sur le terrain FINAL : la case
valable la plus proche (au plus RAYON_RECHERCHE hex) : terre des tuiles, hors ville, emprise, route, rivière, pente
douce pour un animal au sol ; une bête volante tourne au-dessus de son ancre, à la hauteur de CA ; un effet d'eau se
pose sur l'eau. Les paires de CA (loups, sangliers, chevaux) gardent leur écart et leurs échelles de CA.

Usage : python vie_expanded.py      (à blanc, sur le projet du bac à sable)
"""
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H, SUD, UX, UZ, px_de                          # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
RECHERCHE = os.path.join(ATELIER, r"05-journal\2026-10-04-vie-expanded\vie-expanded.json")
APPROUVES = ("gyrocoptere", "grand_aigle", "pegase", "sangliers", "chevaux_bretons", "loups", "corbeaux", "chauves_souris",
             "mouches_essaims", "libellules", "feuilles", "montures_slaanesh", "brume_de_mer",       # groupe sûr
             "destriers_elfes", "etincelles_hef",                                                   # Tor Soleil
             "sabretusks", "vouivre",                                                               # ogres, vouivres
             "brume_pourpre")                                                                       # Bois Rêveur
VOLANTS = ("gyrocoptere", "grand_aigle", "pegase", "vouivre", "corbeaux")
SUR_L_EAU = ("etincelles_hef", "brume_de_mer")
DANS_LE_MARAIS = ("mouches_essaims", "libellules")
RAYON_RECHERCHE = 3                    # hex
PENTE_MAX = 0.5                        # u par u, pour un animal au sol
HAUTEURS_VOL = {"gyrocoptere": 9.5, "grand_aigle": 5.2, "pegase": 3.0, "vouivre": 6.0, "corbeaux": 12.0}   # + relief (CA)
ECHELLES = {"gyrocoptere": 0.42, "grand_aigle": 0.1, "pegase": 0.3, "vouivre": 0.15, "sabretusks": 0.2,
            "destriers_elfes": 0.36, "montures_slaanesh": 0.6, "corbeaux": 0.25}
PAIRE_MAX_U = 4.0                      # entités de CA à moins de cette distance de la première : une même composition
# (premier essai : sabretusks sans case) la Vallée d'Osséine est dans le cadre de WH1, mais ses ogres sont un ajout
# d'Expanded : leurs bêtes y vont, sur un sol plus accidenté (CA les pose à +0,73 sur des pentes)
PERMIS_ZONE_GARDEE = ("sabretusks",)
PENTES_MAX = {"sabretusks": 0.9}
# (4.10.2026, contrôle après la pose : une Monture de Slaanesh à 0,9 u d'une pierre-dragon, des chevaux à 0,9 u d'un
# maillage de rivière) un animal au sol se tient à au moins DEGAGEMENT_U du pivot de tout maillage des autres calques du
# projet (royaume de Slaanesh, abords des villes, rivières, WH1) ; l'ancre entière (hex + demi-diagonale) doit l'être
DEGAGEMENT_U = 1.0
DEMI_HEX_U = 0.4
# (premier essai : pas de bloc XML) CA pose ses Montures de Slaanesh sur la carte des Royaumes du Chaos, compilée
# (global_props.bin, lot BASE, échelle 0,6, au sol, sans masque) : entité au format de ses scènes de faune (celle de ses
# loups des Empires), chemin de la scène de CA
GABARITS_DERIVES = {
    "montures_slaanesh": [
        {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0], "echelle": [0.6, 0.6, 0.6], "y_moins_relief": 0.0,
         "xml_ca": '\t\t<entity id="0">\n\t\t\t<ECCompositeScene path="composite_scene/campaign_fauna/raptor1/'
                   'rp1_steed_of_slaanesh_grp{g}_idle01.csc" script_id="" autoplay="true"/>\n\t\t\t<ECVisibilitySettingsCampaign '
                   'visible_in_tactical_view="false" visible_in_tactical_view_only="false"/>\n\t\t\t<ECTransform position="0 0 0" '
                   'rotation="0. 0. 0." scale="0.6 0.6 0.6" pivot="0 0 0"/>\n\t\t\t<ECCampaignProperties visible_in_shroud="False" '
                   'visible_in_shroud_only="False" no_culling="False" culture_mask=""/>\n\t\t</entity>\n'}],
}
RX_ID = re.compile(r'<entity id="[^"]*">')
RX_T = re.compile(r'<ECTransform position="[^"]*" rotation="[^"]*" scale="[^"]*"')


def _h01(*cles):
    return int(hashlib.sha1("/".join(map(str, cles)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def _ident(*cles):
    return "1" + hashlib.sha1(("saison_expanded/vie/" + "/".join(map(str, cles))).encode()).hexdigest()[:14]


def _eau_mer(tuiles, forme):
    import cv2
    mer = (tuiles[..., :3] == np.array((83, 141, 213))).all(-1)
    return cv2.resize(mer.astype(np.uint8), (forme[1], forme[0]), interpolation=cv2.INTER_NEAREST) > 0


def _encombrement(dst, forme, rayon_u, sauf=("vie_expanded",)):
    """Masque (forme du relief) des pixels à moins de `rayon_u` du pivot d'un maillage des calques de `dst`, hors des
    calques `sauf` (le calque qu'on repose ne s'évite pas lui-même ; les calques sont déjà à leurs positions d'Expanded
    quand projet_expanded pose la vie)."""
    import cv2
    import glob
    m = np.zeros(forme, np.uint8)
    r_px = max(1, int(round(rayon_u * forme[1] / (W * UX))))
    rx = re.compile(r'<ECPropMesh/>.*?<ECTransform position="([-0-9.eE]+) [-0-9.eE]+ ([-0-9.eE]+)"', re.S)
    n = 0
    for f in glob.glob(os.path.join(dst, "*.layer")):
        t = open(f, encoding="utf-8").read()
        if any(f"<!-- {s} -->" in t[:200] for s in sauf):
            continue
        for x, z in rx.findall(t):
            a, b = px_de(np.asarray(float(x)), np.asarray(float(z)), forme)
            cv2.circle(m, (int(round(float(a))), int(round(float(b)))), r_px, 1, -1)
            n += 1
    return m > 0, n


def _placer_groupe(cid, k, q0, r0, x0, z0, lacet0, compo, p0, case_ok, encombre_pt, px):
    """(x0, z0, lacet) où toute la composition tient (case valable, hors de l'encombrement), ou None. D'abord l'ancre
    choisie aux 12 orientations, puis les cases des anneaux autour de l'ancre de la recherche."""
    def tient(x, z, lacet):
        cs, sn = math.cos(math.radians(lacet)), math.sin(math.radians(lacet))
        for m in compo:
            dx, dz = m["position"][0] - p0[0], m["position"][2] - p0[2]
            xm, zm = x + cs * dx - sn * dz, z + sn * dx + cs * dz
            if not case_ok(int(xm / UX), int(zm / UZ), cid) or encombre_pt[px(xm, zm)]:
                return False
        return True
    lacets = [lacet0 + 30.0 * t for t in range(12)]
    for lacet in lacets:
        if tient(x0, z0, lacet):
            return x0, z0, lacet
    for d in range(RAYON_RECHERCHE + 3):
        anneau = [(q0 + dq, r0 + dr) for dq in range(-d, d + 1) for dr in range(-d, d + 1) if max(abs(dq), abs(dr)) == d]
        anneau.sort(key=lambda c: _h01(cid, k, "groupe", c))
        for q, r in anneau:
            if not case_ok(q, r, cid):
                continue
            x, z = (q + 0.5) * UX, (r + 0.5) * UZ
            for lacet in lacets:
                if tient(x, z, lacet):
                    return x, z, lacet
    return None


def poser(height, tuiles, villes=None, routes=None, rivieres=None):
    """Texte du calque `vie_expanded` et bilan."""
    import cv2
    import projet_expanded as P
    if villes is None:
        import royaume_slaanesh
        villes, routes, rivieres = royaume_slaanesh.couches_grille()
    encombre_pt, _ = _encombrement(P.DST, height.shape, DEGAGEMENT_U)
    encombre_hex, n_obj = _encombrement(P.DST, height.shape, DEGAGEMENT_U + DEMI_HEX_U)
    rech = {c["id"]: c for c in json.load(open(RECHERCHE, encoding="utf-8"))["candidats"]}
    f = height.shape[1] // W
    reste = height.shape[0] - H * f
    mer = _eau_mer(tuiles, height.shape)
    garde = P.garde_wh1_hex()
    _, net, _, voile = P.bois_reveur(f, reste)
    gy, gx = np.gradient(cv2.GaussianBlur(height, (0, 0), 1.0))
    pente = np.hypot(gx * height.shape[1] / (W * UX), gy * height.shape[0] / (H * UZ * 3 ** 0.5 / 2))

    def px(x, z):
        a, b = px_de(np.asarray(x, float), np.asarray(z, float), height.shape)
        return (int(np.clip(round(float(b)), 0, height.shape[0] - 1)), int(np.clip(round(float(a)), 0, height.shape[1] - 1)))

    def case_ok(q, r, genre):
        if not (0 <= q < W and 0 <= r < H) or (garde[r, q] and genre not in PERMIS_ZONE_GARDEE):
            return False
        x, z = (q + 0.5) * UX, (r + 0.5) * UZ
        p = px(x, z)
        if genre in SUR_L_EAU:
            return bool(mer[p])
        if mer[p] or height[p] < 0.12:
            return False
        if r < SUD and (not net[p] or voile[p]):
            return False
        if genre in VOLANTS:
            return True                      # (premier essai : corbeaux écartés, ancrés sur leur ville) un vol tourne au-dessus
        if villes[r, q] or routes[r, q]:
            return False
        if rivieres[r, q] and genre not in DANS_LE_MARAIS:
            return False
        if genre not in DANS_LE_MARAIS and encombre_hex[p]:
            return False
        autour = [px(x + dx * UX, z + dz * UZ) for dx, dz in ((0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6))]
        if any(mer[a] or height[a] < 0.1 for a in autour):
            return False
        return genre in DANS_LE_MARAIS or float(pente[p]) <= PENTES_MAX.get(genre, PENTE_MAX)

    def recaler(q0, r0, genre):
        for d in range(RAYON_RECHERCHE + 1):
            anneau = [(q0 + dq, r0 + dr) for dq in range(-d, d + 1) for dr in range(-d, d + 1) if max(abs(dq), abs(dr)) == d]
            anneau.sort(key=lambda c: _h01(genre, c))
            for q, r in anneau:
                if case_ok(q, r, genre):
                    return q, r
        return None

    def ancres_de(cid, c):
        a = list(c.get("proposition", {}).get("ancres", []))
        if cid == "brume_de_mer" and not a:
            # (recherche : CA pose sea_mist dans la mer que l'Atlas appelle le Gué de Mistnar) le centre de cette mer
            a = [{"hex_qr": hx, "ancre": "mistnar"} for hx in _mers_nommees("mistnar")[:2]]
        return a

    sortie, bilan, poses = [], Counter(), []
    for cid in APPROUVES:
        c = rech.get(cid)
        if not c:
            bilan[f"absent de la recherche : {cid}"] += 1
            continue
        modeles = [m for m in (c.get("xml_ca") or []) if m.get("xml_ca")] or GABARITS_DERIVES.get(cid, [])
        if not modeles:
            bilan[f"sans bloc XML de CA : {cid}"] += 1
            continue
        # la composition de CA : la première entité et celles qui l'accompagnent (paire de loups, de sangliers…)
        p0 = np.array(modeles[0]["position"], float)
        compo = [m for m in modeles if math.hypot(m["position"][0] - p0[0], m["position"][2] - p0[2]) <= PAIRE_MAX_U]
        for k, a in enumerate(ancres_de(cid, c)):
            q0, r0 = (int(v) for v in a["hex_qr"])
            case = recaler(q0, r0, cid)
            if case is None:
                bilan[f"{cid} : ancre sans case valable"] += 1
                continue
            q, r = case
            x0 = (q + _h01(cid, k, "x")) * UX
            z0 = (r + _h01(cid, k, "z")) * UZ
            if cid in VOLANTS:
                # au-dessus de l'ancre, décalé de 1 à 2 u (CA : « à côté de la ville, du côté des cols »)
                ang = 2 * math.pi * _h01(cid, k, "angle")
                x0, z0 = x0 + math.cos(ang) * 1.5, z0 + math.sin(ang) * 1.5
            lacet0 = 360.0 * _h01(cid, k, "lacet") - 180.0
            if cid not in VOLANTS and cid not in SUR_L_EAU and cid not in DANS_LE_MARAIS and len(compo) > 1:
                # (4.10.2026, Charles : « replace à la main pour les créatures, fais en sorte que ce soit bien ») une paire
                # de CA (destriers, chevaux, loups, sangliers) ne perd plus de compagnon : le groupe entier tourne autour
                # de son ancre (12 orientations), puis glisse vers les cases voisines, jusqu'à ce que TOUS tiennent
                trouve = _placer_groupe(cid, k, q0, r0, x0, z0, lacet0, compo, p0, case_ok, encombre_pt, px)
                if trouve is None:
                    bilan[f"{cid} : groupe sans place entière (compagnons écartés)"] += 1
                else:
                    if trouve != (x0, z0, lacet0):
                        bilan[f"{cid} : groupe tourné ou déplacé pour tenir entier"] += 1
                    x0, z0, lacet0 = trouve
            for j, m in enumerate(compo):
                dx, dz = m["position"][0] - p0[0], m["position"][2] - p0[2]
                cs, sn = math.cos(math.radians(lacet0)), math.sin(math.radians(lacet0))
                x, z = x0 + cs * dx - sn * dz, z0 + sn * dx + cs * dz
                p = px(x, z)
                if cid in VOLANTS:
                    y = float(height[p]) + HAUTEURS_VOL[cid]
                elif cid in SUR_L_EAU:
                    y = max(float(m.get("y_moins_relief") or 0.0), 0.0) + 0.01
                else:
                    if not (cid in DANS_LE_MARAIS or j == 0 or case_ok(int(x / UX), int(z / UZ), cid)):
                        bilan[f"{cid} : compagnon écarté (eau, route, pente)"] += 1
                        continue
                    if cid not in DANS_LE_MARAIS and encombre_pt[p]:
                        bilan[f"{cid} : écarté, trop près d'un décor"] += 1
                        continue
                    dy = float(m.get("y_moins_relief") or 0.0)
                    y = float(height[p]) + (dy if abs(dy) <= 1.6 else 0.0)
                s_ca = float(m["echelle"][0]) if m.get("echelle") else 1.0
                s = ECHELLES.get(cid, s_ca) * (s_ca / float(compo[0]["echelle"][0]) if m.get("echelle") and compo[0].get("echelle") else 1.0)
                lacet = lacet0 + float(m["rotation"][1] if m.get("rotation") else 0.0)
                # montures : 4 groupes de type 1 et 2 de type 2, comme la recherche le propose (CA : grp1 et grp2)
                gabarit = m["xml_ca"].replace("{g}", "2" if cid == "montures_slaanesh" and k % 3 == 2 else "1")
                e = RX_ID.sub(f'<entity id="{_ident(cid, k, j)}">', gabarit, count=1)
                e = RX_T.sub(f'<ECTransform position="{x:.5f} {y:.5f} {z:.5f}" rotation="0. {lacet:.3f} 0." '
                             f'scale="{s:.5f} {s:.5f} {s:.5f}"', e, count=1)
                sortie.append(e if e.endswith("\n") else e + "\n")
                poses.append((cid, x, z))
                bilan[cid] += 1
    texte = ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- vie_expanded -->\n<layer version="41">\n\t<entities>\n'
             + "".join(sortie) + "\t</entities>\n\t<associations>\n\t\t<Logical/>\n\t\t<Transform/>\n\t</associations>\n"
             "</layer>\n")
    print(f"  vie d'Expanded (CA, lore par région ; dégagement {DEGAGEMENT_U} u autour de {n_obj} maillages) : "
          + " ; ".join(f"{k} {v}" for k, v in sorted(bilan.items())))
    return texte, poses


def _mers_nommees(motif):
    """Hex centraux (q, r) des régions de mer de la grille dont le nom contient `motif`."""
    import subprocess
    import tempfile
    import villes_expanded as V
    from caime_layers import read_layer, caime_names
    noms = caime_names(V.CAIME, V.CARTE_EXP)[0]
    regs = noms.get("Land regions", []) + noms.get("Sea regions", [])
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([V.CAIME, "export-layer", "--map", V.CARTE_EXP, "--out", d, "--format", "binary",
                        "--layer", "Regions"], capture_output=True)
        rg = read_layer(os.path.join(d, "layer_regions.hex_layer"))[1].reshape(H, W)
    out = []
    for i, n in enumerate(regs):
        if motif in n.lower():
            r, q = np.nonzero(rg == i)
            if len(q):
                k = np.argmin((q - q.mean()) ** 2 + (r - r.mean()) ** 2)
                out.append((int(q[k]), int(r[k])))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import glob
    from PIL import Image
    import projet_expanded as P
    Image.MAX_IMAGE_PIXELS = None
    height = np.asarray(Image.open(glob.glob(os.path.join(P.DST, "*.height.*.tif"))[0]), np.float32)
    tuiles = np.asarray(Image.open(os.path.join(P.DST, "tile_map.png")).convert("RGBA"))
    texte, poses = poser(height, tuiles)
    if "--apply" in sys.argv:
        import decors_expanded
        decors_expanded.declarer(P.DST, P.CIBLE_CLE, "vie_expanded", texte)
        print(f"  calque vie_expanded écrit dans {P.DST} ({len(poses)} entités)")
    else:
        print(f"  à blanc : {len(poses)} entités ({len(texte) // 1024} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
