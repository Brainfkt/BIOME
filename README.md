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
- Topologie de carte modifiable: vallees, cretes et lissage du relief en mode sandbox.
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

Charger un preset JSON dans l'interface:

```bash
biome-lab ui --preset presets/default_experiment.json
```

Charger un etat sandbox sauvegarde dans l'interface:

```bash
biome-lab ui --preset exports/20260626_120000_sandbox_state.json
```

Lancer une experience headless avec exports JSON/CSV:

```bash
biome-lab run --preset presets/default_experiment.json --duration 300 --repetitions 5 --output-dir exports
```

Pour les runs massifs ou les essais de performance, les evenements detailles peuvent etre desactives:

```bash
biome-lab run --preset presets/default_experiment.json --duration 300 --repetitions 5 --output-dir exports --no-events
```

Dans ce mode, `events.csv` garde ses en-tetes mais ne contient pas de lignes; les metriques basees sur les evenements sont marquees comme incompletes dans `metadata.json`.

Pour maximiser le debit sur de tres grands nombres d'agents, utilisez aussi le mode de metriques leger:

```bash
biome-lab run --preset presets/default_experiment.json --duration 300 --repetitions 5 --output-dir exports --no-events --metrics-mode light
```

`--metrics-mode light` exporte les populations et energies principales, mais saute les taux evenementiels, parts comportementales, variances fenetrees et resumes terrain couteux. Le mode par defaut reste `full`.

Le mode headless accepte aussi un `world_state` JSON. Dans ce cas, le run reprend depuis l'etat sauvegarde; `--duration` represente la duree simulee additionnelle.

## Controles

- `Play` / `Pause`: lance ou suspend la simulation.
- `Reset`: relance le preset courant avec la meme seed.
- `Speed -` / `Speed +`: ajuste la vitesse de simulation.
- `Vision`: affiche ou masque les champs de vision.
- `States`: affiche ou masque les etats comportementaux.
- `Morts: espece` / `Morts: cause`: alterne le graphique de mortalite.
- `Export`: ecrit le preset, les series temporelles et le protocole dans `exports/`.
- `Save`: sauvegarde un etat sandbox JSON dans `exports/`.
- `Load` ou `L`: recharge le dernier etat sandbox sauvegarde dans `exports/`.
- `View`: recentre la camera.
- Outils sandbox: `Select`, `Plant`, `Herb`, `Pred`, `Obstacle`, `Valley`, `Ridge`, `Smooth`, `Erase`.
- Reglages sandbox: `Topo`, `Seasons`, `Disease`, `Mutation` activent ou desactivent les systemes experimentaux.
- `Palette`: alterne les palettes de terrain (`natural`, `hydrology`, `arid`, `grayscale`).
- `Espace`: lance ou suspend la simulation.
- `R`: relance la simulation.
- `M`: alterne le graphique de mortalite.
- `1` a `9`: selection rapide des outils sandbox.
- Avec `Valley`, `Ridge` ou `Smooth`, clic gauche et glisser peint directement le relief.
- `T`: active ou desactive la topologie.
- `N`: active ou desactive les saisons.
- `D`: active ou desactive les maladies; si possible, une creature est infectee pour demarrer la dynamique.
- `U`: active ou desactive les mutations.
- `P`: change la palette du terrain.
- Molette: zoom.
- Clic droit ou clic molette + glisser: deplacement de camera.
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

Biome Lab utilise deux formats JSON distincts:

- `preset`: configuration experimentale versionnee et partageable. Il decrit les parametres de simulation, les traits, le protocole et les seeds, mais pas l'etat instantane des agents.
- `world_state`: sauvegarde sandbox versionnee. Il contient le preset courant plus le temps simule, les agents, les plantes, les obstacles, les zones, la grille de topologie peinte, les toggles experimentaux et l'etat du generateur aleatoire.

Le preset par defaut est construit dans `biome_lab/config/defaults.py`. Un preset JSON equivalent peut etre stocke dans `presets/` pour documenter une experience precise.

Les parametres principaux sont:

- `max_speed`: vitesse maximale d'une creature.
- `vision_range` et `vision_angle_deg`: portee et ouverture du champ de vision.
- `basal_metabolism` et `movement_energy_cost`: couts energetiques.
- `hunger_threshold`: seuil a partir duquel l'alimentation devient prioritaire.
- `reproduction_threshold`, `reproduction_cost` et `reproduction_cooldown`: contraintes de reproduction.
- `flee_distance`, `attack_range` et `food_energy_gain`: regles propres aux interactions predateur-proie.
- `topology`: grille d'elevation permettant de creer vallees, cretes, collines et bassins; les pentes augmentent le cout de deplacement.
- `topology.palette`: palette visuelle du relief, sans effet direct sur la dynamique.

`simulation.seed` et `protocol.seed` doivent etre identiques dans un preset valide. Le runner headless utilise cette seed comme depart puis incremente de 1 a chaque repetition.

## Ordre de simulation

A chaque tick, le monde applique dans l'ordre: vieillissement et mortalite par age, maladies, decisions et mouvements des herbivores, decisions et mouvements des predateurs, predation, repousse des plantes, puis nettoyage des entites mortes.

Les nouveau-nes sont ajoutes pendant la decision de reproduction. Un herbivore ne juste avant le tour des predateurs peut donc etre mange dans le meme tick; cette regle est volontairement conservee pour garder une boucle simple et deterministe.

## Exports

Le bouton `Export` produit des fichiers dans `exports/`:

- `*_preset.json`: configuration experimentale reproductible.
- `*_metrics.csv`: series temporelles des metriques.
- `*_protocol.md`: question, hypothese, variables, constantes et definitions.

Le mode headless produit un dossier horodate contenant:

- `preset.json`: preset utilise.
- `metrics.csv`: series temporelles avec repetition et seed.
- `events.csv`: naissances, morts, predations, infections, guerisons et mutations heritees.
- `summary.csv`: resume final par repetition.
- `metadata.json`: contexte du run.

Le bouton `Save` produit un fichier `*_sandbox_state.json` chargeable par `Load`, `L`, ou `biome-lab ui --preset`. Ce fichier est un `world_state`, pas un preset experimental minimal.

Le dossier `exports/` est ignore par Git, car il contient des resultats de runs locaux. Si un resultat doit etre partage, copiez le fichier pertinent dans un dossier dedie et documentez le contexte de generation.

## Benchmarks headless

Le script `scripts/bench_headless.py` mesure la boucle headless sans importer Pygame:

```bash
.venv/bin/python scripts/bench_headless.py --scenario headless_1k --steps 100
.venv/bin/python scripts/bench_headless.py --scenario all --steps 1 --output exports/benchmarks.json
.venv/bin/python scripts/bench_headless.py --scenario headless_1k --steps 5 --profile /tmp/biome_profile.txt
```

Les scenarios disponibles sont `headless_1k`, `headless_5k` et `headless_10k`. La sortie JSON inclut le nombre de steps, les steps/s, le temps d'initialisation, le pic memoire, les populations finales et des cibles indicatives (`target_steps_per_second`, `target_peak_memory_mb`, `target_update_seconds`). Ces cibles documentent une baseline locale; elles ne sont pas des assertions de test.

## Tests

```bash
.venv/bin/python -m pytest
```

Les tests couvrent les schemas de configuration, les priorites comportementales, le lissage des virages, les metriques et le contenu des exports Markdown.

## Limites scientifiques

- Le monde par defaut reste un espace 2D simplifie; topologie, obstacles et zones sont des extensions sandbox configurables.
- Topologie, obstacles, zones, saisons, maladies et mutations sont disponibles comme extensions sandbox, mais restent des modeles abstraits.
- La perception utilise distance et angle, sans occlusion.
- L'energie, la reproduction et la predation sont volontairement abstraites.
- Les resultats sont qualitatifs et doivent etre interpretes avec plusieurs repetitions et seeds controlees.
