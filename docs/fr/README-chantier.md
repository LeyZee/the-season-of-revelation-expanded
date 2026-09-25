# Saison Expanded : la carte agrandie à toute la Bretonnie

Chantier ouvert le 25.09.2026 vers 15 h 25 à la demande de Charles : « fais une copie du pack, tu la nommes Expanded, et
tu commences à dessiner toute l'extension ; bien dessiné, ultra cohérent à 100 % avec l'Atlas et la carte Expanded ;
utilise CAIME et tous les outils nécessaires ».

## Principes (décisions de Charles et règles de l'atelier)

- **Construit en public** (Charles, 25.09.2026 vers 16 h 10 : « building public, build in public ») : article du site
  « créer une expansion de carte de zéro à 100 » (session « Vidéo »), captures et avancées partagées ; source :
  `JOURNAL.md` et `captures-article\`. Le PACK, qui contient des fichiers de WH1, suit la décision de la bêta (Workshop
  masqué, lien donné aux volontaires) tant que Charles n'en décide pas autrement.

- **La bêta reste intacte.** Expanded est une COPIE : nouveau nom de carte dans le kit, ses propres fichiers, son propre
  pack. Jamais d'écriture sous `terrain\campaigns\wh_dlc05_wood_elves_map_1` ni dans les fichiers de la bêta.
- **Au centre, la carte de WH1 identique à 100 %** (décision de fond du projet) ; autour, la terre de l'extension, d'après
  l'Atlas (bretonia.dev, session « Extension »).
- **Première étape : la terre en décor**, hors de la zone jouable, infranchissable, sous le brouillard, comme les bords des
  Empires Immortels ; les régions jouables viendront ensuite, une à une.
- **Clés** : `saison_` pour tout ce que nous créons ; `wh_dlc05_` seulement pour ce qui vient de WH1.
- Préavis de 5 minutes avant toute écriture dans le kit ; jamais pendant une chaîne ou un essai de la bêta.

- **Charles (15 h 35)** : « prends en compte la topographie, je ne veux pas une map plate : les reliefs, les plaines, les
  forêts… bien faite, bien pensée, correcte par rapport à tout le travail de recherche, conforme à la map de l'Atlas » ; et
  « le miroir d'Athel Loren qu'on a mis sur les dernières versions de la map en local » (à retrouver dans l'Atlas : le
  Miroir de la session « Extension »).

## Ce que l'Atlas fournit déjà (agent de recherche, 25.09 vers 15 h 30)

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

- `saison_expanded-base-20260925.pack` : copie du pack de la bêta du 25.09 à 14 h 22 (chaîne 16), point de départ, hors
  du dossier `data` du jeu (non chargé).

## Étapes prévues (à préciser après l'inventaire)

1. Inventaire : géométrie de l'Atlas et son repère (session « Extension ») ; ce qui est figé sur le nom et la taille de la
   carte dans la chaîne (agent de recherche, 25.09 15 h 25).
2. Grille de la nouvelle carte : taille en hex, place de la carte de WH1 dedans (décalage), zone jouable = la Saison.
3. Chaîne paramétrée par nom de carte et taille ; masques de terre, mer, rivières, forêts, montagnes de l'extension
   produits depuis l'Atlas sur cette grille.
4. CAIME : grille hex, lookups, pathfinding de la carte agrandie (zone hors jeu infranchissable).
5. Premier compilé, contrôle dans Terry et en jeu (pack Expanded chargé SEUL, jamais avec celui de la bêta).
