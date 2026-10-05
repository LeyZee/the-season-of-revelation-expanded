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
- **19 h (décisions de Charles)** : dans Expanded, **l'Atlas l'emporte sur WH1** ; la partie jouable de WH1 est
  redessinée d'après l'Atlas (provinces, villes) ; coutures terre / mer réglées selon l'Atlas (terrain adapté dans
  `projet_expanded.py` : l'Île Silencieuse levée, la Baie Moussille et Manaanspoort creusées) ; les 11 maîtres de départ
  à trancher : recherche (équilibrage, lore, gameplay), 11 recommandations validées par Charles
  (`decisions-maitres.json`). Publication du dépôt Expanded validée par Charles : public depuis 19 h 30
  (github.com/LeyZee/the-season-of-revelation-expanded ; liste blanche, rien de dérivé de WH1).
- **19 h 14 - 19 h 28** : PHASE 2 BIS, RÉGIONS DÉCLARÉES dans le kit depuis `expanded_declaration.json` (session
  « Extension ») : 76 régions (32 neuves, 14 découpes, 11 mers, 18 du Bois Rêveur, 1 reprise), 21 provinces
  (`saison_province_*`), 65 colonies ; couleurs de région écartées, stables d'une génération à l'autre. Deux
  corrections dans la foulée : 9 clés renommées par l'Atlas (noms abandonnés : Thurin -> Barfleur…,
  `outils\retirer_cles_renommees.py`) ; **Fort Solstice** : la province d'une région étant GLOBALE dans WH3, la région de
  WH1 garde sa province (la bêta n'en voit rien) et Expanded prend une reprise à clé à nous,
  `saison_glanborielle_fort_solstice`, capitale de Glanborielle. Sauvegardes : `db-backups\20260925-191420`, `-192132`,
  `-192133`, `-192836`.
- **19 h 30** : COUCHE DES RÉGIONS dans CAIME (`outils\regions_expanded.py`) : `sync-names` (136 régions : 122 terrestres,
  14 maritimes), puis chaque hex reçoit sa région d'après les grilles de l'Atlas (découpes > régions neuves > mers >
  reprise > régions de WH1 > Bois Rêveur > terres et mers sauvages ; les 405 cases de lacs en mer sauvage). Contrôles :
  0 case sans région, 0 région sans case. Aperçu : `captures-article\11-regions-expanded.png`.
- **19 h 45 - 20 h** : VILLES ET PASSAGE (`outils\villes_expanded.py`, `retouches_expanded.py`) : les 57 villes de WH1
  recopiées (aucune coupée par une découpe), 64 villes neuves (au `hex_ville_expanded` de l'Atlas ; celles du Bois Rêveur
  au reflet de leur modèle de WH1), 13 ports (hex de port rattachés à la région de la ville, comme dans WH1), poussées à
  19 hex (16 en port) par `grow_town_slots.py` ; Bois Rêveur : sols et climats reflétés d'Athel Loren, éther en mer,
  voile en montagne ; passage selon l'Atlas (régions neuves et mers franchissables, 5 ouvertures de cols = 65 hex, voile
  fermé) ; climats de l'extension (`mtn_pass` en montagne, `brt_moorlands` ailleurs, comme la Saison) ; 30 infranchissables
  isolés ouverts ; 8 hex de cols rattachés à leur région. Validation CAIME : restent 4 erreurs d'étalement « deux zones
  dangereuses », dont 2 existent déjà dans la carte de la Saison, que le jeu compile (Chêne, Défilé de la Hache) ; les 2
  neuves (Poste de la Pierre Noire, par l'ouverture du Sentier ; Ubersreik, sur sa rivière) sont de même nature : à
  surveiller à la première compilation.
- **20 h 10** : MINICARTE D'EXPANDED (`outils\lookup_expanded.py`) : trame hex -> pixels validée contre le lookup de CAIME
  de la Saison (99,77 % d'accord) ; lookup 2240 × 3810 et quart, contours lissés comme la Saison (0,66 % des pixels),
  palette de 136 couleurs (les 11 mers, déclarées en noir, recolorées dans le kit : `maj_couleurs_mers.py`) ; parchemin
  de la session « Extension » (1120 × 1905, cadre exact). Contrôle : `images-carte\controle_regions.png`.
- **20 h** : BORDURE DE WH1 REMPLACÉE PAR L'ATLAS (`projet_expanded.py`, `garde_wh1_hex`) : le terrain de WH1 n'est plus
  gardé que sur sa partie jouable + 4 hex et là où l'Atlas n'a rien de neuf ; sur 25 898 hex de la bordure décorative,
  sous des régions ou mers neuves, c'est le relief de l'Atlas, raccordé ; 270 objets de WH1 (falaises, montagnes posées)
  retirés de cette bordure. Le cadre reste visible là où l'Atlas n'a que de la terre sauvage (est, sud) : à reprendre.
- **20 h 15** : CONSEIL DE CHAOSROBIE (Discord, #showcase, 18 h 46) : le calcul des chemins du jeu se dérègle si une
  partie de la carte n'est reliée à rien (les nœuds de téléportation ne comptent pas ; le Royaume du Chaos de CA s'en
  sort sans colonies et avec une IA « sur rails »). Or le Bois Rêveur (18 colonies) était coupé du reste. DÉCISION DE
  CHARLES : on garde les PORTAILS comme seule entrée, plus sa solution de The Old World (Rivière des Échos) : un FIL DE
  RIVIÈRE CACHÉ d'un hex, sous le voile, de la Porte d'hiver (Tal Mora, Atylwyth) à son reflet (Tal Amere du Bois
  Rêveur), colonne 376, rangées 192 à 316 (`retouches_expanded.py`, étape 5). Contrôle `outils\connexite_expanded.py` :
  les 121 colonies sur une seule composante franchissable (le Camp des Orques de fer, enfermé dans les Irrana, a reçu un
  passage de 3 hex). À vérifier au premier essai en jeu d'Expanded (ChaosRobie : « I believe »).
- **20 h 20** : PLUS DE CADRE AUTOUR DE WH1 (`projet_expanded.py`) : le terrain de WH1 n'est gardé que sur ses 59 régions
  (massifs infranchissables intérieurs compris) + 4 hex, soit 103 834 hex ; l'Atlas partout ailleurs, raccordé
  (72 166 hex du cadre) ; 514 objets de la bordure retirés. Nord, est et ouest : plus de bord visible ; les Montagnes
  Grises de l'Atlas enveloppent la carte. Reste : au sud-ouest, une baie de l'Atlas s'arrête net sur le bord ouest de WH1
  (côte droite, `scratchpad\zoom_couture_so.png`) ; à reprendre avec la session « Extension », comme la couture du
  nord-est. Idée de la communauté notée au PLAN : les Voûtes, pour une extension future.
- **20 h 30** : DÉCISION DE CHARLES : les VOÛTES entrent dans Expanded (sud-est de la bande du sud, voile raccourci au
  miroir) et Kemmler y part (sources lues avec le navigateur de Charles : Krinal, sa forteresse des Voûtes, WD 309 p. 61 ;
  tombeau de Krell dans les Grises ; bataille des Cairns, Wood Elves 8e p. 32). Recherche et dessin : session « Extension ».
- **21 h - 21 h 35** : RELIEF (`outils\ombrage_expanded.py`, `captures-article\12-relief-ombre.jpg`) : rebord de bord de
  carte de WH1 retiré sur 8 hex (sauf ses terres franchissables) ; raccord à largeur proportionnelle à l'écart d'altitude
  (pente ≤ 0,5 u par hex) ; piémonts de l'Atlas plus larges (altitude lissée sur 4 hex) ; le front des Grises vers le
  Reikland reste raide (vraie falaise, ~0,9 u par hex). ÎLES DES HAUTS ELFES (Charles : « ça fait un peu bizarre ») :
  Tor Martel et sa petite île étaient noyées à 100 % (couche `mer` de l'Atlas sur des régions terrestres, puis raccord
  qui prolongeait la mer de WH1 jusqu'à elles) ; l'Île Silencieuse à moitié ; corrigé (terre des régions prioritaire,
  pas de raccord terre de l'Atlas / mer de WH1, altitude de collines basses, montée douce depuis le rivage) ; une
  fausse bande de terre dans la mer (rivage de la couture de la Baie Moussille qui relevait la mer) supprimée. Reste :
  léger trait vertical sur l'Île Silencieuse, au bord du cadre.
- **21 h 15** : page Workshop d'Expanded créée par la session « Extension » (id 3807968769, masquée ; pack de démonstration).
- **21 h 50 - 22 h 15** : TRAITS DROITS DU RELIEF (`projet_expanded.py`) :
  - Grises de l'ouest (rangée 532), texture fine de WH1 d'un côté, remplissage lisse de l'autre, le long du bord de la
    zone gardée : le détail de WH1 (relief moins son flou sur 2 hex) est rendu au raccord, dans le cadre, hors du rebord,
    et s'efface quand l'Atlas l'emporte. Reste un petit rectangle, présent dans WH1 lui-même : gardé.
  - Mer près de l'Île Silencieuse : bande trop peu profonde le long du cadre, parce que le fond venait de la surface
    prolongée de WH1 (−0,1). Désormais le fond de mer de WH1 est prolongé et fondu dans celui de l'Atlas ; le fond est
    aussi lissé sur ±6 hex du bord du cadre, sous l'eau. Marche au bord ouest : 0,035 au plus (contre 0,36).
  - Arête presque droite des Grises de l'est (rangées 528-535, hex 460-535) : c'est la vallée d'un col dessiné par
    l'Atlas (altitude 3,3 entre des sommets à 7-8), rendue telle quelle (poids de l'Atlas = 1). Signalée à la session
    « Extension ».
  - Couture du sud-ouest : la baie et un lac de l'Atlas s'arrêtent sur le bord du cadre (colonne 119), donnée de
    l'Atlas : demandé à la session « Extension ».
  - Couture du nord-est : pas de marche (0,008 u), seulement une teinte de l'aperçu.
  - Essayée puis retirée : une marge variable autour de WH1, sans effet sur l'arête de l'est.
- **21 h 45 (25.09)** : VOÛTES, esquisse v2 de la session « Extension » (trois lieux dans la bande de montagnes au sud d'Athel
  Loren : Krinal pour Kemmler et Krell, Karak Bhufdar, Karak Izor capitale) envoyée à Charles ; rien n'est touché avant
  son accord.

## 3.10.2026 (session « Expanded map integration et polish », REPRISE `05-journal\2026-10-03-expanded-suite\`)

- **13 h 10 - 13 h 30** : GRILLE CAIME AU CADRE 560 × 905, étapes 1 et 2 de la REPRISE (rien dans le kit). Carte vierge
  rangée (`archives\vierge-560x905-20261003\`) ; `sync-names` : 132 régions de terre + 14 de mer, 15 + 6 sols, 42
  climats, 12 attritions. Toute la chaîne en un lanceur : `outils\chaine_grille_expanded.py <étiquette>` (grille,
  régions, villes, retouches, connexité, validation CAIME rangée par zone ; journaux
  `05-journal\2026-10-03-expanded-suite\validations\`). Corrections, chacune mesurée par la validation :
  - **côtes** (`outils\cotes_expanded.py`, appelé par `villes_expanded` avant la pose des villes) : la Saison n'a aucun
    avertissement de côte, Expanded en avait ~700 (langues de terre d'un hex, cases isolées, 262 cases de mer dans des
    régions de terre), tous dans l'Atlas et le Bois Rêveur. Lissage majoritaire (4 voisins sur 6) jusqu'à stabilité :
    514 cases de terre -> mer, 380 de mer -> terre, 236 régions remises d'accord avec le sol ; jamais les régions de
    WH1 restées les siennes, ni le voile, ni plus de 15 % d'une région nommée (les îles restent des îles) ; -> 0 ;
  - **rivières de l'extension** (`outils\rivieres_svg_grille.py`) : celles de la carte de l'Atlas (`carte_papier_v2.svg`,
    raccordées et lissées, les mêmes que la minicarte) au lieu de `riv_ext` (7 819 cases en escaliers ; au Reikland,
    un maillage qui coinçait Ubersreik) : 1 908 cases. Repère linéaire de l'Atlas, contrôlé sur les rivières de WH1 du
    même fichier : 100 % à une case au plus de celles de la Saison ;
  - **ports** : mesuré sur la Saison (qui tourne en jeu), ses cases de port en mer gardent leur RÉGION DE MER ; on les
    rattachait à la ville (« comme dans WH1 », faux) : 25 avertissements. Rattachées le temps de `grow_town_slots`
    (qui reconnaît un port à la région de ses cases), puis rendues à leur mer : 13 ports, 0 avertissement ;
  - **Brèche des Orques de fer** : l'ouverture de l'Atlas finissait en cul-de-sac, à 4 cases de la Gasconnie, sur la
    bordure de WH1 (Camp des Orques de fer hors de la composante principale). Toute ouverture qui n'atteint pas la
    composante principale est prolongée par la terre (+3 cases), dans le sens que lui donne l'Atlas, plutôt qu'un
    passage au plus court à travers la forêt de Férignac ;
  - **rivières du Bois Rêveur** reflétées AVANT la pose des villes (elles l'étaient après : Error d'étalement du palais
    d'Argwylon reflété) ;
  - retouches : terre sauvage ouverte seule laissée fermée ou rattachée ; trous et poches franchissables sans ville
    refermés (6 cases) ; cases isolées de leur région rattachées à la voisine (Oisillon, Camp des Orques : plus de région
    en deux morceaux).
  Bilan (`validation-7.log`) : 131 colonies sur une seule composante franchissable ; restent 4 Error d'étalement, toutes
  des villes en col (deux vallées de sortie) : Chêne d'Âges et Défilé de la Hache (déjà dans la Saison, qui tourne en
  jeu), Poste de la Pierre Noire (le Sentier de Kemmler lui ouvre une seconde sortie), ruine de Karag-Dar : à juger en
  jeu (le guide CAIME : CA en a cinq). Avertissement restant : la terre sauvage en 14 morceaux (décors hors jeu, massifs
  enclavés, îlots), quand la Saison n'en a qu'un : à surveiller à la génération du startpos.
  Aperçus : `apercus\grille-v2-*.png|jpg` (`outils\carte_grille_expanded.py`), envoyés à Charles.
  Constat pour la session « Saison » : la `map.hex` de la Saison dans le kit n'est plus d'accord avec la base 9.0.2
  (42 climats contre 40, 12 attritions contre 11 ; `validation-saison-reference.log`) : sans effet tant qu'on ne la
  réexporte pas ; à resynchroniser (`sync-names`) avant tout export de la Saison. Et la ligne de `saison_expanded_map`
  est la DERNIÈRE de `campaign_map_playable_areas.xml` : l'export Map Data plantera (guide CAIME, « le piège de la
  dernière ligne ») ; à déplacer, sous préavis, avant le premier `process`.
- **13 h 40 - 16 h** : GRILLE, suite (demandes de Charles et de la session « Extension ») :
  - rivières de l'Atlas reprises à chaque version de `carte_papier_v2.svg` (dernière : 15 h, rivières du lore de Couronne,
    des Marches et du Reikland) ; bande de mer droite du sud-ouest corrigée dans les grilles de l'Atlas par sa session ;
  - **col de jeu Grises - Voûtes** (Charles : « les montagnes du sud connectées aux montagnes de l'est, avec les
    passages ») : `villes_expanded.OUVERTURES_JEU`, de la vallée de Grimhold à celle des Brise-Nuques ;
  - **enclaves de terre sauvage** (« province sans nom » vue par Charles entre Couronne, les Marches, les Sœurs Pâles,
    Gisoreux et l'Artois) : réparties entre leurs régions voisines (`regions_expanded`, règle de la session
    « Extension », appliquée aussi à la minicarte) ; 4 enclaves, 8 718 cases ; leur haute montagne reste FERMÉE (7 643
    cases : le massif intérieur des Grises de l'est l'aurait sinon été ouvert, +4 800 cases franchissables, rattrapé) ;
  - **villes neuves placées au mieux** (`villes_expanded.meilleur_emplacement`, ≤ 3 hex de l'Atlas) : 16 bougent de 1 à
    2 hex (Oisillon, sur une rivière ; Karag-Dar…). Validation (`validation-14.log`) : 3 Error, toutes des villes de col
    de WH1 (Chêne d'Âges, Défilé de la Hache, Poste de la Pierre Noire) ; 131 colonies, une seule composante.
- **14 h - 16 h** : TERRAIN (projet Terry du bac à sable, rien dans le kit), aperçus `apercus\relief-v*`, `terrain-v*` :
  - **relief v4** (`outils\relief_alpin.py`, à la place de `relief_atlas`) : les montagnes « en marbre fondu » refaites par
    érosion fluviale avec soulèvement (Braun et Willett) à l'échelle de l'hex, plaines et vallées de jeu pour exutoires,
    diffusion des versants, receveurs bruités (sans « peignes »), ramenées aux sommets de l'Atlas ; les vallées
    franchissables de la grille creusées en auge (on voit passer les armées là où elles passent) ; aucun détail plus fin
    qu'un hex (Charles : « trop pixelisé… tout smooth ») ; massifs reliés par leurs cases fermées (Grises -> Voûtes) ;
    bords de massif ondulés (jamais sur une case franchissable) ; bords de carte en exutoires, quelques-uns seulement au
    sud ;
  - **raccord à WH1** : marge de WH1 réduite à 2 hex (1 sous les régions neuves et les enclaves) et fondue sur 2,5 hex
    hors de ses régions jouables : plus de bourrelet de cadre ni de dents de scie ;
  - **habillage** (`outils\habillage_expanded.py`) : textures, arbres et couleurs de l'extension tissés depuis la matière
    de la Saison (fenêtres de 64 hex par type de sol, cellules irrégulières de ~28 hex puisant chacune ailleurs, lisières
    bruitées : ±1 hex en jeu, ±8 hex dans le décor fermé) ; éboulis de WH1 sur les pentes, neige des hauts sommets au
    masque ; abords d'une ville bretonne de WH1 autour de chaque ville bretonne ou impériale neuve (31) ; mer lissée ;
  - **eau** (`outils\eau_expanded.py`) : les mers de l'Atlas n'avaient aucun plan d'eau ; les 3 mers de WH1 remplacées par
    46 polygones couvrant toutes les mers d'Expanded (99,99 %, sans recouvrement, découpés par intersection exacte), 24
    lacs de WH1 gardés, calque `ether_reves` à part ; éther remis à la convention de WH1 (surface 0,02, fond sous 0 ; il
    avait l'inverse, qui aurait masqué l'eau) ;
  - **la déchirure** : le voile devient éther, le bord sud des Voûtes une falaise déchirée (1 à 14 hex, cases fermées
    seulement) ; le fil caché, passage de jeu, reste une chaussée visible ;
  - **décors** (`outils\decors_expanded.py`) : 2 452 objets des abords des villes de WH1 (fermes, cultures, clôtures,
    potagers, chemins, sons, décors conditionnels de pillage et de corruption) recopiés autour des 31 villes neuves, à
    la hauteur du nouveau terrain ; un calque vide par région neuve (85, guide Terry : un File Layer par région) ;
    Fort Solstice de WH1 renommé en sa reprise ; identifiant de projet propre.
  Restent avant le jeu : matériau d'eau et masques d'Expanded (éther compris ; domaine « IA et modding 3D »), kit
  (ligne de la carte, projet dans `raw_data`, exports CAIME), BOB, chaîne d'après BOB au cadre d'Expanded (textures de
  WH1, arbres de WH1, brouillard, caméra, `lf_normal`), pack, factions de l'Atlas, startpos.
- **16 h 05 - 17 h** : KIT ET BOB (Charles : « Kit + BOB, avec la Construction » ; préavis unique 16:13:20 annoncé à la
  Construction et à « Lakemen » ; BOB après la série d'essais en jeu de « Lakemen ») :
  - `outils\kit_expanded.py` : ligne de `saison_expanded_map` déplacée avant la dernière de `campaign_map_playable_areas`
    (piège de Map Data) et **zone jouable étendue au monde entier** (elle n'était que la Saison décalée : x 0-373,14,
    z 0-697,06) ; grille et fichiers d'appui (`outils\appui_caime.py`) dans `raw_data\EmpireDesignData\campaign_maps\`,
    projet Terry dans `raw_data\terrain\campaigns\` ; sauvegardes `db-backups\20261003-161411-avant-ligne-expanded` (et
    163545) ; anciennes copies rangées dans `terrain-backups\` ;
  - **exports CAIME** tous réussis (`05-journal\2026-10-03-expanded-suite\exports\`) : Map Data (3,3 Mo, code 0),
    pathfinding, routes commerciales, lookup, et Borders en ligne de commande avec notre CAIME ;
  - **BOB** (`compiler_terrain_bob.py`, DLL 9.0.2 relevée par la Construction) : premier passage en échec (9 actions sur
    12, « Wrong size, expecting 3200x3524 » : le .terry recopié déclarait les tailles de rasters de la Saison ; masque des
    parcelles faux aussi) ; corrigé dans `projet_expanded` ; second passage **12 actions sur 12, code 0, 0 « Failed to
    find tile », 0 « quadtree »** (journal `2026-09-21-phase-3-terrain\compilations\saison_expanded_map-20261003-163550\`) ;
  - **après BOB** (crochets de la Construction dans `carte_config.SOURCE_MONDE`, `textures_sol_wh1`, `lf_normal` ;
    tout avec `SAISON_CARTE=expanded`) : brouillard, caméra (280 × 453), `lf_normal` (4480 × 7244), textures (19 groupes
    `wh1_*`, 100 % des pixels du monde en textures de WH1 ; la roche de l'extension en snow3, mud_a0, sand_b0, WH1 n'ayant
    pas d'éboulis) ;
  - **arbres** (`outils\arbres_expanded.py`) : **découverte** : BOB écrête la coordonnée z des arbres à
    world_width × 2/√3 (431 pour Expanded) : carte en portrait, 54 000 arbres empilés sur une ligne à la rangée 560 ; les
    rasters et les objets (`global_props.bin`) ne sont pas touchés. Liste finale : arbres de WH1 de la Saison à leur place
    dans la zone gardée (44 852), arbres de BOB au sud de la limite, arbres générés au nord depuis le raster d'arbres à la
    densité et au mélange mesurés sur BOB (73 629), tous rendus aux essences de WH1 (porteuses ET familles génériques de
    WH3, sinon des pins) : 138 098 arbres, 62 identifiants ;
  - aperçu depuis les fichiers compilés : `outils\apercu_compile_expanded.py`, `apercus\compile-v2-*.jpg`.
  Pas d'Expanded en jeu avant la conversion des montagnes de WH1 par la Construction (matériau 49 -> 68, cause probable du
  plantage de rendu de la Saison, que les objets recopiés dans Expanded partagent).
- **3.10, soir : l'eau d'Expanded** (Charles : « attaque tout ça », point 2). `outils\eau_materiau_expanded.py` : importe
  `masques_eau_carte` (session IA, hors ligne) sans le modifier et lui donne le monde d'Expanded (373,142 × 697,06) :
  mer = relief du projet à 0,02 (mers, éther, déchirure), rivières et courant de WH1 de la Saison posés à leur place dans
  la zone gardée, lacs = plans de lac recopiés. Masque A : mer 35,8 %, rivières et lacs 0,49 %, 23 lacs ; 72 plans de mer.
  Trois matériaux à clés à nous : `saison_expanded_campaign_water_plane`, `..._lake_plane`, `saison_expanded_ether_plane`
  (même eau, sans écume ni vagues de rivage, lisse : l'éther). `eau_expanded` et `projet_expanded` font pointer plans et
  `.terry` sur eux (à la prochaine relance). Liste des dossiers du pack pour la Construction :
  `05-journal\2026-10-03-expanded-suite\pour-la-construction-pack.md` (crochet demandé dans `textures_sol_wh1.py`).
  Rivières de l'Atlas : toujours sans eau (lits secs).
- **3.10, soir : les 16 factions de l'Atlas** (Charles : « toi, parce que tu fais la map »). `outils\factions_atlas.py`
  (fiche `05-journal\2026-10-03-expanded-suite\fiche-factions-atlas.md`) : à blanc, 651 lignes en 11 tables, faites sur
  des mineures de CA (Karak Ziflin, Red Fangs, Necksnappers, Redhorn, Crossed Clubs, Lyonesse), 0 référence manquante ;
  hors des filtres du pack de la Saison (contrôlé) ; drapeaux de jeu (`drapeaux-jeu\`, planche
  `apercus\drapeaux-factions-atlas.jpg`) et textes EN/FR (`textes\factions_atlas.json`). Le kit n'est pas encore
  écrit (feu vert de la Construction et préavis). Départs (start_pos), Kemmler à Krinal, maîtres et diplomatie :
  après la recopie du départ de la Saison vers `saison_expanded` par la Construction (correspondance des identifiants).
  Charles a donné son accord pour la conversion des montagnes (transmis à la Construction).
- **3.10, 18 h 42 : factions écrites dans le kit** (préavis de 18:42:02, Construction et « Lakemen » prévenues) :
  651 lignes en 10 tables, sauvegarde `05-journal\db-backups\20261003-184210-factions-atlas`, 0 référence manquante,
  idempotent. La Construction a converti les montagnes de WH1 (matériau 68, kit libre à 18 h 36). `projet_expanded` lancé
  puis ARRÊTÉ à 18 h 39 (6,4 Go de mémoire : la série de 20 parties de la Construction en avait besoin ; le projet du bac à
  sable est donc à moitié écrit) : à relancer après « série finie », puis pose, CAIME, BOB, après-BOB, arbres, eau.
- **3.10, 19 h 05 : le départ d'Expanded par-dessus la recopie de la Construction** (`outils\depart_atlas.py`, préavis
  19:05:10) : 596 lignes en 10 tables start_pos de `saison_expanded` ; 29 factions de départ neuves (nos 16 et 13 de CA,
  aucune jouable) ; 74 régions neuves, colonies et emplacements (7 ruines ; Bois Rêveur : emplacements de la région de
  WH1 en miroir) ; 29 chefs avec armée (5 hordes) ; Kemmler, Krell et son nécromancien devant Krinal (capitale), Poste
  de la Pierre Noire rendu à Karak Ziflin ; 15 lignes de diplomatie de la fiche. Sauvegarde
  `db-backups\20261003-190519-depart-atlas`. À surveiller à l'essai de démarrage : Aislinn (horde chez CA) reçoit 3
  régions ; Karl Franz part de Helmgart (question posée à Charles). Suite : Construction (pack, startpos, essai).
- **3.10, 21 h 50 - 22 h 10 : terrain d'Expanded refait et reposé dans le kit.** Grille « bidouze » (lisière des mers de
  WH1 ouverte : 434 cases ; mer franchissable en 1 composante de 58 749 hex, 0 port fermé ; île de Landri gardée) ;
  `projet_expanded` (montagnes de WH1 converties au matériau 68 par la Construction, matériaux d'eau d'Expanded :
  46 plans de mer, 26 d'éther, 23 lacs) ; `eau_materiau_expanded --apply` ; préavis 22:00:20 ; `kit_expanded --apply`
  (anciens rangés : `terrain-backups\20261003-220026-*`) ; CAIME process code 0 ; BOB 12/12 en 85 s, 0 tuile manquante ;
  après-BOB code 0 (textures de WH1 sur 100 % des pixels) ; arbres 138 192. `warscape_asset_variation_db` : BOB ne l'a
  pas créé (processeur non construit), rien de neuf dans le kit partagé. Kit rendu à la Construction (pack, startpos,
  essai de démarrage).
- **4.10, midi (Charles : « vas y continue, tu as toutes mes autorisations »)** : décisions de la session : Lyonesse
  reste non jouable (dix seigneurs) ; Karl Franz remplacé à Helmgart par un général impérial ordinaire, Helmut
  Ludenhof (`depart_atlas.CHEFS_ORDINAIRES`, écrit 12:37, sauvegarde `db-backups\20261004-123704-depart-atlas`).
  Images déclarées par la zone jouable (provisoires, `images_campagne_expanded.py`), maillages des rivières de WH1 au
  chemin d'Expanded (`rivieres_maillages_expanded.py`), lookup à la taille du .bmp de CAIME, noms FR des régions de
  l'Atlas (`textes_atlas.py`). L'EAU des rivières de l'Atlas : `rivieres_atlas_eau.py` (89 maillages
  river_atlas_cXX_YY, même méthode que l'eau lisse de WH1), méandres doux sur les tracés de l'Atlas
  (`rivieres_atlas.meandres`), masque d'eau mis à jour ; projet relancé, pose et BOB à suivre.
- **4.10, 14 h 30 - 15 h : plantage au chargement d'Expanded, cause trouvée avec la Construction ; polish des positions.**
  Pilote sous débogueur (Construction) : +0x2613117, liste vide d'un objet de la colonie `wh_dlc05_bordeleaux_bordeleaux`,
  même plantage sans son port. Comparaison des grilles du kit (Saison / Expanded) : les trois ports de WH1 (Bordeleaux,
  Brionne, Mousillon) avaient 19 cases principales + 3 de port dans Expanded, 16 + 3 dans la Saison ; `grow_town_slots`
  les avait regrossis. Règle codée : `villes_expanded.villes_wh1_a_l_identique` (après la croissance, les colonies de
  WH1 reviennent à l'identique de la Saison) ; appliquée à la grille du chantier par `outils\villes_wh1_expanded.py`
  (11 cases ; sauvegarde `terrain-backups\20261004-144958-*`). Erreurs 333 et 334 de la Construction. Modèles
  d'emplacement : `depart_atlas.modeles_du_lore` (Bois Rêveur sous Slaanesh -> modèles humains génériques de CA, taille
  du bâtiment posé ; colonies elfes sylvaines neuves -> forêt majeure sans monument ; île Silencieuse en mineur ; jamais
  de *_port sans port), 42 lignes. Polish : conversion monde -> pixel unique (`cadre_expanded.px_de`, raster de Terry
  étiré sur 697,06 u : l'ancienne règle de la Saison décalait de 5 px au nord) dans les arbres, les décors, le contrôle
  et l'eau des rivières de l'Atlas (maillages recalés, jusqu'à 0,45 u) ; arbres à 3 px de l'eau hors WH1 gardé :
  contrôle à 0 arbre et 0 objet dans l'eau. Rivières lues sur une copie figée du SVG de l'Atlas (préavis des Voûtes :
  Brienne redessinée, feu vert attendu).
- **4.10, 15 h - 15 h 30 : kit et polish.** Préavis 14:55:38 : grille corrigée dans le kit (SHA-1 5253A90E…, ancien rangé
  `terrain-backups\20261004-145547-*`), 42 modèles d'emplacement (`db-backups\20261004-145553-depart-atlas`), CAIME
  process code 0, « kit libre » à la Construction. Arbres : `arbres_expanded.comme_wh1` règle le nombre d'arbres par hex
  de l'extension sur la distribution de WH1 (forêts et prairies seulement ; type de sol lu aux lisières ondulées de
  l'habillage, sinon la forêt s'arrêtait net sur la colonne 450 au nord-est) : forêts en massifs (63 % des hex de forêt
  dense boisés au lieu de 52 %), prairies ouvertes, 129 440 arbres, 0 dans l'eau. Prêts dans `projet_expanded`, pour la
  prochaine reconstruction du terrain : mur de 0,4 à 0,55 u au bord de la zone gardée (gros plan (440, 408) : base et
  détail rejoignent le prolongement sur RACCORD_BORD_HEX) ; grains de terre de moins de 40 px dans l'éther rentrés sous
  l'eau. Copies figées des sources de l'Atlas (SVG des rivières, extension_routes.json) jusqu'au feu vert des Voûtes.
- **4.10, 15 h 10 - 15 h 40 : Poste de la Pierre Noire et tissage des sols.** Plantage suivant au chargement (bâtiment
  introuvable, wh_dlc05_grey_mountains_2_blackstone_post) : le Poste, rendu à Karak Ziflin le 3.10, gardait les modèles
  et bâtiments de Kemmler ; entièrement nain (primary mineur nain, building1-5 vidés, modèles génériques mineurs), règle
  dans depart_atlas § 4 ; préavis 15:12:17, 3 lignes, `db-backups\20261004-151247-depart-atlas` ; audit de toutes les
  colonies à 0. Tissage des sols (`habillage_expanded`, gros plans du blend : patchwork serré, coupes droites, motifs en
  miroir, traînées) : cellules à bords ondulés au pixel (CELLULE 36) ; décalage de chaque cellule tiré DANS sa fenêtre
  (plus de miroir visible) ; fenêtre de WH1 la plus représentative de chaque type (histogramme des textures, parmi les
  fenêtres où le type domine à 60 % du maximum ; la prairie venait d'un coin de champs bigarrés) ; trous de fenêtre
  bouchés par croissance aléatoire au lieu du plus proche pixel. Taches de l'extension 1,9 -> 2,6 hex (WH1 : 3,4).
  À appliquer avec la prochaine reconstruction du terrain (projet_expanded, ~6 Go : pas pendant un essai en jeu).
- **4.10, 15 h 50 : lits doublés des rivières de l'est.** Les sept rivières de l'est (Teufel, Karak Norn, Grimhold, Wut,
  Helmgart, Arena, Skiros ouest) étaient lues deux fois, dans le SVG de l'Atlas et dans extension_rivieres.json (« est »,
  tracés droits du 24.09), à 0,3 hex d'écart, la Teufel à 1 hex : deux lits côte à côte. `rivieres_atlas.traces` ne les
  prend plus que du SVG (13 tracés reconnus « est », largeur gardée). Au feu vert des Voûtes (SVG vivant), plus aucun
  méandre ajouté : les tracés du SVG ont les leurs ; raccords droits, voulus. À appliquer à la prochaine reconstruction.
- **4.10, 15 h 55 - 16 h 10 : ports au modèle de CA et au guide ; routes (brouillon).** Plantage suivant au chargement
  (+0x2613117, liste vide) sur `saison_tor_soleil` : 9 ports neufs hors du disque de CA. `outils\ports_expanded.py` :
  `recentrer_emplacements` (ERREURS-ET-LECONS n° 45) puis un placeur au GUIDE CAIME de l'Atlas (§ Les villes) et aux
  règles de `SprawlValidator.cs` : disque de 19, 16 principales sur terre, 3 cases de port consécutives du second
  anneau dont UNE en mer (au milieu, comme chez CA), terrain à risque au contact ou à 3 hex, une seule zone au contact.
  10 ports repeints (≈ 1 hex ; L'Anguille, ville à l'intérieur des terres, rapprochée de sa côte de ~5 hex), 0 case de
  WH1 changée. CAIME validate --all : Error 3, Warning 1 avant comme après (Chêne des Âges et Défilé de la Hache :
  identiques dans la Saison ; Poste de la Pierre Noire : ville de col, le passage de l'Atlas coupe son massif ; exception
  du guide) ; une case d'étendue en trop sous le Poste retirée (`villes_wh1_a_l_identique` compare aussi l'étendue).
  Aislinn déplacée de 2 hex hors de la ville de Tor Martel (depart_atlas § 4 bis : aucun personnage sur une ville).
  villes-sortie mis à jour (abords des villes à leur nouvelle place) ; projet_expanded relancé. Routes : la grille
  n'avait AUCUNE route hors de WH1 ; `outils\routes_expanded.py` (codage relevé : bit k = direction k de DIRS, voisin
  bit k + 3), 84 routes de l'Atlas en courbes douces, 4 350 cases, 14 branchées sur les routes de WH1 en suivant le
  tracé de l'Atlas ; BROUILLON, à appliquer au feu vert des Voûtes (routes recalculées) et après regard de Charles.
- **4.10, 16 h 15 - 16 h 50 : audit d'Expanded contre les guides de l'Atlas (CAIME, Terry, BOB) et corrections.**
  Audit en lecture seule (agent) : règles des guides vérifiées une à une. Écarts et suites :
  1. **Region Borders VIDE** (0 hex sur 34 057 ; Saison 12 301) : l'export Pathfinding n'écrivait aucun passage entre
     régions (debug_land_region_passable_edges.raw à 0). Le guide CAIME se trompe (« recalculé depuis Regions à
     l'enregistrement ») : `CalculateRegionEdgeMasks` ne recalcule que les hex déjà marqués. Verbe CLI ajouté à notre
     CAIME : `generate-region-borders` (le code du bouton Auto-generate) ; Saison : 12 301 -> 12 301 ; Expanded :
     0 -> 34 057, enregistré, relu.
  2. **tile_map.png ≠ grille** : verbe CLI `export-tilemap` ajouté à notre CAIME (le code du menu Baseline Tilemap ;
     image à l'envers, rangée 0 au sud). `projet_expanded.tuiles_de_caime` : hors WH1 gardé, mer, terre franchissable et
     routes de l'export (1 042 px mis en mer, 505 px franchissables remis en terre, 456 px de routes sans route de jeu
     retirés) ; éther et déchirure gardés en mer sur l'infranchissable ; côtes sans cliff_gen, comme la Saison (côtes de
     WH1 validées par Charles : écart au guide voulu).
  3. Routes du Bois Rêveur reflétées dans la grille (1 392 hex ; côte et plages exclues ; validate --roads OK).
  4. Fond marin ≥ 0 sous la mer (≈ 256 hex) : ramené à −0,3 sous toute la mer de la carte des tuiles, hors WH1.
  5. `.terry.user` recopié de la Saison (aperçu de Terry).
  6. Terrain de bataille : 3 « Failed to find tile » = les 3 rangées hors de la grille des tuiles (bord sud d'éther),
     la Saison a le même cas sur sa dernière rangée : laissé.
  Recettes de CA (plantage +0x2602213 sur saison_tor_soleil) : `depart_atlas.RECETTES_CA` (colonie elfe de CA pour Tor
  Soleil et Tor Martel, niveaux de CA pour les Bretons majeurs, Bois Rêveur en mineures génériques), 29 lignes,
  `db-backups\20261004-163424-depart-atlas`.
- **4.10, 16 h 40 - 17 h 10 : côtes de CA, ports de CA, revue de l'aperçu.** Charles : « ajoute les côtes de CA » (modèle
  The Old World) : `outils\tuiles_expanded.py`, la carte des tuiles = export CAIME tel quel (cliff_gen, cliff_gen_ends,
  sea_coast, routes) + l'éther en mer sur l'infranchissable + l'eau de la Saison (lacs, chenaux) gardée dans WH1 ; fond
  marin sous −0,3 sous toute la mer. Ports au modèle MESURÉ de CA (session des fleuves, 290 ports) : 3 Port [mer, mer,
  plage], 10 plages ajoutées ; île Silencieuse [mer, mer, mer] (cas de CA) ; Repanse et Aislinn déplacées hors des
  villes (db-backups\20261004-165414-depart-atlas). Chaîne du kit lancée 16:49 ; CAIME process long (Pathfinding sur les
  34 057 hex de frontière, enfin pris en compte). Revue de l'aperçu (apercus\terrain-v4-10-*) et corrections pour la
  prochaine reconstruction : couleur de l'eau et du sol de WH1 fondue dans l'extension (6 et 1,5 hex : ligne droite dans
  la mer à l'ouest du golfe, ligne le long du bord est du cadre) ; bord ORGANIQUE de la zone gardée (élargi de 1 ± 0,8 hex
  dans le cadre, jamais rétréci ; escaliers d'hex autour du Chêne des Âges et dans les Grises) ; cuvettes sous la mer
  loin de l'eau comblées (creux carrés au fond d'une anse de la Lyonesse ; vrais lacs de la grille épargnés) ; méandres
  renforcés (0,9 hex) sur les tracés de l'Atlas presque droits (rainure de 30 hex dans le nord). Vus et laissés : frise
  de la déchirure (voulue), chaussée du fil caché (voulue).
- **4.10, 17 h 10 - 18 h 05 : le Bois Rêveur en royaume de Slaanesh de CA ; trous de la côte de CA.** Charles : « que le
  miroir d'Athel Loren soit vraiment le royaume de Slaanesh… tous les décors du royaume, tout ce qui peut te servir ».
  Inventaire en lecture seule de `wh3_main_chaos_map_1` (agent ; scripts et extraits dans le scratchpad de la session,
  instantané gardé : `royaume-slaanesh\royaume_slaanesh_ca.json`). Appliqué, rien inventé :
  1. **Sol** (`outils\textures_reves.py`, après BOB) : chaos_relm_slaanesh0..3 ; la corruption rampante du premier jet
     retirée (le royaume de CA n'en a pas).
  2. **Couleur** : le colour_overlay de CA sur son royaume est GRIS NEUTRE (médiane 115, 113, 115 ; mer 123, 125, 123,
     relevés dans ses DDS) : teinte lilas et lisière magenta du Bois Rêveur retirées (`GRIS_ROYAUME`).
  3. **Arbres** (`arbres_expanded.reves_slaanesh`) : nos `wh1_*` n'avaient pas de variante SLAANESH, le jeu montrait leur
     BASE (pins de l'Empire). Les 16 812 arbres du Bois Rêveur passent aux familles génériques de CA (tree_large ->
     WOODELVES chêne d'Athel Loren / SLAANESH pin de Slaanesh ; herbes, buissons, neige, marais de même) : royaume de
     Slaanesh tant que Slaanesh le tient, Athel Loren si les elfes le reprennent, comme partout chez CA. (CA ne met
     aucun arbre sur le sol de son royaume ; le Bois Rêveur reste une forêt, reflet d'Athel Loren.)
  4. **Décors** (`outils\royaume_slaanesh.py`, calque `royaume_slaanesh`) : 3 098 entités de CA (1 933 objets : griffes,
     tentacules, cornes, langues, falaises flottantes, portails, tours ; 791 décalques ; 235 effets : braseros, torches,
     portails ; 51 lumières magenta ; 88 sons des accessoires), 0,226 par u² (CA : ~0,26). Pavage en cellules de 10 u,
     chacune un morceau du royaume de CA translaté (positions relatives, orientations, échelles, écarts au sol de CA ;
     relief de CA décodé du BC6H). Écartés : palais, hameau de Marienburg, forteresse ; hors terre, villes, routes,
     rivières, pentes étrangères. Pas de rotation : convention des matrices non tranchée (test des pentes : 0,47 / 0,44).
  5. **Voile** : grains de terre en chapelet au bas du voile (trous de la déchirure, relief de terre resté) et bande
     lavande droite d'un bord à l'autre (brume du seul voile ; « bande rose en frontière » refusée le 3.10) : tout le
     voile est éther (sauf la chaussée), sans brume.
  6. **Côtes de CA, première compilation** : 280 « Failed to find tile » (cliff_gen). 234 à 2 px d'une retouche (éther,
     lacs de WH1) ; le reste : anses et bras de mer d'un hex (règle n° 97 côté mer : 32 hex de mer à > 3 voisins de terre,
     dont 30 dans la mer logique de WH1). `tuiles_expanded` : près d'une retouche et sur ces formes (+ voisins), la côte
     redevient `generic` (691 px) ; ailleurs l'export CAIME reste tel quel. **Écart au guide** (« pas de retouche de
     tile_map.png ») voulu : l'éther doit rester de la terre infranchissable dans la grille (sinon navigable), et la mer
     logique de WH1 reste celle de WH1 ; generic contre la mer = la règle de la Saison, compilée sans trou.
  À proposer à Charles, non appliqué (éclairage zone par zone, erreur 251) : l'ambiance `slaanesh.environment` de CA
  (brouillard violet, ciel de Slaanesh, sans LUT) en cylindre sur le Bois Rêveur.
  Vu et laissé (domaine de la grille de l'Atlas) : le contour de l'île du Bois Rêveur a, à l'est, des marches à angle
  droit et une encoche carrée (les frontières d'hex des régions d'Athel Loren reflétées, devenues côte). Un bord
  organique dans les rasters a été essayé puis retiré : l'éther est de la MER dans la grille (eau_expanded.masques),
  le contour en jeu est celui de la grille ; il se corrige dans reves_grilles (session de l'Atlas / des Voûtes),
  avec la règle n° 97 sur le nouveau trait.
- **4.10, 18 h 25 : ambiance de Slaanesh du Bois Rêveur, PRÉPARÉE (non posée).** Charles : « prépare l'ambiance [de
  Slaanesh] pour le Bois Rêveur ». `outils\eclairage_reves.py` : 5 cylindres d'environnement (groupes compacts de l'île,
  rayon intérieur = 99 % de chaque groupe, transition de CA de 20 u ; 97,5 % de l'île dans un rayon intérieur ; rien au
  nord des Voûtes) qui citent tel quel le fichier de CA `Weather/campaign/chaos/slaanesh.environment` (celui de son
  royaume : sans LUT, brouillard violet 0,247/0,055/0,384, ciel campaign_sky_slaanesh_01, soleil 45 000) ; aucune copie.
  Aperçu : `apercus\eclairage-reves.png`. À poser après l'accord de Charles (erreur 251 : image, puis essai en jeu) :
  `build_pack.produits_eclairage` (Construction) ajoute `eclairage_reves.lignes_cylindres()` à la collection d'Expanded
  et son contrôle des cylindres les attend.
  18 h 30 : accord de Charles (« oui, vas-y, tu as mon go ») ; demande d'intégration envoyée à la Construction
  (build_pack.produits_eclairage, branche Expanded + contrôle explicite des 5 cylindres) ; puis essai en jeu.
- **4.10, 19 h 30 - 20 h 35.** Kit : chaîne finie (BOB : 280 -> 75 « Failed to find tile », 3 « quadtree » = décors de
  Slaanesh au bord sud, corrigés dans le bac à sable) ; « kit libre » à 19 h 29. Bois Rêveur : hauteurs des décors de
  CA refaites (le relief de CA, full_height_map BC6H, est rangé du SUD au nord ; calé sur les 434 décalques : écart 0,02 u),
  falaises flottantes de bord de royaume écartées, modèles posés ramenés au sol, effets liés à leur objet ; arbres dégagés
  sous les grands décors (boîte orientée) : décision de Charles « le royaume d'abord » (~45 % des arbres gardés).
  Côtes : un repli local en generic crée lui-même des trous (une falaise de CA ne finit que sur une plage) ; à reprendre
  dans la grille (plages aux jonctions) avec les données vivantes de l'Atlas (feu vert de Charles à 19 h 15).
  **Plantage de Tor Soleil** (Construction : Aislinn est une HORDE chez CA, sans région) : décision de Charles « faction
  elfe mineure » : `saison_hef_tor_soleil` (factions_atlas, sur la Citadelle du Crépuscule de CA ; drapeau PROVISOIRE
  ivoire et bleu au soleil d'or), maîtresse des trois Tor (depart_atlas.MAITRES_CORRIGES), alliée d'Aislinn ; écrit à
  20 h 34 après préavis (db-backups 20261004-203356 et -203401).
- **4.10, 20 h 35 - 20 h 50 : routes de l'Atlas dans la grille du bac à sable.** `routes_expanded` trace désormais chaque
  morceau du tracé de l'Atlas par recherche de chemin (couloir de 3 hex ; suivre une route posée coûte peu, longer une
  route sans la rejoindre coûte ; jamais plus de 3 branches, comme WH1 ; ni côte ni plage, bouts de port ramenés à la case
  permise la plus proche) : 0 carrefour à 4 branches (102 avant : routes tracées côte à côte au lieu de se rejoindre, un
  défaut de notre tramage, pas de l'Atlas), 180 à 3. Écrit (sauvegarde terrain-backups\20261004-203807-...), CAIME
  `validate --roads` OK, Pathfinding de `process` au bout sur une copie (routes 0,9 s). Source : copie FIGÉE ; le fichier
  vivant (routes vers les 7 villes déplacées) passe avec le lot des fleuves, après le démarrage de référence validé par
  Charles (CLAUDE.md § 2). Premier essai refusé par CAIME (11 routes sur la côte) : grille restaurée, rangé dans
  terrain-backups\20261004-203707-...-routes-sur-cotes-refuse.
- **4.10, ~20 h 40 : EXPANDED CHARGE** (Construction : pack de 20 h 36, terrain compilé de 19 h 28, startpos généré ; Orion
  au tour 1, FirstTickAfterWorldCreated, aucun plantage). Démarrage de référence SANS fleuves : à voir et valider par
  Charles en jeu ; ensuite le lot des fleuves (cours du lore, villes déplacées, routes vivantes) et les côtes de CA.
- **4.10, après le démarrage de référence (bac à sable seulement, rien dans le kit).** Bois Rêveur : deuxième passe sur
  l'EMPRISE des grands objets de CA (boîte orientée, 1,5 u de haut et plus) : 327 écartés (corps sur une ville, une route,
  une rivière), 155 écartés (chevauchement entre deux cellules ; les chevauchements internes d'une composition de CA,
  voulus, restent), effets liés retirés avec eux : 2 309 entités, 65 % de la végétation gardée. `controle_cotes.py` :
  prédicteur des trous de côte depuis la grille (règle n° 97 terre et mer, falaises ramifiées) : n'explique que 16 des
  60 hex à trou de la 2e compilation (le reste vient du repli « generic », abandonné au profit de plages aux jonctions,
  au lot des fleuves). Marches de relief : 98 % expliquées (éther, montagnes) ; 498 px d'amas : fosses en hex sous 0,05 au
  bout des chenaux de mer, où les tuiles disent terre -> comblées après la carte des tuiles (projet_expanded). Bord d'eau
  des rivières de l'Atlas en l'air : 31 px, résidu déjà étudié (marches du lit), laissé. Reconstruction lancée.
  Reconstruction faite (bac à sable) : 20 213 px de fosses comblés ; surtout des rivages à fleur d'eau sur les côtes de
  l'ouest (+3 cm au plus), et la CHAUSSÉE DU FIL CACHÉ, que le relief compilé jusqu'ici laissait sous l'eau presque sur
  toute sa longueur (règle du 3.10 : « le terrain ne cache pas un passage ») : de nouveau au-dessus de l'éther. La carte
  des tuiles porte les routes de l'Atlas (4 322 px de routes sur 1 px sur 7). Pas de chaîne du kit avant la validation
  du démarrage de référence par Charles (le kit compilé reste celui de 18 h 53 / 19 h 28).
  Inspection du terrain compilé (apercu_compile_expanded, qui lit maintenant les groupes de CA dans les packs : le Bois
  Rêveur sort au bordeaux du royaume au lieu de gris) : bande pâle du nord-est = crête de 10 à 12 u (snow3 « roche et
  neige sale » au-dessus de 9,5 u, la règle des sommets), la crête de l'ancien bord de WH1 : laissée, à juger en jeu.
  sand_b3 = un sol ordinaire de WH1 (45 % de sa terre), pas du fond de mer sur la terre.
- **4.10, revue zone par zone du terrain compilé (Charles : « aucun bug, anomalie ou bizarrerie visuelle, même très
  mineur ; que tout semble naturel et vivant »).** Corrigé dans projet_expanded (reconstruction du bac à sable lancée) :
  1. 5 714 taches pâles de sable de berge de WH1 (sand_a0) loin de toute eau dans l'extension (les « taches orange-beige
     informes » du 24.09) : l'extension était tissée depuis le mélange de WH1 CORRIGÉ pour ses tuiles (fond de mer,
     plages, berges, lits) ; désormais tissée depuis son climat brut, taches de carrefour retirées.
  2. Fosses en 8 au bout des bras de mer du nord-ouest, encore là après le premier comblement : épargnées par le champ
     d'une rivière de l'Atlas qui part de là ; seul le lit même (champ ≥ 0,5) est désormais épargné.
  Vu, laissé, à juger en jeu : couture de texture au bord de la zone gardée haut dans les Grises de l'est (vers la
  rangée 614 : herbe de WH1 sous ses maillages de montagne / « roche et neige sale » de l'extension au-dessus de 9,5 u) ;
  frise de la déchirure (voulue, 3.10) ; neige carrée de Winterheart (WH1 tel quel).
  Vie : recherche de lore et des poses de CA lancée (agent ; sortie 05-journal\2026-10-04-vie-expanded\), recette de la
  Saison (vie_carte_wh3.py, rapport-vie-ambiante-wh3.md).
- **4.10, ~22 h 30 : la vie d'Expanded.** Recherche (agent, lecture seule) : 05-journal\2026-10-04-vie-expanded\
  (rapport-vie-expanded.md, vie-expanded.json : 23 candidats, 9 à éviter, lore par zone, poses de CA relevées). Choix de
  Charles : le groupe sûr + destriers elfes de Tor Soleil (et étincelles) + sabretusks et vouivres + brume pourpre du Bois
  Rêveur. `outils\vie_expanded.py` (calque `vie_expanded`, appelé par projet_expanded) : 104 entités de CA (chevaux des
  duchés bretons, loups, sangliers chez les orques, gyrocoptères au-dessus des Karaks, aigles et pégases des Grises,
  vouivres, corbeaux et chauves-souris des Voûtes, mouches et libellules des marais, feuilles, brume de mer du Gué de
  Mistnar, destriers elfes, sabretusks des ogres d'Osséine, 6 groupes de Montures de Slaanesh, 12 nappes de brume
  pourpre), réglages de CA, ancres recalées sur le terrain final ; rien dans la zone gardée (la vie de la Saison y est),
  sauf les bêtes des ogres d'Osséine. Montures de Slaanesh : gabarit dérivé (CA les pose dans le compilé de la carte des
  Royaumes du Chaos). Relief : détecteur de creux étroits en plaine (fermeture, CREUX_U 0,2, hors Bois Rêveur), qui
  prend les fosses en hex (94, 821) et (95, 820) restées après les comblements.
  Reconstruction faite : 104 entités de vie posées (carte : apercus\vie-expanded.png) ; fosses (94, 821) et (95, 820)
  refermées (relief 1,03 et 1,26, au niveau des terres voisines), 12 659 px de creux étroits. Reste vu : sillons d'un
  pixel (4 à 7 cm) sur l'ancien contour des fosses, dus au fondu : fermeture désormais appliquée pleine sur l'amas élargi
  (elle ne fait que combler), essai local sans sillon ; prise à la prochaine reconstruction. Fork de CAIME : verbes
  export-tilemap et generate-region-borders commités en local (accord de Charles), 0f06478 sur la branche
  cli-tilemap-region-borders, rien poussé.
- **4.10.2026, vers 23 h 20** — Relecture croisée de la Construction (H1) : `generate-region-borders` ajouté aux deux
  chaînes (`chaine_grille_expanded.py` sur le bac à sable, `chaine_kit_expanded.ps1` sur la carte du kit), après toute
  écriture des régions, avant validate et process (process déjà borné à 5 min) ; la chaîne en attente (préavis 23:46:19)
  prend cette version. Recette CAIME de la REPRISE marquée remplacée par `CLAUDE.md` § 5 ; copies dans
  `05-journal\historique-documents\expanded-*-20261004-2318-avant-H1.md` (les copies d'avant les retouches du soir
  n'avaient pas été gardées). Contrôle vie / décors (`scratchpad\vie_contre_decors.py`) : 10 entités à moins de 1 u d'un
  maillage d'un autre calque, dont une Monture de Slaanesh à 0,89 u d'une pierre-dragon et des chevaux à 0,93 u d'un
  maillage de rivière. Règle ajoutée à `vie_expanded` : dégagement de 1 u autour du pivot de tout maillage des autres
  calques (ancre : hex + 0,4 u). Calque reposé dans le bac à sable : 103 entités (un sanglier compagnon écarté), 0 à
  moins de 1 u.
- **4.10.2026, vers 23 h 25** — Mesure de densité (`scratchpad\densite_objets.py`), maillages des calques par hex de
  terre : WH1 gardé 0,470 ; Atlas 0,006 (970 objets des abords de villes seulement) ; Bois Rêveur 0,041 ; Voûtes 0. Hors
  des forêts de BOB, l'extension était nue. Nouveau `outils\nature_expanded.py` (calque `nature_expanded`, appelé par
  `projet_expanded` avant la vie) : cellules de 6 u sur la terre de l'Atlas, chacune reçoit par translation les objets
  NATURELS d'une cellule de WH1 au même mélange de sols CAIME et de pente voisine (tirage parmi les 8 meilleures).
  Familles gardées : roches, buissons, herbes, roseaux, menhirs et pierres dressées bretonniens, décalques de racines,
  mousse, feuilles, marais. Exclues après relevé : décors de région (fissures peaux-vertes, crânes, lave, Chaos, tombes et
  toiles de Mousillon, pointes), pierres de voie et pierres levées elfes, dallage elfe, glace de Winterheart, champignons
  peaux-vertes, herbes des hommes-bêtes, et tous les MAILLAGES elfes `wef_` (flore d'Athel Loren). Résultat : 10 350
  maillages + 1 556 décalques (0,062 par hex ; WH1 en objets naturels : 0,082). `arbres_expanded.degager_decors` lit aussi
  ce calque (arbres sous les objets hauts). Vie reposée après : 101 entités. Aperçu : `apercus\nature-expanded.png`. Posé
  dans le bac à sable pour la chaîne du kit de 23 h 46 ; à juger en jeu.
- **4.10.2026, vers 23 h 30** — Charles : « replace à la main pour les créatures, fais en sorte que ce soit bien ».
  `vie_expanded._placer_groupe` : une paire de CA ne perd plus de compagnon ; le groupe tourne (12 orientations) puis
  glisse vers les cases voisines jusqu'à ce que tous tiennent. 107 entités : destriers elfes 2, chevaux 12, loups 10,
  sangliers 4 ; les 7 ancres sans case (2 corbeaux, 4 feuilles, 1 sanglier) sont dans la zone gardée, où vit déjà la
  faune de la Saison (voulu). Charles : « si ça rend bien, de belles montagnes, ajoute les objets naturels de WH1 sur les
  Voûtes » (la session des Voûtes n'a pas d'habillage en objets prévu) : `nature_expanded.VOUTES` ; menhirs bretonniens
  écartés des Voûtes (79). Bug corrigé au passage : le calque déjà posé s'évitait lui-même (1 688 écartés à tort ;
  `vie_expanded._encombrement(…, sauf=…)`). Résultat : 11 926 maillages + 1 958 décalques (Voûtes : roches et buissons
  de montagne, aiguilles, cairns). Question de Charles, « comment sont faites les montagnes dans WH3 » : objets
  `generic_props/mountains/<culture>/` posés sur le relief, avec height patch (GUIDE § 15 n° 96) ; recherche lancée sur
  l'habillage des Voûtes de CA dans les Empires Immortels (`05-journal\2026-10-04-montagnes-ca\`), pour un habillage
  « à la CA » de nos Voûtes plus tard.
- **4.10.2026, 23 h 30** — La session des Voûtes a réécrit `reves_grilles.npz` à 23 h 27 (île lissée, décision de
  Charles : 31 410 cases de terre, règle n° 97 à 0 défaut ; copie d'avant dans
  `05-journal\2026-10-04-fleuves-navigables-atlas\avant-villes-20261004\`, 31 272 cases). La chaîne du kit attendait
  son préavis, et `textures_reves` relit ce fichier : épinglée sur la copie d'avant (`SAISON_REVES_NPZ`, lu par
  `projet_expanded.REVES`), celle avec laquelle le projet a été construit. La nouvelle île entre à la prochaine
  reconstruction complète (chaîne de la grille, projet, eau, kit), après la validation du démarrage par Charles.
- **4.10.2026, 23 h 48 – 00 h 05** — Chaîne du kit de 23 h 46 ARRÊTÉE au contrôle du guide BOB : 12/12, 0 quadtree, mais
  107 « Failed to find tile » (75 attendus) ; les 32 nouveaux sont des TileSet_roads, sur les routes de l'Atlas
  (`scratchpad\diff_trous.py`, `routes_contact.py`). Cause : des nœuds que WH1 n'emploie jamais, sans tuile de CA :
  21 carrefours voisins (Saison : 0), virages de 60° et 3 branches collées (formes canoniques 3, 7, 23 ; Saison :
  seulement 1, 5, 9, 11, 13, 21), routes côte à côte sans lien (les 31 contacts de la Saison sont TOUS des fourches) ;
  25 trous sur 26 à 1 hex d'un tel nœud. Charles : « dans l'Atlas les routes rendent bien » ; oui, c'est la traduction en
  hex qui fautait. `routes_expanded` : formes de CA seulement et jamais deux carrefours voisins dans la recherche de
  chemin (`ok_noeud`), longer une route coûte 6 (au lieu de 1,5), puis zigzags et virages de 60° coupés
  (`couper_zigzags`) et bouts morts qui frôlent une autre route élagués (`elaguer_bouts`) ; contrôle `defauts_reseau`
  au bilan. Essai refusé en route : interdire tout contact (59 morceaux sans chemin, 1 200 cases perdues). Grille d'avant
  les routes remise (`terrain-backups\20261004-203807-…-avant-routes`, l'état aux trous rangé en
  `20261004-2352-map.hex-expanded-routes-trous-bob`), routes reposées : 3 256 cases neuves, 0 forme hors CA, 0
  carrefour voisin, 2 contacts côte à côte, tous deux dans l'emprise d'une ville ; validate --roads OK ; validate --all
  3 / 1. Projet, eau et chaîne du kit relancés (préavis 00:01:23 ; `SAISON_REVES_NPZ` = île d'avant le lissage, celle de
  la grille).
- **5.10.2026, vers 00 h 05** — Charles : « vérifie que les routes sont bien cohérentes… pas de chemin qui poursuit au sud
  des Voûtes vers le Bois Rêveur ? » puis « c'est normal : une dimension démoniaque, accessible seulement par les
  portails d'Athel Loren ; reliée par une rivière invisible » (mémoire `bois-reveur-portails-sans-route`) : pas de route
  vers la chaussée du voile (colonne 397, rangées 224-249). Contrôle de cohérence du réseau (`scratchpad\
  routes_coherence2.py`, `routes_liaisons.py`, `routes_image_morceaux.py`) : 12 morceaux (Saison seule : 2), 48 bouts
  morts hors des villes, 5 villes de l'Atlas sans route ((117, 581), (97, 632), (77, 657), (209, 724), (143, 811)).
  Cause principale : dans les vallées étroites des Voûtes, le tracé de l'Atlas coupe un éperon et la route était posée
  en morceaux jamais rejoints. Ajouté à `routes_expanded` (à blanc seulement, pas dans la chaîne en cours) :
  `souder_bouts` (bout mort relié au morceau voisin par la vallée, 40 hex au plus, formes de CA), `retirer_doublons`,
  option `--base` (lire une grille sans routes). À blanc : 12 -> 8 morceaux, 0 forme hors CA, 0 carrefour voisin.
  Restent : le réseau ouest de l'Atlas (1 977 cases) relié au petit morceau de WH1 (147 cases, déjà séparé dans la
  Saison) et pas au grand : 19 cases de route DANS la zone gardée de WH1 le relieraient (décision de Charles : WH1 à
  100 %) ; deux morceaux de l'ouest (75 et 38 cases) idem (50 et 34 cases dans WH1) ; deux nœuds de vallée des Voûtes
  (46 et 12 cases, à 3 hex) que seule une fourche collée relierait ; un morceau à l'est (118 cases, (536, 613)) sans
  chemin trouvé. À reprendre à la prochaine reconstruction (avec l'île lissée).
- **5.10.2026, 00 h 05 – 00 h 10** — Chaîne relancée FINIE : BOB 12/12, 0 quadtree, 75 trous (tous de côte, connus ; 0
  de route, contre 32) ; après-BOB, royaume, arbres, contrôle des anomalies faits. `arbres_expanded._boite_ca` lit
  aussi les modèles de WH1 (`saison-des-revelations\fichiers-wh1`) : 11 926 objets de la nature étaient « sans boîte »
  et ne dégageaient pas leurs arbres ; arbres refaits (769 objets, 5 955 arbres retirés de dessous). « Kit libre » à la
  Construction (startpos et pack). Charles : « oui, relie l'ouest au grand réseau » (exception à « WH1 à 100 % »,
  Expanded seulement) : `routes_expanded.relier_morceaux` (case de WH1 coûte 3, formes de CA, sans longer une autre
  route ; au plus GARDE_MAX_LIAISON = 60 cases de WH1 par liaison). Ouest relié : 33 + 51 + 34 = 118 cases de route
  dans la zone de WH1, plus 1 + 1 dans les Voûtes ; réseau : 3 morceaux (le grand, le Bois Rêveur voulu à part, et un
  morceau de l'est de 118 cases, autour de (536, 613), qu'un col étroit au bord de la carte de WH1 relierait au prix de
  86 cases dans WH1 : question à Charles). Posé dans la grille du bac à sable (sauvegarde
  `terrain-backups\20261005-000643-…-avant-routes`) ; validate --roads OK ; entre au jeu à la prochaine reconstruction.
- **5.10.2026, 00 h 10 – 00 h 40** — Charles : « règle les 75 trous de côte, puis attaque la reconstruction ».
  Diagnostic (`scratchpad\trous_cote_planche.py`, `trous_cote_classes.py`, `lacs_grille.py`) :
  - 23 trous autour de 14 étendues d'eau fermées de 4 à 24 hex, dont les 8 lacs de WH1, que la grille de la Saison a
    aussi ; la carte des tuiles de WH1 les peint en TERRE ORDINAIRE (l'eau vient du maillage et du creux du relief),
    l'export CAIME les entourait de falaises sans tuile de CA. `tuiles_expanded.lacs_hex`/`lacs_eau` : lacs fermés
    (au plus 30 hex, hors bord de carte) et leur anneau de côte en terre ordinaire ; `projet_expanded` les garde en eau
    pour le relief (`mer_t |= lacs_eau`). 184 hex, 1 636 px.
  - Reconstruction complète (île lissée, grille, ports, routes reliées, projet, eau, kit ; préavis 00:23:14) :
    BOB 12/12, 0 quadtree, 59 trous (75 avant ; 39 disparus, 23 nouveaux), tous de côte, 0 de route. Les nouveaux :
    autour des PORTS de l'ouest (plage d'une case du modèle de port de CA au milieu des falaises : Tor Soleil, Lyonesse,
    Merton, Tor Martel, Erguy, l'Anguille, Hendaye, Tancred) et 4 au bord sud de la carte (rangée 0, l'île lissée la
    touche). Recherche des formes de côte de CA lancée (`05-journal\2026-10-05-tuiles-cote\`). « Kit libre » à la
    Construction (00 h 28).
  - Marches de relief (> 0,6 u d'un pixel au voisin) : Bois Rêveur 13 862 px (falaises de WH1 reflétées, fidèles),
    Voûtes 454 (falaise de la déchirure, voulue), Atlas 690 en lignes droites et escaliers d'hex, TOUTES dans la
    bordure de WH1 remplacée, aux mêmes endroits que dans le relief de WH1 (cachées dans la Saison par ses maillages de
    montagne, retirés de la bordure). `projet_expanded` : détail de WH1 pris sur son relief aux marches fondues, et
    passe de sûreté « marches adoucies » (> MARCHE_U 0,5, hors WH1, Bois Rêveur, côtes). Essai sur `relief_alpin`
    (vallées et passage fondus) : sans effet sur ces marches, annulé.
- **5.10.2026, 00 h 40 – 00 h 55** — Charles en jeu : « c'est déjà bien mieux que je pensais… jouable » ; à reprendre :
  arbres qui s'arrêtent net aux montagnes autour d'Athel Loren (continuité Saison / Expanded), montagnes flottantes, côtes
  logiques (falaises et plages là où il faut), fleuves navigables (feu vert implicite : il les attend).
  - FLOTTANTS (`scratchpad\flottants_emprise.py`, sur le projet du kit) : grands objets au dessous en l'air de plus de
    0,4 u : royaume 327 / 1 043, nature 397 / 2 814 (objets de WH1 penchés pour la pente de leur place d'origine, objets de
    CA couchés). Nouveau `outils\pose_au_sol.py` : `ecarts` (face basse de l'axe le plus vertical de la boîte tournée),
    `ajuster` (abaissé jusqu'au sol à 0,2 u près, refusé s'il devait s'enterrer de plus de la moitié), `orienter`
    (lacet gardé ; objet plat couché sur NOTRE pente, objet haut debout ; décomposition vérifiée), `normale`. Branché
    dans `nature_expanded` (dès 0,3 u) et `royaume_slaanesh` (matrice telle qu'écrite ; effets, lumières et sons suivent
    leur objet). Résultat : nature 0, royaume 0, abords des villes 5.
  - ARBRES : la fenêtre « montagne » de WH1 est presque nue (montagnes en maillages sur sol plat) ; `projet_expanded` :
    forêt claire de WH1 sur la montagne de l'extension, éclaircie par plaques avec l'altitude et la pente
    (FORET_MONTAGNE 0,55, rien au-dessus de 9 u ni sur les parois) ; LISIÈRE : les arbres de WH1 prolongés sur LISIERE_HEX
    6 hex hors de la zone gardée, de plus en plus clairsemés (`habillage_expanded.habiller(…, forcer=)`).
  - Reconstruction complète lancée (préavis 00:53:32).
- **5.10.2026, vers 01 h** — FLEUVES NAVIGABLES (v3 validée : Brienne B, Grismerie G2 + branche de l'Ois, Sannez ;
  Expanded seulement), préparation :
  - `spec_expanded.lot_fleuves` : les 7 régions d'eau dans l'ordre (saison_sea_brienne_2, _1, grismerie_3, _2, _1, _4,
    sannez_1 ; rangs 146 à 152 de la fiche), couleur propre chacune, is_sea, in_encyclopedia 0 ; fiche d'avant gardée
    (`historique-documents\map_spec_expanded-20261005-avant-fleuves.json`).
  - `declarer_expanded --ajouts-seulement` : une redéclaration complète aurait REMPLACÉ la zone jouable (kit_expanded la
    met au monde entier) et la campagne (masque vidé par la Construction) ; à blanc : regions +7, campaign_map_regions +7,
    rien d'autre. À écrire après la chaîne en cours (kit_expanded écrit aussi dans raw_data\db), puis sync-names.
  - `routes_expanded` : cases de la couche Bridges et cases d'approche (berges voisines) permises aux routes.
  - Point d'entrée de branchement demandé à la session « Recherche or et rivières navigables » (auteur de l'outil v3) :
    `banc-fleuve\outils\creuser\integrer_fleuves_expanded.py` ; ordre convenu : chaine_grille -> ports_expanded -> son
    script -> routes_expanded -> frontières -> projet -> kit.
  - `projet_expanded` : berges des rivières de l'Atlas plus basses que l'eau voisine relevées au niveau de l'eau (contrôle
    n° 6, 31 px).
- **5.10.2026, 00 h 55 – 01 h 10** — Charles : « corriger les trois erreurs de chaque validation CAIME ». Validateur lu
  (`SprawlValidator.cs`) : une emprise ne touche qu'UNE composante de danger (infranchissable, rivière, côte ; composantes
  de toute la carte) et aucune autre à 2 hex. Les villes de col de WH1 (Chêne des Âges, Poste de la Pierre Noire, Défilé
  de la Hache) touchent deux massifs que rien ne relie. Nouveau `outils\cols_sprawl.py` (dans `chaine_grille_expanded`,
  avant les frontières) : liaison la plus courte (≤ 3 cases) hors de l'emprise et de son anneau, par des cases sans route,
  rivière ni ville, refusée si la terre franchissable perd plus que ces cases. 5 cases de recoin fermées ; validate --all :
  0 Error, 1 Warning (terre sauvage en 11 morceaux). Sur la carte de CA, cinq villes de col ont la même Error (guide CAIME).
  - CÔTES (`05-journal\2026-10-05-tuiles-cote\RAPPORT.md`, agent) : formes des tuiles lues dans `_tile_database` ; sur 36
    zones de trous : 15 de la composition (côte rendue en terre ordinaire qui coupe le ruban de falaise), 12 des plages
    d'UNE case (10 sur 10 en trou), 4 au bord de la carte (rangée 0), 3 d'un isthme d'un hex (108, 678), 2 décrochements.
    Prédicteurs `modele_pavage.py`, `modele_local.py`. Doc de CAIME : Beaches = « coastal landing hexes where amphibious
    armies can come ashore » ; l'extension n'avait de plage qu'aux ports. Nouveau `outils\plages_expanded.py` : plages sur
    la côte basse de l'Atlas (relief ≤ BAS_U 0,8 sur 3 hex vers l'intérieur ; 1,6 en faisait 85 %), hors montagne, route,
    rivière ; suites d'au moins 3 cases ; plage de port prolongée à 3 cases. Posé dans le bac à sable : 109 -> 471 cases de
    plage, validate --beaches OK. Prédicteurs : couverture 38 -> 31 px, liens 35 -> 39 boîtes : à juger par BOB.
- **5.10.2026, vers 01 h 15** — Charles, capture en jeu (vers Montfort / Défilé de la Hache) : « des montagnes qui
  flottent… deux styles de montagne qui se chevauchent ». Ce sont les MAILLAGES de montagne de WH1 (`montagnes_wh1`, drapés
  d'avance sur le relief de WH1, une pose = un modèle) : dans la marge de décor lissée de la zone gardée et là où leur
  rectangle dépasse la zone, le relief d'Expanded est plus bas (197 000 px à plus de 1 u). Ils échappaient au contrôle des
  flottants (modèles hors des packs de CA, sans boîte). `projet_expanded.montagnes_gardees` : rectangles des 999 poses
  gardées (pivot dans la zone gardée, comme `trie` ; z des calques = z × 2/√3, premier essai faux : 217 pivots sur 818),
  élargis d'un hex ; relief de WH1 EXACT dessous, fondu sur ~2 hex, dans le cadre de WH1 seulement ; exclus des passes de
  fosses, creux, marches, berges et crête ; aucun arbre de l'extension dessous. Reconstruction lancée (préavis 01:17:15)
  avec aussi les plages et les villes de col. Résultat (01 h 24) : 999 poses ; validate --all du kit 0 Error / 1 Warning ;
  BOB 12/12, 0 quadtree, 52 trous de côte (59 avant ; les plages en ôtent un peu) ; controle_anomalies : 0 bord d'eau de
  rivière en l'air (31 avant), marches > 0,6 u 17 485 (relief de WH1 rendu sous ses montagnes, couvert par les maillages).
  Charles, encore en jeu (pack de 01 h 02, sans ce correctif) : « des montagnes flottantes un peu partout… deux, tout au
  nord, qui n'ont rien à faire ici… le Massif Orcal rend moins bien que dans la Saison ». (a) Les deux du nord : maillages
  de terrain de WH1 recopiés par `decors_expanded.copier` (abords des villes neuves) : 31 (montagnes en (232, 830) et
  (286, 804), 26 pans de `cliff_inland_custom_passable`, 3 ancres) ; ne se recopient plus. (b) Massif Orcal : ses 4 régions
  sont dans la zone gardée ; relief, arbres, neige IDENTIQUES à la Saison ; objets en l'air en même nombre que dans la
  Saison (poses de WH1). Cause probable : matériau 68 des montagnes de WH1 (kit, donc Expanded) contre 49 dans le pack
  candidat de la Saison que joue Charles (A5, domaine de la Construction, prévenue). (c) L'éclairage n'en est pas la
  cause : la Saison n'a que le global et Winterheart.
  « Kit libre » à la Construction. Régions d'eau des fleuves NON déclarées : seulement au moment de creuser la grille (un
  startpos ne doit pas partir avec des régions déclarées mais absentes de la carte).
- **5.10.2026, 01 h 40 – 01 h 55** — FLEUVES, branchement. Point d'entrée de la session des rivières :
  `banc-fleuve\outils\creuser\integrer_fleuves_expanded.py` (+ base_expanded, chaine_v3, analyse_v3, routes_v3,
  masques_caime, README ; essais sur l'archive de référence et sur une copie de notre grille : 1 579 hex d'eau, 11 ports,
  9 ponts, 7 villes déplacées, 3 207 hex réaffectés, 0 Error / 0 Warning nouvelle). Grille du bac à sable ramenée à ses
  routes d'avant routes_expanded (couche Roads de `terrain-backups\20261005-001406-…-avant-routes` ; état précédent rangé
  en `20261005-0140-…-avant-retrait-routes-atlas`) : le script passe AVANT les routes de l'Atlas. Préavis 01:47:19 ;
  `declarer_expanded --ajouts-seulement --apply` : regions +7, campaign_map_regions +7 (sauvegarde
  `db-backups\20261005-014721-expanded`) ; sync-names (grille d'avant : `20261005-0148-…-avant-sync-fleuves`). CAIME
  CLASSE les mers par ordre alphabétique : indices 135, 136, 141 à 144, 148 (et non 146 à 152 ; aucune case n'a changé
  de région par son nom, `scratchpad\verif_sync.py`). Le dry-run s'arrête sur son contrôle d'indices : demandé à la
  session des rivières de vérifier par les clés. NE PAS reconstruire startpos ni pack avant « terrain prêt » (régions
  déclarées, carte du kit encore sans fleuves).
  - 02 h 00 – 02 h 10 : contrôle corrigé par la session des rivières (clés, indices quelconques) ; dry-run sur la vraie
    grille IDENTIQUE à la v3 (1 579 hex d'eau, 11 ports [mer, mer, plage], 9 ponts, 7 villes déplacées — Férignac, Muret,
    Parravon, Montfort, Yremy, Couronne (182, 789), L'Anguille (146, 807) — 3 207 hex réaffectés ; Error 0 -> 0, Warning
    1 -> 1 ; connexité inchangée ; 0 route restée coupée) ; --apply (sauvegarde `db-backups\20261005-020306-map.hex-avant-
    fleuves`), validate 0 / 1. Puis `routes_expanded --apply` (91 cases de pont, 74 d'approche ; garde-fou des
    carrefours à 4 : seuls ceux que nous ajoutons arrêtent l'écriture, 1 dans la base aux raccords de pont), cols_sprawl
    (rien), frontières 33 398 -> 35 128, validate 0 / 1. 8 nœuds de route hors des formes de CA dans les raccords de pont
    (153, 494), (211, 499), (189, 501), (243, 675), (249-251, 680-682) : la session des rivières corrige routes_v3.
    `outils\donnees_fleuves.py --apply` : campaign_storms_excluded_regions +7, battle_catchment_override_battle_mappings +2
    (Gatekeeper naval pour saison_expanded_map) ; sauvegarde `db-backups\20261005-020621-fleuves-donnees`. Chaîne du
    terrain lancée.
  - Côtes, essais à blanc (`scratchpad\essai_rubans.py`, `essai_ck.py`, prédicteurs de l'agent) : avec les fleuves, la
    côte passe de 10 658 à 14 540 px et le prédicteur de 35 à 102 boîtes sans pavage. Rubans de falaise coupés rendus
    entiers à la terre : refusé (7 rubans, 4 478 px, presque la moitié des falaises). RACCORD DIRECT PLAGE-FALAISE de CA
    (cliff_gen_ends -> cliff_gen) : 102 -> 43 boîtes ; Charles (02 h 10) : « oui, comme CA ». Dans
    `tuiles_expanded.composer` ; écart au guide Terry (« export sans retouche ») signalé à la Construction pour
    ERREURS-ET-LECONS. Reste au prochain passage de grille : isthme d'un hex (108, 676-678, Lyonesse), bord de carte
    (rangée 0 de l'île du Bois Rêveur), décrochements (256, 1331), (146, 1564).
  - Charles : « attaque tout ça ». Nouveau `outils\retouches_cotes.py` : (1) langues de terre d'un hex de large rendues à
    la mer pas à pas depuis le bout (jamais WH1 gardé, ville, étendue, route, rivière, pont) ; (2) terre CÔTIÈRE sur le bord
    de la grille rendue à la mer (relevé figé avant changement : deux essais refusés, 804 cases par contagion). À blanc :
    15 cases (4 au bord sud du Bois Rêveur, celles des 4 trous ; 4 autres au bord ; 7 de langues dont l'isthme de
    Lyonesse). À appliquer au prochain passage (après la chaîne des fleuves en cours, qui a déjà le raccord plage-falaise
    de CA : 871 px). Décrochements : jugés au prochain BOB.
- **5.10.2026, vers 02 h** — PROCHAIN CHANTIER, l'ARDEN (Charles : « commence par l'Ardenne, une fois les fleuves en
  jeu ; très bien tes suggestions ») : relevé (`scratchpad\foret_arden.py`) : les régions de l'Artois (forêt d'Arden)
  ont 81 à 98 % de sol forestier et 0,69 à 0,87 arbre par hex (Athel Loren : 0,57 à 0,69). À faire, montré en image avant
  pose : ambiance plus sombre et brumeuse (cylindre d'éclairage, à la manière de CA, erreur 251) ; clairières naturelles ;
  décor des hommes-bêtes à la manière de WH1 : 138 pièces `generic_props/beastmen/` (perches, cages d'os, crânes, cornes,
  boucliers, tissus) dans les calques de WH1, dont 126 en VARIANTE D'OCCUPATION (culture_mask hommes-bêtes, Chaos, Norsca,
  démons : visibles quand ils tiennent la région) et 12 permanentes ; même système pour l'Arden (quelques signes
  permanents, le camp quand la Harde la tient). Ensuite : Châlons, Montagnes Grises, marais de Mousillon, côte de Lyonesse.
- **5.10.2026, vers 01 h 10** — À FAIRE APRÈS LES ESSAIS D'EXPANDED (session des Voûtes ; bilan de l'audit de lore validé
  par Charles le 5.10 : `05-journal\2026-10-04-factions-lore\BILAN.md`), tables de départ (`depart_atlas.py`) :
  (1) Morghur part de l'Antre de Morghur dans l'Arden, Atlas (94, 435) = grille (214, 765), franchissabilité à vérifier
  (la Saison garde (106, 132)) ; (2) Sigmarsheim sous la Lyonesse ; (3) Dragon Falls à la Gasconnie
  (`wh_main_brt_carcassonne`), plus aux Orques de fer ; (4) capitale d'Aislinn = Tor Martel (l'Atlas donne encore les Tor
  à Aislinn, nous à `saison_hef_tor_soleil` : à aligner) ; (5) siège de L'Anguille = Château de Grasgar (duc Taubert) ;
  (6) capitale de l'Aquitanie = la ville d'Aquitanie. Après la mesure du temps de tour : factions `saison_bst_chalons`
  (vers 78, 266), `saison_cst_bataille_des_marees` (armée errante), `saison_grn_crocs_noirs` ; diplomatie : Karak Norn en
  guerre contre Durthu et les Sœurs, Kemmler contre Karak Eksfilaz (au lieu de ses guerres de la Saison), factions de
  Slaanesh en guerre entre elles ; unités de DLC de CA permises à l'IA, jamais d'unité inventée. À vérifier : trou probable
  du col de la Dame Grise (bande du Teufeltal, Atlas x ≈ 367 à 382, sans région :
  `05-journal\2026-10-05-revue-suggestions-atlas\rapport-col-de-fer-teufeltal.md`).
  Suite (même bilan, décisions du 5.10) : l'ancienne place de Morghur (106, 132) reprise par « les morts de la
  Glanborielle » = invasions scriptées de factions `_qb` de CA (forts hantés vers le tour 10, Fort Solstice ou Brusse ;
  nécromancien des Chutes du Dragon vers le tour 18 ; liche Hardakh depuis sa crypte des Voûtes (182, −12), tours 25 à 40) :
  VÉRIFIER que leurs cases d'apparition sont franchissables (`05-journal\2026-10-04-factions-lore\ancienne-place-de-morghur.md`).
  Seigneurs légendaires de CA en IA à la tête des évènements (Wulfrik pour les raids norses, Hellebron pour les druchii,
  Mannfred derrière Mallobaude) : scripts par la session IA ; si leurs factions doivent exister dans le départ
  d'Expanded (même mortes ou cachées), c'est ici (`depart_atlas.py`).
  Encore (5.10) : (1) Lyonesse à la faction ducale de CA `wh_main_brt_lyonesse`, duc Adalhard (*Knights of the Grail*), à
  la place des Chevaliers de Repanse ; (2) Repanse (`wh2_dlc14_brt_chevaliers_de_lyonesse`) en armée de croisade sans
  ville sur la côte de Lyonesse, en paix et accès militaire avec Adalhard (comme les Sœurs avec Wydrioth) ; PAS une horde
  chez CA : comportement sans ville à éprouver, sinon un fief (Ora Lamae ou Merton) ; (3) la faction de Golgfag de CA
  remplace `saison_ogr_osseine` ; (4) Hellebron et Rakarth à deux endroits (raids scriptés par la session IA) ;
  (5) Kairos puis Ku'gath, l'Année de Malheur, invasion scriptée de milieu de partie (Montfort et Quenelles, puis
  Mousillon) ; pas d'Arkhan ni de Snikch ; (6) à venir : grandes villes du lore aujourd'hui simples découpes -> vraies
  villes, voire capitales de province (ville d'Aquitanie) ; audit `05-journal\2026-10-04-factions-lore\audit-provinces.md`.
- **5.10.2026, 02 h 20** — PORTS DES FLEUVES DANS LE DÉPART : 24 régions ont un emplacement de port dans la grille, 14
  seulement avaient un gabarit de port dans `saison_expanded`. `outils\ports_fleuves_depart.py --apply` ajoute aux 10
  autres (Couronne, Muret, Férignac, Gisoreux, Montfort, Yremy, Parravon, Brusse, Laguiller, Quenelles) la ligne de
  Brionne : « port » / `wh_main_port`, principal et secondaire inchangés (sauvegarde
  `05-journal\db-backups\20261005-022051-ports-fleuves\`, nouvelle passe à 0 ligne ; contrôle : 24 / 24). Chaîne du kit
  avec les fleuves finie à 02 h 17 (BOB : 52 trous, dont 8 de routes aux ponts du lot, en cours chez la session des
  fleuves ; anomalies : 0). Terrain annoncé prêt à la Construction (startpos, pack, essai d'Orion).
- **5.10.2026, 02 h 25** — ARDEN, relevé (lecture seule, kit gelé par l'essai de la Construction) : les calques de WH1
  ont 24 609 entités d'OCCUPATION « Chaos / hommes-bêtes / Norsca / démons » (fissures, lave, accessoires du Chaos,
  herbes bst_) et 7 550 « vampires » ; parmi elles, un CAMP DES HOMMES-BÊTES par région (13 pièces environ : 2 bst_pole,
  boucliers, crânes, cornes, tissus sanglants, cage d'os ; 27 camps mesurés) : à 13 hex de la ville en médiane (9 à 20),
  sur la prairie (24 / 27), une route à 3 hex ou moins (22 / 27) ; quelques camps PERMANENTS (Tal Rond, Threllock, et
  la pierre de harde des Salles d'Anaereth). Les 4 régions neuves de l'Artois n'en ont aucun (1 seule pièce bst_).
  Planche `apercus\arden-camps-proposes-20261005.png` (`scratchpad\planche_arden.py`) : un camp par région selon la règle
  de WH1 (Château d'Artois (176, 758), Larret (142, 718), Sigmarsheim (163, 702), Uesin (190, 747)). Antre de Morghur
  (214, 765) : collines franchissables, région `saison_couronne_contreforts` (pas l'Artois). À montrer à Charles avant
  toute pose ; même manque probable pour toutes les régions neuves de l'Atlas (décors d'occupation à généraliser).
- **5.10.2026, 02 h 30** — FLEUVES EN JEU (Construction, essai `05-journal\2026-10-04-essais-auto-expanded\20261005-022333-orion\`) :
  tables de départ 1 307 lignes, 0 cellule à corriger ; startpos en 26 s ; Orion charge, tour 1 à 34,6 s, 0 erreur, aucun
  crash_report ; sortie propre (Charles). NON vérifié par le pilote : flottes sur les 7 régions d'eau, ports fluviaux
  constructibles : à voir en jeu par Charles. Pas de reconstruction pendant son essai ; prochaine passe de grille
  (retouches_cotes, ponts corrigés par la session des rivières) ensuite.
- **5.10.2026, 02 h 35 – 02 h 40** — FLEUVES : TROU SANS EAU EN JEU (Charles : « la rivière flotte sur un énorme trou
  béant… il n'y a pas d'eau sur la voie navigable »). Causes : (1) les COPIES des couches de la grille lues par le terrain
  (`couches-expanded\*.hex_layer`, `villes-sortie\`) dataient de 00 h 13, avant le lot des fleuves (02 h 05) : régions de
  mer aux anciens indices (148 730 cases), pas les 1 579 hex d'eau ; donc ni plan d'eau ni masque d'eau sur les chenaux ;
  (2) l'étape « terrain » de la méthode de CA (SYNTHESE des fleuves § 1.4) n'avait été faite par personne : sur le
  chenal, terre de WH1 à 0,8 u (médiane) et fond à −2,1 u, d'où le trou sous les tuiles de mer ; rubans de WH1 de
  l'ancienne Brienne à leur hauteur. Correctifs : `outils\couches_a_jour.py` (copies refaites depuis le map.hex, en tête
  de projet_expanded ; `couches-expanded\layer_impassable` n'est PAS une copie, épargnée ; anciennes copies rangées
  dans `couches-expanded\archives\20261005-023126\`) ; `outils\chenaux_fleuves.py` (surface 0,02, fond −0,35 en
  plateau, fondu aux embouchures sur 4 hex, berges abaissées vers 0,12 u sur 3 hex, jamais sous les montagnes de WH1
  gardées, fond −1,0 sous la terre sur 3 hex ; delta du relief dans `relief\chenaux_delta.npz`) ; projet_expanded :
  objets de WH1 sur le chenal retirés, objets des berges recalés (y + delta) ; `rivieres_maillages_expanded.ecrire()` :
  rubans de WH1 rognés sur le chenal (36 rubans, 36 836 triangles à blanc) et sommets recalés, rubans vidés retirés avec
  leur objet. Les rubans de l'Atlas s'arrêtent seuls (relief du chenal à 0,02 ≤ NIVEAU_MER). `retouches_cotes --apply`
  (15 cases ; sauvegarde `terrain-backups\20261005-023714-…`), frontières, validate 0 Error / 1 Warning.
  Provinces validées par Charles (session des Voûtes, `05-journal\2026-10-04-factions-lore\audit-provinces.md` § 5),
  À APPLIQUER APRÈS LES ESSAIS : P1 ville d'Aquitanie capitale à murs de `saison_province_pre_de_ceren` (Pré de Ceren
  mineur ; nom à confirmer, « Aquitanie du sud » proposé), `wh_dlc05_aquitaine` retrouve Château d'Épée (capitale),
  Derrevin Libre, Gien ; P2 Grung Zint au Défilé de la Hache ; P3 Oisillon seul, province neuve « Gisoreux du nord »,
  capitale ; P4 Lyonesse coupée : nord « Duché de Lyonesse » (Lyonesse, Barfleur), sud neuve « Lacs de Lyonesse »
  (Merton, Ora Lamae, Sigmarsheim qui quitte l'Artois ; capitale Sigmarsheim, ou Merton si le Duc est bouché au nord) ;
  Repanse en armée sans ville (repli : le sud) ; P5 les Contreforts aux Marches de la Couronne (province et faction) ;
  P6 province neuve « Karak Eksfilaz » (capitale) avec les Tombeaux de Stonewrath, les Voûtes de l'ouest gardent Krinal
  (capitale) et Karag-Dar ; P7 province neuve « Ubersreik » (capitale à murs), le Reikland garde Helmgart ; Tallerhof y
  entre si le trou du Teufeltal est comblé. D'abord : où se règle le rang majeur / mineur (guide CAIME, fichiers de CA).
- **5.10.2026, 02 h 45 – 03 h** — REJEU DES FLEUVES avec les routes aux ponts corrigées (session des rivières :
  `routes_ca.py`, 0 nœud hors des formes de CA) depuis la copie de `db-backups\20261005-020306-…-avant-fleuves` (état
  précédent : `terrain-backups\…-avant-rejeu-fleuves`) ; puis routes_expanded, cols_sprawl (0), retouches_cotes (15),
  frontières, validate 0 Error / 1 Warning. CAMPS DES HOMMES-BÊTES (Charles : « vas-y… généralise à tout l'Atlas ») :
  `outils\camps_expanded.py` (calque `camps_expanded`, appelé par projet_expanded après la vie ; arbres dégagés autour par
  arbres_expanded) : les 24 camps d'occupation entiers de WH1 (≥ 9 pièces, avec perches) recopiés tels quels, tournés,
  posés selon la règle de WH1 (prairie d'abord, 9-20 hex de la ville, route à 3 hex) : 36 camps, 483 pièces ; 8 régions
  sans camp (4 sans case à 9-20 hex près d'une route, 4 sans place entière). Vue : `apercus\camps-hommes-betes-expanded-
  20261005.png`. projet_expanded + eau_materiau refaits (chenal, rubans rognés : 31 rognés, 17 vidés), chaîne du kit
  lancée après le préavis de 02:52:47.
- **5.10.2026, 03 h 05** — ARDEN, AMBIANCE (proposition, rien d'écrit dans le pack) : CA n'a pas de zone propre à
  l'Arden (Empires Immortels : Bretonnie sous `combi/bretonnia.environment`, Athel Loren sous `combi/woodelf.environment`,
  rayons 30 / 42). Proposé : `outils\eclairage_arden.py`, deux cylindres qui citent `woodelf.environment` TEL QUEL sur
  les régions de l'Artois (90 % des hex dans un rayon intérieur, transition 12 u comme CA) ; brouillard 2,0 contre 1,3,
  sommet 6 u contre 4,5, soleil 30 000 contre 60 000, LUT `campaign_ie_woodelves`. Aperçu schématique
  `apercus\eclairage-arden.png`. À brancher par la Construction dans build_pack comme eclairage_reves (interrupteur
  proposé SAISON_ECLAIRAGE_ARDEN=1, éteint par défaut), seulement après accord de Charles, puis essai en jeu.
- **5.10.2026, 03 h 09** — camps_expanded : règle élargie si celle de WH1 ne trouve pas de place (6 à 24 hex, route à
  5 hex, puis les trois camps modèles les plus petits) ; à blanc : 41 camps (37 par la règle de WH1, 4 élargie), 549
  pièces, 3 régions sans place. Pris au prochain passage de projet_expanded (le pack en essai a les 36 camps).
- **5.10.2026, 03 h 15 – 03 h 40** — CÔTES ET BERGES SANS ESCALIER (Charles, en jeu : « beaucoup d'effets escaliers sur les
  bords des rivières… les côtes, des trucs en carré… les falaises au bon endroit, les plages au bon endroit » ; puis
  « sers-toi vraiment de la documentation de CAIME, des guides »). Relu : documentation officielle de CAIME (§ 4.2 Baseline
  Tilemap : couches Roads, Rivers, Cliffs, Beaches), guide CAIME de l'Atlas (falaise = tout hex de terre côtier qui n'est
  pas une plage : le choix falaise / plage se fait dans Beaches), guide Terry (« sans retouche », « le fond visuel de la
  côte se règle dans Terry », « Une côte lisse en jeu »), guide BOB. Aucun guide ne dit le relief sous une tuile de
  falaise : mesuré chez CA (Empires Immortels, `scratchpad\profil_cote_ca.py`, `profil_cote_comparer.py`) : FALAISE =
  plateau de terre 0,74 u (p10 0,28, p90 1,23), fond voisin −0,40 ; PLAGE = terre sous l'eau au trait (−0,16, puis −0,08,
  +0,05, +0,12 à 1 u), fond −0,19 ; la Saison (WH1, côte generic sans tuile de côte) : terre −0,08 au trait, continu.
  Expanded (`scratchpad\marches_cote.py`) : terre 0,13 au trait partout, fond −0,63 (marche médiane 0,94 u). Nouveau
  `outils\cotes_relief.py` (appelé par projet_expanded avant l'écriture du relief) : profil de CA selon la tuile, fondu
  sur 1 u derrière, mer voisine sur 1 u ; côte sans tuile de côte : pente douce du guide Terry ; jamais la terre sous les
  montagnes de WH1 gardées, rien dans le Bois Rêveur ; delta ajouté à `relief\chenaux_delta.npz` (objets de WH1 et rubans
  recalés en hausse ET en baisse). À blanc : falaises 0,6 (plancher ; CA 0,74), plages −0,16 / −0,11 / −0,05 / +0,04,
  fond plage −0,28, fond falaise −0,35 ; aperçus `scratchpad\cotes_*.png` (côte de plage lisse ; falaise : marche franche
  comme chez CA, la paroi est celle de la tuile). Correction du guide Terry signalée à la Construction (pour la session
  Extension). Préavis kit 03:37:45.
- **5.10.2026, 04 h** — À FAIRE (lot de données après les essais ; demandes de Charles relayées par la session des
  Voûtes) : (1) AISLINN part EN MER près de Tor Martel : Atlas (−26, 290) = grille (94, 620), mer franche, ~14 hex au
  sud de l'île de Tor Martel (aujourd'hui (95, 631), au bord de la côte : vérifier mer franche) ; (2) nouvelle bannière
  de `saison_hef_tor_soleil` (tour blanche, soleil, vagues de la Patrouille) :
  `05-journal\2026-09-23-extension-carte\travail\images_source\drapeaux_projet\saison_hef_tor_soleil_256.png` (et _64)
  -> `drapeaux-jeu\ui\flags\saison_hef_tor_soleil\` (mon_24, mon_64, mon_256, mon_banner.dds, mon_icon, mon_rotated) ;
  (3) JEANNE DE LYONESSE (`wh2_dlc14_brt_chevaliers_de_lyonesse`) tient toute la province du sud « Lacs de Lyonesse » :
  Sigmarsheim capitale (clé artois_venin_rouge, à renommer saison_), Merton, Ora Lamae (lyonesse_portsall) ; le nord
  (Lyonesse, Thurin) au duc Adalhard (`wh_main_brt_lyonesse`). Remplace « Repanse en armée sans ville » (P4).
- **5.10.2026, 03 h 41 – 04 h 01** — Côtes, deux passages. Premier (03 h 41) : îlots de terre dans la mer 15 -> 155 (bouts
  du tracé lissé de la mer au-dessus de l'eau sur des tuiles de MER, isolés par les plages passées sous l'eau), bords d'eau
  de rivière en l'air 0 -> 7 (berges des rivières de l'Atlas relevées AVANT le profil des côtes). CA, mesuré : falaise à
  moins de 4 px d'une plage, médiane 0,21 ; cliff_gen_ends 0,15. Corrigé : falaise abaissée vers 0,12-0,4 au contact
  d'une plage (RACCORD_U 0,8 u) ; relief des tuiles de mer à 0,02 (48 890 px) ; profil des côtes AVANT les berges des
  rivières de l'Atlas. Deuxième passage (04 h 01) : validate 0 / 1, BOB 41, îlots 12, bords en l'air 0, arbres dans l'eau
  0, marches 18 611 (17 549 : pentes derrière les falaises). « Terrain prêt » à la Construction, essai avec l'Arden.
- **5.10.2026, 04 h 05 – 04 h 15** — PETITES RIVIÈRES (Charles : « des rivières qui n'arrivent pas… pas bien dessinées »).
  Relevé (`scratchpad\petites_rivieres.py`, `embouchures.py`, `sonde_embouchure.py`) : tracés de l'Atlas 522 hex, en eau
  285, SECS 188 (surtout en montagne, relief 3 à 7 u ; quelques-uns dans l'Arden) ; 20 morceaux d'eau sans débouché,
  dont 7 arrêtés à 2-4 hex d'une plage et 2 d'une falaise (ouest : Lyonesse, Artois). Sonde vers (140, 814) : le lit
  descend jusqu'à la côte, mais l'embouchure est une tuile de FALAISE (plateau 0,3-0,45) : l'eau s'arrête à 3 hex.
  Code de CAIME (`BaselineTilemapExporter.cs`) : une terre côtière non plage est une falaise MÊME avec une rivière (la
  falaise passe avant) ; « river ending at beach » = rivière ET plage. `plages_expanded.py` excluait les rivières :
  désormais chaque EMBOUCHURE (Rivers ou tracé de l'Atlas, terre côtière) est une plage, prolongée jusqu'à 3 cases,
  zone de WH1 comprise. Appliqué à la grille du chantier (sauvegarde `terrain-backups\20261005-041429-…-avant-plages`) :
  33 embouchures, 49 cases, plages 792 -> 909 ; frontières ; validate 0 Error / 1 Warning, plages OK. projet_expanded :
  lits de l'Atlas RECREUSÉS à la fin (après côtes et marches ; à blanc : secs 188 -> 173). Reste : torrents de montagne
  secs (la règle « eau jamais au-dessus de la berge la plus basse » de rivieres_atlas_eau les vide sur les pentes
  raides) ; à reprendre avec une capture de Charles. kit_expanded : zones jouables réécrites seulement si elles changent
  (demande de la Construction). Tout cela au PROCHAIN passage (le pack en essai a le terrain de 04 h 01).
- **5.10.2026, 11 h 20 – 11 h 45** — ESCALIERS, TROISIÈME REPRISE (Charles : « encore des hachures, des escaliers par-ci
  par-là… les fleuves creusés pas parfaits… les rivières qui ne partent pas de la mer… réalistes, naturelles »). Relief
  ombré au pixel (`scratchpad\relief_ombre_zoom.py`) : NOS côtes et berges en TERRASSES suivant les hex des tuiles (profil
  calculé au trait des tuiles ; relief remis à 0,02 sur chaque tuile de mer). CA (`relief_ombre_ca.py`, Empires
  Immortels) : relief LISSE et CONTINU, la terre passe sous les tuiles de mer, aucun chenal creusé : le trait de côte
  n'est que dans les tuiles et le fond. Correctifs : `cotes_relief` v2 (côte lissée sur 0,7 hex, parts falaise / plage
  lissées, relief sous la mer continu avec la terre la plus proche puis 0,02 au large sur 1,5 u ; delta nul sur les
  tuiles de mer pour les objets posés sur l'eau) ; `chenaux_fleuves` ne touche plus le relief (seulement le fond) ;
  nouveau `mer_tuiles.py` : la mer lue sur les tuiles (+ lacs) pour eau_materiau, rivieres_atlas_eau, arbres_expanded,
  decors_expanded, controle_anomalies. Gros plans après : côte nord lisse et arrondie, berges de la Brienne lisses (les
  rayures restent sous les tuiles de mer, où le jeu dessine le fond). Préavis kit 11:45:38, chaîne lancée ; grille
  changée (plages d'embouchure) : startpos neuf demandé à la Construction.
- **5.10.2026, 12 h** — TEXTURES DU RIVAGE ET FALAISES (Charles : « enlève tous les trucs en escalier, en pixels… côtes
  parfaites, falaises impressionnantes, majestueuses, plages vraiment belles »). Carte des textures au pixel
  (`scratchpad\textures_zoom.py`) : limites des textures en bords d'hex (tissage par type de sol), et AUCUNE texture de
  rivage hors de la zone de WH1 (ni sable sous l'eau, ni boue au bord, ni lit de rivière) : l'herbe allait jusqu'à l'eau.
  `cotes_relief.textures_rivage` (appelé par projet_expanded, réécrit `terrain-wh1\wh1_blend_monde.npy` lu par
  textures_sol_wh1) : la recette de la Saison validée (textures_tuiles_wh1, C1 à C4) sur la côte LISSÉE : sous la mer
  sand_b3 ; au rivage une bande de mud_a0 (0,25 u, 0,7 u sur les plages, bord bruité) ; sous l'eau des rivières de
  l'Atlas le marais, berges en sand_a0 ; dans la zone de WH1, seulement près des chenaux des fleuves (deltas de WH1 sans
  boue, Charles 25.09). Falaises : plateau entre la médiane et le p90 de CA (0,74 à 1,23 u ; avant 0,6 à 1,15).
  NOUVELLES DÉCISIONS (session des Voûtes, 5.10), lot de données après les essais : Derrevin Libre à une petite faction
  bretonnienne `saison_brt_derrevin_libre` (paysans soulevés et Herrimaults, Recherre ; KotG p. 50), en guerre avec
  l'Aquitanie au tour 1, unités de CA ; siège de l'Aquitanie = la ville d'Aquitanie (découpe aquitaine_chateau_depee),
  la Saison garde le Château d'Épée ; Harde de Châlons horde en (198, 596) ; Flotte des Marées en mer franche (132, 628) ;
  Gobelins de Karag-Dar tiennent voutes_karag_dar ; Fantômes de la Glanborielle `saison_vmp_glanborielle` (faction de
  ChaosRobie, Fort Solstice) en (240, 450) sans ville : faction ou évènements, à voir avec Charles (cinq factions neuves :
  mesurer d'abord le temps de tour) ; bannières dans `travail\images_source\drapeaux_projet\` et `drapeaux_mods\`.
- **5.10.2026, 12 h 10 – 12 h 25** — DIGUE ET FAUSSES PLAGES. Aperçu du rivage (`scratchpad\rivage_textures_zoom.py`) : ombre
  sombre le long de la berge nord de la Brienne. Coupe (`coupe_berge.py`) : terre à 1,25-1,33 u, tuile de PLAGE (lot des
  fleuves), le profil de plage de CA forcé = chute de 1,2 u en 0,7 u. (1) cotes_relief : le plancher du plateau de
  falaise ne dépasse plus la terre voisine (floutée sur 2 hex), sans descendre sous le p10 de CA (0,28) : plus de digue
  au-dessus de terres basses. (2) plages_expanded : partout (zone de WH1 et berges comprises), une plage dont la terre
  monte au-delà de BAS_U (0,8) dans les 3 hex vers l'intérieur redevient falaise, sauf ports (et leurs voisines) et
  embouchures ; puis les restes de moins de 3 cases. 909 -> 621 plages (345 cases rendues à la falaise) ; sauvegarde
  `terrain-backups\20261005-122335-…-avant-plages` ; validate 0 / 1. Préavis kit 12:43:44, chaîne lancée.
- **5.10.2026, 13 h 30 – 13 h 55** — AUDIT DES MONTAGNES (Charles : « montagnes cohérentes, jolies, naturelles entre
  elles… pics, karaks, passages naturels… ne pas bloquer les armées… même très mineur »). `scratchpad\audit_montagnes.py`,
  `audit_montagnes2.py`, `audit_poses_wh1.py` (référence : la zone de WH1). (a) murs invisibles : 15 hex, terre sauvage du
  bord, rien à faire ; connexité : les 131 colonies sur une seule composante franchissable, ports aussi. (b) 24 des 999
  poses de montagne de WH1 gardées (pivot dans la zone de WH1) débordaient sur 1 854 hex FRANCHISSABLES de l'Atlas, les
  grandes montagnes de bordure à 80-92 % hors de la zone (Sanglac, La Maisontaal, Sœurs Pâles, Grung Zint, Helmgart, Voûtes)
  : « deux styles de montagne qui se chevauchent », armées à travers la roche. Nouveau `outils\montagnes_wh1_expanded.py` :
  pose retirée si moins de la moitié de son rectangle est dans la zone gardée (objet et relief de WH1 gardé ; projet_expanded
  lit `est_retiree`) ; sous la ROCHE (emprise au pixel `relief-wh1\montagnes_wh1.npy`) des poses gardées, 251 hex de l'Atlas
  franchissables -> infranchissables (jamais ville, étendue, route, rivière, pont, plage), hex isolés laissés, 6 hex de poche
  refermés ; sauvegarde `terrain-backups\20261005-135134-…-avant-roche-wh1` ; validate 0 / 1 ; 1 composante. (c) 4 275 hex
  franchissables de l'extension plus raides que 99 % de ceux de WH1 (pieds des massifs, cols des Voûtes et des Grises) :
  nouveau `outils\vallees_relief.py` (projet_expanded, avant les côtes) : sur la terre franchissable de l'extension (masque
  lissé), relief ≤ fond de vallée local + 0,3 u, fondu sur 0,6 hex depuis le bord ; la montée se fait sur l'infranchissable.
