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

