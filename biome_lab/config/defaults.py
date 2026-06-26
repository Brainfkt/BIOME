from __future__ import annotations

from biome_lab.config.schemas import (
    BiomeLabPreset,
    CreatureTraits,
    ExperimentProtocol,
    PlantConfig,
    ScientificCard,
    SimulationConfig,
)


def create_default_preset() -> BiomeLabPreset:
    herbivore_card = ScientificCard(
        ecological_role="Consommateur primaire convertissant les ressources vegetales en biomasse animale.",
        morphological_traits=[
            "Corps leger favorisant les changements rapides de direction.",
            "Rayon corporel modeste afin de representer une proie mobile.",
        ],
        sensory_traits=[
            "Vision directionnelle a moyenne portee.",
            "Detection des predateurs dans un cone frontal.",
        ],
        energetic_traits=[
            "Reserve energetique plafonnee.",
            "Perte d'energie continue par metabolisme et deplacement.",
        ],
        reproductive_traits=[
            "Reproduction conditionnee par un surplus energetique.",
            "Cooldown limitant les naissances successives.",
        ],
        behavioral_rules=[
            "Fuir un predateur visible dans la distance de fuite.",
            "Chercher une plante si l'energie passe sous le seuil de faim.",
            "Se reproduire si l'energie et le cooldown le permettent.",
            "Explorer sinon.",
        ],
        rule_justification=[
            "La fuite prioritaire modele la pression de predation immediate.",
            "La recherche alimentaire limite la famine avant reproduction.",
            "La reproduction depend d'un surplus pour eviter une croissance sans cout.",
        ],
    )
    predator_card = ScientificCard(
        ecological_role="Consommateur secondaire regulant la population d'herbivores.",
        morphological_traits=[
            "Corps plus rapide et plus couteux energetiquement.",
            "Portee d'attaque courte representant une capture de proximite.",
        ],
        sensory_traits=[
            "Vision directionnelle plus longue que celle des herbivores.",
            "Detection des proies dans un cone de chasse.",
        ],
        energetic_traits=[
            "Metabolisme basal eleve representant le cout de maintien du predateur.",
            "Gain energetique important lors d'une predation reussie.",
        ],
        reproductive_traits=[
            "Reproduction autorisee uniquement avec reserve energetique suffisante.",
            "Cooldown imposant une dynamique demographique plus lente.",
        ],
        behavioral_rules=[
            "Chasser une proie visible si faim ou proie immediatement accessible.",
            "Se reproduire si l'energie et le cooldown le permettent.",
            "Explorer sinon.",
        ],
        rule_justification=[
            "La chasse conditionnelle evite une predation constante sans besoin energetique.",
            "La chasse opportuniste pres d'une proie represente un benefice attendu eleve.",
            "Le cout reproductif limite les explosions de population de predateurs.",
        ],
    )

    herbivore = CreatureTraits(
        name="Herbivore A",
        role="herbivore",
        color=(60, 185, 120),
        max_speed=72.0,
        vision_range=150.0,
        vision_angle_deg=230.0,
        basal_metabolism=0.75,
        movement_energy_cost=0.018,
        max_energy=120.0,
        hunger_threshold=46.0,
        reproduction_threshold=92.0,
        reproduction_cost=34.0,
        reproduction_cooldown=10.0,
        max_age=240.0,
        flee_distance=145.0,
        attack_range=0.0,
        food_energy_gain=24.0,
        science_card=herbivore_card,
    )
    predator = CreatureTraits(
        name="Predateur A",
        role="predator",
        color=(220, 86, 76),
        max_speed=88.0,
        vision_range=210.0,
        vision_angle_deg=190.0,
        basal_metabolism=1.05,
        movement_energy_cost=0.024,
        max_energy=150.0,
        hunger_threshold=58.0,
        reproduction_threshold=118.0,
        reproduction_cost=46.0,
        reproduction_cooldown=18.0,
        max_age=260.0,
        flee_distance=0.0,
        attack_range=12.0,
        food_energy_gain=42.0,
        science_card=predator_card,
    )
    simulation = SimulationConfig(
        world_width=1120,
        world_height=760,
        initial_herbivores=42,
        initial_predators=9,
        max_creatures=520,
        fixed_dt=1.0 / 30.0,
        metrics_sample_interval=1.0,
        metrics_window_seconds=30.0,
        seed=42,
        plant=PlantConfig(
            initial_count=180,
            max_count=260,
            radius=4.0,
            energy=22.0,
            regrowth_per_second=2.0,
        ),
    )
    protocol = ExperimentProtocol(
        research_question=(
            "Comment la pression de predation influence-t-elle la stabilite "
            "de la population d'herbivores dans un environnement a ressources renouvelables ?"
        ),
        hypothesis=(
            "Une pression de predation moderee produit des oscillations populationnelles, "
            "tandis qu'une pression trop forte augmente le risque d'extinction locale des herbivores."
        ),
        independent_variable="Traits de predation : vision_range, attack_range, food_energy_gain.",
        dependent_variables=[
            "population_herbivores",
            "population_predators",
            "predation_rate",
            "mean_survival_time",
            "population_variance_window",
        ],
        constant_parameters=[
            "Taille du monde",
            "Regeneration des plantes",
            "Population initiale",
            "Seed aleatoire",
            "Regles comportementales",
        ],
        duration_seconds=300.0,
        seed=42,
        repetitions=5,
        notes="Preset qualitatif de depart pour observer cycles predateur-proie-ressource.",
    )
    return BiomeLabPreset(
        name="default_predator_prey_resource",
        simulation=simulation,
        herbivore=herbivore,
        predator=predator,
        protocol=protocol,
    )

