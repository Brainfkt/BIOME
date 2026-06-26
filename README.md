# Biome Lab

Biome Lab est une simulation scientifique 2D de type agent-based model. Elle permet d'observer les dynamiques d'un ecosysteme artificiel compose de plantes, d'herbivores et de predateurs.

La version actuelle vise une simulation qualitative et reproductible. Elle ne cherche pas a predire un ecosysteme reel, mais a rendre visibles les interactions entre ressources, deplacement, energie, reproduction et predation.

## Fonctionnalites

- Simulation temps reel d'un monde 2D avec plantes, herbivores et predateurs.
- Comportements lisibles: exploration, fuite, recherche de nourriture, chasse, reproduction et repos.
- Perception directionnelle basee sur une portee et un angle de vision.
- Mouvement lisse avec limite de rotation pour eviter les demi-tours instantanes.
- Tableau de bord Pygame avec populations, metriques, repartition comportementale et causes de mortalite.
- Inspection individuelle d'une creature par clic.
- Export des resultats en JSON, CSV et Markdown.

## Installation

Prerequis: Python 3.9 ou plus recent.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Lancer l'application

```bash
biome-lab
```

ou depuis le dossier du projet:

```bash
python main.py
```

## Controles

- `Play` / `Pause`: lance ou suspend la simulation.
- `Reset`: relance le preset courant avec la meme seed.
- `Speed -` / `Speed +`: ajuste la vitesse de simulation.
- `Vision`: affiche ou masque les champs de vision.
- `States`: affiche ou masque les etats comportementaux.
- `Morts: espece` / `Morts: cause`: alterne le graphique de mortalite.
- `Export`: ecrit le preset, les series temporelles et le protocole dans `exports/`.
- `Espace`: lance ou suspend la simulation.
- `R`: relance la simulation.
- `M`: alterne le graphique de mortalite.
- Clic gauche sur une creature: affiche son etat interne et sa fiche scientifique.

## Structure du projet

```text
biome_lab/
  behavior/      Regles de decision et fonctions de steering.
  config/        Schemas, preset par defaut et documentation des parametres.
  entities/      Entites du monde: creatures et plantes.
  experiments/   Execution de protocoles experimentaux.
  exports/       Serialisation JSON, CSV et Markdown.
  metrics/       Collecte et definition des indicateurs.
  rendering/     Rendu Pygame et overlays.
  simulation/    Monde, moteur temporel, spatial index et evenements.
  ui/            Panneaux, controles et inspecteur.
presets/         Presets experimentaux versionnables.
tests/           Tests unitaires.
```

## Presets et reproductibilite

Le preset par defaut est construit dans `biome_lab/config/defaults.py`. Un preset JSON equivalent peut etre stocke dans `presets/` pour documenter une experience precise.

Les parametres principaux sont:

- `max_speed`: vitesse maximale d'une creature.
- `vision_range` et `vision_angle_deg`: portee et ouverture du champ de vision.
- `basal_metabolism` et `movement_energy_cost`: couts energetiques.
- `hunger_threshold`: seuil a partir duquel l'alimentation devient prioritaire.
- `reproduction_threshold`, `reproduction_cost` et `reproduction_cooldown`: contraintes de reproduction.
- `flee_distance`, `attack_range` et `food_energy_gain`: regles propres aux interactions predateur-proie.

Les seeds sont fixees dans les presets pour rendre les runs comparables.

## Exports

Le bouton `Export` produit des fichiers dans `exports/`:

- `*_preset.json`: configuration experimentale reproductible.
- `*_metrics.csv`: series temporelles des metriques.
- `*_protocol.md`: question, hypothese, variables, constantes et definitions.

Le dossier `exports/` est ignore par Git, car il contient des resultats de runs locaux. Si un resultat doit etre partage, copiez le fichier pertinent dans un dossier dedie et documentez le contexte de generation.

## Tests

```bash
pytest
```

Les tests couvrent les schemas de configuration, les priorites comportementales, le lissage des virages, les metriques et le contenu des exports Markdown.

## Limites scientifiques

- Le monde est un espace 2D simplifie sans obstacles ni zones environnementales.
- La perception utilise distance et angle, sans occlusion.
- L'energie, la reproduction et la predation sont volontairement abstraites.
- Les resultats sont qualitatifs et doivent etre interpretes avec plusieurs repetitions et seeds controlees.
