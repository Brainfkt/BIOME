from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Color = Tuple[int, int, int]


class ScientificCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ecological_role: str = Field(..., description="Role fonctionnel de l'espece dans l'ecosysteme.")
    morphological_traits: List[str] = Field(default_factory=list)
    sensory_traits: List[str] = Field(default_factory=list)
    energetic_traits: List[str] = Field(default_factory=list)
    reproductive_traits: List[str] = Field(default_factory=list)
    behavioral_rules: List[str] = Field(default_factory=list)
    rule_justification: List[str] = Field(default_factory=list)


class CreatureTraits(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str
    role: Literal["herbivore", "predator"]
    color: Color
    max_speed: float = Field(gt=0)
    vision_range: float = Field(gt=0)
    vision_angle_deg: float = Field(gt=0, le=360)
    basal_metabolism: float = Field(ge=0)
    movement_energy_cost: float = Field(ge=0)
    max_energy: float = Field(gt=0)
    hunger_threshold: float = Field(gt=0)
    reproduction_threshold: float = Field(gt=0)
    reproduction_cost: float = Field(gt=0)
    reproduction_cooldown: float = Field(gt=0)
    max_age: float = Field(gt=0)
    flee_distance: float = Field(ge=0)
    attack_range: float = Field(ge=0)
    food_energy_gain: float = Field(gt=0)
    science_card: ScientificCard

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Color) -> Color:
        if len(value) != 3:
            raise ValueError("color must contain exactly three RGB channels")
        if any(channel < 0 or channel > 255 for channel in value):
            raise ValueError("color channels must be between 0 and 255")
        return value

    @model_validator(mode="after")
    def validate_energy_thresholds(self) -> "CreatureTraits":
        if self.hunger_threshold >= self.max_energy:
            raise ValueError("hunger_threshold must be lower than max_energy")
        if self.reproduction_threshold > self.max_energy:
            raise ValueError("reproduction_threshold must be lower than or equal to max_energy")
        if self.reproduction_threshold <= self.hunger_threshold:
            raise ValueError("reproduction_threshold must be higher than hunger_threshold")
        if self.reproduction_cost >= self.reproduction_threshold:
            raise ValueError("reproduction_cost must be lower than reproduction_threshold")
        if self.role == "herbivore" and self.flee_distance <= 0:
            raise ValueError("herbivores require a positive flee_distance")
        if self.role == "predator" and self.attack_range <= 0:
            raise ValueError("predators require a positive attack_range")
        return self


class PlantConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_count: int = Field(ge=0)
    max_count: int = Field(gt=0)
    radius: float = Field(gt=0)
    energy: float = Field(gt=0)
    regrowth_per_second: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> "PlantConfig":
        if self.initial_count > self.max_count:
            raise ValueError("initial_count cannot be greater than max_count")
        return self


class ObstacleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "obstacle"
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    blocks_movement: bool = True


class EnvironmentZoneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "zone"
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    color: Color = (70, 106, 124)
    speed_multiplier: float = Field(gt=0)
    metabolism_multiplier: float = Field(gt=0)
    movement_cost_multiplier: float = Field(gt=0)
    plant_regrowth_multiplier: float = Field(ge=0)
    disease_transmission_multiplier: float = Field(ge=0)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Color) -> Color:
        if len(value) != 3:
            raise ValueError("color must contain exactly three RGB channels")
        if any(channel < 0 or channel > 255 for channel in value):
            raise ValueError("color channels must be between 0 and 255")
        return value


class EnvironmentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obstacles: List[ObstacleConfig] = Field(default_factory=list)
    zones: List[EnvironmentZoneConfig] = Field(default_factory=list)


class TopologyFeatureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "topology_feature"
    kind: Literal["valley", "ridge", "hill", "basin"]
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    strength: float = Field(gt=0, le=1)
    orientation_deg: float = 0.0


class MapTopologyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    palette: Literal["natural", "hydrology", "arid", "grayscale"] = "natural"
    grid_columns: int = Field(default=80, ge=8, le=512)
    grid_rows: int = Field(default=54, ge=8, le=512)
    base_elevation: float = Field(default=0.5, ge=0, le=1)
    movement_cost_per_slope: float = Field(default=0.75, ge=0)
    features: List[TopologyFeatureConfig] = Field(default_factory=list)


class SeasonPhaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    duration_fraction: float = Field(gt=0)
    plant_regrowth_multiplier: float = Field(ge=0)
    metabolism_multiplier: float = Field(gt=0)
    movement_cost_multiplier: float = Field(gt=0)
    disease_transmission_multiplier: float = Field(ge=0)


class SeasonConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    cycle_seconds: float = Field(default=120.0, gt=0)
    phases: List[SeasonPhaseConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_phases(self) -> "SeasonConfig":
        if self.enabled and not self.phases:
            raise ValueError("enabled seasons require at least one phase")
        if self.phases and sum(phase.duration_fraction for phase in self.phases) <= 0.0:
            raise ValueError("season phase durations must sum to a positive value")
        return self


class DiseaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    initial_infected: int = Field(default=0, ge=0)
    transmission_radius: float = Field(default=18.0, gt=0)
    transmission_probability_per_second: float = Field(default=0.05, ge=0)
    energy_drain_per_second: float = Field(default=0.2, ge=0)
    mortality_probability_per_second: float = Field(default=0.0, ge=0)
    recovery_seconds: float = Field(default=30.0, gt=0)


class MutationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    probability: float = Field(default=0.03, ge=0, le=1)
    strength: float = Field(default=0.08, ge=0, le=1)
    min_trait_multiplier: float = Field(default=0.5, gt=0)
    max_trait_multiplier: float = Field(default=1.5, gt=0)
    mutable_traits: List[str] = Field(
        default_factory=lambda: [
            "max_speed",
            "vision_range",
            "vision_angle_deg",
            "basal_metabolism",
            "movement_energy_cost",
            "food_energy_gain",
        ]
    )

    @model_validator(mode="after")
    def validate_trait_bounds(self) -> "MutationConfig":
        if self.min_trait_multiplier > self.max_trait_multiplier:
            raise ValueError("min_trait_multiplier cannot exceed max_trait_multiplier")
        return self


class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    world_width: int = Field(gt=200)
    world_height: int = Field(gt=200)
    initial_herbivores: int = Field(ge=0)
    initial_predators: int = Field(ge=0)
    max_creatures: int = Field(gt=0)
    fixed_dt: float = Field(gt=0, le=0.25)
    metrics_sample_interval: float = Field(gt=0)
    metrics_window_seconds: float = Field(gt=0)
    seed: int
    plant: PlantConfig
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    topology: MapTopologyConfig = Field(default_factory=MapTopologyConfig)
    seasons: SeasonConfig = Field(default_factory=SeasonConfig)
    disease: DiseaseConfig = Field(default_factory=DiseaseConfig)
    mutation: MutationConfig = Field(default_factory=MutationConfig)
    herbivore_radius: float = Field(default=6.0, gt=0)
    predator_radius: float = Field(default=7.5, gt=0)
    creature_turn_rate_deg: float = Field(default=220.0, gt=0)
    boundary_bounce: float = Field(default=0.45, ge=0, le=1)
    plant_interaction_margin: float = Field(default=2.0, ge=0)
    predator_attack_margin: float = Field(default=6.0, ge=0)
    reproduction_spawn_radius: float = Field(default=18.0, ge=0)
    initial_energy_min_fraction: float = Field(default=0.55, ge=0, le=1)
    initial_energy_max_fraction: float = Field(default=0.88, ge=0, le=1)
    birth_energy_min_fraction: float = Field(default=0.35, ge=0, le=1)
    birth_energy_max_fraction: float = Field(default=0.55, ge=0, le=1)

    @model_validator(mode="after")
    def validate_energy_fractions(self) -> "SimulationConfig":
        if self.initial_energy_min_fraction > self.initial_energy_max_fraction:
            raise ValueError("initial_energy_min_fraction cannot exceed initial_energy_max_fraction")
        if self.birth_energy_min_fraction > self.birth_energy_max_fraction:
            raise ValueError("birth_energy_min_fraction cannot exceed birth_energy_max_fraction")
        return self


class ExperimentProtocol(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_question: str
    hypothesis: str
    independent_variable: str
    dependent_variables: List[str]
    constant_parameters: List[str]
    duration_seconds: float = Field(gt=0)
    seed: int
    repetitions: int = Field(gt=0)
    notes: Optional[str] = None


class BiomeLabPreset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    name: str
    simulation: SimulationConfig
    herbivore: CreatureTraits
    predator: CreatureTraits
    protocol: ExperimentProtocol

    @classmethod
    def from_json_path(cls, path: Path) -> "BiomeLabPreset":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
