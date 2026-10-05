#!/usr/bin/env python3
"""
relief_alpin.py - le relief de l'Atlas pour Expanded, v4 (3.10.2026), à la place de `relief_atlas.relief` (v3, gardé).

Pourquoi : l'aperçu du relief au nouveau cadre (`apercus\\relief-v1-sud-voutes.jpg`) montrait des montagnes en « marbre
fondu » : volutes (bruit à crêtes sur un domaine très déformé, 18 hex), plateaux plats, aucune vallée lisible ; c'était déjà
noté le 25.09 (« motifs marbrés sur les grands massifs »). Charles veut des montagnes bien placées, « la plus stylée et
jolie possible ».

Méthode (calée sur les hauteurs de WH1, comme la v3 : prairie ~1,6, collines 2,4-6,9, montagne 3,2-10,5, max 13,8) :
1. enveloppe : `alt` de l'Atlas lissée, convertie par classe (plaine, collines, montagnes, Voûtes plus hautes) ;
2. montagnes : multifractal à crêtes (chaque octave pondérée par la précédente : arêtes nettes, pics, cols), domaine à
   peine déformé (2 hex) ; hauteur des sommets selon `alt` ;
3. VALLÉES DE JEU : les cases franchissables de la grille CAIME (couche Impassable d'Expanded) dans les montagnes sont
   creusées en auge (fond de vallée à hauteur de collines, versants à ~1,3 u par hex) : on voit passer les armées là où
   elles passent ;
4. érosion à 2 px par hex : talus (érosion thermique, pente de repos) puis ravines (aire drainée, D8 : l'eau creuse
   d'autant plus qu'elle draine de surface), seulement en montagne et en collines ;
5. agrandi à 8 px par hex, détail fin sur les pentes ; rivières de l'Atlas en vallées douces ; mer de plus en plus
   profonde loin des côtes, montée douce depuis le rivage.

Usage : module (`relief(px, graine, ky)`, même signature que relief_atlas) ; `python relief_alpin.py` = aperçu.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W as W_G, H as H_G, RANG_ATLAS                 # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
T = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASSAGE = os.path.join(ICI, r"couches-expanded\villes-sortie\layer_impassable.hex_layer")


def valeur(forme, echelle, rng):
    """Bruit de valeur lisse (grille aléatoire agrandie en bicubique), ~[-1, 1]."""
    h, w = forme
    gh, gw = max(2, int(h / echelle) + 3), max(2, int(w / echelle) + 3)
    g = rng.standard_normal((gh, gw)).astype(np.float32)
    big = cv2.resize(g, (int((gw - 1) * echelle), int((gh - 1) * echelle)), interpolation=cv2.INTER_CUBIC)
    oy, ox = rng.integers(0, max(1, big.shape[0] - h)), rng.integers(0, max(1, big.shape[1] - w))
    return big[oy:oy + h, ox:ox + w] / 1.1


def fbm(forme, echelle, rng, octaves=5, persistance=0.5):
    tot, amp, norme, e = np.zeros(forme, np.float32), 1.0, 0.0, echelle
    for _ in range(octaves):
        tot += amp * valeur(forme, e, rng)
        norme += amp
        amp *= persistance
        e /= 2.0
    return tot / norme


def multifractal_cretes(forme, echelle, rng, octaves=6, gain=2.2, lacunarite=2.0):
    """Multifractal à crêtes (Musgrave) : arêtes nettes, pics, cols ; ~[0, 1]."""
    tot = np.zeros(forme, np.float32)
    poids = np.ones(forme, np.float32)
    e, amp, norme = echelle, 1.0, 0.0
    for _ in range(octaves):
        s = 1.0 - np.abs(valeur(forme, e, rng))
        s = s * s * poids
        tot += s * amp
        norme += amp
        poids = np.clip(s * gain, 0, 1)
        amp *= 0.5
        e /= lacunarite
    return tot / norme


def erosion_thermique(h, masque, iterations=40, repos=0.9, taux=0.25):
    """Matière qui glisse vers le voisin le plus bas au-delà de la pente de repos (u par pixel), là où `masque`."""
    h = h.copy()
    for _ in range(iterations):
        pad = np.pad(h, 1, mode="edge")
        voisins = [pad[1:-1, 2:], pad[1:-1, :-2], pad[2:, 1:-1], pad[:-2, 1:-1]]
        diffs = np.stack([h - v for v in voisins])
        dmax = diffs.max(0)
        k = diffs.argmax(0)
        exces = np.clip(dmax - repos, 0, None) * taux * masque
        h -= exces
        for i, (dy, dx) in enumerate(((0, 1), (0, -1), (1, 0), (-1, 0))):
            recu = np.where(k == i, exces, 0)
            h += np.roll(np.roll(recu, dy, 0), dx, 1)
    return h


def aire_drainee(h):
    """Aire drainée D8 (nombre de pixels en amont, soi compris)."""
    H, W = h.shape
    plat = h.reshape(-1)
    ordre = np.argsort(-plat, kind="stable")
    pad = np.pad(h, 1, mode="edge")
    depl = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    pentes = np.stack([(h - pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]) / (1.414 if dy and dx else 1.0)
                       for dy, dx in depl])
    k = pentes.argmax(0)
    descend = pentes.max(0) > 0
    ys, xs = np.divmod(np.arange(H * W), W)
    dy = np.array([d[0] for d in depl])[k.reshape(-1)]
    dx = np.array([d[1] for d in depl])[k.reshape(-1)]
    cible = np.clip(ys + dy, 0, H - 1) * W + np.clip(xs + dx, 0, W - 1)
    cible = np.where(descend.reshape(-1), cible, -1)
    a = np.ones(H * W, np.float64)
    for i in ordre:
        c = cible[i]
        if c >= 0:
            a[c] += a[i]
    return a.reshape(H, W)


def erosion_fluviale(h, fixe, iterations=40, kdt=0.02, m=0.5, repos=None, soulev=None, diffusion=0.0):
    """Érosion fluviale implicite (Braun et Willett, 2013) sur une grille à 1 case = 1 unité de distance : chaque case
    descend vers son receveur (plus forte pente, 8 voisins) de f = kdt · A^m / d, A = aire drainée. `fixe` : cases qui ne
    bougent pas (exutoires : plaines, vallées de jeu). Rend la hauteur et l'aire drainée finale."""
    h = h.astype(np.float64).copy()
    H, W = h.shape
    n = H * W
    depl = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    dist = np.array([1.414 if dy and dx else 1.0 for dy, dx in depl])
    ys, xs = np.divmod(np.arange(n), W)
    fixe_p = fixe.reshape(-1)
    rng = np.random.default_rng(11)
    for _ in range(iterations):
        if soulev is not None:
            h = h + np.where(fixe, 0, soulev)
        # (essai 4 : « peignes » de ravines parallèles sur les pentes régulières, artefact des 8 directions fixes) : les
        # receveurs se choisissent sur la hauteur légèrement bruitée, tirée à neuf à chaque passe
        hb = h + rng.standard_normal(h.shape) * 0.08
        pad = np.pad(hb, 1, mode="edge")
        pentes = np.stack([(hb - pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]) / dist[k] for k, (dy, dx) in enumerate(depl)])
        k = pentes.argmax(0).reshape(-1)
        descend = pentes.max(0).reshape(-1) > 0
        dy = np.array([d[0] for d in depl])[k]
        dx = np.array([d[1] for d in depl])[k]
        rec = np.clip(ys + dy, 0, H - 1) * W + np.clip(xs + dx, 0, W - 1)
        rec = np.where(descend & ~fixe_p, rec, np.arange(n))
        dk = dist[k]
        hp = h.reshape(-1)
        ordre = np.argsort(hb.reshape(-1), kind="stable")
        A = np.ones(n)
        rl = rec.tolist()
        for i in ordre[::-1].tolist():
            c = rl[i]
            if c != i:
                A[c] += A[i]
        f = (kdt * A ** m / dk).tolist()
        hl = hp.tolist()
        for i in ordre.tolist():
            c = rl[i]
            if c != i:
                hl[i] = (hl[i] + f[i] * hl[c]) / (1.0 + f[i])
        h = np.array(hl).reshape(H, W)
        if repos:
            h = erosion_thermique(h.astype(np.float32), (~fixe).astype(np.float32), iterations=2, repos=repos,
                                  taux=0.3).astype(np.float64)
        if diffusion:
            # diffusion des versants (essai 7 : sans elle, crêtes d'un hex alignées sur la grille, « velours côtelé ») :
            # elle fixe l'écartement des vallées
            lap = cv2.Laplacian(h.astype(np.float32), cv2.CV_32F, ksize=1).astype(np.float64)
            h = np.where(fixe, h, h + diffusion * lap)
    return h.astype(np.float32), A.reshape(H, W)


def relief(px, graine, ky, retour_masques=False):
    """Relief de l'Atlas (NH_ATLAS × W hex, nord en haut) à `px` px par hex ; `ky` comme relief_atlas (1 pour le jeu)."""
    sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
    from caime_layers import read_layer
    rng = np.random.default_rng(graine)
    g = np.load(os.path.join(T, "extension_geo.npz"))
    r = np.load(os.path.join(T, "extension_regions.npz"))
    NH, W = g["alt"].shape
    P = 2                                                   # travail (érosion) à 2 px par hex
    lw, lh = W * P, int(round(NH * P * ky))

    def petit(x, interp=cv2.INTER_LINEAR):
        return cv2.resize(np.ascontiguousarray(x[::-1]).astype(np.float32), (lw, lh), interpolation=interp)

    terre_r = r["terre"]
    mer = petit((g["mer"] & ~terre_r).astype(np.float32)) > 0.5
    # (montagne de l'Atlas, plus toute altitude au-dessus du seuil d'infranchissable : l'est des Voûtes restait lisse)
    sys.path.insert(0, T)
    import geo_extension as GE
    mont_hex = (g["montagne"] | (g["alt"] >= GE.SEUIL_INFRANCHISSABLE)).astype(np.float32)
    # MASSIFS RELIÉS (3.10.2026, Charles : « les montagnes du sud connectées aux montagnes de l'est… une continuation ») :
    # là où deux massifs se touchent presque par des cases FERMÉES (coin du Reikland hors jeu entre les Grises et les
    # Voûtes, bande au sud d'Athel Loren), le relief monte en selle de montagne au lieu de retomber en plaine. Fermeture
    # morphologique du masque (rayon 7 hex), jamais sur une case franchissable ni en mer : aucun effet sur le jeu.
    _, imp_t = read_layer(PASSAGE)
    ferme = (imp_t.reshape(H_G, W_G)[RANG_ATLAS:RANG_ATLAS + NH] != 1) & r["terre"]
    k7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    joint = (cv2.morphologyEx(mont_hex.astype(np.uint8), cv2.MORPH_CLOSE, k7).astype(bool) & ferme & ~(mont_hex > 0))
    mont_hex = np.maximum(mont_hex, joint.astype(np.float32))
    alt_src = np.where(terre_r & (g["alt"] <= 0.05), 2.2, g["alt"]).astype(np.float32)
    alt_src = np.maximum(alt_src, np.where(joint, 6.0, 0.0)).astype(np.float32)
    alt = cv2.GaussianBlur(petit(cv2.GaussianBlur(alt_src, (0, 0), 1.2)), (0, 0), P * 2.5)
    mont = np.clip(cv2.GaussianBlur(petit(mont_hex), (0, 0), P * 2.0) * 1.4, 0, 1)
    # (3.10.2026) bords de massif organiques : l'Atlas dessine les Voûtes comme une bande au bord nord droit (y ≈ +28) ;
    # le masque de montagne et l'altitude sont ondulés de ±4 hex (bruit lent) ; les vallées de jeu, creusées d'après la
    # grille, et la zone de WH1 gardée par projet_expanded n'en dépendent pas
    gx0, gy0 = np.meshgrid(np.arange(lw, dtype=np.float32), np.arange(lh, dtype=np.float32))
    ox = fbm((lh, lw), 22 * P, rng, 3) * 4.0 * P
    oy = fbm((lh, lw), 22 * P, rng, 3) * 4.0 * P
    mont_avant, alt_avant = mont.copy(), alt.copy()
    mont = cv2.remap(mont.astype(np.float32), gx0 + ox, gy0 + oy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    alt = cv2.remap(alt.astype(np.float32), gx0 + ox, gy0 + oy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # jamais de montagne de plus sur une terre franchissable (le relief ne doit pas mentir sur le jeu)
    passe = cv2.GaussianBlur(petit((ferme == 0).astype(np.float32)), (0, 0), P * 1.0) > 0.5
    mont = np.where(passe, np.minimum(mont, mont_avant), mont)
    alt = np.where(passe, np.minimum(alt, alt_avant), alt)
    coll = cv2.GaussianBlur(petit(g["colline"].astype(np.float32)), (0, 0), P * 2.0)
    # passage de la grille de jeu (rangées de l'Atlas = rangées RANG_ATLAS.. de la grille)
    _, imp = read_layer(PASSAGE)
    imp = imp.reshape(H_G, W_G)[RANG_ATLAS:RANG_ATLAS + NH]
    vallee_hex = (imp == 1) & (mont_hex > 0) & terre_r
    vallee = petit(vallee_hex.astype(np.float32), cv2.INTER_NEAREST) > 0.5
    # 1. enveloppe
    base = np.interp(alt, [0, 1, 2, 3, 4, 5.3, 7, 10], [0.0, 0.6, 1.6, 2.6, 3.6, 5.0, 7.0, 9.0]).astype(np.float32)
    # 2. montagnes : multifractal à crêtes, domaine à peine déformé
    gx, gy = np.meshgrid(np.arange(lw, dtype=np.float32), np.arange(lh, dtype=np.float32))
    dx = fbm((lh, lw), 30 * P, rng, 3) * 2.0 * P
    dy = fbm((lh, lw), 30 * P, rng, 3) * 2.0 * P
    cr = multifractal_cretes((lh, lw), 14 * P, rng, octaves=6)
    cr = cv2.remap(cr, gx + dx, gy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    lo, hi = np.percentile(cr[mont > 0.5], (3, 99.5)) if (mont > 0.5).any() else (cr.min(), cr.max())
    cr = np.clip((cr - lo) / (hi - lo + 1e-6), 0, 1)
    # (essais 1 et 2 du 3.10 : bruit seul -> plateau, puis « vers » à sommet plat ; les arêtes et les vallées ramifiées
    # d'un vrai massif viennent de l'eau : un dôme aux hauteurs de l'Atlas, puis l'érosion fluviale les sculpte)
    # (essai 3, profil mesuré : plateau de 11 à 13 u entre les vallées, montée en falaise de 3 à 11 u en 6 hex) : piémont
    # en pente douce sur ~6 hex depuis le bord du massif, et une rugosité de départ forte (l'érosion s'en nourrit)
    coeur = cv2.distanceTransform((mont > 0.3).astype(np.uint8), cv2.DIST_L2, 5) / P
    piemont = np.clip(coeur / 6.0, 0, 1)
    piemont = piemont * piemont * (3 - 2 * piemont)
    sommet = np.interp(alt, [3, 5.3, 7, 9, 10], [4.5, 9.0, 12.0, 14.0, 15.0]).astype(np.float32)
    sommet = sommet * (0.6 + 0.4 * np.clip(coeur / 12.0, 0, 1))
    dome = base + np.clip(mont * 1.2, 0, 1) * (sommet - base) * piemont * (0.4 + 0.6 * cr)
    # 3. vallées de jeu : exutoires, au fond d'une auge à hauteur de collines
    fond = np.clip(cv2.GaussianBlur(np.where(vallee, base, 0).astype(np.float32), (0, 0), P * 3) /
                   np.maximum(cv2.GaussianBlur(vallee.astype(np.float32), (0, 0), P * 3), 1e-3), 1.5, 4.5)
    fond = (fond + fbm((lh, lw), 6 * P, rng, 3) * 0.2).astype(np.float32)
    # 4. (essai 6, 3.10.2026 : l'érosion d'un dôme uniforme donnait des plateaux en mesa) ÉROSION AVEC SOULÈVEMENT, à
    # l'échelle de l'hex, jusqu'à l'équilibre : le massif monte pendant que l'eau le creuse ; les exutoires sont les
    # plaines et les vallées de jeu. Puis chaque massif est ramené à l'enveloppe des sommets de l'Atlas.
    h0 = np.where(vallee, fond, dome)

    def hexa(x, interp=cv2.INTER_AREA):
        return cv2.resize(x.astype(np.float32), (W, int(round(NH * ky))), interpolation=interp)
    mont1, vallee1, mer1 = hexa(mont), hexa(vallee.astype(np.float32)) > 0.5, hexa(mer.astype(np.float32)) > 0.5
    fond1, base1 = hexa(fond), hexa(base)
    fixe1 = (mont1 < 0.15) | vallee1 | mer1
    # (aperçu du 3.10 : le coin sud-est restait un plateau lisse, l'eau n'y trouvait aucune sortie) : les bords de la carte
    # sont des exutoires, l'eau s'écoule hors du cadre comme vers une plaine
    bords1 = np.zeros_like(fixe1)
    bords1[:, [0, -1]] = True
    bords1[0, :] = True
    # (au sud, la déchirure : un exutoire sur toute la longueur faisait des ravines parallèles ; quelques exutoires
    # espacés de ~15 hex rassemblent l'eau en bassins)
    for q in range(int(rng.integers(3, 12)), W, 15):
        bords1[-1, max(0, q - 1):q + 2] = True
    fixe1 |= bords1
    depart = fbm(mont1.shape, 6.0, rng, 4) * 1.2 + hexa(cr) * 1.5
    h1 = np.where(fixe1, np.where(vallee1, fond1, base1), base1 + depart)
    h1, aire1 = erosion_fluviale(h1, fixe1, iterations=220, kdt=0.06, m=0.5, repos=2.6, diffusion=0.12,
                                 soulev=(0.12 * np.clip(mont1 * 1.3, 0, 1)).astype(np.float32))
    # enveloppe : relief d'équilibre (au-dessus des exutoires) ramené aux sommets de l'Atlas
    leve = np.clip(h1 - np.where(fixe1, h1, base1), 0, None)
    mx = cv2.dilate(leve, np.ones((9, 9), np.uint8))
    mx = cv2.GaussianBlur(mx, (0, 0), 4.0) + 1e-3
    cible = hexa(sommet) - base1
    h1 = np.where(fixe1, h1, base1 + leve / mx * np.clip(cible, 0, None) * np.clip(mont1 * 1.2, 0, 1))
    h = cv2.resize(h1, (lw, lh), interpolation=cv2.INTER_CUBIC)
    m2 = cv2.resize(np.clip(mont1 * 1.2, 0, 1), (lw, lh), interpolation=cv2.INTER_LINEAR)
    h = h * m2 + h0 * (1 - m2)
    roc = np.clip(mont + coll * 0.6, 0, 1).astype(np.float32)
    h = h * (1 - roc * 0.5) + cv2.GaussianBlur(h, (0, 0), 0.9) * roc * 0.5
    # arêtes secondaires sous l'hex, puis talus
    h = h + mont * (cr - 0.5) * 0.9
    h = erosion_thermique(h.astype(np.float32), roc, iterations=8, repos=1.6, taux=0.3)
    # collines : ondulations ; plaines : houle large
    h = h + fbm((lh, lw), 8 * P, rng, 4) * (0.15 + 0.9 * coll) * (1 - mont) + fbm((lh, lw), 40 * P, rng, 4) * 0.35
    # (essai 8 : gradins en escalier le long des vallées de jeu, au bord des cases fixées) : fond de vallée et bords fondus
    # sur ~1,5 hex
    vdoux = cv2.GaussianBlur(vallee.astype(np.float32), (0, 0), 1.5 * P)
    h = h * (1 - vdoux) + np.minimum(h, fond + 0.3) * vdoux
    lisse = cv2.GaussianBlur(h.astype(np.float32), (0, 0), 1.2 * P)
    bord = np.clip(vdoux * (1 - vdoux) * 4, 0, 1)
    h = (h * (1 - bord) + lisse * bord).astype(np.float32)
    # 5. agrandi, détail fin sur les pentes
    LW, LH = W * px, int(round(NH * px * ky))
    H8 = cv2.resize(h, (LW, LH), interpolation=cv2.INTER_CUBIC)
    roc8 = cv2.resize(roc, (LW, LH), interpolation=cv2.INTER_LINEAR)
    pente8 = np.clip(np.hypot(*np.gradient(cv2.GaussianBlur(H8, (0, 0), px))) * px, 0, 2.0)
    # (Charles, 3.10 : « trop pixelisé… il faut que tout soit smooth ») : aucun détail plus fin qu'un hex
    fin = 1.0 - np.abs(fbm((LH, LW), 3.0 * px, rng, 2))
    H8 = H8 - np.clip(fin, 0, 1) ** 4 * pente8 * 0.25 * roc8 + fbm((LH, LW), 4.0 * px, rng, 2) * 0.05
    H8 = cv2.GaussianBlur(H8.astype(np.float32), (0, 0), 0.35 * px)
    # rivières de l'Atlas : vallées douces (lits creusés par projet_expanded)
    import rivieres_svg_grille as RS
    riv = np.zeros((LH, LW), np.uint8)
    for t in RS.traces():
        p = np.array([[q * px, (NH - (rr - RANG_ATLAS)) * px * ky] for q, rr in t], np.float64)
        cv2.polylines(riv, [np.round(p * 4).astype(np.int32)], False, 1, max(1, px // 2), cv2.LINE_AA, 2)
    dr = cv2.distanceTransform((riv == 0).astype(np.uint8), cv2.DIST_L2, 5) / px
    mont8 = cv2.resize(mont, (LW, LH), interpolation=cv2.INTER_LINEAR)
    H8 = H8 - np.exp(-(dr / 1.8) ** 2) * (0.35 + 1.2 * mont8)
    # mer et rivage
    mer8 = cv2.resize(mer.astype(np.float32), (LW, LH), interpolation=cv2.INTER_LINEAR) > 0.5
    dm = cv2.distanceTransform(mer8.astype(np.uint8), cv2.DIST_L2, 5) / px
    dt = cv2.distanceTransform((~mer8).astype(np.uint8), cv2.DIST_L2, 5) / px
    plancher = 0.15 + 0.45 * (1 - np.exp(-dt / 1.5))
    bruit_mer = fbm((LH, LW), 10 * px, rng, 3) * 0.08
    H8 = np.where(mer8, -0.05 - 1.45 * (1 - np.exp(-dm / 8)) + bruit_mer, np.maximum(H8, plancher)).astype(np.float32)
    if retour_masques:
        return H8, dict(mont=mont8, roc=roc8, mer=mer8)
    return H8, None


if __name__ == "__main__":
    import time
    from PIL import Image
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    h, _ = relief(4, 7, 1.0)
    print(f"relief {h.shape} en {time.time() - t0:.0f} s ; min {h.min():.2f} max {h.max():.2f}")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from apercu_relief_expanded import coloriser
    mer = h <= 0.035
    col = coloriser(h)
    col[mer] = (60, 96, 130)
    gy, gx = np.gradient(np.where(mer, 0, h) * 3.0)
    col = np.clip(col * np.clip(1.0 + (-gx - gy) * 0.55, 0.45, 1.45)[..., None], 0, 255).astype(np.uint8)
    Image.fromarray(col).save(os.path.join(ICI, "apercus", "relief-alpin-essai.jpg"), quality=90)
    z = Image.fromarray(col).crop((180 * 4, (655 - 120) * 4, 560 * 4, 655 * 4))
    z.save(os.path.join(ICI, "apercus", "relief-alpin-essai-voutes.jpg"), quality=92)
    z = Image.fromarray(col).crop((420 * 4, (655 - 520) * 4, 560 * 4, (655 - 120) * 4))
    z.save(os.path.join(ICI, "apercus", "relief-alpin-essai-grises-est.jpg"), quality=92)
    print("aperçus : apercus\\relief-alpin-essai*.jpg")
