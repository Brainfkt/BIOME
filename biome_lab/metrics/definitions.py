from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    definition: str
    scientific_use: str


METRIC_DEFINITIONS: Dict[str, MetricDefinition] = {
    "population": MetricDefinition(
        name="Population par espece",
        definition="Nombre d'individus vivants par type d'entite a un instant donne.",
        scientific_use="Suit stabilite, extinction, explosion demographique et cycles predateur-proie.",
    ),
    "population_time_series": MetricDefinition(
        name="Population dans le temps",
        definition="Serie temporelle des populations echantillonnee regulierement.",
        scientific_use="Revele oscillations, transitions et decalages temporels entre especes.",
    ),
    "resources_available": MetricDefinition(
        name="Ressources disponibles",
        definition="Nombre de plantes vivantes et energie vegetale totale disponible.",
        scientific_use="Relie la base trophique a la survie et reproduction des herbivores.",
    ),
    "mean_energy": MetricDefinition(
        name="Energie moyenne par espece",
        definition="Energie moyenne des individus vivants d'une espece.",
        scientific_use="Mesure le stress energetique avant mortalite ou baisse de reproduction.",
    ),
    "death_causes": MetricDefinition(
        name="Distribution des causes de mortalite",
        definition="Comptage cumulatif des morts par famine, maladie, predation et vieillesse.",
        scientific_use="Identifie le mecanisme dominant de declin populationnel.",
    ),
    "infection_rate": MetricDefinition(
        name="Taux d'infection",
        definition="Nombre de nouvelles infections par seconde simulee sur la fenetre recente.",
        scientific_use="Mesure la pression epidemiologique creee par densite, saisons et proximite.",
    ),
    "infected_population": MetricDefinition(
        name="Population infectee",
        definition="Nombre d'individus vivants actuellement dans l'etat infecte.",
        scientific_use="Suit l'intensite instantanee d'une epidemie dans l'ecosysteme.",
    ),
    "mutation_load": MetricDefinition(
        name="Charge mutationnelle moyenne",
        definition="Nombre moyen de mutations heritees par individu vivant.",
        scientific_use="Suit la derive des traits sous reproduction et pression de selection.",
    ),
    "mutation_rate": MetricDefinition(
        name="Taux de mutation",
        definition="Nombre de nouvelles mutations heritees par seconde simulee sur la fenetre recente.",
        scientific_use="Mesure l'intensite de variation hereditaire produite par la reproduction.",
    ),
    "season_index": MetricDefinition(
        name="Indice saisonnier",
        definition="Indice numerique de la phase saisonniere active, -1 si les saisons sont desactivees.",
        scientific_use="Relie les changements demographiques aux cycles environnementaux.",
    ),
    "terrain_roughness": MetricDefinition(
        name="Rugosite topographique",
        definition="Ecart-type des elevations de la grille de terrain.",
        scientific_use="Quantifie a quel point la carte contient relief, vallees, cretes ou transitions abruptes.",
    ),
    "predation_rate": MetricDefinition(
        name="Taux de predation",
        definition="Nombre de predations par seconde simulee sur la fenetre recente.",
        scientific_use="Quantifie la pression exercee par les predateurs sur les herbivores.",
    ),
    "reproduction_rate": MetricDefinition(
        name="Taux de reproduction",
        definition="Nombre de naissances par seconde simulee sur la fenetre recente.",
        scientific_use="Compare le remplacement demographique aux pertes.",
    ),
    "mean_survival_time": MetricDefinition(
        name="Temps moyen de survie",
        definition="Age moyen au deces pour les individus morts d'une espece.",
        scientific_use="Resume la viabilite individuelle sous les contraintes du milieu.",
    ),
    "behavior_time_distribution": MetricDefinition(
        name="Repartition du temps comportemental",
        definition="Part du temps cumule des individus vivants passee dans chaque comportement.",
        scientific_use="Relie les regles locales aux dynamiques globales observees.",
    ),
    "population_variance_window": MetricDefinition(
        name="Variance des populations sur fenetre",
        definition="Variance de la population recente sur une fenetre temporelle glissante.",
        scientific_use="Detecte instabilite, oscillations ou regime proche d'une transition.",
    ),
}
