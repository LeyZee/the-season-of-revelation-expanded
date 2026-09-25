# Saison Expanded : plan de travail (construction, 25.09.2026 vers 15 h 45)

Sources : inventaire de l'Atlas (agent, 15 h 30 ; résumé dans `README.md`) et inventaire de la chaîne (agent, 15 h 45 ;
résumé ci-dessous). Rien n'a encore été écrit hors de ce dossier.

## Ce que l'inventaire de la chaîne a trouvé

1. **Une seule constante `CARTE` sert à deux choses** dans presque tous les modules : la SOURCE WH1
   (`03-references\...\terrain-wh1\terrain\campaigns\<CARTE>`) et la CIBLE dans le kit. Il faut séparer `CARTE_SOURCE`
   (WH1, inchangée) et `CARTE` (cible).
2. **Une campagne ne connaît qu'une carte** (`campaigns.map_name`) : Expanded = nouvelle clé de carte ET nouvelle clé de
   campagne, nouvelle zone jouable (`campaign_map_playable_areas`, index neuf).
3. **Dimensions en dur** : `HEX_L, HEX_H = 400, 440`, `LARGEUR_MONDE = 266.53` (répété dans 5 modules), rasters
   3200 × 3524 et 800 × 881 (`tuiles_wh1.LARGEUR, HAUTEUR`), `masques_eau_carte` (266,53 × 338,9, N = 2048),
   liste d'arbres (bornes de WH1 recopiées), zone jouable du kit, `map_spec.json`, bornes de caméra.
4. **Collisions dans le kit sans clé de carte** (dangereuses pour la bêta) :
   - `working_data\rigidmodels\_wh1\campaign\montagnes\` : maillages DRAPÉS sur le relief, réécrits à chaque générateur ;
   - `working_data\warscape_asset_variation_db\` (réécrit par chaque BOB) ;
   - matériau de neige `wh_dlc05_wood_elves_campaign_snow.xml.material` ; matériaux et masques d'eau
     `wh_dlc05_wood_elves_*` (dépendent de la taille du monde) ;
   - `terrain_textures_campaign.assetdb` (une seule copie pour toutes les campagnes : à fusionner).
   Avec clé de carte (sans risque si la clé change) : `raw_data\terrain\campaigns\<carte>`, `working_data\terrain\...`,
   `campaign_maps\<carte>`, `EmpireDesignData\campaign_maps\<carte>\map.hex`, `binaries\BOB\zz_<carte>_configuration.xml`.
5. **Tout l'atelier** écrit dans `04-projets\saison-des-revelations\` (relief-wh1, eau-carte, montagnes-wh1, rivieres-wh1,
   arbres, éclairage, textures, couches, map_spec…) : à rediriger vers `04-projets\saison-expanded\`.
6. **CAIME** : `create --width --height` en ligne de commande ; pas de redimensionnement en ligne de commande (seulement
   Edit → Resize dans l'interface). Voie scriptable : `create` à la nouvelle taille, couches `.hex_layer` élargies en
   Python (`caime_layers.encode_flat`), `import-layer`, `validate`, `process`. **Décalage horizontal pair obligatoire**
   (+120 : pair, bon).

## Principe retenu

- Tout le traitement de WH1 reste dans son repère 400 × 440 ; UNE étape de placement l'insère dans le monde agrandi
  (décalage x + 120 colonnes, rien au sud) : rasters élargis, entités, arbres, montagnes, rivières, éclairage translatés.
- Autour, la terre de l'extension est fabriquée depuis l'Atlas (`extension_geo.npz`, `extension_regions.npz`) :
  relief modelé depuis `alt` (pentes, vallées, sommets ; pas de paliers), sols CAIME, forêts, marais, rivières, côtes.
- Un module de configuration unique (carte, campagne, taille, décalage, dossier d'atelier, noms des matériaux),
  choisi par `--carte` ou une variable d'environnement ; la bêta garde ses valeurs actuelles, à l'octet près.

## Phases

1. **Configuration par carte** (1 à 2 jours) : module commun, `CARTE_SOURCE` / `CARTE`, sorties par projet ; contrôle :
   la chaîne de la bêta produit les MÊMES fichiers qu'avant (comparaison octet par octet du compilé).
2. **Grille agrandie** (1 jour) : map.hex 560 × 575 par CAIME, couches de la Saison recopiées décalées, régions de
   l'extension déclarées hors jeu et infranchissables ; zone jouable = la Saison.
3. **Terrain de l'extension** (2 à 3 jours) : relief, sols, forêts, rivières, côtes, montagnes depuis l'Atlas ; le
   Miroir d'Athel Loren ; contrôle dans Terry puis décodage du compilé.
   **Couche infranchissable d'Expanded** (session « Extension », 25.09.2026, 18 h ; l'Atlas dessine les passages ainsi) :
   franchissable = la couche impassable de WH1 (1 = franchissable) + les régions neuves (`lab` ≥ 0) + les **cinq
   ouvertures** de `travail\extension_routes.json` (clé `ouvertures` : `points` et `cases_a_creuser`) : Helmgart par le
   versant impérial du Défilé de la Hache, Grung Zint, La Maisontaal (Sentier de la Pierre Noire), Tal Jul-Finel (Pics
   des Pins), Orques de fer vers la Gasconnie. Sans elles, ces cinq accès manquent en jeu. Les cols de l'extension sont
   déjà creusés dans `alt` (vallées de 4 à 5 hex) : le relief modelé depuis `alt` les reprend.
   **Décors 3D des lieux** : `travail\lieux_frontiere.json` (32 lieux sourcés de la frontière Empire–Bretonnie et des
   Terres Désolées ; hex dans le repère de la Saison, + (120, 250) pour Expanded ; certitude A/B/C, priorité 1 à 3).
   Priorité 1 (9) : mur de Helmgart, route de l'Amitié, Helspire, Corridor tortueux, temple du Loup gris, comptoir
   d'Azgaraz, Tallerhof, Schlüsselschloss, ruines du Grauesland. Deuxième liste (points d'intérêt de toute la carte,
   champ `decor_3d`) à venir. Modèles : ceux de CA qui existent, choisis par nous.
**DÉCISION DE CHARLES (25.09.2026, 19 h)** : dans Expanded, **l'Atlas l'emporte sur WH1** (« c'est une expansion »).
Conséquences : (1) les coutures terre / mer au bord du cadre de WH1 (Île Silencieuse sur la mer de WH1, Baie Moussille et
Manaanspoort sur des terres de WH1) se règlent selon l'Atlas : le terrain du cadre est ADAPTÉ à ces cases (terre levée,
mer creusée), par exception à la règle « cadre de WH1 intact », qui reste vraie partout ailleurs ; (2) la partie jouable
de WH1 est redessinée d'après l'Atlas : provinces redécoupées, villes ajoutées (les 14 découpes, `regions_wh1_touchees`)
; (3) les maîtres des régions sans maître (`a_trancher`) : recherche lore / gameplay / équilibrage, puis choix de Charles.

**Provinces globales (25.09.2026, 19 h 15)** : dans WH3, la province d'une région (`region_to_province_junctions`) ne
dépend pas de la carte. Donc : (1) une région de WH1 ne change JAMAIS de province dans Expanded ; si l'Atlas le veut,
elle est remplacée par une « reprise » à clé `saison_` (Fort Solstice -> `saison_glanborielle_fort_solstice`, capitale de
Glanborielle, voie (a) confirmée) ; (2) dix régions neuves entrent dans des provinces de WH1 : sans effet sur la bêta
(`build_pack` ne prend que les jonctions de régions `wh_dlc05_`), mais **le pack d'Expanded et celui de la Saison ne
doivent pas être actifs ensemble** (à dire sur les deux pages et à contrôler par script au lancement).
Déclaration faite le 25.09 à 19 h 14 (préavis 19 h 09) : 75 régions, 21 provinces, 64 colonies ; sauvegarde
`05-journal\db-backups\20260925-191420`.

2 bis. **Régions neuves** (après la déclaration du 25.09 à 18 h 08, qui ne porte que les 61 régions de WH1) : source
   `travail\extension_regions.json` (32 régions, 11 mers avec `cle_proposee`, 15 provinces, 14 **découpes** de régions de
   WH1 en régions neuves, ex. Aquitanie prise sur Château d'Épée) et `travail\reves_grilles.json` (18 régions du Bois
   Rêveur, `saison_reves_…`, 6 domaines, 4 factions de Slaanesh de CA). Clés : `saison_<clé>`, `saison_sea_<clé>`, et les
   factions proposées en `ext_…` passent en `saison_…` (règle de Charles). Une découpe change une région de WH1 DANS
   Expanded seulement (couche des régions de la grille d'Expanded) ; la bêta garde les siennes. Ordre : couche des régions
   CAIME d'Expanded depuis les grilles de l'Atlas -> fiche (`spec_expanded.py`, lot 2) -> `declare_map.py` sous préavis ->
   `sync-names` CAIME -> contrôle (chaque hex terrestre a une région, couleurs uniques). Aucune faction neuve dans le kit
   sans essai de démarrage (erreur 107).
4. **Campagne Expanded** : clé de campagne, startpos, pack `saison_expanded.pack` chargé SEUL ; premier essai en jeu.

## Compatibilité avec les autres mods de carte (Charles, 25.09.2026 : « que tout cohabite », « attaque tout ça aussi »)

Audit : `05-journal\2026-09-25-audits\compatibilite-autres-mods.md`. Pour la bêta ET Expanded :
1. Catalogue des textures de sol : fichier à nous (`textures_sol_wh1.CATALOGUE_SEPARE`, 58 entrées), essai en jeu (pack
   refait à neuf) ;
2. bandeaux par niveau de bâtiment de CA et sous-types permis à Mousillon : analyse de l'IA (niveaux d'affichage à nous ;
   lignes seulement au startpos ?) ;
3. 686 fichiers de WH1 à des chemins de style CA : les ranger sous un dossier à nous (`fichiers_wh1`, chaîne, pack).

## Extension future (idée de la communauté, notée avec l'accord de Charles, 25.09.2026, 20 h 20)

- **Les Voûtes (The Vaults)** : un moddeur du Discord propose d'ajouter les Voûtes (pour y jouer Kemmler, déjà jouable
  avec Krell). Conflit avec la bande du Bois Rêveur au sud (décision de Charles : miroir d'Athel Loren derrière le voile)
  et avec la largeur de la grille à l'est : donc pas dans Expanded v1. Piste pour une extension suivante (grille agrandie
  vers le sud-est, Atlas d'abord, sources), en réutilisant la chaîne d'Expanded (grille, régions, villes, raccords,
  minicarte, connexité).
  **Mise à jour 20 h 25 (Charles : Kemmler « devrait être plus au sud », « pas mal d'espace entre les montagnes et le
  miroir »)** : la place existe DANS Expanded, sans agrandir la grille : l'est de la bande du sud (x ≈ 343 à 440,
  y ≈ −224 à 0, éther vide), au sud de la pointe des Grises et au sud-est d'Athel Loren. Le voile serait raccourci à la
  largeur du miroir, et les Voûtes rejoindraient les Grises par la terre ; le miroir garde son voile et ses portails.
  Recherche sourcée demandée à la session « Extension » (géographie, lieux, Kemmler et le tombeau de Krell dans les
  sources). Rien n'est construit avant l'accord de Charles sur ses résultats. Dans la Saison, Kemmler reste au Poste de
  la Pierre Noire.
  **DÉCISION DE CHARLES (20 h 30)** : les Voûtes ENTRENT dans Expanded et dans l'Atlas (site compris), et Kemmler y
  part dans Expanded (« plus logique là qu'ailleurs »). La session « Extension » dessine et source ; la construction
  déclare et construit avec la même chaîne (déclaration, CAIME, villes, connexité, relief, minicarte).

## Idées validées par Charles, à placer (sans urgence)

- **Ruines de l'Empire** en décor non habité, dans les cols et sur le versant bretonnien des Montagnes Grises, « au loin » :
  le West Mark (conquis par Sigismond II, 479-505 CI ; WFRP 2e, *Sigmar's Heirs*, p. 14) et le Grauesland (perdu pendant
  la Première guerre de Montfort, 955-970 CI ; WFRP 4e, *Enemy in Shadows*, p. 116-117) : provinces perdues avant la
  fondation de la Bretonnie (978 CI), donc ni faction ni ville à l'époque de la Saison. Objets de ruine de CA ou de WH1
  posés à la phase 3 (session « Vidéo », 25.09 vers 17 h ; place étudiée sur la carte papier par la session « Extension »).
- **Le Bois des Rêves, habillage de Slaanesh** (Charles, 25.09.2026 vers 17 h 35 : « des effets chaotiques autour, pour
  montrer que c'est du Slaanesh ») : tout est déjà chez CA (relevé `scratchpad\chercher_slaanesh.py`) : LUT
  `lut/campaign_chaos_slaanesh.dds` (zone d'éclairage à la manière de CA) ; textures de sol
  `terrain/textures/campaign/default/chaos_relm_slaanesh/*` (tcamp.pack) ; 131 modèles `rigidmodels/campaign/slaanesh/*`
  (tentacules, cornes, barbelés, palais ; models4.pack) ; failles `rigidmodels/campaign/rifts/fx_campaign_rift_sla_*`
  pour les portes saisonnières ; effets `vfx/materials/*sla*` (dont `wh3_sla_waterfall_01`). Principe (lore : reflet
  d'Athel Loren où rôdent les démons de Slaanesh, Wood Elves 8e éd. p. 12) : forêt reconnaissable, teintée et corrompue ;
  textures de Slaanesh en taches, plus denses au cœur et aux portes ; modèles en petits groupes ; failles aux portes ;
  voile de brume. Phase 3.
- **Bordures démoniaques du Bois Rêveur et du voile** (Charles, 25.09.2026 vers 17 h 40 : « des effets un peu
  démoniaques sur les contours du miroir… et la séparation qui longe les montagnes ») ; relevé
  `scratchpad\chercher_effets_chaos.py` (packs de CA) :
  - contour du reflet : failles de Slaanesh `vfx/materials/fx_campaign_sla_rift_{energy,fire_edge,emissive}` sur les
    modèles `fx_campaign_rift_base_*`, en chapelet ; décor de Slaanesh (tentacules, cornes, barbelés) en petits groupes ;
  - le voile (le long des Voûtes) : déchirure du Grand Vortex `campaign_wh3_vortex_tear_main.wsmodel` répétée ;
    colonnes et rayons `campaign_vortex_pillar_*`, `campaign_vortex_beam_*`, `campaign_vortex_helix_01` ; maelströms
    `campaign_maelstorm_base{,_02,_03}` ; nuages et brume teintés ;
  - portes saisonnières : `rigidmodels/campaign/chaos/chs_gate_01`, `chs_portal_01` (animé), sphère
    `campaign_teleport_portal_sphere*`, faille de Slaanesh au-dessus.
  Précautions : peu d'effets, bien placés (images par seconde) ; chaque effet essayé SEUL en jeu avant d'être gardé
  (précédent : effets de WH1 qui plantaient le rendu, `EFFETS_ECARTES`). Phase 3.
- **Plus tard** : un morceau du Reikland à la frontière (Helmgart au débouché du Défilé de la Hache, face à Montfort ; la
  Trouée de Gisoreux) ; Marienbourg quand Charles l'aura vue en jeu.

Les phases ne tournent JAMAIS pendant une chaîne, un pack ou un essai de la bêta ; préavis de 5 minutes avant toute
écriture dans le kit.
