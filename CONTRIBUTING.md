# Contribuer a Biome Lab

Ce document decrit le flux de travail attendu pour modifier le projet sans casser la reproductibilite des simulations.

## Environnement local

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Avant de commit

1. Lancez les tests:

   ```bash
   pytest
   ```

2. Verifiez l'etat Git:

   ```bash
   git status --short
   ```

3. Ne committez pas les artefacts locaux:

   - `.venv/`
   - `.pytest_cache/`
   - `*.egg-info/`
   - `exports/`
   - fichiers systeme comme `.DS_Store`

## Style de code

- Garder les modules courts et axes sur une responsabilite claire.
- Preferer les noms explicites aux abreviations.
- Eviter les commentaires qui repetent le code; commenter seulement les choix de modele ou les calculs qui demandent du contexte.
- Conserver les comportements reproductibles quand une seed est fournie.
- Ajouter ou ajuster un test quand une regle de simulation, une metrique ou un schema change.

## Simulation et modelisation

- Les comportements doivent rester lisibles: decision dans `biome_lab/behavior/`, execution physique dans `biome_lab/simulation/`.
- Les nouveaux parametres doivent etre documentes dans `biome_lab/config/parameter_docs.py` quand ils sont exposes aux presets ou aux exports.
- Les changements de dynamique doivent etre decrits dans la README si l'utilisateur les observe directement.
- Les exports doivent rester deterministes dans leur contenu, hors horodatage du nom de fichier.

## Documentation

Mettre a jour la documentation quand un changement modifie:

- les commandes d'installation ou de lancement;
- les controles de l'interface;
- la structure du projet;
- les hypotheses scientifiques;
- le format des exports;
- les parametres disponibles.

## Tests attendus

Les tests actuels couvrent:

- validation des schemas et presets;
- priorites comportementales;
- lissage des virages;
- metriques et exports Markdown.

Pour une contribution plus large, ajouter des tests au niveau le plus proche du changement: comportement, simulation, export, metrique ou configuration.
