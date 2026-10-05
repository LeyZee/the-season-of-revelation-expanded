#!/usr/bin/env python3
"""
rivieres_maillages_expanded.py - les maillages d'eau des rivières de WH1 pour Expanded (3.10.2026).

Pourquoi (Construction, 3.10.2026, 22 h 13) : les calques recopiés de la Saison par `projet_expanded` posent les
rivières de WH1 en objets `terrain/campaigns/saison_expanded_map/models/river_wh1_cXX_YY.wsmodel` (clé de la carte
remplacée), que rien ne produisait : `global_props.bin` d'Expanded en cite 105, introuvables. Les maillages sont ceux de
la Saison (`04-projets\\saison-des-revelations\\rivieres-wh1\\`, `rivieres_wh1.py`) : leur géométrie
(`.rigid_model_v2`) ne porte aucun chemin (relevé) et se pose par la position de l'objet, décalée par `projet_expanded` ;
seul le `.wsmodel` nomme sa géométrie et son matériau. Copie au chemin d'Expanded, `.wsmodel` réécrit : chemin de la
géométrie à la clé d'Expanded, matériau d'eau d'Expanded (`eau_expanded.MATERIAU_MER`, masques à la taille de son monde).
Seuls les maillages cités par les calques du projet d'Expanded sont copiés.

Sortie : `04-projets\\saison-expanded\\rivieres-wh1\\terrain\\campaigns\\saison_expanded_map\\models\\` (même arborescence
que la Saison, pour build_pack). Usage : python rivieres_maillages_expanded.py [--apply]
"""
import argparse
import glob
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eau_expanded                                                       # noqa: E402

ATELIER = r"C:\TotalWar-CampaignMap"
SRC_CLE, CLE = "wh_dlc05_wood_elves_map_1", "saison_expanded_map"
SRC = os.path.join(ATELIER, r"04-projets\saison-des-revelations\rivieres-wh1\terrain\campaigns", SRC_CLE, "models")
ICI = os.path.join(ATELIER, r"04-projets\saison-expanded")
DST = os.path.join(ICI, r"rivieres-wh1\terrain\campaigns", CLE, "models")
TERRY = os.path.join(ICI, "terry", CLE)
MATERIAU_SAISON = "materials/environment/campaign_sea/wh_dlc05_wood_elves_campaign_water_plane.xml.material"


def cites():
    noms = set()
    for f in glob.glob(os.path.join(TERRY, "*.layer")):
        noms |= set(re.findall(rf"terrain/campaigns/{CLE}/models/(river_wh1_c\d+_\d+)\.wsmodel",
                               open(f, encoding="utf-8", errors="replace").read()))
    return sorted(noms)


def positions():
    """{nom du maillage: (x, y, z) de son objet} dans les calques du projet d'Expanded."""
    ent = re.compile(rf'model_path="terrain/campaigns/{CLE}/models/(river_wh1_c\d+_\d+)\.wsmodel".*?'
                     r'<ECTransform position="([-0-9.eE]+) ([-0-9.eE]+) ([-0-9.eE]+)"', re.S)
    out = {}
    for f in glob.glob(os.path.join(TERRY, "*.layer")):
        for n, x, y, z in ent.findall(open(f, encoding="utf-8", errors="replace").read()):
            out[n] = (float(x), float(y), float(z))
    return out


def retirer_objets(vides):
    """Retire des calques du projet les objets des maillages vidés (tout le ruban sur le chenal)."""
    if not vides:
        return 0
    motif = re.compile(r'[ \t]*<entity id="[^"]*">(?:(?!</entity>).)*?/models/(?:' + "|".join(map(re.escape, vides))
                       + r')\.wsmodel".*?</entity>[ \t]*\r?\n', re.S)
    n = 0
    for f in glob.glob(os.path.join(TERRY, "*.layer")):
        t = open(f, encoding="utf-8").read()
        t2, k = motif.subn("", t)
        if k:
            open(f, "w", encoding="utf-8", newline="\n").write(t2)
            n += k
    return n


def ecrire():
    """Copie les maillages cités, rognés sur le chenal des fleuves navigables et recalés sur les berges abaissées
    (5.10.2026, `chenaux_fleuves`) ; un maillage vidé est retiré, avec son objet."""
    import chenaux_fleuves as C
    noms = cites()
    manquants = [n for n in noms if not os.path.exists(os.path.join(SRC, n + ".wsmodel"))]
    if manquants:
        raise SystemExit(f"{len(manquants)} maillage(s) cité(s) absent(s) de la Saison : {manquants[:5]}")
    for f in glob.glob(os.path.join(DST, "river_wh1_c*")):
        os.remove(f)                         # sortie générée, refaite à chaque fois
    os.makedirs(DST, exist_ok=True)
    pos = positions()
    dedans, dy = C.dans_chenal_monde(), C.delta_monde()
    vides, n_ret, n_tot, n_touches = [], 0, 0, 0
    for n in noms:
        geo, r, t = C.rogner_rmv2(open(os.path.join(SRC, n + ".wsmodel.rigid_model_v2"), "rb").read(), pos[n], dedans, dy)
        n_ret, n_tot = n_ret + r, n_tot + t
        n_touches += r > 0
        if r == t:
            vides.append(n)
            continue
        t_ = open(os.path.join(SRC, n + ".wsmodel"), encoding="utf-8").read()
        t2 = t_.replace(f"terrain/campaigns/{SRC_CLE}/models/", f"terrain/campaigns/{CLE}/models/")
        t2 = t2.replace(MATERIAU_SAISON, eau_expanded.MATERIAU_MER)
        if SRC_CLE in t2 or "wh_dlc05_wood_elves_campaign" in t2:
            raise SystemExit(f"{n} : chemin de la Saison resté dans le .wsmodel")
        open(os.path.join(DST, n + ".wsmodel"), "w", encoding="utf-8", newline="\n").write(t2)
        open(os.path.join(DST, n + ".wsmodel.rigid_model_v2"), "wb").write(geo)
    n_obj = retirer_objets(vides)
    print(f"  rubans de WH1 : {len(noms)} cités ; {n_touches} rognés sur le chenal ({n_ret} / {n_tot} triangles), "
          f"{len(vides)} vidés et retirés ({n_obj} objets)")
    return len(noms) - len(vides)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    noms = cites()
    manquants = [n for n in noms if not os.path.exists(os.path.join(SRC, n + ".wsmodel"))]
    if manquants:
        raise SystemExit(f"{len(manquants)} maillage(s) cité(s) absent(s) de la Saison : {manquants[:5]}")
    print(f"  {len(noms)} maillages de rivière cités par le projet d'Expanded ; tous présents dans la Saison")
    if not a.apply:
        print("  à blanc : rien d'écrit")
        return 0
    ecrire()
    return 0


if __name__ == "__main__":
    sys.exit(main())
