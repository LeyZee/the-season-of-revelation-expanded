#!/usr/bin/env python3
"""
depart_atlas.py - le départ d'Expanded par-dessus la recopie de la Saison (3.10.2026) : régions neuves et leurs maîtres,
factions de départ absentes de la Saison (les 16 de l'Atlas et celles de CA), leurs chefs et leurs armées, Kemmler à
Krinal avec Krell, la diplomatie de la fiche.

Pourquoi : répartition avec la Construction (3.10.2026) : elle a recopié le départ de la Saison vers `saison_expanded`
(`02-scripts\\recopier_depart_expanded.py`, correspondance `depart\\correspondance_depart.json`) ; cette session ajoute,
en lot à part, ce qui est propre à Expanded. Sources : `expanded_declaration.json` (régions, faction de départ de
chacune, départ de Kemmler), `decisions-maitres.json` (11 maîtres tranchés par Charles le 25.09), fiche du lot
`05-journal\\2026-10-03-expanded-suite\\fiche-factions-atlas.md` (hordes, diplomatie).

Méthode (même que la recopie : `TableKit`, identifiants `ident_numerique` à graine « expanded-atlas:… ») :
- FACTIONS : chaque faction de départ d'une région neuve, ou horde de la fiche, absente de `saison_expanded` reçoit sa
  ligne `start_pos_factions`, faite sur celle des Empires (factions de CA) ou sur celle de son modèle
  (`factions_atlas.FACTIONS`) ; jamais jouable (les dix seigneurs jouables restent ceux de la Saison) ;
- RÉGIONS : chaque région terrestre de la carte d'Expanded sans ligne de départ reçoit `start_pos_regions` (maître, capitale
  de faction, culture), sa colonie (`start_pos_settlements` : bâtiment principal de la culture du maître, majeur pour une
  capitale de province, port s'il y a un port ; ruine sans maître) et ses emplacements (`start_pos_region_slot_templates` :
  ceux de la région de WH1 en miroir pour le Bois Rêveur, sinon les génériques humains de CA, majeurs ou mineurs, à port) ;
- CHEFS ET ARMÉES : chaque faction neuve reçoit son chef de faction (celui des Empires pour une faction de CA, celui du
  modèle pour une des nôtres), en armée sur une case franchissable libre près de sa capitale (ou au lieu de la fiche pour
  une horde), avec l'armée de CA du même personnage, sinon celle d'un général de la même sous-culture ; horde : ses
  détails de horde ;
- KEMMLER : sa capitale passe du Poste de la Pierre Noire (rendu à Karak Ziflin, colonie naine) à Krinal ; Kemmler en armée
  devant Krinal, Krell (héros des Empires 9.0) à côté ;
- DIPLOMATIE : celle de la fiche (alliances des nains des Voûtes autour d'Izor et commerce entre eux ; guerres Izor /
  Brise-Nuques, Grom / Gutrippaz, Teef Snatchaz / Gisoreux, Lakemen / hardes).
Les guerres « au tour N » de la fiche (Grom contre l'Aquitanie, Orques de fer contre la Fée) sont des scripts : hors de ce lot.

Essai à blanc par défaut ; `--apply` : préavis du kit d'abord ; sauvegarde des XML touchés dans
`05-journal\\db-backups\\<date>-depart-atlas\\` ; idempotent (une seconde passe n'écrit rien). Puis la Construction
synchronise le startpos et le génère (erreur 107 : essai de démarrage avant toute annonce).

Usage : python depart_atlas.py [--apply]
"""
import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadre_expanded import W, H, DX, DY                                   # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
from donnees_campagne import TableKit, ident_numerique                   # noqa: E402
from caime_layers import read_layer, caime_names                         # noqa: E402
import factions_atlas as FA                                              # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
TRAVAIL = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail")
CORR = os.path.join(ICI, r"depart\correspondance_depart.json")
CAIME = os.path.join(ATELIER, r"01-outils\CampaignMapToolkit\CAIME\bin\Debug\CAIME.exe")
CARTE = os.path.join(ICI, r"caime\saison_expanded_map\map.hex")
SORTIE_GRILLE = os.path.join(ICI, r"couches-expanded\villes-sortie")
CAMP, COMBI, SAISON = "saison_expanded", "wh3_main_combi", "wh_dlc05_wood_elves"
v = TableKit.valeurs

# hordes et camps de la fiche : lieu de départ dans le repère de l'Atlas (x, y) -> Expanded (x + 120, y + 330)
HORDES = {"saison_bst_khorok_manripper": (68, 386), "saison_bst_harrowmaw": (30, 335), "saison_bst_lakemen": (25, 372),
          "saison_ogr_osseine": (232, 326)}
# préfixe des bâtiments de colonie par sous-culture du maître (building_levels : <p>_settlement_major_1, _minor_1,
# _port_1 et leurs ruines existent pour chacun, relevé du 3.10)
PREFIXES = {"wh_main_sc_brt_bretonnia": "wh_main_brt", "wh_main_sc_dwf_dwarfs": "wh_main_dwf",
            "wh_main_sc_grn_greenskins": "wh_main_grn", "wh_main_sc_grn_savage_orcs": "wh_main_grn",
            "wh_main_sc_emp_empire": "wh_main_emp", "wh3_main_sc_ogr_ogre_kingdoms": "wh3_main_ogr",
            "wh2_main_sc_hef_high_elves": "wh2_main_hef", "wh3_main_sc_sla_slaanesh": "wh3_main_sla",
            "wh_main_sc_vmp_vampire_counts": "wh_main_vmp"}
# sous-culture -> (bâtiment principal majeur, mineur, port)
BATIMENTS = {sc: (f"{p}_settlement_major_1", f"{p}_settlement_minor_1", f"{p}_port_1") for sc, p in PREFIXES.items()}
# elfes sylvains : comme dans la Saison, toutes leurs colonies sont « majeures » (wh_dlc05_wef_settlement_major_main_*)
BATIMENTS["wh_dlc05_sc_wef_wood_elves"] = ("wh_dlc05_wef_settlement_major_main_1",) * 2 + ("wh_dlc05_wef_port_1",)
# factions de CA sans ligne de départ aux Empires (posées par script chez CA) : ligne et chef faits sur un modèle de même
# sous-culture
SANS_DEPART_IE = {"wh3_dlc20_brt_march_of_couronne": "wh_main_brt_lyonesse"}
# chefs de faction de CA qui n'ont rien à faire sur cette carte (lore) : remplacés par un général ordinaire de la même
# sous-culture (personnage des Empires donneur). (4.10.2026, décision de la session, autorisation de Charles : « tu as
# toutes mes autorisations ») Karl Franz ne quitte pas Altdorf pour Helmgart : un général impérial ordinaire, Helmut
# Ludenhof (général des Séparatistes aux Empires, sans rôle dans le lore ; pas celui d'Ostland, Valmir von Raukov,
# comte électeur nommé)
CHEFS_ORDINAIRES = {"wh_main_emp_empire": "1093690084"}
COLONNES_PERSONNE = ("Name", "Surname", "subtype", "portrait_id", "model", "immortal", "override_general_unit",
                     "clan_name", "other_name", "legacy_override", "unique")
# (4.10.2026, plantages au startpos d'Expanded) une RUINE, chez CA comme dans la Saison, a TOUJOURS une culture, une
# faction rebelle et un bâtiment de ruine (Tal Rond : wh_dlc05_wef_settlement_major_main_ruin, culture des elfes
# sylvains, rebelles d'Anmyr ; aux Empires : wh_main_vmp_settlement_minor_ruin…) ; les nôtres n'avaient rien.
# région -> (sous-culture, faction rebelle, bâtiment principal, bâtiment de port) selon le peuple de chaque lieu
RUINES = {
    "saison_ile_silencieuse": ("wh_main_sc_brt_bretonnia", "wh_main_brt_bretonnia_rebels",
                               "wh_main_brt_settlement_minor_ruin", "wh_main_brt_port_ruin"),
    "saison_voutes_stonewrath": ("wh_main_sc_dwf_dwarfs", "wh_main_dwf_dwarf_rebels", "wh_main_dwf_settlement_minor_ruin", ""),
    "saison_voutes_karag_dar": ("wh_main_sc_dwf_dwarfs", "wh_main_dwf_dwarf_rebels", "wh_main_dwf_settlement_minor_ruin", ""),
    "saison_carcassonne_tumulus_de_grudsnik": ("wh_main_sc_grn_greenskins", "wh_main_grn_greenskins_rebels",
                                               "wh_main_grn_settlement_minor_ruin", ""),
    "saison_atylwyth_tal_mora": ("wh_dlc05_sc_wef_wood_elves", "wh_dlc05_wef_atylwyth",
                                 "wh_dlc05_wef_settlement_major_main_ruin", ""),
    "saison_dame_grise_chateau_de_sanglac": ("wh_main_sc_brt_bretonnia", "wh_main_brt_bretonnia_rebels",
                                             "wh_main_brt_settlement_minor_ruin", ""),
}
KEMMLER, KRELL_IE, POSTE = "wh2_dlc11_vmp_the_barrow_legion", "1366449517", "wh_dlc05_grey_mountains_2_blackstone_post"
ZIFLIN = "wh_main_dwf_karak_ziflin"
KRINAL = "saison_voutes_krinal"
# diplomatie de la fiche : (faction 1, faction 2, état, accès militaire, commerce, pacte de non-agression)
IZOR = "saison_dwf_karak_izor"
NAINS_VOUTES = ["saison_dwf_karak_kaferkammaz", "saison_dwf_karak_eksfilaz", "saison_dwf_karak_grom",
                "saison_dwf_karak_bhufdar"]
# (4.10.2026, plantage +0x2602213 sur saison_tor_soleil:0, cause trouvée par la Construction : chez CA, Aislinn
# (wh3_dlc27_hef_aislinn) est une HORDE qui ne tient aucune région ; l'Atlas lui donnait les trois Tor ; décision de
# Charles : « faction elfe mineure ») les trois Tor passent à notre colonie hef mineure (factions_atlas), Tor Soleil
# capitale ; Aislinn reste une horde, sa mécanique de CA intacte, alliée de la colonie au départ
TOR_SOLEIL, AISLINN = "saison_hef_tor_soleil", "wh3_dlc27_hef_aislinn"
MAITRES_CORRIGES = {"saison_tor_soleil": TOR_SOLEIL, "saison_tor_martel": TOR_SOLEIL,
                    "saison_tor_martel_petite": TOR_SOLEIL}
CAPITALES_CORRIGEES = {TOR_SOLEIL: "saison_tor_soleil"}


def maitre_de(r):
    """Le maître de départ d'une région de la déclaration, corrections de MAITRES_CORRIGES comprises."""
    return MAITRES_CORRIGES.get(r["cle_jeu"], r.get("faction_depart"))


DIPLOMATIE = ([(IZOR, n, "military_allies", "1", "1", "1") for n in NAINS_VOUTES]
              + [(TOR_SOLEIL, AISLINN, "military_allies", "1", "1", "1")]
              + [(a, b, "neutral", "0", "1", "1") for i, a in enumerate(NAINS_VOUTES) for b in NAINS_VOUTES[i + 1:]]
              + [(IZOR, "saison_grn_brise_nuques", "war", "0", "0", "0"),
                 ("saison_dwf_karak_grom", "saison_grn_gutrippaz", "war", "0", "0", "0"),
                 ("wh_main_grn_teef_snatchaz", "wh_dlc05_brt_gisoroux", "war", "0", "0", "0"),
                 ("saison_bst_lakemen", "saison_bst_khorok_manripper", "war", "0", "0", "0"),
                 ("saison_bst_lakemen", "saison_bst_harrowmaw", "war", "0", "0", "0")])


class Lot:
    def __init__(self):
        self.t = {}
        self.journal = []

    def T(self, nom):
        if nom not in self.t:
            self.t[nom] = TableKit(nom)
        return self.t[nom]

    def ident(self, nom, col, graine):
        t = self.T(nom)
        pris = getattr(t, "_pris_" + col, None)
        if pris is None:
            pris = {v(c).get(col) for _, c in t.lignes}
            setattr(t, "_pris_" + col, pris)
        n = ident_numerique(f"expanded-atlas:{nom}:{graine}", pris)
        pris.add(n)
        return n

    def copier(self, nom, cle, corps, changes):
        t = self.T(nom)
        anciennes = t.valeurs(corps)
        neuve = cle
        for c, val in changes.items():
            corps = t.avec(corps, c, val)
            vieux = anciennes.get(c, "")
            if vieux and vieux != val and neuve == vieux:          # clé = l'identifiant seul (court : « 60 »)
                neuve = val
            elif len(vieux) >= 3 and vieux != val and vieux in neuve:
                neuve = neuve.replace(vieux, val, 1)
        if neuve == cle:
            raise SystemExit(f"{nom} : la clé {cle} ne change pas")
        return t.ajouter(neuve, corps)

    def une(self, nom, **egal):
        l = self.T(nom).ou(**egal)
        if not l:
            raise SystemExit(f"{nom} : aucune ligne {egal}")
        return l[0]


def grille():
    """(région de chaque case par nom, case principale de chaque région, cases libres pour une armée)."""
    listes, _, _ = caime_names(CAIME, CARTE)
    noms = listes.get("Land regions", []) + listes.get("Sea regions", [])
    reg = read_layer(os.path.join(SORTIE_GRILLE, "layer_regions.hex_layer"))[1].reshape(H, W)
    slots = read_layer(os.path.join(SORTIE_GRILLE, "layer_townslots.hex_layer"))[1].reshape(H, W)
    etal = read_layer(os.path.join(SORTIE_GRILLE, "layer_townsprawl.hex_layer"))[1].reshape(H, W)
    imp = read_layer(os.path.join(SORTIE_GRILLE, "layer_impassable.hex_layer"))[1].reshape(H, W)
    gt = read_layer(os.path.join(SORTIE_GRILLE, "layer_groundtypes.hex_layer"))[1].reshape(H, W)
    terre = gt < len(listes.get("Land ground types", []))
    ville = {}
    for r, q in zip(*np.nonzero(slots == 0)):                   # index 0 = emplacement principal
        if reg[r, q] >= 0:
            ville.setdefault(noms[reg[r, q]], (int(q), int(r)))
    libre = (imp == 1) & terre & (slots < 0) & (etal == 0)
    return noms, reg, ville, libre


def case_libre(libre, reg, q0, r0, region_i=None, pris=()):
    """La case franchissable libre la plus proche de (q0, r0) (dans la région si donnée), à 2 cases au moins."""
    for rayon in range(2, 25):
        meilleur = None
        for dr in range(-rayon, rayon + 1):
            for dq in range(-rayon, rayon + 1):
                q, r = q0 + dq, r0 + dr
                if not (0 <= q < W and 0 <= r < H) or max(abs(dq), abs(dr)) != rayon or (q, r) in pris:
                    continue
                if libre[r, q] and (region_i is None or reg[r, q] == region_i):
                    d = dq * dq + dr * dr
                    if meilleur is None or d < meilleur[0]:
                        meilleur = (d, q, r)
        if meilleur:
            return meilleur[1], meilleur[2]
    raise SystemExit(f"aucune case libre près de ({q0}, {r0})")


ELFES_SYLVAINS = "wh_dlc05_sc_wef_wood_elves"
# elfes sylvains (relevé du 4.10, slot_template_permitted_building_chains) : waterfall_palace_primary = le seul jeu
# « primary_core_special_major_forest » (colonie de forêt majeure, sans monument : toutes les colonies elfes sylvaines
# sont majeures, BATIMENTS), le plus employé par CA pour une colonie elfe sylvaine et celui d'Athel Loren dans la Saison ;
# secondaire : wh_dlc05_elf_major_secondary (garnison majeure + « secondary_core_generic_major_variant_wef_forest »),
# celui des colonies elfes de la Saison ; PAS waterfall_palace_secondary, qui porte le monument du Palais des Cascades
MODELES_ELFES = (("primary", "wh_main_special_waterfall_palace_primary"),
                 ("secondary", "wh_dlc05_elf_major_secondary"))


# RECETTES DE CA (4.10.2026 ; plantage au chargement +0x2602213, « bâtiment introuvable », nommé par la Construction sur
# saison_tor_soleil:0 : modèle wh3_dlc27_human_major_primary_port + wh2_main_hef_settlement_major_1, combinaison
# qu'aucun port haut-elfe de CA n'emploie). Règle : une région neuve prend une combinaison (modèles, bâtiment principal,
# bâtiment de port) que CA emploie pour la même sous-culture, la même taille et la même présence de port ; relevé des
# tables de départ de CA (start_pos_regions / settlements / region_slot_templates des campagnes de CA), exemple cité.
RECETTES_CA = {
    # Citadelle du Crépuscule (wh3_main_combi_region_citadel_of_dusk) : la colonie elfe, le plus proche du lore pour les
    # tours d'Aislinn en Bretonnie ; secondaire : wh_main_human_major_secondary, le jeu de celui de la Citadelle
    # (garnison majeure + generic major) sans le monument de la Citadelle
    ("wh2_main_sc_hef_high_elves", "major", True): {
        "modeles": {"primary": "wh2_main_special_elven_colony_major_primary", "secondary": "wh_main_human_major_secondary",
                    "port": "wh_main_port"},
        "primary_building": "wh2_main_special_settlement_colony_major_hef_1", "port_building": "wh2_main_hef_port_1"},
    # 5 ports hauts-elfes mineurs de CA (dont wh3_main_combi_region_mistnar)
    ("wh2_main_sc_hef_high_elves", "minor", True): {
        "modeles": {"primary": "wh3_dlc27_human_minor_primary_port", "secondary": "wh_main_human_minor_secondary",
                    "port": "wh_main_port"},
        "primary_building": "wh2_main_hef_settlement_minor_2", "port_building": "wh2_main_hef_port_1"},
    # Lyonesse de CA (wh3_main_combi_region_lyonesse)
    ("wh_main_sc_brt_bretonnia", "major", True): {
        "modeles": {"primary": "wh3_dlc27_human_major_primary_port", "secondary": "wh_main_human_major_secondary",
                    "port": "wh_main_port"},
        "primary_building": "wh_main_brt_settlement_major_2", "port_building": "wh_main_brt_port_1"},
    # Château de Tancred, Château d'Artois de CA : 3 sur 3 en major_2 avec ce modèle
    ("wh_main_sc_brt_bretonnia", "major", False): {
        "modeles": {"primary": "wh_main_human_major_primary", "secondary": "wh_main_human_major_secondary"},
        "primary_building": "wh_main_brt_settlement_major_2", "port_building": ""},
    # Slaanesh sans port : CA n'a AUCUNE colonie majeure générique (ses majeures sont des lieux spéciaux) ; 6 colonies
    # mineures génériques en sla_settlement_minor_1 (dont wh3_main_chaos_region_the_tower_of_flies)
    ("wh3_main_sc_sla_slaanesh", "major", False): {
        "modeles": {"primary": "wh_main_human_minor_primary", "secondary": "wh_main_human_minor_secondary"},
        "primary_building": "wh3_main_sla_settlement_minor_1", "port_building": ""},
}


def modeles_du_lore(L, r, sc, taille, port):
    """[(slot_type, slot_template)] d'une région neuve d'Expanded, selon la culture de son maître (4.10.2026).

    (Plantage au chargement +0x2602213, session « Construction », 4.10.2026 : 49 lignes de modèles hors de la culture du
    maître, dont le Bois Rêveur, tenu par Slaanesh avec les modèles spéciaux elfes d'Athel Loren recopiés de la Saison.)
    Règle : Bois Rêveur sous les elfes sylvains -> les modèles de sa région d'Athel Loren dans la Saison ; colonie elfe
    sylvaine -> MODELES_ELFES ; toute autre culture, et les ruines -> les modèles humains génériques de CA, ceux que CA
    pose pour Slaanesh, les hauts elfes, les Bretons, les nains, les peaux-vertes et les vampires (relevé des tables de
    départ de CA) ; un *_port seulement sur une région à port, jamais ailleurs."""
    if (sc, taille, port) in RECETTES_CA:                    # la combinaison de CA d'abord (§ 2 ter, même règle)
        return list(RECETTES_CA[(sc, taille, port)]["modeles"].items())
    if r["categorie"] == "bois_reveur" and sc == ELFES_SYLVAINS:
        src = r["cle_jeu"].replace("saison_reves_", "wh_dlc05_")
        emp = [(v(c)["slot_type"], v(c)["slot_template"])
               for _, c in L.T("start_pos_region_slot_templates").ou(campaign=SAISON, region=src)]
        if emp and any(t == "port" for t, _ in emp) == port:
            return emp
    if sc == ELFES_SYLVAINS and not port:
        return list(MODELES_ELFES)
    if port:
        return [("port", "wh_main_port"), ("primary", f"wh3_dlc27_human_{taille}_primary_port"),
                ("secondary", f"wh_main_human_{taille}_secondary")]
    return [("primary", f"wh_main_human_{taille}_primary"), ("secondary", f"wh_main_human_{taille}_secondary")]


def construire():
    L = Lot()
    corr = json.load(open(CORR, encoding="utf-8"))
    decl = json.load(open(os.path.join(TRAVAIL, "expanded_declaration.json"), encoding="utf-8"))
    F, RG = L.T("start_pos_factions"), L.T("start_pos_regions")
    fac_exp = {v(c)["faction"]: v(c)["ID"] for _, c in F.ou(campaign=CAMP)}
    fac_combi = {v(c)["faction"]: (k, c) for k, c in F.ou(campaign=COMBI)}
    sous_culture = {v(c)["key"]: v(c)["subculture"] for _, c in L.T("factions").lignes}
    noms, reg, ville, libre = grille()
    idx = {n: i for i, n in enumerate(noms)}
    regions_exp = {v(c)["region"]: (k, c) for k, c in RG.ou(campaign=CAMP)}
    neuves = [r for r in decl["regions"] if not r.get("is_sea") and r["cle_jeu"] not in regions_exp]

    # --- 1. factions de départ absentes
    voulues = sorted({maitre_de(r) for r in neuves if maitre_de(r)} | set(HORDES) | set(FA.FACTIONS))
    nouvelles = {}
    for fac in voulues:
        if fac in fac_exp:
            continue
        modele = fac if fac in fac_combi else SANS_DEPART_IE.get(fac) or FA.FACTIONS[fac][0]
        k, c = fac_combi[modele]
        fid = L.ident("start_pos_factions", "ID", fac)
        L.copier("start_pos_factions", k, c, {"ID": fid, "faction": fac, "campaign": CAMP, "playable": "0"})
        fac_exp[fac] = nouvelles[fac] = fid
        L.journal.append(f"faction {fac} ({fid}) sur {modele}")

    # --- 2. régions neuves, colonies, emplacements
    S, SL = L.T("start_pos_settlements"), L.T("start_pos_region_slot_templates")
    modele_r = L.une("start_pos_regions", campaign=CAMP)
    modele_s = S.ou(region=v(modele_r[1])["id"])[0]
    modele_sl = SL.ou(campaign=CAMP)[0]
    capitales_faites = set(v(c)["owning_faction"] for _, c in RG.ou(campaign=CAMP) if v(c)["faction_capital"] == "1")
    neuves.sort(key=lambda r: -int(r.get("est_capitale") or 0))
    for r in neuves:
        cle = r["cle_jeu"]
        if cle not in idx:
            L.journal.append(f"!! région {cle} absente de la carte d'Expanded : écartée")
            continue
        maitre = maitre_de(r)
        fid = fac_exp.get(maitre, "") if maitre else ""
        sc = sous_culture.get(maitre, "")
        bat = BATIMENTS.get(sc)
        if maitre and not bat:
            raise SystemExit(f"{cle} : sous-culture {sc!r} de {maitre} sans bâtiments connus")
        majeur = bool(r.get("est_capitale"))
        port = bool(r.get("port"))
        # capitale de faction : la première région de la faction (capitales de province d'abord, `neuves` est trié) ;
        # Krinal pour Kemmler (sa capitale de la Saison, le Poste, est rendue à Karak Ziflin plus bas)
        cap_fac = "1" if fid and (fid not in capitales_faites or cle == KRINAL) else "0"
        if cap_fac == "1":
            capitales_faites.add(fid)
        rid = L.ident("start_pos_regions", "id", cle)
        L.copier("start_pos_regions", modele_r[0], modele_r[1], {
            "id": rid, "region": cle, "owning_faction": fid, "faction_capital": cap_fac,
            "cultural_originator": sc, "rebel_faction": maitre or "", "rebel_faction_name": ""})
        taille = "major" if majeur else "minor"
        prim = (bat[0] if majeur else bat[1]) if (bat and fid) else ""
        L.copier("start_pos_settlements", modele_s[0], modele_s[1], {
            "id": L.ident("start_pos_settlements", "id", cle), "region": rid, "settlement_id": "settlement:" + cle,
            "primary_building": prim, "port_building": bat[2] if (port and prim) else "",
            "building1": "", "building2": "", "building3": "", "building4": "", "building5": "",
            "onscreen_name": r.get("nom_en", cle)})
        emp = modeles_du_lore(L, r, sc, taille, port)
        for typ, gab in emp:
            L.copier("start_pos_region_slot_templates", modele_sl[0], modele_sl[1], {
                "id": L.ident("start_pos_region_slot_templates", "id", f"{cle}:{typ}"), "region": cle,
                "slot_type": typ, "slot_template": gab})
        L.journal.append(f"région {cle} : {maitre or 'ruine'}{' (capitale)' if cap_fac == '1' else ''}, {prim or 'ruine'}"
                         f"{', port' if port else ''}")

    # --- 1 bis. (4.10.2026) maîtres corrigés des régions DÉJÀ écrites (les trois Tor : d'Aislinn, horde, à la colonie
    # Tor Soleil) ; idempotent
    for cle, fac in MAITRES_CORRIGES.items():
        if cle not in regions_exp or fac not in fac_exp:
            continue
        k, c = regions_exp[cle]
        voulu = {"owning_faction": fac_exp[fac], "faction_capital": "1" if CAPITALES_CORRIGEES.get(fac) == cle else "0",
                 "cultural_originator": sous_culture.get(fac, ""), "rebel_faction": fac}
        if any(v(c).get(col) != val for col, val in voulu.items()):
            RG.modifier(k, voulu)
            L.journal.append(f"région {cle} : maître {v(c)['owning_faction']} -> {fac} ({fac_exp[fac]})"
                             f"{', capitale' if voulu['faction_capital'] == '1' else ''}")

    # --- 2 bis. (4.10.2026) modèles d'emplacement des régions déjà écrites remis à la règle de modeles_du_lore
    id_vers_fac = {i: k for k, i in fac_exp.items()}
    for r in decl["regions"]:
        if r.get("is_sea") or r["cle_jeu"] not in regions_exp:
            continue
        cle = r["cle_jeu"]
        d = v(regions_exp[cle][1])
        sc = sous_culture.get(id_vers_fac.get(d["owning_faction"], ""), "") or d.get("cultural_originator", "")
        # taille : celle du bâtiment principal posé (jamais un modèle majeur sur une colonie mineure)
        prims = [v(c)["primary_building"] for _, c in S.ou(region=d["id"])]
        if not prims or not ("_major" in prims[0] or "_minor" in prims[0]):
            L.journal.append(f"!! {cle} : taille inconnue (bâtiment {prims}) : emplacements laissés")
            continue
        taille = "major" if "_major" in prims[0] else "minor"
        voulu = dict(modeles_du_lore(L, r, sc, taille, bool(r.get("port"))))
        lignes = SL.ou(campaign=CAMP, region=cle)
        types = {v(c)["slot_type"] for _, c in lignes}
        if types != set(voulu):
            L.journal.append(f"!! {cle} : emplacements {sorted(types)} au lieu de {sorted(voulu)} (laissés)")
            continue
        for k, c in lignes:
            gab = voulu[v(c)["slot_type"]]
            if v(c)["slot_template"] != gab and SL.modifier(k, {"slot_template": gab}):
                L.journal.append(f"emplacement {cle} {v(c)['slot_type']} : {v(c)['slot_template']} -> {gab} ({sc or 'sans culture'})")

    # --- 2 ter. (4.10.2026) RECETTES DE CA : modèles et bâtiments de chaque région neuve pris tels que CA les combine
    for r in decl["regions"]:
        if r.get("is_sea") or r["cle_jeu"] not in regions_exp:
            continue
        cle = r["cle_jeu"]
        d = v(regions_exp[cle][1])
        if not d["owning_faction"]:
            continue                                         # ruines : comme la Saison (ruines de WH1 qui chargent)
        sc = sous_culture.get(id_vers_fac.get(d["owning_faction"], ""), "")
        lignes_s = S.ou(region=d["id"])
        if not lignes_s:
            continue
        ks, cs = lignes_s[0]
        s = v(cs)
        port = bool(s["port_building"])
        taille = "major" if "_major" in s["primary_building"] else "minor"
        rec = RECETTES_CA.get((sc, taille, port))
        if not rec:
            continue
        voulu_b = {"primary_building": rec["primary_building"], "port_building": rec.get("port_building", "")}
        if any(s[c] != val for c, val in voulu_b.items()):
            S.modifier(ks, voulu_b)
            L.journal.append(f"recette de CA {cle} : {s['primary_building']} / {s['port_building']} -> "
                             f"{voulu_b['primary_building']} / {voulu_b['port_building']}")
        for kl, cl in SL.ou(campaign=CAMP, region=cle):
            typ = v(cl)["slot_type"]
            gab = rec["modeles"].get(typ)
            if gab and v(cl)["slot_template"] != gab:
                SL.modifier(kl, {"slot_template": gab})
                L.journal.append(f"recette de CA {cle} {typ} : {v(cl)['slot_template']} -> {gab}")

    # --- 3. chefs et armées des factions neuves
    P, U, HD = L.T("start_pos_characters"), L.T("start_pos_land_units"), L.T("start_pos_horde_details")
    capitale_de = {}
    for r in neuves:
        if maitre_de(r) and r["cle_jeu"] in ville:
            capitale_de.setdefault(maitre_de(r), (r["cle_jeu"], int(r.get("est_capitale") or 0)))
            if r.get("est_capitale"):
                capitale_de[maitre_de(r)] = (r["cle_jeu"], 1)
    for fac, cle in CAPITALES_CORRIGEES.items():
        if cle in ville:
            capitale_de[fac] = (cle, 1)
    # cases déjà prises par les personnages recopiés de la Saison
    pris = {(int(v(c)["startx"]), int(v(c)["starty"])) for _, c in P.lignes
            if v(c)["faction"] in set(fac_exp.values()) and v(c)["startx"].lstrip("-").isdigit()
            and v(c)["starty"].lstrip("-").isdigit()}
    for fac, fid in nouvelles.items():
        modele = fac if fac in fac_combi else SANS_DEPART_IE.get(fac) or FA.FACTIONS[fac][0]
        fid_ie = v(fac_combi[modele][1])["ID"]
        persos = [(k, c) for k, c in P.ou(faction=fid_ie)]
        chef = next(((k, c) for k, c in persos if v(c)["ministerial_position"] == "faction_leader"), persos[0])
        if fac in CHEFS_ORDINAIRES:
            chef = P.ou(ID=CHEFS_ORDINAIRES[fac])[0]
        if fac in HORDES:
            x, y = HORDES[fac]
            q, r_ = case_libre(libre, reg, x + DX, y + DY, pris=pris)
            # une horde part avec le général qui porte les détails de horde (camp des ogres), sinon son chef
            avec_horde = [(k, c) for k, c in persos if HD.ou(general=v(c)["ID"])]
            if avec_horde:
                chef = avec_horde[0]
        else:
            cap = capitale_de.get(fac)
            if not cap:
                raise SystemExit(f"{fac} : ni région ni lieu de horde")
            q0, r0 = ville[cap[0]]
            q, r_ = case_libre(libre, reg, q0, r0, idx[cap[0]], pris)
        pris.add((q, r_))
        cid = L.ident("start_pos_characters", "ID", fac + ":chef")
        L.copier("start_pos_characters", chef[0], chef[1], {"ID": cid, "faction": fid, "startx": str(q),
                                                            "starty": str(r_), "ministerial_position": "faction_leader"})
        armee = U.ou(general=v(chef[1])["ID"])
        if not armee:
            sc = sous_culture[modele]
            for kf, cf in F.ou(campaign=COMBI):
                if sous_culture.get(v(cf)["faction"]) != sc:
                    continue
                for kp, cp in P.ou(faction=v(cf)["ID"], Type="general"):
                    if v(cp)["subtype"] == v(chef[1])["subtype"] and len(U.ou(general=v(cp)["ID"])) >= 6:
                        armee = U.ou(general=v(cp)["ID"])
                        break
                if armee:
                    break
        for i, (ku, cu) in enumerate(armee):
            L.copier("start_pos_land_units", ku, cu, {"id": L.ident("start_pos_land_units", "id", f"{fac}:{i}"),
                                                      "general": cid})
        for kh, ch in HD.ou(general=v(chef[1])["ID"]):
            L.copier("start_pos_horde_details", kh, ch, {"general": cid})
        for nom, col in (("start_pos_character_traits", "character_id"),
                         ("start_pos_character_ancillaries", "character_id")):
            for i, (kt, ct) in enumerate(L.T(nom).ou(**{col: v(chef[1])["ID"]})):
                L.copier(nom, kt, ct, {col: cid, "id": L.ident(nom, "id", f"{fac}:{i}")})
        L.journal.append(f"chef de {fac} : {v(chef[1])['subtype']} en ({q}, {r_}), {len(armee)} unités"
                         f"{', horde' if HD.ou(general=v(chef[1])['ID']) else ''}")

    # --- 2 bis. les ruines : culture, rebelles et bâtiment de ruine (lignes déjà écrites retouchées ; idempotent)
    for k, c in RG.ou(campaign=CAMP):
        r = v(c)
        if r["region"] not in RUINES or r["owning_faction"]:
            continue
        sc, reb, prim, port = RUINES[r["region"]]
        RG.modifier(k, {"cultural_originator": sc, "rebel_faction": reb})
        for ks, cs in S.ou(region=r["id"]):
            S.modifier(ks, {"primary_building": prim, "port_building": port})
        L.journal.append(f"ruine {r['region']} : {prim}{', ' + port if port else ''}, rebelles {reb}")
    sans = [r["cle_jeu"] for r in neuves if not maitre_de(r) and r["cle_jeu"] not in RUINES]
    if sans:
        raise SystemExit(f"ruines sans entrée dans RUINES : {sans}")

    # --- 3 bis. chefs remplacés par un général ordinaire (déjà écrits avec le chef de CA : la ligne est retouchée, ses
    # traits et objets retirés ; idempotent)
    for fac, donneur in CHEFS_ORDINAIRES.items():
        d = v(P.ou(ID=donneur)[0][1])
        for k, c in P.ou(faction=fac_exp[fac], ministerial_position="faction_leader"):
            if v(c)["subtype"] == d["subtype"]:
                continue
            P.modifier(k, {col: d[col] for col in COLONNES_PERSONNE})
            for nom in ("start_pos_character_traits", "start_pos_character_ancillaries"):
                for kt, _ct in L.T(nom).ou(character_id=v(c)["ID"]):
                    L.T(nom).retirer(kt)
            L.journal.append(f"chef de {fac} : {v(c)['subtype']} remplacé par {d['subtype']} (personnage {donneur})")

    # --- 4. Kemmler à Krinal, le Poste rendu à Karak Ziflin
    kem = fac_exp[KEMMLER]
    for k, c in RG.ou(campaign=CAMP, region=POSTE):
        L.T("start_pos_regions").modifier(k, {"owning_faction": fac_exp[ZIFLIN], "faction_capital": "0",
                                              "cultural_originator": "wh_main_sc_dwf_dwarfs", "rebel_faction": ZIFLIN})
        # (4.10.2026, plantage au chargement +0x2602213, « bâtiment introuvable », point d'arrêt de la Construction sur
        # wh_dlc05_grey_mountains_2_blackstone_post:0) : seul le bâtiment principal passait en nain ; les modèles
        # (castle_drachenfels_primary, blackstone_post_major_secondary) et les bâtiments de Kemmler (castle_drachenfels_1,
        # vmp_bindingcircle_1) restaient vampiriques. RÈGLE : une région de WH1 qui change de maître prend ses modèles
        # ET ses bâtiments dans la culture du nouveau maître (modeles_du_lore ; bâtiments secondaires vidés)
        for ks, cs in S.ou(region=v(c)["id"]):
            S.modifier(ks, {"primary_building": "wh_main_dwf_settlement_minor_1", "port_building": "",
                            **{f"building{i}": "" for i in range(1, 6)}})
        voulu = dict(modeles_du_lore(L, {"categorie": "", "cle_jeu": POSTE}, "wh_main_sc_dwf_dwarfs", "minor", False))
        for ksl, csl in SL.ou(campaign=CAMP, region=POSTE):
            gab = voulu.get(v(csl)["slot_type"])
            if gab is None:
                L.T("start_pos_region_slot_templates").retirer(ksl)
            elif v(csl)["slot_template"] != gab:
                L.T("start_pos_region_slot_templates").modifier(ksl, {"slot_template": gab})
    q0, r0 = ville[KRINAL]
    # tous les personnages de Kemmler posés sur la carte (lui, Krell, recopiés de la Saison devant le Poste) passent
    # devant Krinal ; idempotent : un personnage déjà dans la région de Krinal ne bouge plus
    for k, c in P.ou(faction=kem):
        x, y = v(c)["startx"], v(c)["starty"]
        if not (x.isdigit() and y.isdigit()) or (x, y) == ("0", "0"):
            continue
        if reg[int(y), int(x)] == idx[KRINAL]:
            continue
        q, r_ = case_libre(libre, reg, q0, r0, idx[KRINAL], pris)
        pris.add((q, r_))
        P.modifier(k, {"startx": str(q), "starty": str(r_)})
        L.journal.append(f"{v(c)['subtype']} en ({q}, {r_}) devant Krinal")
    if not [1 for _, c in P.ou(faction=kem) if v(c)["subtype"] == "wh3_dlc29_vmp_krell"]:
        (k, c), = P.ou(ID=KRELL_IE)
        q, r_ = case_libre(libre, reg, q0, r0, idx[KRINAL], pris)
        pris.add((q, r_))
        L.copier("start_pos_characters", k, c, {"ID": L.ident("start_pos_characters", "ID", "krell"), "faction": kem,
                                                "startx": str(q), "starty": str(r_)})
        L.journal.append(f"Krell en ({q}, {r_})")

    # --- 4 bis. (4.10.2026, ports remis au modèle de CA : Aislinn se retrouvait sur une case de la ville de Tor Martel,
    # déplacée d'un hex) aucun personnage posé sur une case d'emplacement ou d'étendue de ville : case libre la plus proche
    for k, c in P.lignes:
        d = v(c)
        if d["faction"] not in set(fac_exp.values()):
            continue
        x, y = d["startx"], d["starty"]
        if not (x.isdigit() and y.isdigit()) or (x, y) == ("0", "0"):
            continue
        q, r_ = int(x), int(y)
        if not (0 <= q < W and 0 <= r_ < H) or libre[r_, q]:
            continue
        q2, r2 = case_libre(libre, reg, q, r_, None, pris)
        pris.add((q2, r2))
        P.modifier(k, {"startx": str(q2), "starty": str(r2)})
        L.journal.append(f"{d['subtype']} ({d['faction']}) : ({q}, {r_}) sur une ville ou hors du franchissable -> ({q2}, {r2})")

    # --- 5. diplomatie
    D = L.T("start_pos_diplomacy")
    modele_d = D.ou()[0]
    for a, b, etat, acces, commerce, pacte in DIPLOMATIE:
        fa, fb = fac_exp.get(a), fac_exp.get(b)
        if not (fa and fb):
            L.journal.append(f"!! diplomatie {a} / {b} : faction absente du départ")
            continue
        if D.ou(faction1=fa, faction2=fb) or D.ou(faction1=fb, faction2=fa):
            continue
        L.copier("start_pos_diplomacy", modele_d[0], modele_d[1], {
            "key": L.ident("start_pos_diplomacy", "key", f"{a}:{b}"), "faction1": fa, "faction2": fb, "stance": etat,
            "grants_military_access": acces, "grants_trade_agreement": commerce, "relations_modifier": "0",
            "non_aggression_pact": pacte})
        L.journal.append(f"diplomatie {a} / {b} : {etat}")
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    L = construire()
    for ligne in L.journal:
        print("  " + ligne)
    from donnees_campagne import verifier_references
    manques = [m for m in verifier_references(L.t) if m[2] not in ("", "0")]
    for m in manques[:30]:
        print("  RÉFÉRENCE MANQUANTE :", m)
    if manques and a.apply:
        print(f"{len(manques)} référence(s) manquante(s) : rien n'est écrit")
        return 1
    total = 0
    for nom, t in L.t.items():
        n = len(t.neuves) + len(t.modifiees) + len(t.retirees)
        if n:
            print(f"  {nom:44s} {len(t.neuves):4d} neuve(s), {len(t.modifiees):3d} modifiée(s), "
                  f"{len(t.retirees):3d} retirée(s)")
        total += n
    print(f"{total} ligne(s) {'écrites' if a.apply else 'à écrire'}")
    if not a.apply:
        return 0
    dossier = os.path.join(ATELIER, "05-journal", "db-backups", datetime.now().strftime("%Y%m%d-%H%M%S") + "-depart-atlas")
    for t in L.t.values():
        t.ecrire(dossier)
    reste = {n: len(t.neuves) + len(t.modifiees) + len(t.retirees) for n, t in construire().t.items()
             if t.neuves or t.modifiees or t.retirees}
    if reste:
        print(f"!!! NON IDEMPOTENT : {reste} (sauvegarde {dossier})")
        return 2
    print(f"écrit ; sauvegarde {dossier} ; nouvelle passe à 0 ligne")
    return 0


if __name__ == "__main__":
    sys.exit(main())
