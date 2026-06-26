from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SandboxTool(str, Enum):
    SELECT = "select"
    ADD_PLANT = "add_plant"
    ADD_HERBIVORE = "add_herbivore"
    ADD_PREDATOR = "add_predator"
    ADD_OBSTACLE = "add_obstacle"
    ERASE = "erase"


TOOL_LABELS = {
    SandboxTool.SELECT: "Select",
    SandboxTool.ADD_PLANT: "Plant",
    SandboxTool.ADD_HERBIVORE: "Herb",
    SandboxTool.ADD_PREDATOR: "Pred",
    SandboxTool.ADD_OBSTACLE: "Obstacle",
    SandboxTool.ERASE: "Erase",
}


@dataclass
class SandboxState:
    active_tool: SandboxTool = SandboxTool.SELECT
    obstacle_width: float = 90.0
    obstacle_height: float = 58.0

