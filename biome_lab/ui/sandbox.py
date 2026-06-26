from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SandboxTool(str, Enum):
    SELECT = "select"
    ADD_PLANT = "add_plant"
    ADD_HERBIVORE = "add_herbivore"
    ADD_PREDATOR = "add_predator"
    ADD_OBSTACLE = "add_obstacle"
    CARVE_VALLEY = "carve_valley"
    RAISE_RIDGE = "raise_ridge"
    SMOOTH_TERRAIN = "smooth_terrain"
    ERASE = "erase"


TOOL_LABELS = {
    SandboxTool.SELECT: "Select",
    SandboxTool.ADD_PLANT: "Plant",
    SandboxTool.ADD_HERBIVORE: "Herb",
    SandboxTool.ADD_PREDATOR: "Pred",
    SandboxTool.ADD_OBSTACLE: "Obstacle",
    SandboxTool.CARVE_VALLEY: "Valley",
    SandboxTool.RAISE_RIDGE: "Ridge",
    SandboxTool.SMOOTH_TERRAIN: "Smooth",
    SandboxTool.ERASE: "Erase",
}


@dataclass
class SandboxState:
    active_tool: SandboxTool = SandboxTool.SELECT
    obstacle_width: float = 90.0
    obstacle_height: float = 58.0
    topology_brush_radius: float = 95.0
    topology_brush_strength: float = 0.08


TOPOLOGY_TOOLS = {
    SandboxTool.CARVE_VALLEY,
    SandboxTool.RAISE_RIDGE,
    SandboxTool.SMOOTH_TERRAIN,
}
