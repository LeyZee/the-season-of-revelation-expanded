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
- **21 h 45** : VOÛTES, esquisse v2 de la session « Extension » (trois lieux dans la bande de montagnes au sud d'Athel
  Loren : Krinal pour Kemmler et Krell, Karak Bhufdar, Karak Izor capitale) envoyée à Charles ; rien n'est touché avant
  son accord.
