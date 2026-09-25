<p align="center"><img src="docs/art/banner-fr.svg" width="100%" alt="La Saison de la Révélation : Expanded"></p>

<p align="center">
<a href="https://bretonia.dev"><b>Atlas de Bretonnie</b></a> ·
<a href="https://github.com/LeyZee/the-season-of-revelation"><b>La Saison originale</b></a> ·
<a href="docs/fr/JOURNAL.md"><b>Journal du chantier</b></a> ·
<a href="README.md"><b>Read in English</b></a>
</p>

**La Saison de la Révélation : Expanded** agrandit la carte de la mini-campagne de Warhammer I à **toute la Bretonnie**.
Au centre, la carte de Warhammer I reste identique à la dernière pierre. Autour, la terre de l'extension est dessinée
d'après l'[Atlas de Bretonnie](https://bretonia.dev) : les duchés, les montagnes, les côtes et, loin au sud, le Bois Rêveur. Le
chantier est **construit en public** : chaque étape est dans le [journal](docs/fr/JOURNAL.md).

<p align="center"><img src="docs/art/divider.svg" width="100%" alt=""></p>

## <img src="docs/art/seal-green.svg" height="34" alt=""> D'un coup d'œil

| | |
|---|---|
| **Grille** | 560 × 825 hex. La carte de Warhammer I est placée en (+120, +250), un décalage pair comme CAIME l'exige. |
| **Au centre** | La Saison originale, intacte (relief, objets, arbres, eaux) ; elle reste la zone jouable pour l'instant. |
| **Autour** | La terre de l'Atlas : relief modelé depuis ses altitudes, sols, forêts, rivières et côtes, raccordés en douceur au relief de Warhammer I. |
| **Le Bois Rêveur** | Le reflet d'Athel Loren en miroir, dans une mer d'éther, au sud de la forêt. |
| **Clés** | Carte `saison_expanded_map`, campagne `saison_expanded`, régions neuves `saison_…` ; jamais les clés de la bêta. |
| **État** | En chantier : phase 2 (déclaration dans l'Assembly Kit). Voir le [PLAN](docs/fr/PLAN.md). |

<p align="center"><img src="docs/art/divider.svg" width="100%" alt=""></p>

## <img src="docs/art/seal-gold.svg" height="34" alt=""> Ce qu'on trouve ici

- [`outils/`](outils/) : les outils d'Expanded. Ils font la grille, le relief, les raccords et les aperçus, et écrivent
  la déclaration de la carte (`spec_expanded.py` → `map_spec_expanded.json`).
- [`map_spec_expanded.json`](map_spec_expanded.json) : la déclaration de la carte.
- [`docs/fr/`](docs/fr/) : la page du chantier, le plan en phases, le journal horodaté.

**Absent, volontairement.** Tout ce qui dérive de Warhammer I (couches de carte, rasters de terrain, relief, aperçus,
packs) reste privé. Les outils lisent aussi les données géographiques de l'Atlas, qui appartiennent au projet privé du
site et ne sont pas fournies. La chaîne commune (terrain, données, pack) est dans le
[dépôt de la Saison originale](https://github.com/LeyZee/the-season-of-revelation).

<p align="center"><img src="docs/art/divider.svg" width="100%" alt=""></p>

## <img src="docs/art/seal-red.svg" height="34" alt=""> Mentions

Warhammer et tous les noms associés appartiennent à **Games Workshop** ; Total War: WARHAMMER à **Creative Assembly**
et **SEGA**. Projet de fan non commercial, sans lien avec eux. Notre code : [licence MIT](LICENSE) ; voir la
[NOTICE](NOTICE.md).
