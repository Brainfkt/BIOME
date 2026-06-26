from __future__ import annotations

from typing import Dict


PARAMETER_DOCS: Dict[str, Dict[str, str]] = {
    "max_speed": {
        "definition": "Distance maximale parcourue par seconde par une creature.",
        "role": "Controle la capacite d'exploration, de fuite et de poursuite.",
        "expected_effect": "Une vitesse plus elevee augmente les rencontres et les couts de deplacement.",
    },
    "vision_range": {
        "definition": "Distance maximale a laquelle une creature peut detecter une cible.",
        "role": "Determine l'information locale disponible pour les decisions.",
        "expected_effect": "Une vision longue favorise l'anticipation, la fuite et la chasse.",
    },
    "vision_angle_deg": {
        "definition": "Ouverture angulaire du cone de perception, exprimee en degres.",
        "role": "Modele une perception directionnelle plutot qu'omnidirectionnelle.",
        "expected_effect": "Un angle large augmente la detection mais reduit la contrainte directionnelle.",
    },
    "basal_metabolism": {
        "definition": "Energie perdue par seconde, meme sans mouvement.",
        "role": "Modele le cout energetique minimal de survie.",
        "expected_effect": "Un metabolisme eleve augmente le risque de famine.",
    },
    "movement_energy_cost": {
        "definition": "Energie perdue par unite de distance parcourue.",
        "role": "Relie le comportement spatial au bilan energetique.",
        "expected_effect": "Un cout eleve penalise exploration, fuite et chasse prolongee.",
    },
    "max_energy": {
        "definition": "Reserve energetique maximale d'une creature.",
        "role": "Borne l'accumulation apres alimentation.",
        "expected_effect": "Une reserve elevee amortit les periodes sans nourriture.",
    },
    "hunger_threshold": {
        "definition": "Niveau d'energie sous lequel la nourriture devient prioritaire.",
        "role": "Declenche la recherche alimentaire ou la chasse.",
        "expected_effect": "Un seuil haut rend les agents plus opportunistes et moins exploratoires.",
    },
    "reproduction_threshold": {
        "definition": "Niveau d'energie minimal pour autoriser une reproduction.",
        "role": "Reserve la reproduction aux individus energetiquement viables.",
        "expected_effect": "Un seuil haut reduit les naissances mais favorise des parents moins epuises.",
    },
    "reproduction_cost": {
        "definition": "Energie retiree au parent lors d'une naissance.",
        "role": "Modele le compromis entre croissance de population et survie individuelle.",
        "expected_effect": "Un cout eleve reduit les reproductions successives.",
    },
    "reproduction_cooldown": {
        "definition": "Temps minimal entre deux reproductions du meme individu.",
        "role": "Evite une croissance instantanee non realiste.",
        "expected_effect": "Un cooldown long ralentit la croissance demographique.",
    },
    "max_age": {
        "definition": "Age maximal avant mort par vieillesse.",
        "role": "Introduit un renouvellement independant de la famine et de la predation.",
        "expected_effect": "Un age maximal court reduit la stabilite des populations.",
    },
    "flee_distance": {
        "definition": "Distance a laquelle un predateur visible declenche la fuite d'un herbivore.",
        "role": "Modele une zone de danger comportementale.",
        "expected_effect": "Une distance longue augmente l'evitement mais peut accroitre le cout energetique.",
    },
    "attack_range": {
        "definition": "Distance maximale pour qu'un predateur capture une proie.",
        "role": "Transforme une poursuite reussie en evenement de predation.",
        "expected_effect": "Une portee longue augmente le taux de predation.",
    },
    "food_energy_gain": {
        "definition": "Energie gagnee lorsqu'une nourriture est consommee.",
        "role": "Relie alimentation, survie et reproduction.",
        "expected_effect": "Un gain eleve favorise la survie et la reproduction.",
    },
    "environment.zones": {
        "definition": "Zones rectangulaires qui modifient localement vitesse, cout energetique, repousse ou transmission; les multiplicateurs exposes sont bornes de 0 a 10 ou de >0 a 10 selon le parametre.",
        "role": "Modele des heterogeneites spatiales comme biomes, refuges ou zones hostiles.",
        "expected_effect": "Des zones favorables concentrent les populations; des zones couteuses fragmentent les trajectoires.",
    },
    "environment.obstacles": {
        "definition": "Rectangles bloquants que les creatures ne peuvent pas traverser.",
        "role": "Ajoute une structure spatiale au monde et perturbe les lignes de poursuite.",
        "expected_effect": "Les obstacles reduisent certaines rencontres et peuvent creer des refuges.",
    },
    "topology": {
        "definition": "Grille d'elevation continue de 0 a 1 pouvant representer vallees, cretes, collines et bassins.",
        "role": "Ajoute une structure topographique modifiable dans le sandbox.",
        "expected_effect": "Une carte plus rugueuse augmente les couts de deplacement sur les pentes et canalise les trajectoires.",
    },
    "topology.palette": {
        "definition": "Palette de couleurs utilisee pour representer visuellement l'elevation du terrain.",
        "role": "Adapte la lecture du relief au contexte pedagogique ou esthetique.",
        "expected_effect": "Aucun effet dynamique; seule la perception visuelle de la carte change.",
    },
    "seasons": {
        "definition": "Cycle temporel modifiant repousse, metabolisme, cout de mouvement et transmission.",
        "role": "Introduit une contrainte periodique sur l'ecosysteme.",
        "expected_effect": "Les saisons defavorables augmentent famine, extinction locale ou propagation de maladie.",
    },
    "disease": {
        "definition": "Modele epidemiologique simple avec infection par proximite, cout energetique et guerison.",
        "role": "Ajoute une pression sanitaire dependante de la densite et de la mobilite.",
        "expected_effect": "Une transmission elevee penalise les populations denses et accelere les effondrements.",
    },
    "mutation": {
        "definition": "Variation hereditaire aleatoire de certains traits au moment de la reproduction.",
        "role": "Modele une derive evolutive simplifiee sous contraintes ecologiques.",
        "expected_effect": "Des mutations fortes augmentent la diversite mais peuvent destabiliser la population.",
    },
}


METRIC_DOC_INTRO = (
    "Chaque metrique est definie pour expliquer une dynamique ecologique precise. "
    "Les metriques sans interpretation scientifique directe sont exclues."
)
