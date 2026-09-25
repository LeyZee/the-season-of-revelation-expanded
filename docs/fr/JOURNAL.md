# Journal du chantier « Saison Expanded » (construction)

Une ligne par étape, avec l'heure. Images de l'article du site dans `captures-article\` (numérotées par étape).
Plan : `PLAN.md` ; principes et données de l'Atlas : `README.md`.

## 25.09.2026

- **15 h 25** : demande de Charles (« copie du pack, nommée Expanded ; dessiner toute l'extension ; ultra cohérent avec
  l'Atlas ; CAIME et tous les outils »). Dossier `04-projets\saison-expanded\`, copie du pack de la bêta
  (`saison_expanded-base-20260925.pack`, 825 Mo, hors du dossier du jeu). Deux agents de recherche en lecture seule :
  géométrie de l'Atlas, et ce qui est figé dans la chaîne.
- **15 h 30** : l'Atlas est déjà dans notre repère hex : cadre de 560 × 575 hex, carte de WH1 en x + 120, rien au sud ;
  grilles `extension_geo.npz` et `extension_regions.npz` (session « Extension »).
- **15 h 35** : aperçu 1 des données brutes (`captures-article\01_atlas_donnees_brutes.jpg`) : relief ombré de `alt`,
  forêts, montagnes, rivières. Relevé : couture verticale au nord-est, rivières très denses à l'est (signalés à la session
  « Extension »).
- **15 h 45** : inventaire de la chaîne : `CARTE` sert de source WH1 ET de cible ; taille 400 × 440 en dur dans ~30
  modules ; fichiers du kit sans clé de carte qui écraseraient la bêta (montagnes drapées, base des variantes de sol,
  matériaux d'eau et de neige). CAIME : `create --width --height`, pas de redimensionnement en ligne de commande ;
  décalage de colonnes pair obligatoire (+120 : bon). Plan en 4 phases (`PLAN.md`).
- **15 h 50** : phase 1 préparée : relevé de référence de 952 constantes dans 30 modules
  (`releve-constantes-avant-phase1.json`, outil `outils\releve_constantes.py`), module `02-scripts\carte_config.py`
  (profils `saison` et `expanded`), pas encore branché (la chaîne 17 de la bêta passe d'abord).
- **16 h** : aperçu 2 (`captures-article\02_atlas_regions_et_mers.jpg`) : 32 régions neuves et 11 mers. Découverte : une
  partie des régions neuves (Artois, Grung Zint, Helmgart, Karak Norn) est déjà dans le cadre de WH1, sur sa bordure de
  décor non jouable. Leçon : dans WH1, le sol est PLAT sous les montagnes (elles sont des maillages posés dessus).
- **16 h 05** : relief modelé v2 (`outils\relief_atlas.py`, `captures-article\03_relief_modele_v2.jpg`) : base = `alt`
  lissée ; bruit fractal ; bruit à crêtes sur domaine déformé pour les massifs (plis, arêtes) ; vallées creusées le long
  des rivières ; fonds marins progressifs. À faire : plaines trop plates, motifs marbrés sur les grands massifs.
- **16 h 10** : réponse vérifiée de la session « Extension » (`...\3b2e722f-...\scratchpad\est\expanded\reponse_construction.md`) :
  grilles FINALES = `extension_regions.npz` (pas `extension_geo.npz`) ; `alt` n'est pas une hauteur (pseudo-altitude en
  paliers ; l'Atlas n'a pas de relief numérique ; meilleure source : `atlas_relief.png`, 12 classes ; table classe →
  hauteur calée sur WH1 au § 4) ; garder WH1 tel quel dans tout le 400 × 440. Couture du nord-est = défaut de leur calage
  (moyenne des coordonnées), corrigé par eux : pas de terrain là d'ici leur feu vert. Rivières de l'Atlas 1,6 à 1,9 fois
  plus denses que WH1 : prendre les polylignes de `extension_rivieres.json`, filtrées. Miroir d'Athel Loren = « le Bois
  Rêveur », ajout à nous (18 régions d'Athel Loren reflétées), sans place dans le cadre : proposition au sud, derrière un
  voile infranchissable d'environ 26 rangées (`bois-des-reves.md` § 4) : décision de Charles. Minicarte parchemin :
  faisable par eux (≈ 1 jour), en deux calques cadrés sur Expanded.
- **16 h 15** : DÉCISION de Charles (sur conseil) : le Bois des Rêves (reflet d'Athel Loren) AU SUD, EN MIROIR (sud de la
  forêt contre le voile, comme un reflet dans l'eau ; lore : « s'étend le long de la forêt tout entière », Wood Elves 8e
  éd. p. 12), place réservée DÈS la grille : **Expanded = 560 × 825 hex, carte de WH1 en (x + 120, y + 250)**, voile
  d'environ 26 rangées. `carte_config.PROFILS["expanded"]` mis à jour.
- **16 h 25** : consigne de Charles : l'Atlas est la SOURCE UNIQUE (site et jeu identiques). La session « Extension »
  intègre : (1) le Bois Rêveur dans la carte, ce soir : voile en y −26..0, reflet des 18 régions d'Athel Loren (rangées
  33..256 de la Saison) en y' = 7 − y (de −26 à −249), à l'aplomb (x' = x), éther hors jeu ailleurs dans la bande sud ;
  (2) tri des rivières (ordre de Strahler, longueur, troncs reliés) et (4) couture du nord-est : demain matin ; (3) le
  relief du site reprendra le nôtre quand il sera stable.
- **16 h 45 - 17 h** : PHASE 1 commencée (pendant les essais de la bêta). 11 modules branchés sur `carte_config`
  (générateur, caméra, lf_normal, textures du sol, éclairage, arbres, rivières, entités, ajouts WH3, montagnes ; la
  source WH1 séparée de la cible). Contrôle : carte `saison` = 0 constante différente sur 955 ; carte `expanded` = 28
  différences, toutes des cibles (clé de carte, dossiers du kit et de l'atelier), aucune source WH1. Sauvegardes :
  `05-journal\scripts-backups\*-avant-expanded-phase1-20260925.py`. Reste : `masques_eau_carte` (domaine de l'IA),
  `build_pack`, tables et startpos, noms des matériaux d'eau et de neige, puis l'étape de placement (monde agrandi).
- **17 h 07 - 17 h 30** : PHASE 2 lancée (Charles : « pourquoi attendre demain »). Dans le bac à sable (`caime\`,
  rien dans le kit) : CAIME `create --name saison_expanded_map --width 560 --height 825`, `sync-names` (15 sols de
  terre, 6 de mer, 42 climats, 12 attritions ; aucune région : la carte n'est pas déclarée dans la base). Script
  `outils\grille_expanded.py` : 8 couches de la Saison renumérotées par nom et posées en (x + 120, y + 250) ; Atlas
  (`biome` = index CAIME à plat, rivières) partout hors de la partie JOUABLE de la Saison (mesure : accord Atlas / Saison
  98,5 % sur le jouable, 61 % sur la bordure de décor de WH1, où l'Atlas a 25 680 hex de régions neuves) ; tout
  infranchissable hors Saison ; bande du sud vide (Bois des Rêves). `import-layer`, `export-layer --format png`.
  Rendu aux couleurs naturelles : `captures-article\04_grille_caime_560x825.jpg` (`outils\rendu_grille.py`).
- **17 h 35** : relief du MONDE ENTIER assemblé (`outils\relief_monde.py`, 4 px par hex pour l'aperçu) : au centre, la
  hauteur réelle du projet Terry de la Saison (repère des rasters, nord en haut, posée à x + 120 hex, 135 hex sous le
  haut) ; autour, le relief de l'Atlas RECALÉ sur les hauteurs de WH1 (table de la session « Extension » : prairie ~1,6,
  collines 2,4-6,9, montagne 3,2-10,5, maximum 13,8 ; mon prototype plafonnait à 3) ; raccord progressif sur 6 hex,
  seulement dans la bordure de décor de la Saison (le jouable reste celui de WH1). Aperçu :
  `captures-article\05_relief_monde_4px.jpg`. À reprendre : plaines de l'extension un peu plates, couture du nord-est
  (données de l'Atlas, corrigée demain), Bois des Rêves.
- **17 h 45** : LE BOIS DES RÊVES dans l'aperçu (Charles : « attaque aussi le miroir ») : définition de la session
  « Extension » (18 régions d'Athel Loren de la Saison, royaumes de `bois_des_reves.DOMAINES` ; hex (x, y) -> (x, 7 - y),
  rangée 257 - y de la grille ; voile de brume de 26 rangées) : 31 276 hex reflétés, hauteurs et sols compris, teintés
  aux couleurs de Slaanesh ; éther sombre ailleurs dans la bande. `captures-article\05_relief_monde_4px.jpg`.
- **17 h 55** : NOM : « le Bois Rêveur » est la forme officielle française de CA (session « Extension ») ; « Bois des
  Rêves » dans les lignes plus haut et les scripts = le même lieu. Zooms à 8 px par hex (`captures-article\06a` côte de
  Lyonesse, `06b` jonction Saison / Artois, `06c` Bois Rêveur) : vues de DONNÉES (sols par hex, relief ombré), pas encore
  le rendu du jeu. Les commandes en ligne de CAIME (create, import-layer, export-layer, info, sync-names) sont sur notre
  branche locale `cli-create-import`, non poussée.
- **17 h 45** : PHASE 3 commencée (Charles : « attaque la phase 3 dès que c'est bon »). `outils\projet_expanded.py` fabrique
  le projet Terry `saison_expanded_map` À PARTIR de celui de la Saison (lu, jamais écrit), dans le bac à sable
  (`terry\saison_expanded_map\`) : 10 rasters agrandis (relief et fond de mer 6604 × 4480, blend et couleurs, corruption,
  neige, arbres, ombre, visibilité), carte des tuiles, 51 523 positions d'objets décalées de (+79,959 ; +192,557) u,
  `.terry` (world_width 373,142) et `rules.bob` à la clé d'Expanded, éclairage recopié. RÈGLE : tout le cadre 400 × 440
  reste celui de WH1 (ses montagnes sont drapées sur son relief) ; raccord HORS du cadre, sur 6 hex. Défauts vus sur
  l'aperçu `apercus\08-projet-expanded-relief.png` : rayures du raccord le long des bords (prolongement par rangée /
  colonne, à lisser) ; blend et arbres de l'extension = valeur la plus fréquente de la Saison par type de sol (à affiner
  avec les forêts de l'Atlas). Reste avant BOB : déclarer la carte Expanded dans la base (zone jouable, régions), zones
  d'éclairage décalées, liste des arbres.
- **16 h** : demande de Charles transmise par la session « Vidéo » : un grand article du site, « créer une expansion de
  carte de zéro à 100 ». Ce journal et `captures-article\` servent de source.
- **18 h** : RACCORD NATUREL (Charles : « que la map de WH1 déboule naturellement, sans bordure ») : le relief de WH1 est
  prolongé hors du cadre par un remplissage lisse (« push-pull » par pyramide, plus de rayures), puis fondu dans celui de
  l'Atlas en smoothstep sur 12 hex ; côtes de l'extension lissées (masque de mer flouté sur 1,2 hex) ; relief de l'Atlas
  érodé (ravines fines sur les pentes, comme le relief de WH1).
- **18 h 08** : PHASE 2, DÉCLARATION DANS LE KIT (préavis de 18 h 02) : `outils\spec_expanded.py` écrit
  `map_spec_expanded.json`, que `02-scripts\declare_map.py --apply` inscrit dans `raw_data\db` (sauvegarde
  `05-journal\db-backups\20260925-180842`) : carte `saison_expanded_map` (560 × 825), campagne `saison_expanded`
  (« The Season of Revelation: Expanded »), zone jouable 1758400003 = celle de la Saison décalée (x 79,96 à 346,49 ;
  z 192,56 à 531,46), routes `saison_expanded_road_lv_1` à `3`, 61 régions de WH1 reliées à la carte (clés `wh_dlc05_`
  partagées : les scripts de la Saison restent valables). Clés vérifiées libres avant écriture. Le pack de la bêta n'en
  prend rien (`build_pack` filtre carte et campagne sur les clés exactes de la Saison). Régions et mers neuves
  (`saison_<clé>`, `saison_sea_<clé>`, noms revus par la session « Extension ») : phase 2 bis.
- **18 h 30 - 18 h 40** : LE BOIS RÊVEUR DANS LE PROJET DE TERRAIN (`projet_expanded.py`), depuis les grilles de la session
  « Extension » (`travail\reves_grilles.npz` : terre, voile, rivières, régions ; 250 × 560, ligne 0 au sud) : relief, eau
  (rivières et étangs), sols, arbres, neige d'hiver et carte des tuiles d'Athel Loren REFLÉTÉS depuis WH1 (rangée de pixel
  p' <- 1142·f − 1 − p), fondus sur ~1 hex ; couleur teintée de Slaanesh (lilas, 35 %), LISIÈRE magenta et corrompue
  (masque de corruption au plus haut) ; voile de brume lilas et corrompu ; autour, une MER D'ÉTHER violet sombre (fond
  −1,2, surface 0,02) où le reflet flotte comme une île. Aperçu : `captures-article\10-bois-reveur.jpg`. À faire : bords
  du voile adoucis et effets de brume (phase 3, objets d'effets), objets du reflet (arbres et décors de WH1, positions
  reflétées), habillage de Slaanesh (PLAN.md, idées).
