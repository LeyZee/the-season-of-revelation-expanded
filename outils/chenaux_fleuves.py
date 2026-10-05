#!/usr/bin/env python3
"""
chenaux_fleuves.py - le TERRAIN des fleuves navigables d'Expanded (5.10.2026) : relief du chenal, berges basses, rubans de
rivière de WH1 rognés, objets des berges recalés.

Pourquoi (Charles, 5.10.2026, premier essai en jeu des fleuves : « la rivière flotte sur un énorme trou béant qui
correspond à la voie navigable… il n'y a pas d'eau sur la voie navigable ») : le lot des fleuves (session des rivières,
`banc-fleuve\\outils\\creuser\\integrer_fleuves_expanded.py`) fait la GRILLE (hex de mer `sea_river`, 7 régions d'eau) ;
l'étape « terrain » de la méthode de CA pour le Reik (`banc-fleuve\\etude\\SYNTHESE-fleuves-navigables.md` § 1.4 et
étape 4) n'avait été faite par personne :
- tuiles de mer sur le chenal (déjà : la carte des tuiles est l'export CAIME de la grille) ;
- `sea_height` en PLATEAU à −0,35 sous le chenal, −1,0 sous la terre sur 1,5 à 2,5 u de marge ; relief ≥ 0, BERGES BASSES ;
- plan d'eau `ECPolygonMesh` à y = 0 au matériau de la mer (`eau_expanded`, sur les couches à jour : `couches_a_jour`) ;
- les rubans `river_*` ne servent qu'aux affluents : sur le chenal, aucun ruban.
Dans la zone gardée de WH1 (la Brienne la traverse), le relief et le fond restaient ceux de WH1 : terre à ~1 u, fond de WH1
sous la terre, d'où le trou sous les tuiles de mer, et les rubans de WH1 de l'ancienne Brienne à leur hauteur.

Ce module (appelé par `projet_expanded` et `rivieres_maillages_expanded`) :
- `chenal_hex()` : hex des 7 régions d'eau des fleuves (`FLEUVES`, par leur NOM : les indices de mer suivent l'ordre
  alphabétique de CAIME) ;
- `relief(height, sea, f, reste, epargne)` : sur le chenal (tracé lissé comme la mer de l'Atlas, 1,2 hex), surface à
  HAUTEUR_SUR_MER et fond à FOND_CHENAL ; à l'embouchure, fond fondu dans celui de la mer voisine ; berges abaissées en
  pente douce vers BERGE_U sur BERGE_HEX hex (jamais relevées ; jamais sous les montagnes de WH1 gardées, `epargne`) ;
  fond à −1,0 sous la terre sur MARGE_HEX hex ; rend aussi la différence de relief (pour recaler les objets) ;
- `rogner_rmv2(octets, centre, dans)` : un maillage d'eau RMV2 v8 (format de `rivieres_wh1.rmv2`) sans les triangles
  dont le centre tombe sur le chenal (élargi de RUBAN_MARGE_HEX) ; sommets inchangés, index et tailles réécrits.
"""
import os
import struct
import subprocess
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, UX, UZ                                  # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from caime_layers import read_layer, caime_names, flat_names             # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
SORTIE_GRILLE = os.path.join(ICI, r"couches-expanded\villes-sortie")
FLEUVES = ("saison_sea_brienne_", "saison_sea_grismerie_", "saison_sea_sannez_")
HAUTEUR_SUR_MER = 0.02
FOND_CHENAL = -0.35          # CA, le Reik : fond en plateau à −0,35 (SYNTHESE § 1.4)
FOND_SOUS_TERRE = -1.0       # CA : −1,0 sous la terre de la marge
MARGE_HEX = 3.0              # ~2 u (CA : 1,5 à 2,5 u)
BERGE_U = 0.12               # hauteur de la berge au bord de l'eau (au-dessus de la surface : 0,02)
BERGE_HEX = 3.0              # pente de la berge : de BERGE_U au relief d'origine sur 3 hex
EMBOUCHURE_HEX = 4.0         # fond fondu dans celui de la mer voisine sur 4 hex
RUBAN_MARGE_HEX = 0.6        # un triangle de ruban à moins de 0,6 hex du chenal est retiré
DELTA = os.path.join(ICI, r"relief\chenaux_delta.npz")   # relief après − avant (projet_expanded), nord en haut, 8 px/hex


def chenal_hex():
    """Masque (H, W), rangée 0 au sud, des hex des régions d'eau des fleuves, lu sur les couches À JOUR du map.hex
    (couches_a_jour d'abord) ; contrôle : les mêmes hex que dans un export frais."""
    noms = flat_names(caime_names(CAIME, CARTE)[0], "Regions")
    idx = [i for i, n in enumerate(noms) if n.startswith(FLEUVES)]
    if len(idx) != 7:
        raise SystemExit(f"régions d'eau des fleuves : {len(idx)} trouvées au lieu de 7 ({[noms[i] for i in idx]})")
    reg = read_layer(os.path.join(SORTIE_GRILLE, "layer_regions.hex_layer"))[1].reshape(H, W)
    m = np.isin(reg, idx)
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([CAIME, "export-layer", "--map", CARTE, "--out", d, "--format", "binary", "--layer", "Regions"],
                       capture_output=True)
        frais = read_layer(os.path.join(d, "layer_regions.hex_layer"))[1].reshape(H, W)
    if not np.array_equal(m, np.isin(frais, idx)):
        raise SystemExit("couches de la grille périmées : lancer couches_a_jour.py")
    return m


def px_nord(m, f, reste):
    """Masque d'hex (rangée 0 au sud) -> raster à f px par hex, nord en haut, `reste` rangées de plus en bas."""
    g = np.repeat(np.repeat(m[::-1], f, 0), f, 1)
    return np.concatenate([g, np.repeat(g[-1:], reste, 0)]) if reste else g


def eau_px(f, reste):
    """Le chenal au pixel : hex flouté sur 1,2 hex, seuillé à 0,5 (côtes sans angles d'hex, comme la mer de l'Atlas)."""
    m = px_nord(chenal_hex(), f, reste).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 1.2 * f) > 0.5


def relief(height, sea, f, reste, epargne=None):
    """(height, sea, delta, bilan) : le chenal et ses berges à la manière de CA ; `delta` = height après − avant."""
    avant = height.copy()
    eau = eau_px(f, reste)
    d_eau = cv2.distanceTransform((~eau).astype(np.uint8), cv2.DIST_L2, 5) / f        # hex jusqu'au chenal
    epargne = np.zeros_like(eau) if epargne is None else epargne
    # (5.10.2026, deuxième version, Charles en jeu : « les fleuves qu'on a creusés ne sont pas parfaits ») CA ne creuse
    # pas ses chenaux dans le RELIEF (Empires Immortels, relief ombré au pixel : rien ne se voit sous le Reik) ; la
    # première version abaissait les berges vers 0,12 et posait le relief du chenal à 0,02 : une rigole lissée qui ne
    # suivait pas les tuiles (en hex), d'où des rebords et des escaliers. Le relief n'est plus touché ici : la côte du
    # chenal (falaise, plage, relief continu sous l'eau) est celle de toutes les côtes (cotes_relief) ; reste le FOND.
    berge = np.zeros_like(eau)
    autre_eau = ~eau & (avant <= 0.035)
    sea = np.where(eau, FOND_CHENAL, sea).astype(np.float32)
    # 3. embouchure : fond fondu dans la mer voisine (moyenne floutée des seules cases d'eau, près de l'autre eau)
    d_autre = cv2.distanceTransform((~autre_eau).astype(np.uint8), cv2.DIST_L2, 5) / f
    zone = (eau | autre_eau) & (d_autre <= EMBOUCHURE_HEX) & (d_eau <= EMBOUCHURE_HEX)
    if zone.any():
        e = (eau | autre_eau).astype(np.float32)
        lisse = cv2.GaussianBlur(sea * e, (0, 0), 1.5 * f) / np.maximum(cv2.GaussianBlur(e, (0, 0), 1.5 * f), 1e-3)
        sea = np.where(zone, np.minimum(lisse, -0.1), sea).astype(np.float32)
    # 4. sous la terre de la marge : fond à −1,0 au plus
    marge = ~eau & (d_eau <= MARGE_HEX) & (height > 0.035)
    sea = np.where(marge, np.minimum(sea, FOND_SOUS_TERRE), sea).astype(np.float32)
    delta = (height - avant).astype(np.float32)
    bilan = {"chenal_hex": int(eau.sum() / f / f), "berges_px": int((berge & (delta < -0.005)).sum()),
             "abaissement_max_u": float(-delta[~eau].min()) if (~eau).any() else 0.0,
             "embouchure_px": int(zone.sum()), "epargne_px": int((epargne & ~eau & (d_eau <= BERGE_HEX)).sum())}
    return height, sea, delta, bilan


def dans_chenal_monde(marge_hex=RUBAN_MARGE_HEX, f=8):
    """Fonction (x, z) du monde -> booléens : sur le chenal élargi de `marge_hex`."""
    m = px_nord(chenal_hex(), f, 0).astype(np.uint8)
    k = int(round(marge_hex * f))
    if k > 0:
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    m = m > 0

    def dedans(x, z):
        c = np.clip((np.asarray(x) / UX * f).astype(int), 0, W * f - 1)
        r = np.clip(((H * UZ - np.asarray(z)) / UZ * f).astype(int), 0, H * f - 1)
        return m[r, c]
    return dedans


def delta_monde():
    """Fonction (x, z) du monde -> abaissement du relief des berges (u, ≤ 0) enregistré par projet_expanded."""
    from cadre_expanded import ipx_de
    d = np.load(DELTA)["delta"].astype(np.float32)

    def dy(x, z):
        cx, cy = ipx_de(x, z, d.shape)
        return d[cy, cx]
    return dy


def rogner_rmv2(octets, centre, dedans, dy=None):
    """(octets, retirés, total) : le maillage RMV2 v8 d'un morceau (format `rivieres_wh1.rmv2`, sommets de 48 octets,
    positions relatives au centre écrit à +628 du morceau) sans les triangles dont le centre (monde = centre de l'objet
    + position) est `dedans` ; avec `dy`, chaque sommet descend avec le relief des berges (y + dy(x, z)). Les sommets
    inutilisés restent (sans effet au rendu)."""
    off = struct.unpack_from("<I", octets, 152)[0]
    _mat, _u, taille, voff, nvc, ioff, nic = struct.unpack_from("<HHIIIII", octets, off)
    sommets = np.frombuffer(octets, np.uint8, nvc * 48, off + voff).reshape(nvc, 48).copy()
    pos = sommets[:, :12].copy().view("<f4").reshape(nvc, 3).astype(np.float64)
    tris = np.frombuffer(octets, "<u2", nic, off + ioff).reshape(-1, 3)
    c = pos[tris].mean(1) + np.asarray(centre, np.float64)
    garde = ~dedans(c[:, 0], c[:, 2])
    bouge = False
    if dy is not None:
        dd = dy(pos[:, 0] + centre[0], pos[:, 2] + centre[2])
        if (np.abs(dd) > 0.005).any():
            bouge = True
            p32 = pos.astype("<f4")
            p32[:, 1] += dd.astype("<f4")
            sommets[:, :12] = p32.view(np.uint8).reshape(nvc, 12)
    if garde.all() and not bouge:
        return octets, 0, len(tris)
    t = tris[garde]
    tete_f = bytearray(octets[:off])
    tete_m = bytearray(octets[off:off + voff])
    nic2 = t.size
    taille2 = voff + nvc * 48 + nic2 * 2
    struct.pack_into("<IIIII", tete_m, 4, taille2, voff, nvc, voff + nvc * 48, nic2)
    struct.pack_into("<I", tete_m, 68, taille2)
    struct.pack_into("<II", tete_f, 144, nvc * 48, nic2 * 2)
    if bouge:                                    # boîte englobante du morceau (y), relative au centre
        lo = struct.unpack_from("<6f", tete_m, 24)
        ys = sommets[:, :12].copy().view("<f4").reshape(nvc, 3)[:, 1]
        struct.pack_into("<6f", tete_m, 24, lo[0], float(min(lo[1], ys.min())), lo[2], lo[3], float(max(lo[4], ys.max())),
                         lo[5])
    neuf = bytes(tete_f) + bytes(tete_m) + sommets.tobytes() + t.astype("<u2").tobytes()
    return neuf, int((~garde).sum()), len(tris)
