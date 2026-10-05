#!/usr/bin/env python3
"""
cotes_relief.py - le relief des CÔTES selon la tuile de côte, comme CA (5.10.2026) ; appelé par `projet_expanded`.

Pourquoi (Charles, 5.10.2026, en jeu après les fleuves : « beaucoup d'effets escaliers sur les bords des rivières… les
côtes, beaucoup de trucs en carré… les falaises au bon endroit, les plages au bon endroit… pas d'escalier du tout » ;
puis « sers-toi vraiment de la documentation de CAIME… des guides ») :
- CAIME (documentation officielle, `docs\\user-guide-processing-and-exporting.md` § 4.2 ; guide CAIME de l'Atlas) : la
  carte des tuiles est exportée des couches Roads, Rivers, Cliffs, Beaches ; pour CAIME, tout hex de terre qui touche la
  mer sans être une PLAGE est une FALAISE (`cliff_gen`) : où vont falaises et plages se décide dans la couche Beaches ;
- guide Terry de l'Atlas : tile_map.png exportée sans retouche ; « le fond visuel de la côte se règle dans Terry » ; fond
  sous 0 sur la mer ; « Une côte lisse en jeu » : sans tuile de falaise (côte de la Saison, `generic`), la surface coupe 0
  en pente douce ; le guide ne dit rien du relief sous une tuile de falaise ;
- donc, « ce que fait CA » vérifié sur les fichiers de CA (`scratchpad\\profil_cote_ca.py`, `profil_cote_comparer.py`,
  Empires Immortels, relief et fond du kit, distances au trait des tuiles) :
  · FALAISE (`cliff_gen`, `cliff_gen_ends`, `cliff_custom`) : la terre de la tuile est un plateau, médiane 0,74 u (p10
    0,28, p90 1,23) de 0 à 1 u du trait ; le fond de la mer voisine −0,40 (p10 −0,76, p90 −0,18) : la paroi est celle de
    la tuile, entre les deux ;
  · PLAGE (`sea_coast` et variantes) : la terre passe SOUS l'eau au trait (−0,16 à 0-0,15 u, −0,08 à 0,15-0,3, +0,05
    à 0,3-0,6, +0,12 à 0,6-1 u) ; le fond voisin −0,19 (p10 −0,34, p90 −0,07) : continu ;
  · Expanded avant ce module (`marches_cote.py`) : terre 0,13 au trait partout, fond −0,63 : trop basse pour la paroi
    d'une falaise, trop haute pour une plage.
Règle : le profil de CA selon la tuile, sur la terre de la tuile et une bande derrière (fondu), et sur la mer voisine ;
une côte de terre sans falaise ni plage (anneau des lacs, lisière) garde la pente douce du guide Terry. Hors du Bois
Rêveur ; la terre sous les montagnes de WH1 gardées (maillages drapés) n'est jamais touchée. Rend la différence de
relief (objets de WH1 et rubans la suivent, comme pour les chenaux).
"""
import cv2
import numpy as np

# CA, falaises
# (premier essai : plancher à 0,45, toute notre côte basse y tombait, médiane 0,45 contre 0,74 chez CA)
# (5.10.2026, Charles : « des falaises vraiment impressionnantes, majestueuses ») plancher à la MÉDIANE de CA, plafond à
# son p90 : la paroi de la tuile monte de ~1,1 à ~1,6 u au-dessus du fond, comme les plus hautes de CA, sans dépasser CA
FALAISE_MIN, FALAISE_MAX = 0.74, 1.23     # plateau de la terre de la tuile (CA : p10 0,28, médiane 0,74, p90 1,23)
FALAISE_P10 = 0.28
FOND_FALAISE = (-0.80, -0.25)             # fond de la mer voisine (CA : p10 −0,76, médiane −0,40, p90 −0,18)
# CA, plages : relief = PLAGE_BORD + PLAGE_PENTE · d (u), jusqu'à PLAGE_HAUT
PLAGE_BORD, PLAGE_PENTE, PLAGE_HAUT = -0.17, 0.33, 0.13
FOND_PLAGE = (-0.35, -0.12)               # (CA : p10 −0,34, médiane −0,19, p90 −0,07)
# guide Terry (côte sans tuile de côte) : pente douce autour de 0
BORD_TERRE, BORD_MER, PENTE = 0.03, -0.03, 0.5
BANDE_U = 1.0                             # bande derrière la tuile où le profil se fond dans le relief d'origine
RACCORD_U, RACCORD_BAS, RACCORD_HAUT = 0.8, 0.12, 0.4     # falaise au contact d'une plage (CA : 0,15 à 0,21)
HAUTEUR_SUR_MER = 0.02
MER_U = 1.0                               # mer voisine réglée jusqu'à 1 u du trait
LISSE_HEX = 0.7                           # côte lissée : tuiles de mer floutées sur 0,7 hex (angles d'hex arrondis)
PARTS_HEX = 1.0                           # parts falaise / plage lissées sur 1 hex
MER_RELIEF_U = 1.5                        # le relief sous la mer rejoint 0,02 en 1,5 u (CA : il reste haut, voir mer_tuiles)

COUL = {"mer": [(83, 141, 213)], "falaise": [(253, 3, 1), (84, 230, 84), (254, 0, 0)],
        "plage": [(255, 255, 0), (220, 180, 0), (255, 255, 170)]}


def masques_tuiles(tm, forme, lacs=None):
    """(mer, falaise, plage) à la résolution `forme` du relief, depuis tile_map.png (RVB ou RVBA) ; `lacs` (à la taille
    des tuiles) comptés comme eau."""
    def m(nom):
        return np.any([(tm[..., :3] == c).all(-1) for c in COUL[nom]], 0)
    mer = m("mer") if lacs is None else (m("mer") | lacs)
    out = []
    for a in (mer, m("falaise"), m("plage")):
        out.append(cv2.resize(a.astype(np.uint8), (forme[1], forme[0]), interpolation=cv2.INTER_NEAREST) > 0)
    return out


def _fondu(d, largeur):
    t = np.clip(d / largeur, 0, 1)
    return 1 - t * t * (3 - 2 * t)


def _lisse(m, sigma_px):
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), sigma_px)


def raccorder(height, sea, mer, falaise, plage, u_par_px, epargne=None, hors=None):
    """(height, sea, delta, bilan). `epargne` : terre jamais touchée ; `hors` : rien touché (Bois Rêveur).

    (5.10.2026, deuxième version, Charles en jeu : « encore des hachures, des escaliers ») la première version prenait
    ses distances au trait des TUILES (en hex) : terrasses en escalier dans le relief même, et relief des tuiles de mer
    remis à 0,02, une marche au bord de chaque tuile. CA (relief ombré au pixel) : relief lisse, continu sous la mer.
    Désormais tout se calcule sur une côte LISSÉE (tuiles de mer floutées sur LISSE_HEX hex, seuil 0,5) et des parts
    lissées falaise / plage ; le relief passe le trait sans marche : sous la mer, il prolonge celui de la côte la plus
    proche et rejoint la surface (0,02) au large, sur MER_RELIEF_U."""
    hors = np.zeros(mer.shape, bool) if hors is None else hors
    epargne = (np.zeros(mer.shape, bool) if epargne is None else epargne) | hors
    px_hex = 0.666325 / u_par_px
    mer_s = _lisse(mer, LISSE_HEX * px_hex) > 0.5                 # côte lissée (arrondie, sans angle d'hex)
    terre_s = ~mer_s
    d_t = cv2.distanceTransform(terre_s.astype(np.uint8), cv2.DIST_L2, 5) * u_par_px     # terre -> côte lissée
    d_m = cv2.distanceTransform(mer_s.astype(np.uint8), cv2.DIST_L2, 5) * u_par_px       # mer -> côte lissée
    f_f, f_p = _lisse(falaise, PARTS_HEX * px_hex), _lisse(plage, PARTS_HEX * px_hex)
    w_pl = f_p / np.maximum(f_f + f_p, 1e-6)                   # part de plage (0 : falaise) ; lissée
    cote = (f_f + f_p) > 0.01                                   # près d'une tuile de côte
    avant, sea0 = height.copy(), sea.copy()
    # 1. LA TERRE DE LA BANDE : falaise = plateau de CA (abaissé au contact d'une plage, CA 0,15-0,21), plage = profil de CA
    #    selon la distance à la côte lissée ; côte sans tuile de côte : pente douce du guide Terry
    # (5.10.2026, aperçu de la Brienne : une DIGUE sombre le long de la berge nord, plateau relevé à 0,74 au-dessus de
    # terres plus basses derrière) chez CA, la terre près des côtes est elle-même à ~0,65 : la falaise ne la surélève pas.
    # Le plancher du plateau ne dépasse pas la terre voisine (moyenne floutée sur ~2 hex de la terre seule), sans descendre
    # sous le p10 de CA (0,28)
    t_m = _lisse(terre_s, 2 * px_hex)
    voisine = _lisse(np.where(terre_s, height, 0), 2 * px_hex) / np.maximum(t_m, 1e-3)
    plancher = np.clip(voisine, FALAISE_P10, FALAISE_MIN)
    lo = plancher * (1 - w_pl) + RACCORD_BAS * w_pl
    hi = FALAISE_MAX * (1 - w_pl) + RACCORD_HAUT * w_pl
    cible_f = np.clip(height, lo, hi)
    profil = np.minimum(PLAGE_BORD + PLAGE_PENTE * d_t, np.maximum(height, PLAGE_HAUT))
    cible_c = cible_f * (1 - w_pl) + profil * w_pl
    cible_a = np.minimum(height, BORD_TERRE + PENTE * d_t)
    cible = np.where(cote, cible_c, cible_a)
    w = _fondu(d_t, BANDE_U) * (terre_s & ~epargne)
    height = (height * (1 - w) + cible * w).astype(np.float32)
    # 2. LE RELIEF SOUS LA MER (côte lissée) : continu avec la terre la plus proche, rejoint 0,02 au large
    _, lab = cv2.distanceTransformWithLabels(mer_s.astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    val = np.zeros(int(lab.max()) + 1, np.float32)
    val[lab[terre_s]] = height[terre_s]
    pres_terre = val[lab]
    t = 1 - _fondu(d_m, MER_RELIEF_U)
    sous_mer = mer_s & ~epargne
    height = np.where(sous_mer, pres_terre * (1 - t) + HAUTEUR_SUR_MER * t, height).astype(np.float32)
    # 3. LE FOND DE LA MER VOISINE (jusqu'à MER_U de la côte lissée) : CA selon la part falaise / plage ; plage : il
    #    prolonge la pente de la plage (continu avec la terre à −0,17) ; ailleurs, pente douce
    fond_f = np.clip(sea, FOND_FALAISE[0], FOND_FALAISE[1])
    fond_p = np.clip(PLAGE_BORD - PLAGE_PENTE * d_m, FOND_PLAGE[0], FOND_PLAGE[1])
    fond_c = fond_f * (1 - w_pl) + fond_p * w_pl
    fond_a = np.minimum(sea, BORD_MER - PENTE * d_m)
    cible_m = np.where(cote, fond_c, fond_a)
    w_m = _fondu(d_m, MER_U) * ((mer_s | mer) & ~hors)
    sea = (sea * (1 - w_m) + cible_m * w_m).astype(np.float32)
    sea = np.where((mer | mer_s) & ~hors & (sea > BORD_MER), BORD_MER, sea).astype(np.float32)   # jamais au-dessus
    delta = (height - avant).astype(np.float32)
    bilan = {"terre_bande_px": int((w > 0).sum()), "relief_sous_mer_px": int(sous_mer.sum()),
             "fond_px": int((np.abs(sea - sea0) > 1e-4).sum()),
             "levee_max_u": float(delta.max()), "baisse_max_u": float(-delta.min())}
    return height, sea, delta, bilan


# LES TEXTURES DU RIVAGE (5.10.2026, Charles : « que les côtes soient vraiment parfaites… que les plages soient vraiment
# belles ») : la recette de la Saison validée par Charles (« comme dans WH1 », correctifs C1 à C4,
# `02-scripts\textures_tuiles_wh1.py`), posée sur la côte LISSÉE de toute la carte (l'Atlas et les chenaux des fleuves
# n'avaient que la texture de leur sol jusqu'à l'eau, en bords d'hex) : sous la mer le sable sombre `sand_b3` ; au rivage
# une bande de la boue des plages de WH1 `mud_a0`, de largeur modulée par un bruit lisse, plus large sur les plages ; sous
# l'eau des rivières de l'Atlas le marais de WH1, sur leurs berges le sable `sand_a0` (indices du mélange de WH1, 19 groupes)
INDEX_SAND_B3, INDEX_MUD_A0, INDEX_SAND_A0, INDEX_MARSH = 0, 3, 4, 12
RIVAGE_U, RIVAGE_PLAGE_U, RIVAGE_BRUIT_U = 0.25, 0.7, 0.12


def textures_rivage(monde, mer, plage, u_par_px, hors, eau_riv=None, graine=51005, garde=None, chenal=None):
    """(monde, bilan) : indices de texture de WH1 (8 px par hex, nord en haut ; 255 = texture de BOB gardée).
    Dans la zone gardée de WH1 (`garde`), les textures de la Saison restent (validées : pas de boue dans les deltas,
    Charles 25.09) sauf près des chenaux des fleuves (`chenal`, à 3 hex), qui n'y étaient pas."""
    if garde is not None:
        px_hex_ = 0.666325 / u_par_px
        pres_ch = (cv2.dilate(chenal.astype(np.uint8), cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (int(6 * px_hex_) | 1, int(6 * px_hex_) | 1))) > 0) if chenal is not None else \
            np.zeros(mer.shape, bool)
        hors = hors | (garde & ~pres_ch)
    px_hex = 0.666325 / u_par_px
    mer_s = _lisse(mer, LISSE_HEX * px_hex) > 0.5
    d_t = cv2.distanceTransform((~mer_s).astype(np.uint8), cv2.DIST_L2, 5) * u_par_px
    w_pl = _lisse(plage, PARTS_HEX * px_hex)
    w_pl = np.clip(w_pl / max(float(w_pl.max()), 1e-6) * 3, 0, 1)
    rng = np.random.default_rng(graine)
    br = cv2.GaussianBlur(rng.standard_normal(mer.shape).astype(np.float32), (0, 0), 0.6 * px_hex)
    br = br / max(float(np.abs(br).max()), 1e-6)
    largeur = RIVAGE_U * (1 - w_pl) + RIVAGE_PLAGE_U * w_pl + RIVAGE_BRUIT_U * br
    out = monde.copy()
    fond = mer_s & ~hors
    rivage = ~mer_s & ~hors & (d_t <= np.maximum(largeur, 0.05))
    out[fond] = INDEX_SAND_B3
    out[rivage] = INDEX_MUD_A0
    n_lit = n_berge = 0
    if eau_riv is not None:
        lit = eau_riv & ~mer_s & ~hors
        berge = (cv2.dilate(lit.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & ~lit & ~mer_s & ~hors & ~rivage
        out[berge] = INDEX_SAND_A0
        out[lit] = INDEX_MARSH
        n_lit, n_berge = int(lit.sum()), int(berge.sum())
    return out, {"fond_sand_b3_px": int(fond.sum()), "rivage_mud_a0_px": int(rivage.sum()),
                 "lits_marais_px": n_lit, "berges_sable_px": n_berge}


def profil(height, sea, mer, falaise, plage, u_par_px, masque=None):
    """Médianes par tranche de distance au trait (comme `profil_cote_ca.py`) : terre des falaises, des plages, mer."""
    m_ok = np.ones(mer.shape, bool) if masque is None else masque
    d_t = cv2.distanceTransform((~mer).astype(np.uint8), cv2.DIST_L2, 5) * u_par_px
    d_m = cv2.distanceTransform(mer.astype(np.uint8), cv2.DIST_L2, 5) * u_par_px
    d_f = cv2.distanceTransform((~falaise).astype(np.uint8), cv2.DIST_L2, 5) * u_par_px
    d_p = cv2.distanceTransform((~plage).astype(np.uint8), cv2.DIST_L2, 5) * u_par_px
    out = {}
    for nom, t in (("falaise", falaise), ("plage", plage)):
        for a, b in ((0, 0.15), (0.15, 0.3), (0.3, 0.6), (0.6, 1.0)):
            m = t & m_ok & (d_t > a) & (d_t <= b)
            if m.sum() > 30:
                out[f"terre {nom} {a}-{b}"] = round(float(np.median(height[m])), 2)
        cote = (d_f <= d_p) if nom == "falaise" else (d_p < d_f)
        m = mer & m_ok & cote & (d_m <= 0.6)
        if m.sum() > 30:
            out[f"fond {nom} 0-0.6"] = round(float(np.median(sea[m])), 2)
    return out
