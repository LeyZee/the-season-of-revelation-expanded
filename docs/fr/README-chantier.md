# Saison Expanded : la carte agrandie à toute la Bretonnie

Chantier ouvert le 25.09.2026 vers 15 h 25 à la demande de Charles : « fais une copie du pack, tu la nommes Expanded, et
tu commences à dessiner toute l'extension ; bien dessiné, ultra cohérent à 100 % avec l'Atlas et la carte Expanded ;
utilise CAIME et tous les outils nécessaires ».

## Principes (décisions de Charles et règles de l'atelier)

- **Construit en public** (Charles, 25.09.2026 vers 16 h 10 : « building public, build in public ») : article du site
  « créer une expansion de carte de zéro à 100 » (session « Vidéo »), captures et avancées partagées ; source :
  `JOURNAL.md` et `captures-article\`. Le PACK d'Expanded, qui contient des fichiers de WH1 : objet Workshop 3807968769
  MASQUÉ, aucun lien donné (la Saison, elle, est « Non classée » avec lien public depuis le 25.09 : `CLAUDE.md` § 2).
- **Session qui tient le chantier** : « Expanded map integration et polish » (grille, terrain, départ, vie, kit
  d'Expanded) ; pack et startpos : la Construction.
- **Le pack actuel est un pack D'ESSAI** : sans scripts de campagne, sans `__save_counter` ; il a chargé une première fois
  le 4.10.2026 vers 20 h 40 (démarrage de référence, sans fleuves). **Jamais actif avec le pack de la Saison.**

- **La bêta reste intacte.** Expanded est une COPIE : nouveau nom de carte dans le kit, ses propres fichiers, son propre
  pack. Jamais d'écriture sous `terrain\campaigns\wh_dlc05_wood_elves_map_1` ni dans les fichiers de la bêta.
  **Exception** (3.10.2026, accord de Charles) : les modèles de montagnes de WH1 du kit, partagés par les deux cartes,
  ont été convertis au matériau 68 par la Construction (JOURNAL, 3.10, 18 h 42 ; erreur 327) ; conversion non validée
  pour la Saison : un pack de la Saison reconstruit les embarquerait. Où ils vivent (Construction, 4.10) :
  `04-projets\saison-des-revelations\montagnes-wh1\` (maillages embarqués par build_pack pour les DEUX cartes) et
  `working_data` du kit (copies de la chaîne du terrain), convertis par `02-scripts\montagnes_materiau_68.py` ; modèles
  au matériau 49 sauvegardés dans `05-journal\terrain-backups\montagnes-mat49-20261003-183433-*`.
- **Chaîne du terrain d'Expanded** : `outils\chaine_grille_expanded.py` (bac à sable ; frontières de régions
  `generate-region-borders` avant validate) -> `outils\projet_expanded.py` -> `outils\eau_materiau_expanded.py --apply` ->
  (préavis) `outils\chaine_kit_expanded.ps1` (frontières sur la carte du kit, validate --all, process borné à 5 min, BOB,
  après-BOB, arbres) ; puis la Construction (startpos, pack : `02-scripts\chaine_expanded.sh`). Recettes communes :
  `CLAUDE.md` § 5.
- **Au centre, la carte de WH1 identique à 100 %** (décision de fond du projet) ; autour, la terre de l'extension, d'après
  l'Atlas (bretonia.dev, session « Extension »).
- ~~Première étape : la terre en décor, hors de la zone jouable~~ : fait, puis dépassé (3.10.2026) : la zone jouable
  couvre le monde entier et les régions de l'Atlas sont jouables (131 colonies).
- **Clés** : `saison_` pour tout ce que nous créons ; `wh_dlc05_` seulement pour ce qui vient de WH1.
- Préavis de 5 minutes avant toute écriture dans le kit ; jamais pendant une chaîne ou un essai de la bêta.

- **Charles (15 h 35)** : « prends en compte la topographie, je ne veux pas une map plate : les reliefs, les plaines, les
  forêts… bien faite, bien pensée, correcte par rapport à tout le travail de recherche, conforme à la map de l'Atlas » ; et
  « le miroir d'Athel Loren qu'on a mis sur les dernières versions de la map en local » (à retrouver dans l'Atlas : le
  Miroir de la session « Extension »).

## Ce que l'Atlas fournit déjà (agent de recherche, 25.09 vers 15 h 30)

> **Relevé du 25.09, périmé pour le cadre** : grille actuelle 560 × 905, WH1 en (x + 120, y + 330), Voûtes entre la
> Saison et le Bois Rêveur, clés `saison_` : voir `outils\cadre_expanded.py`.

- Tout est déjà dans NOTRE repère hex (400 × 440, x vers l'est, y vers le nord, ligne 0 au sud) : cadre de l'extension
  560 × 575 hex, `X0, X1, Y0, Y1 = -120, 440, 0, 575` (`travail\geo_extension.py:34-35`) ; futur map.hex : x + 120
  (`travail\carte_papier_v2.py:11-12`). +120 colonnes à l'ouest, +40 à l'est, +135 rangées au nord, rien au sud.
- Grilles 575 × 560 (`travail\extension_geo.npz` : terre, mer, lac, alt (pseudo-altitude, infranchissable > 5,3),
  forêt, montagne, colline, rivières, routes ; `extension_regions.npz` : régions, mers, biome aux sols CAIME, hors carte).
- Dans le cadre 400 × 440, nos couches CAIME et le relief de WH1 sont repris tels quels : jointure cohérente.
- Calage Atlas → nous : déformation MLS sur 48 villes (`travail\calage_atlas.py`), écart médian 16,4 hex.
- Passage au raster de WH1 : `travail\geo_extension.py:441-443` (ne pas passer par le SVG, proportions différentes).
- 32 régions neuves, 15 provinces, 11 mers ; clés encore sans préfixe (à passer en `saison_`).

## Fichiers

- (`saison_expanded-base-20260925.pack`, copie du pack de la bêta du 25.09 à 14 h 22 : mis à la corbeille le 3.10.2026
  avec l'accord de Charles, ménage ; il ne servait plus de référence, les packs de la bêta sont dans `pack-backups`.)
- Chaîne de la grille (3.10.2026) : `outils\chaine_grille_expanded.py` ; projet Terry : `outils\projet_expanded.py` (relief
  `relief_alpin`, habillage `habillage_expanded`, eau `eau_expanded`) ; aperçus : `carte_grille_expanded`,
  `apercu_relief_expanded`, `apercu_terrain_expanded`. Journal : `JOURNAL.md`, entrée du 3.10.

## État

Les cinq étapes prévues le 25.09 (inventaire, grille, chaîne paramétrée, CAIME, premier compilé) sont faites ; la campagne
a chargé le 4.10.2026. État courant : `JOURNAL.md` (le plus récent en bas) et `CLAUDE.md` § 4.
