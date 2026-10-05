#!/usr/bin/env python3
"""
royaume_slaanesh.py - les DÉCORS du royaume de Slaanesh de CA dans le Bois Rêveur (4.10.2026), appelé par
`projet_expanded.py` (calque `royaume_slaanesh`) ; seul, il fait un essai à blanc et une image.

Pourquoi (Charles, 4.10.2026) : « il ne fait pas que le sol, mais tous les décors du royaume de Slaanesh, tout ce qui peut
te servir, tu le mets… que ce miroir d'Athel Loren soit vraiment le royaume de Slaanesh ». Le sol (textures_reves.py),
la couleur (gris neutre de CA, projet_expanded.GRIS_ROYAUME) et les arbres (variantes de Slaanesh de CA,
arbres_expanded.reves_slaanesh) suivent le royaume de CA ; ici, ses objets.

Source : la carte des Royaumes du Chaos (`wh3_main_chaos_map_1`, global_props.bin des packs du jeu), lue en entier
(inventaire du 4.10 : 2 694 objets sur le sol du royaume, 0,248 par u²). L'instantané
`royaume-slaanesh\\royaume_slaanesh_ca.json` garde, pour chaque objet, décalque, effet, lumière et son posé sur le sol du
royaume : chemin ou clé de CA, position (espace Terry, comme nos calques), matrice, écart au sol de CA (relief décodé,
full_height_map BC6H), pente de CA sous lui, culture (BASE, ou SLAANESH seul). Écartés à la source : le palais du Prince
des Ténèbres (région unique), le hameau de Marienburg et sa forteresse, les sons qui ne sont pas des accessoires.

Règle de pose, « comme CA, sans rien inventer » : le Bois Rêveur est pavé de cellules hexagonales (CELLULE_U) ; chaque
cellule reçoit, par SIMPLE TRANSLATION, un morceau du royaume de CA tiré au hasard (un disque entièrement sur son sol) :
les compositions de CA (grappes de griffes, portails et leurs braseros, falaises flottantes…) gardent leurs positions
relatives, orientations, échelles et écarts au sol (aucune rotation : la convention des matrices n'a pas pu être
tranchée sur les pentes de CA, 4.10). La densité est celle de CA. Chaque objet est posé à la hauteur de notre relief plus
son écart au sol de CA ; écarté s'il tombe hors de la terre du Bois Rêveur (voile, éther, eau à un demi-hex), sur une
ville ou son emprise, une route, une rivière, ou sur une pente qui n'est pas la sienne (objet de pente raide, falaise :
la nôtre en vaut au moins la moitié ; objet de sol plat : pas plus que PENTE_MAX au-delà de la sienne).

Usage : python royaume_slaanesh.py      (à blanc, sur le projet du bac à sable : bilan et apercus\\royaume-slaanesh.png)
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SAISON_CARTE", "expanded")
from cadre_expanded import W, H, SUD, UX, UZ, px_de                          # noqa: E402

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANTANE = os.path.join(ICI, "royaume-slaanesh", "royaume_slaanesh_ca.json")
APERCU = os.path.join(ICI, "apercus", "royaume-slaanesh.png")
ZH = 3 ** 0.5 / 2                      # z de l'espace Terry -> z du monde (les deux cartes ont la même convention)
CELLULE_U = 10.0                       # rayon d'une cellule (u du monde) : un morceau de royaume par cellule
PENTE_RAIDE = 0.8                      # pente de CA (u par u) au-delà de laquelle l'objet est un objet de pente
PENTE_MAX = 0.6                        # écart de pente toléré pour un objet de sol plat
GRAINE = 20261004
# (4.10.2026, dégagement des arbres : 16 507 arbres sous 173 objets) les falaises FLOTTANTES de CA (gen_cliff_floating_*,
# 27 à 63 u de large, pendues jusqu'à 45 u SOUS leur pivot) bordent son royaume au-dessus du vide ; translatées au cœur
# de l'île, elles faisaient des tables de roche géantes au-dessus de la forêt : écartées de la pose intérieure
EXCLUS_INTERIEUR = ("gen_cliff_floating", "shattered_cliff_floating")
BORD_CARTE_U = 6.0
HAUT_EMPRISE_U = 1.5                  # un « grand » objet (comme le dégagement des arbres, arbres_expanded.HAUT_MIN_U)


def rotation_terry(matrice):
    """(rx, ry, rz) en degrés et (sx, sy, sz) pour Terry ; copie de props_wh1_vers_layers.rotation_terry (vérifiée sur
    12 objets inclinés des Empires) : R = Rx(-rx)·Ry(-ry)·Rz(-rz), échelle par lignes."""
    M = np.array(matrice, float).reshape(3, 3)
    ech = np.linalg.norm(M, axis=1)
    R = M / np.where(ech == 0, 1, ech)[:, None]
    meilleur = None
    b0 = math.asin(max(-1.0, min(1.0, R[0, 2])))
    for b in (b0, math.pi - b0):
        cb = math.cos(b)
        if abs(cb) < 1e-6:
            a, c = math.atan2(R[2, 1], R[1, 1]), 0.0
        else:
            a = math.atan2(-R[1, 2] / cb, R[2, 2] / cb)
            c = math.atan2(-R[0, 1] / cb, R[0, 0] / cb)
        cout = abs(a) + abs(c)
        if meilleur is None or cout < meilleur[0] - 1e-9:
            meilleur = (cout, a, b, c)
    _, a, b, c = meilleur
    return tuple(-math.degrees(t) for t in (a, b, c)), tuple(float(e) for e in ech)


def couches_grille():
    """(villes, routes, rivières) de la grille d'Expanded (H, W), rangée 0 au sud : cases d'emplacement ou d'emprise de
    ville, cases de route, cases de rivière."""
    import villes_expanded as V
    from caime_layers import read_layer
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run([V.CAIME, "export-layer", "--map", V.CARTE_EXP, "--out", d, "--format", "binary",
                            "--layer", "TownSlots", "--layer", "TownSprawl", "--layer", "Roads", "--layer", "Rivers"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode:
            raise SystemExit(p.stdout + p.stderr)
        lire = lambda n: read_layer(os.path.join(d, f"layer_{n}.hex_layer"))[1].reshape(H, W)  # noqa: E731
        # (premier essai : 0 objet posé) TownSlots : −1 = rien ; TownSprawl : 0 = rien, 1 = emprise
        villes = (lire("town_slots") >= 0) | (lire("town_sprawl") > 0)
        return villes, lire("roads") > 0, lire("rivers") > 0


def _entite(graine, corps, pos, rot=(0.0, 0.0, 0.0), ech=(1.0, 1.0, 1.0), culture="", proprietes=True):
    i = "1" + hashlib.sha1(graine.encode()).hexdigest()[:14]
    p = " ".join(f"{v:.5f}" for v in pos)
    r = " ".join(f"{v:.5f}" for v in rot)
    s = " ".join(f"{v:.5f}" for v in ech)
    vis = '\t\t\t<ECVisibilitySettingsCampaign visible_in_tactical_view="False" visible_in_tactical_view_only="False"/>\n'
    if proprietes:
        cp = ('\t\t\t<ECCampaignProperties visible_inside_snow_region="True" visible_outside_snow_region="True" '
              'visible_inside_destruction_region="True" visible_outside_destruction_region="True" '
              f'visible_in_shroud="False" visible_in_shroud_only="False" no_culling="False" culture_mask="{culture}"/>\n')
    else:
        cp = f'\t\t\t<ECCampaignProperties visible_in_shroud="False" visible_in_shroud_only="False" culture_mask="{culture}"/>\n'
    return (f'\t\t<entity id="{i}">\n{corps}{vis if "ECSoundMarker" not in corps else ""}{cp}'
            f'\t\t\t<ECTransform position="{p}" rotation="{r}" scale="{s}" pivot="0 0 0"/>\n\t\t</entity>\n')


def entite(o, pos, graine):
    s = o["sorte"]
    if s in ("maillage", "decalque", "effet"):
        rot, ech = rotation_terry(o["mat"])
    if s == "maillage":
        corps = ('\t\t\t<ECPropMesh/>\n'
                 f'\t\t\t<ECMesh model_path="{o["modele"]}" opacity="1"/>\n'
                 '\t\t\t<ECMeshRenderSettings receive_decals="True"/>\n'
                 '\t\t\t<ECPropHeightPatch apply_height_patch="False" for_camera_height_map_only="false"/>\n')
        return _entite(graine, corps, pos, rot, ech, o["culture"])
    if s == "decalque":
        corps = (f'\t\t\t<ECDecal model_path="{o["modele"]}" parallax_scale="0" tiling="0" normal_mode="DNM_BLEND" '
                 'apply_to_terrain="True" apply_to_objects="False" render_above_snow="False"/>\n'
                 '\t\t\t<ECPropHeightPatch apply_height_patch="False" for_camera_height_map_only="false"/>\n')
        return _entite(graine, corps, pos, rot, ech, o["culture"])
    if s == "effet":
        corps = f'\t\t\t<ECVFX vfx="{o["vfx"]}" autoplay="true" scale="1" instance_name=""/>\n'
        return _entite(graine, corps, pos, rot, ech, o["culture"], proprietes=False)
    if s == "lumiere":
        r, g, b = (int(round(255 * min(1.0, max(0.0, c)))) for c in o["rvb"])
        corps = (f'\t\t\t<ECPointLight colour="{r} {g} {b} 255" colour_scale="{o["echelle"]:.1f}" radius="{o["rayon"]:.5f}" '
                 'animation_type="LAT_NONE" animation_speed_scale="0.00000 0.00000" colour_min="0.00000" '
                 f'random_offset="0.00000" falloff_type="{o["mode"]}" for_light_probes_only="False"/>\n')
        return _entite(graine, corps, pos, culture=o["culture"], proprietes=False)
    corps = f'\t\t\t<ECSoundMarker key="{o["cle"]}" />\n'
    return _entite(graine, corps, pos, proprietes=False)


def poser(height, villes=None, routes=None, rivieres=None):
    """Texte du calque `royaume_slaanesh` et bilan, pour le relief `height` (nord en haut) du projet."""
    import projet_expanded as P
    import cv2
    if villes is None:
        villes, routes, rivieres = couches_grille()
    src = json.load(open(INSTANTANE, encoding="utf-8"))
    objets = src["objets"]
    m = src["masque"]
    masque = np.array([[c == "1" for c in l] for l in m["lignes"]])
    x0, z0 = m["x0"], m["z0"]
    rng = np.random.default_rng(GRAINE)
    sys.path.insert(0, os.path.join(os.path.dirname(ICI), "..", "02-scripts"))
    from contenu_pack import SourcePacks
    import arbres_expanded
    packs = SourcePacks(r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data",
                        exclure=("saison_des_revelations", "zz_startpos_db", "saison_expanded", "!saison", "!!essai"))
    cache_boites = {}

    def boite(m):
        return arbres_expanded._boite_ca(m, packs, cache_boites)
    f = height.shape[1] // W
    reste = height.shape[0] - H * f
    _, net, _, voile = P.bois_reveur(f, reste)
    terre = net & ~voile & (height > 0.1)
    # pente de notre relief, en u par u du monde
    gy, gx = np.gradient(cv2.GaussianBlur(height, (0, 0), 1.0))
    pente_px = np.hypot(gx * height.shape[1] / (W * UX), gy * height.shape[0] / (H * UZ * ZH))

    def ici(x, z):
        pxx, pyy = px_de(np.asarray(x, float), np.asarray(z, float), height.shape)
        return (np.clip(np.rint(pyy).astype(int), 0, height.shape[0] - 1),
                np.clip(np.rint(pxx).astype(int), 0, height.shape[1] - 1))

    # centres de prélèvement : disques de rayon CELLULE_U·1,15 entièrement sur le sol du royaume de CA
    rayon_src = CELLULE_U * 1.15
    k = int(math.ceil(rayon_src))
    dz_cases = int(math.ceil(rayon_src / ZH))
    yy, xx = np.mgrid[-dz_cases:dz_cases + 1, -k:k + 1]
    disque = np.hypot(xx, yy * ZH) <= rayon_src
    ok = cv2.erode(masque.astype(np.uint8), disque.astype(np.uint8)) > 0
    zi, xi = np.nonzero(ok)
    centres = np.stack([xi + x0, zi + z0], 1).astype(float)
    if not len(centres):
        raise SystemExit("aucun disque de prélèvement entier sur le sol du royaume de CA")
    pos = np.array([o["pos"] for o in objets], float)
    # (4.10.2026, contrôle des hauteurs : griffes à +2,6 u en l'air, rochers enfoncés de 3 u) l'écart au sol de CA suit
    # SON relief (bord de pente raide, rocher noyé dans un talus) ; pour un modèle posé sur sa base (boîte qui part du
    # pivot), le pivot reste au sol : jamais plus de 0,1 u au-dessus, ni enfoncé de plus de la moitié de sa hauteur.
    # `delta` : la correction de chaque objet ; effets, lumières et sons prennent celle de l'objet de CA le plus proche
    # (1,5 u au plus : braseros, torches, portails) et sont écartés avec lui (falaises flottantes)
    delta = np.zeros(len(objets))
    est_maillage = np.array([o["sorte"] == "maillage" for o in objets])
    for i in np.flatnonzero(est_maillage):
        o = objets[i]
        bt = boite(o["modele"])
        if bt is None:
            continue
        ech_y = float(np.linalg.norm(np.array(o["mat"]).reshape(3, 3)[1]))
        bas, haut_m = bt[0][1] * ech_y, (bt[1][1] - bt[0][1]) * ech_y
        if bas > -0.1 * haut_m:
            delta[i] = min(max(o["dy"], -0.5 * haut_m), 0.1) - o["dy"]
    parent = np.full(len(objets), -1)
    exclu_parent = np.zeros(len(objets), bool)
    im = np.flatnonzero(est_maillage)
    for i in (k for k in range(len(objets)) if objets[k]["sorte"] in ("effet", "lumiere", "son")):
        d = np.hypot(pos[im, 0] - pos[i, 0], (pos[im, 2] - pos[i, 2]) * ZH)
        j = int(d.argmin())
        if d[j] <= 1.5:
            parent[i] = im[j]
            exclu_parent[i] = any(k in objets[im[j]]["modele"] for k in EXCLUS_INTERIEUR)
    # ancres des cellules : réseau hexagonal (monde) sur l'emprise du Bois Rêveur
    pas = CELLULE_U * 3 ** 0.5
    ancres = []
    zmax = SUD * UZ
    for j, zw in enumerate(np.arange(0, zmax * ZH + pas, pas * ZH)):
        for xw in np.arange((j % 2) * pas / 2, W * UX + pas, pas):
            ancres.append((xw, zw / ZH))
    ancres = np.array(ancres)
    bilan = Counter()
    sortie = []
    choisis = []
    retenus = []
    for ia, (ax, az) in enumerate(ancres):
        c = centres[rng.integers(len(centres))]
        d = np.hypot(pos[:, 0] - c[0], (pos[:, 2] - c[1]) * ZH)
        sel = np.flatnonzero(d <= rayon_src)
        if not len(sel):
            continue
        tx = pos[sel, 0] - c[0] + ax
        tz = pos[sel, 2] - c[1] + az
        # cellule de Voronoï de l'ancre : la plus proche des ancres voisines
        dd = np.hypot(tx[:, None] - ancres[None, :, 0], (tz[:, None] - ancres[None, :, 1]) * ZH)
        sel, tx, tz = sel[dd.argmin(1) == ia], tx[dd.argmin(1) == ia], tz[dd.argmin(1) == ia]
        for i, x, z in zip(sel, tx, tz):
            o = objets[i]
            s_ = o["sorte"]
            if any(k in o.get("modele", "") for k in EXCLUS_INTERIEUR):
                bilan["falaise flottante de bord de royaume"] += 1
                continue
            q, r = int(x / UX), int(z / UZ)
            # (2e compilation : 3 « Failed to find valid quadtree node », objets au bord sud, z de −0,1 à 3,5) : jamais à
            # moins de BORD_CARTE_U du bord de la carte (la boîte d'un objet ne doit pas en sortir)
            if min(x, z, W * UX - x) < BORD_CARTE_U:
                bilan["trop près du bord de la carte"] += 1
                continue
            if not (0 <= q < W and 0 <= r < SUD):
                bilan["hors du Bois Rêveur"] += 1
                continue
            py, pxx = ici(x, z)
            if os.environ.get("DEBOGUE_ROYAUME") and bilan["hors de la terre (voile, éther, eau)"] < 5:
                print("   débogue", (round(x, 1), round(z, 1)), (int(py), int(pxx)), bool(terre[py, pxx]),
                      float(height[py, pxx]))
            autour = [ici(x + dx * UX, z + dz * UZ) for dx, dz in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5))]
            if not terre[py, pxx] or min(height[a] for a in autour) < 0.06 or not all(terre[a] for a in autour):
                bilan["hors de la terre (voile, éther, eau)"] += 1
                continue
            if villes[r, q] or routes[r, q] or rivieres[r, q]:
                bilan["ville, route ou rivière"] += 1
                continue
            p_nous = float(pente_px[py, pxx])
            if o["pente_ca"] > PENTE_RAIDE:
                if p_nous < 0.5 * o["pente_ca"]:
                    bilan["objet de pente sur sol trop plat"] += 1
                    continue
            elif p_nous > o["pente_ca"] + PENTE_MAX:
                bilan["sol trop raide"] += 1
                continue
            if s_ != "maillage" and parent[i] >= 0 and exclu_parent[i]:
                bilan["effet d'un objet écarté"] += 1
                continue
            dy = o["dy"] + (delta[i] if s_ == "maillage" else (delta[parent[i]] if parent[i] >= 0 else 0.0))
            y = float(height[py, pxx]) + dy
            retenus.append({"ia": ia, "i": int(i), "o": o, "pos": (x, y, z)})
    # (4.10.2026) DEUXIÈME PASSE, sur l'EMPRISE des grands objets (boîte orientée du modèle de CA, HAUT_EMPRISE_U de haut
    # au moins), pas seulement leur pivot : un portail ou une falaise dont le pivot est bon mais dont le corps déborde sur
    # une ville, une route ou une rivière est écarté ; deux grands objets de cellules voisines qui se chevauchent : le
    # second est écarté. Les effets, lumières et sons d'un objet écarté le suivent (même cellule, même objet de CA)
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree
    poses_grands, ecartes = [], set()
    # (5.10.2026, Charles en jeu : « des montagnes flottantes un peu partout » ; 327 des 1 043 grands objets du royaume au
    # dessous en l'air de plus de 0,4 u, portails jusqu'à 9 u : le sol du Bois Rêveur, relief de WH1, est plus accidenté
    # que celui de CA) chaque grand maillage est posé PAR SON EMPRISE (pose_au_sol) : abaissé jusqu'au sol, ou écarté s'il
    # devait s'enterrer à moitié ; ses effets, lumières et sons (même cellule, même objet de CA) le suivent
    import pose_au_sol
    abaisse = {}
    for k_r, rr in enumerate(retenus):
        o = rr["o"]
        if o["sorte"] != "maillage":
            continue
        x, y, z = rr["pos"]
        # (premier essai : 83 objets encore en l'air) la matrice TELLE QU'ELLE SERA ÉCRITE (angles de Terry tirés de
        # celle de CA par rotation_terry, inexacte sur certains objets penchés), pas celle de CA
        ang_, ech_ = rotation_terry(o["mat"])
        y2, verdict = pose_au_sol.ajuster(x, y, z, pose_au_sol.matrice_terry(ang_, ech_), boite(o["modele"]),
                                          lambda xs, zs: height[ici(xs, zs)], haut_min=0.3)
        if y2 is None:
            ecartes.add(k_r)
            bilan["grand objet qui flotterait (emprise)"] += 1
        elif verdict == "abaissé":
            rr["pos"] = (x, y2, z)
            abaisse[(rr["ia"], rr["i"])] = y - y2
            bilan["grand objet abaissé jusqu'au sol (emprise)"] += 1
    for rr in retenus:
        if rr["o"]["sorte"] in ("effet", "lumiere", "son") and parent[rr["i"]] >= 0:
            d_ = abaisse.get((rr["ia"], int(parent[rr["i"]])))
            if d_:
                x, y, z = rr["pos"]
                rr["pos"] = (x, y - d_, z)
    for k_r, rr in enumerate(retenus):
        o = rr["o"]
        if o["sorte"] != "maillage" or k_r in ecartes:
            continue
        bt = boite(o["modele"])
        if bt is None:
            continue
        M = np.array(o["mat"]).reshape(3, 3)
        lo, hi = bt
        if (hi[1] - lo[1]) * float(np.linalg.norm(M[1])) < HAUT_EMPRISE_U:
            continue
        coins = np.array([[a, 0.0, c] for a, c in ((lo[0], lo[2]), (hi[0], lo[2]), (hi[0], hi[2]), (lo[0], hi[2]))]) @ M
        x, _, z = rr["pos"]
        poly = Polygon([(x + p[0], z + p[2]) for p in coins]).buffer(0)
        # cases touchées par l'emprise : points tous les 0,3 u
        x0, z0, x1, z1 = poly.bounds
        gx_, gz_ = np.meshgrid(np.arange(x0, x1 + 0.3, 0.3), np.arange(z0, z1 + 0.3, 0.3))
        from shapely import contains_xy
        dedans = contains_xy(poly, gx_.ravel(), gz_.ravel())
        qs = np.clip((gx_.ravel()[dedans] / UX).astype(int), 0, W - 1)
        rs = np.clip((gz_.ravel()[dedans] / UZ).astype(int), 0, H - 1)
        if len(qs) and (villes[rs, qs] | routes[rs, qs] | rivieres[rs, qs]).any():
            ecartes.add(k_r)
            bilan["emprise sur une ville, une route ou une rivière"] += 1
            continue
        poses_grands.append((k_r, poly))
    # (premier essai : 537 écartés) les grands objets de CA se chevauchent À DESSEIN dans une même composition (falaises
    # emboîtées, griffes en grappe) : seul compte le chevauchement entre deux CELLULES différentes (deux morceaux translatés)
    arbre = STRtree([p for _, p in poses_grands])
    gardes = set()
    for j, (k_r, poly) in enumerate(poses_grands):
        voisins_ = [n for n in arbre.query(poly) if n != j]
        if any(poses_grands[n][0] in gardes and retenus[poses_grands[n][0]]["ia"] != retenus[k_r]["ia"]
               and poses_grands[n][1].intersection(poly).area > 0.05 for n in voisins_):
            ecartes.add(k_r)
            bilan["chevauche un autre grand objet"] += 1
            continue
        gardes.add(k_r)
    ecartes_src = {(retenus[k]["ia"], retenus[k]["i"]) for k in ecartes}
    for k_r, rr in enumerate(retenus):
        o = rr["o"]
        if k_r in ecartes:
            continue
        if o["sorte"] in ("effet", "lumiere", "son") and parent[rr["i"]] >= 0 and (rr["ia"], int(parent[rr["i"]])) in ecartes_src:
            bilan["effet d'un objet écarté"] += 1
            continue
        if o["sorte"] == "maillage" and abs(delta[rr["i"]]) > 0.05:
            bilan["hauteur ramenée au sol"] += 1
        sortie.append(entite(o, rr["pos"], f"royaume_slaanesh/{rr['ia']}/{rr['i']}"))
        choisis.append((rr["pos"][0], rr["pos"][2], o["sorte"]))
        bilan["posés : " + o["sorte"]] += 1
    surface = terre.sum() * (W * UX / height.shape[1]) * (H * UZ * ZH / height.shape[0])
    n_obj = sum(v for k_, v in bilan.items() if k_.startswith("posés"))
    print(f"  royaume de Slaanesh : {len(ancres)} cellules, {n_obj} entités de CA posées sur {surface:.0f} u² de terre du "
          f"Bois Rêveur ({n_obj / max(surface, 1):.3f} par u² ; CA : 0,248 objets + effets sur son royaume)")
    print("   " + " ; ".join(f"{k_} {v}" for k_, v in sorted(bilan.items())))
    texte = ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- royaume_slaanesh -->\n<layer version="41">\n\t<entities>\n'
             + "".join(sortie) + "\t</entities>\n\t<associations>\n\t\t<Logical/>\n\t\t<Transform/>\n\t</associations>\n"
             "</layer>\n")
    return texte, choisis


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import glob
    from PIL import Image
    import projet_expanded as P
    Image.MAX_IMAGE_PIXELS = None
    height = np.asarray(Image.open(glob.glob(os.path.join(P.DST, "*.height.*.tif"))[0]), np.float32)
    texte, choisis = poser(height)
    # aperçu : relief ombré du Bois Rêveur, objets en couleur par sorte
    f = height.shape[1] // W
    bas = height[(H - SUD) * f:H * f]
    gy, gx = np.gradient(bas)
    img = np.clip(128 + (-gx + gy) * 90, 0, 255).astype(np.uint8)
    img = np.stack([img] * 3, -1)
    coul = {"maillage": (230, 60, 200), "decalque": (150, 90, 60), "effet": (255, 220, 60), "lumiere": (255, 255, 255),
            "son": (60, 200, 255)}
    for x, z, s in choisis:
        pxx, pyy = px_de(x, z, height.shape)
        pyy -= (H - SUD) * f
        a, b = int(round(pyy)), int(round(pxx))
        if 0 <= a < img.shape[0] and 0 <= b < img.shape[1]:
            img[max(0, a - 1):a + 2, max(0, b - 1):b + 2] = coul[s]
    Image.fromarray(img).save(APERCU)
    if "--apply" in sys.argv:
        # le calque seul, dans le projet du bac à sable (comme projet_expanded à la fin de sa construction)
        import decors_expanded
        decors_expanded.declarer(P.DST, P.CIBLE_CLE, "royaume_slaanesh", texte)
        print(f"  aperçu : {APERCU} ; calque royaume_slaanesh réécrit dans {P.DST} ({len(texte) // 1024} Ko)")
    else:
        print(f"  aperçu : {APERCU} ; à blanc : rien d'écrit ({len(texte) // 1024} Ko de calque)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
