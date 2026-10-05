#!/usr/bin/env python3
"""
factions_atlas.py - les 16 factions neuves de l'Atlas pour Expanded (3.10.2026) : tables de base, textes, drapeaux.

Pourquoi : Charles (3.10.2026, au soir) confie la création des factions de l'Atlas à la session « Expanded map
integration et polish » (« toi, parce que tu fais la map »). Fiche du lot : `05-journal\\2026-10-03-expanded-suite\\
fiche-factions-atlas.md` (session « Lakemen faction models and lore »). Conventions données par la session « Lakemen
faction models discussion » : PAS de lot numéroté dans `donnees_campagne.py` (les lots 1 à 45 sont rejoués tels quels
pour restaurer le kit de la Saison) ; un script à part qui importe `TableKit`, avec sa propre liste d'entrées pour le pack,
à CLÉS EXACTES (un filtre par préfixe `saison_` ferait entrer ces lignes dans le pack de la Saison).

Ce module fait la partie qui ne dépend pas du départ d'Expanded :
- tables de base : chaque faction est faite sur une faction MINEURE de CA de même sous-culture et même genre (MODELES) :
  ligne `factions` (clé, index, noms anglais, chemin du drapeau changés) et ses lignes des tables « par faction » (TABLES,
  colonne de la faction), recopiées sous notre clé ; jamais une ligne de CA modifiée ;
- textes anglais et français des noms (`factions_screen_name_*`, `..._when_rebels_*`, phrases d'attaque et de défense),
  au format de `textes_gameplay.json`, dans `04-projets\\saison-expanded\\textes\\factions_atlas.json` ;
- drapeaux au format de CA (`ui/flags/<clé>/mon_24.png, mon_64.png, mon_256.png, mon_icon.png, mon_rotated.png,
  mon_banner.dds`) depuis les bannières de l'Atlas (64 et 256 px), dans `04-projets\\saison-expanded\\drapeaux-jeu\\`.
Les lignes `start_pos_*` (départ, régions, personnages, armées, diplomatie, Kemmler à Krinal) viennent APRÈS la recopie
du départ de la Saison vers `saison_expanded` par la Construction (table de correspondance des identifiants) :
`--depart`, plus tard.

Essai à blanc par défaut (lit le kit, n'écrit rien dans le kit). `--apply` : PRÉAVIS DE 5 MINUTES à la Construction
d'abord ; sauvegarde des XML touchés dans `05-journal\\db-backups\\<date>-factions-atlas\\` ; contrôle des références et
de l'idempotence. Une table de base neuve dans un pack = un essai de démarrage avant toute annonce (erreur 107).

Usage : python factions_atlas.py [--apply] [--drapeaux] [--textes]
"""
import argparse
import io
import json
import os
import sys
from datetime import datetime

from PIL import Image

ATELIER = r"C:\TotalWar-CampaignMap"
sys.path.insert(0, os.path.join(ATELIER, "02-scripts"))
import donnees_campagne as D                                             # noqa: E402

ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
SOURCES = os.path.join(ATELIER, r"05-journal\2026-09-23-extension-carte\travail\images_source")
SORTIE_TEXTES = os.path.join(ICI, "textes", "factions_atlas.json")
SORTIE_DRAPEAUX = os.path.join(ICI, "drapeaux-jeu")
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data"
CAMPAGNE = "saison_expanded"

# Modèles : factions MINEURES non jouables des Empires (start_pos_factions de wh3_main_combi, playable 0), avec leur
# propre drapeau. Hardes : Redhorn (harde mineure) ; nains : Karak Ziflin ; orques : Red Fangs ; gobelins : les
# Necksnappers de CA (gobelins de la Lune Tordue) ; ogres : Crossed Clubs ; Bretonniens : Lyonesse (duché mineur).
NAINS, ORQUES, GOBELINS = "wh_main_dwf_karak_ziflin", "wh_main_grn_red_fangs", "wh_main_grn_necksnappers"
HARDE, OGRES, BRETONNIENS = "wh_dlc03_bst_redhorn", "wh3_main_ogr_crossed_clubs", "wh_main_brt_lyonesse"
# (4.10.2026, plantage +0x2602213 sur saison_tor_soleil : chez CA, Aislinn est une HORDE sans région ; décision de
# Charles : « faction elfe mineure ») colonie des Asur d'outre-mer : la Citadelle du Crépuscule, colonie mineure de CA
# (la Forteresse de l'Aube, autre colonie, n'a aucun personnage au départ des Empires : pas de chef ni d'armée à recopier ;
# la Citadelle a un Sea Helm et 6 unités, ce qui convient à une enclave marchande de la côte)
COLONIE_HEF = "wh2_main_hef_citadel_of_dusk"

# clé -> (modèle, nom anglais, nom français, bannière 64 px, bannière 256 px) ; noms et bannières : fiche du lot
F = "{}_{}.png"
FACTIONS = {
    "saison_bst_khorok_manripper": (HARDE, "Warherd of Khorok Manripper", "Harde de Khorok Manripper",
                                    "drapeaux_projet", "saison_bst_khorok_manripper"),
    "saison_bst_harrowmaw": (HARDE, "Harrowmaw Tribe", "Tribu Harrowmaw", "drapeaux_projet", "saison_bst_harrowmaw"),
    "saison_bst_lakemen": (HARDE, "Lakemen of Lyonesse", "Lakemen de Lyonesse", "drapeaux_projet", "saison_bst_lakemen"),
    "saison_grn_orques_de_fer": (ORQUES, "Iron Orcs of the Irrana", "Orques de fer des Irrana", "drapeaux_mods",
                                 "orques_de_fer"),
    "saison_grn_lune_sanglante": (GOBELINS, "Bleeding Moon Goblins", "Gobelins de la Lune-Sanglante", "drapeaux_mods",
                                  "lune_sanglante"),
    "saison_grn_ongles_rouges": (GOBELINS, "Red Nails Tribe", "Tribu des Ongles-Rouges", "drapeaux_mods",
                                 "ongles_rouges"),
    "saison_grn_brise_nuques": (GOBELINS, "Necksnappers", "Les Brise-Nuques", "drapeaux_mods", "brise_nuques"),
    "saison_grn_gutrippaz": (ORQUES, "Gutrippaz", "Les Gutrippaz", "drapeaux_voutes", "saison_grn_gutrippaz"),
    "saison_ogr_osseine": (OGRES, "Ogres of Gristle Valley", "Ogres de la Vallée d'Osséine", "drapeaux_mods",
                           "ogres_osseine"),
    "saison_dwf_karak_azgaraz": (NAINS, "Karak Azgaraz", "Karak Azgaraz", "drapeaux_projet",
                                 "saison_dwf_karak_azgaraz"),
    "saison_dwf_karak_izor": (NAINS, "Karak Izor", "Karak Izor", "drapeaux_voutes", "saison_dwf_karak_izor"),
    "saison_dwf_karak_kaferkammaz": (NAINS, "Karak Kaferkammaz", "Karak Kaferkammaz", "drapeaux_voutes",
                                     "saison_dwf_karak_kaferkammaz"),
    "saison_dwf_karak_eksfilaz": (NAINS, "Karak Eksfilaz", "Karak Eksfilaz", "drapeaux_voutes",
                                  "saison_dwf_karak_eksfilaz"),
    "saison_dwf_karak_grom": (NAINS, "Karak Grom", "Karak Grom", "drapeaux_voutes", "saison_dwf_karak_grom"),
    "saison_dwf_karak_bhufdar": (NAINS, "Karak Bhufdar", "Karak Bhufdar", "drapeaux_voutes",
                                 "saison_dwf_karak_bhufdar"),
    "saison_brt_languille": (BRETONNIENS, "L'Anguille", "L'Anguille", "drapeaux_mods", "languille"),
    # nom de sa capitale, comme CA nomme ses colonies (Fortress of Dawn, Citadel of Dusk) ; l'Atlas : « colonie des Asur,
    # côte nord-ouest ; enclave marchande gardée par sa garnison » ; drapeau PROVISOIRE (aucun chez Partipus)
    "saison_hef_tor_soleil": (COLONIE_HEF, "Tor Soleil", "Tor Soleil", "drapeaux_provisoires", "saison_hef_tor_soleil"),
}
# Tables « par faction » recopiées du modèle (table, colonne de la faction) : le cœur relevé par la session « Lakemen
# faction models discussion » sur une faction de CA, plus celles que portent nos modèles. ÉCARTÉES : start_pos_* (plus
# tard), frontend_* (factions non jouables), et ce qui est PROPRE au modèle (unités exclusives, variantes de bâtiments,
# cinématiques, armées des batailles scénarisées, confédérations rituelles, mercenaires, objets d'ancillaires).
TABLES = [("faction_to_faction_groups_junctions", "faction_key"),
          ("faction_agent_permitted_subtypes", "faction"),
          ("faction_rebellion_units_junctions", "faction_key"),
          ("campaign_map_attrition_faction_immunities", "faction"),
          ("climbing_ladders_meshes_definitions", "faction_key"),
          ("faction_banned_unit_purchasable_effects", "faction"),
          ("ui_features_to_factions", "faction"),
          # (faction_potential_difficulty_overrides : à part, `lot`, sa ligne porte la campagne)
          # (pas campaign_group_member_criteria_factions : ses groupes sont ceux de la diplomatie PROPRE au modèle,
          # « FactionRedFangs… » ; notre faction aurait parlé comme les Red Fangs)
          ("faction_factionwide_recruitment_unit_exclusions_set_junctions", "faction"),
          # (pas faction_ownership_content_pack_junctions : 4.10.2026, dichotomie de la Construction sur le pack
          # d'Expanded, le jeu se ferme sans rien dire en 9 à 13 s avec ces jonctions de propriété de DLC recopiées des
          # modèles ; même famille que l'erreur 107. Les 16 lignes déjà écrites dans le kit restent, hors du pack)
          ("army_special_abilities_for_faction_junctions", "faction")]


def lot():
    """Rend ({table: TableKit}, [entrées pour le pack, à clés exactes])."""
    tables = {"factions": D.TableKit("factions")}
    fac = tables["factions"]
    pris = {fac.valeurs(c).get("index") for _, c in fac.lignes}
    for cle, (modele, en, _fr, _d, _b) in FACTIONS.items():
        fac.ajouter_sur_modele(modele, {
            "key": cle, "index": D.ident_numerique("saison_expanded:" + cle, pris),
            "screen_name": en, "screen_name_when_rebels": f"{en} Rebels",
            "attack_desc": f"You are attacking {en}!", "defend_desc": f"You are defending against {en}!",
            "flags_path": "ui\\flags\\" + cle,
            # pas de film de mort (Redhorn en a un, le 71, qui n'est pas dans la base du kit)
            "movie_death_event": "0"})
    for table, col in TABLES:
        t = tables.setdefault(table, D.TableKit(table))
        for cle, (modele, *_r) in FACTIONS.items():
            t.recopier(col, modele, cle)
    # le potentiel de l'IA par difficulté : ligne PAR CAMPAGNE ; celles du modèle aux Empires, recopiées sous notre
    # faction et la campagne d'Expanded (sinon elles ne serviraient jamais)
    po = tables.setdefault("faction_potential_difficulty_overrides", D.TableKit("faction_potential_difficulty_overrides"))
    for cle, (modele, *_r) in FACTIONS.items():
        for k, _c in po.ou(faction=modele, campaign_key="wh3_main_combi"):
            po.ajouter_sur_modele(k, {"faction": cle, "campaign_key": CAMPAGNE})
    # les ensembles de factions (« toutes les factions ordinaires »… : cibles d'effets et de scripts de CA) : la clé est un
    # identifiant numérique, pas la faction ; une ligne neuve par ensemble du modèle, identifiant stable à nous
    si = tables.setdefault("faction_set_items", D.TableKit("faction_set_items"))
    ids = set(si.cles)
    for cle, (modele, *_r) in FACTIONS.items():
        for k, corps in si.ou(faction=modele):
            ens = si.valeurs(corps)["set"]
            n = D.ident_numerique(f"saison_expanded:{cle}:{ens}", ids)
            if any(si.valeurs(c).get("faction") == cle and si.valeurs(c).get("set") == ens for _, c in si.lignes):
                si.deja += 1
                continue
            si.ajouter_sur_modele(k, {"id": n, "faction": cle})
            ids.add(n)
    tables = {n: t for n, t in tables.items() if t.neuves or t.deja}
    cles = sorted(FACTIONS)
    entrees = [("factions", "factions_tables", "key", cles)]
    entrees += [(n, n + "_tables", col, cles) for n, col in TABLES + [("faction_set_items", "faction"),
                ("faction_potential_difficulty_overrides", "faction")] if n in tables]
    return tables, entrees


def textes():
    out = {}
    for cle, (_m, en, fr, _d, _b) in FACTIONS.items():
        out[f"factions_screen_name_{cle}"] = {"en": en, "fr": fr}
        out[f"factions_screen_name_when_rebels_{cle}"] = {"en": f"{en} Rebels", "fr": f"Rebelles : {fr}"}
        out[f"factions_attack_desc_{cle}"] = {"en": f"You are attacking {en}!", "fr": f"Vous attaquez : {fr} !"}
        out[f"factions_defend_desc_{cle}"] = {"en": f"You are defending against {en}!",
                                              "fr": f"Vous vous défendez contre : {fr} !"}
    return out


def drapeaux():
    """{chemin du pack : octets} des six fichiers de drapeau de chaque faction, depuis nos bannières 64 et 256 px."""
    out = {}
    for cle, (_m, _en, _fr, dossier, base) in FACTIONS.items():
        p64, p256 = (os.path.join(SOURCES, dossier, f"{base}_{n}.png") for n in (64, 256))
        if not (os.path.exists(p64) and os.path.exists(p256)):
            raise SystemExit(f"drapeau de {cle} absent : {p64} / {p256}")
        g = Image.open(p256).convert("RGBA").resize((256, 256), Image.LANCZOS)
        im64 = Image.open(p64).convert("RGBA").resize((64, 64), Image.LANCZOS)

        def png(im):
            b = io.BytesIO()
            im.save(b, "PNG")
            return b.getvalue()
        d = f"ui/flags/{cle}/"
        out[d + "mon_256.png"] = png(g)
        out[d + "mon_64.png"] = png(im64)
        out[d + "mon_24.png"] = png(im64.resize((24, 24), Image.LANCZOS))
        # mon_icon : chez CA, l'emblème seul sur fond transparent ; nous n'avons que la bannière entière (à refaire si
        # l'Atlas dessine les emblèmes seuls)
        out[d + "mon_icon.png"] = png(g)
        # mon_rotated (112 × 90) : chez CA, la bannière elle-même en petit, légèrement inclinée (vérifié sur Karak Ziflin,
        # Red Fangs, Crossed Clubs : pas un quart de tour)
        pt = g.resize((84, 84), Image.LANCZOS).rotate(8, resample=Image.BICUBIC, expand=True)
        pt = pt.resize((round(pt.width * 86 / pt.height), 86), Image.LANCZOS)
        fond = Image.new("RGBA", (112, 90), (0, 0, 0, 0))
        fond.paste(pt, ((112 - pt.width) // 2, 2), pt)
        out[d + "mon_rotated.png"] = png(fond)
        out[d + "mon_banner.dds"] = dds_brut(g)
    return out


def dds_brut(im):
    """DDS non compressé BGRA 8 bits avec toute sa chaîne de mipmaps : le format du mon_banner.dds de CA (Karak Ziflin,
    349 652 octets en 256 × 256, sans FourCC)."""
    import struct
    niveaux = [im]
    while niveaux[-1].width > 1:
        niveaux.append(niveaux[-1].resize((max(1, niveaux[-1].width // 2), max(1, niveaux[-1].height // 2)),
                                          Image.LANCZOS))
    w, h = im.size
    pf = struct.pack("<II4sIIIII", 32, 0x41, b"\0\0\0\0", 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    tete = struct.pack("<4sIIIIIII", b"DDS ", 124, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000, h, w, w * 4, 0,
                       len(niveaux)) + b"\0" * 44 + pf + struct.pack("<IIIII", 0x1000 | 0x8 | 0x400000, 0, 0, 0, 0)
    corps = b"".join(n.convert("RGBA").tobytes("raw", "BGRA") for n in niveaux)
    return tete + corps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit dans le kit (préavis de 5 min d'abord)")
    ap.add_argument("--drapeaux", action="store_true", help="écrit les drapeaux dans drapeaux-jeu\\")
    ap.add_argument("--textes", action="store_true", help="écrit textes\\factions_atlas.json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    tables, entrees = lot()
    # movie_death_event = 0 : « pas de film », valeur de toutes les factions de CA (dont nos modèles), sans ligne 0 dans
    # movie_event_strings ; le contrôle des références ne la connaît pas
    manques = [m for m in D.verifier_references(tables) if m[:3] != ("factions", "movie_death_event", "0")]
    for m in manques[:30]:
        print("  RÉFÉRENCE MANQUANTE :", m)
    total = 0
    for nom, t in tables.items():
        print(f"  {nom:62s} {len(t.neuves):4d} neuve(s), {t.deja:3d} déjà là")
        total += len(t.neuves)
    print(f"{total} ligne(s) {'à écrire' if not a.apply else 'écrites'} ; {len(FACTIONS)} factions")
    print("entrées pour le pack d'Expanded (clés exactes) :")
    for e in entrees:
        print(f"    {e[0]!r}, {e[1]!r}, {e[2]!r}, [{len(e[3])} clés]")
    if a.textes:
        os.makedirs(os.path.dirname(SORTIE_TEXTES), exist_ok=True)
        with open(SORTIE_TEXTES, "w", encoding="utf-8", newline="\n") as f:
            json.dump(textes(), f, ensure_ascii=False, indent=1)
        print(f"  textes : {SORTIE_TEXTES}")
    if a.drapeaux:
        fichiers = drapeaux()
        for chemin, octets in fichiers.items():
            dest = os.path.join(SORTIE_DRAPEAUX, *chemin.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(octets)
        print(f"  drapeaux : {len(fichiers)} fichiers dans {SORTIE_DRAPEAUX}")
    if a.apply:
        if manques:
            print(f"{len(manques)} référence(s) manquante(s) : rien n'est écrit")
            return 1
        dossier = os.path.join(ATELIER, "05-journal", "db-backups",
                               datetime.now().strftime("%Y%m%d-%H%M%S") + "-factions-atlas")
        for t in tables.values():
            t.ecrire(dossier)
        relu, _ = lot()
        reste = {n: len(t.neuves) for n, t in relu.items() if t.neuves}
        if reste:
            print(f"!!! NON IDEMPOTENT : {reste} (sauvegarde : {dossier})")
            return 2
        print(f"  écrit ; sauvegarde : {dossier} ; nouvelle passe à 0 ligne")
    return 0


if __name__ == "__main__":
    sys.exit(main())
