from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pygame

from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.exports.service import ExportService
from biome_lab.rendering import colors
from biome_lab.rendering.renderer import Renderer
from biome_lab.simulation.engine import SimulationEngine
from biome_lab.ui.controls import Button, ToggleButton
from biome_lab.ui.inspector import draw_inspector
from biome_lab.ui.panels import draw_death_chart_panel, draw_species_config, draw_stats_panel
from biome_lab.ui.sandbox import TOOL_LABELS, TOPOLOGY_TOOLS, SandboxState, SandboxTool


class BiomeLabApp:
    def __init__(self, preset: BiomeLabPreset) -> None:
        pygame.init()
        pygame.display.set_caption("Biome Lab")
        self.screen = pygame.display.set_mode((1560, 920), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 17)
        self.small_font = pygame.font.SysFont("Arial", 13)
        self.tiny_font = pygame.font.SysFont("Arial", 11)
        self.engine = SimulationEngine(preset)
        self.renderer = Renderer(self.small_font, self.tiny_font)
        self.export_service = ExportService(Path("exports"))
        self.show_vision = False
        self.show_states = True
        self.death_chart_mode = "species"
        self.selected_id: Optional[int] = None
        self.sandbox = SandboxState()
        self.camera_zoom = 1.0
        self.camera_pan = np.zeros(2, dtype=float)
        self._panning = False
        self.buttons: List[Button] = []
        self.export_message = ""
        self.running = True

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(120) / 1000.0
            layout = self._layout()
            self._rebuild_buttons(layout["controls"])
            self._handle_events(layout)
            self.engine.update(dt)
            self._draw(layout)
        pygame.quit()

    def _layout(self) -> Dict[str, pygame.Rect]:
        width, height = self.screen.get_size()
        controls_h = 116
        margin = 10
        left_w = 330
        right_w = 390
        world_rect = pygame.Rect(
            left_w + margin,
            margin,
            max(260, width - left_w - right_w - margin * 2),
            max(260, height - controls_h - margin * 2),
        )
        left_rect = pygame.Rect(margin, margin, left_w - margin * 2, height - controls_h - margin * 2)
        right_rect = pygame.Rect(width - right_w + margin, margin, right_w - margin * 2, height - controls_h - margin * 2)
        left_top_h = int(left_rect.height * 0.55)
        right_top_h = int(right_rect.height * 0.58)
        return {
            "world": world_rect,
            "species": pygame.Rect(left_rect.x, left_rect.y, left_rect.width, left_top_h - 5),
            "inspector": pygame.Rect(left_rect.x, left_rect.y + left_top_h + 5, left_rect.width, left_rect.height - left_top_h - 5),
            "stats": pygame.Rect(right_rect.x, right_rect.y, right_rect.width, right_top_h - 5),
            "death_chart": pygame.Rect(right_rect.x, right_rect.y + right_top_h + 5, right_rect.width, right_rect.height - right_top_h - 5),
            "controls": pygame.Rect(margin, height - controls_h + 8, width - margin * 2, controls_h - 16),
        }

    def _rebuild_buttons(self, controls_rect: pygame.Rect) -> None:
        y = controls_rect.y + 12
        x = controls_rect.x + 12
        specs = [
            ("Pause" if not self.engine.paused else "Play", self.engine.toggle_pause, 84),
            ("Reset", self._reset, 84),
            ("Speed -", lambda: self.engine.adjust_speed(0.75), 92),
            ("Speed +", lambda: self.engine.adjust_speed(1.25), 92),
        ]
        self.buttons = []
        for label, callback, width in specs:
            self.buttons.append(Button(pygame.Rect(x, y, width, 36), label, callback))
            x += width + 10
        self.buttons.append(
            ToggleButton(
                pygame.Rect(x, y, 94, 36),
                "Vision",
                lambda: self.show_vision,
                self._toggle_vision,
            )
        )
        x += 104
        self.buttons.append(
            ToggleButton(
                pygame.Rect(x, y, 94, 36),
                "States",
                lambda: self.show_states,
                self._toggle_states,
            )
        )
        x += 104
        death_label = "Morts: espece" if self.death_chart_mode == "species" else "Morts: cause"
        self.buttons.append(Button(pygame.Rect(x, y, 128, 36), death_label, self._toggle_death_chart_mode))
        x += 138
        self.buttons.append(Button(pygame.Rect(x, y, 94, 36), "Export", self._export))
        x += 104
        self.buttons.append(Button(pygame.Rect(x, y, 94, 36), "Save", self._save_sandbox_state))
        x += 104
        self.buttons.append(Button(pygame.Rect(x, y, 94, 36), "View", self._reset_camera))

        y += 44
        x = controls_rect.x + 12
        for tool in SandboxTool:
            label = TOOL_LABELS[tool]
            width = max(76, len(label) * 10 + 24)
            self.buttons.append(
                ToggleButton(
                    pygame.Rect(x, y, width, 30),
                    label,
                    lambda tool=tool: self.sandbox.active_tool == tool,
                    lambda tool=tool: self._set_tool(tool),
                )
            )
            x += width + 8

    def _handle_events(self, layout: Dict[str, pygame.Rect]) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.engine.toggle_pause()
                elif event.key == pygame.K_r:
                    self._reset()
                elif event.key == pygame.K_m:
                    self._toggle_death_chart_mode()
                elif event.key == pygame.K_ESCAPE:
                    self._set_tool(SandboxTool.SELECT)
                elif event.key == pygame.K_1:
                    self._set_tool(SandboxTool.SELECT)
                elif event.key == pygame.K_2:
                    self._set_tool(SandboxTool.ADD_PLANT)
                elif event.key == pygame.K_3:
                    self._set_tool(SandboxTool.ADD_HERBIVORE)
                elif event.key == pygame.K_4:
                    self._set_tool(SandboxTool.ADD_PREDATOR)
                elif event.key == pygame.K_5:
                    self._set_tool(SandboxTool.ADD_OBSTACLE)
                elif event.key == pygame.K_6:
                    self._set_tool(SandboxTool.ERASE)
                elif event.key == pygame.K_7:
                    self._set_tool(SandboxTool.CARVE_VALLEY)
                elif event.key == pygame.K_8:
                    self._set_tool(SandboxTool.RAISE_RIDGE)
                elif event.key == pygame.K_9:
                    self._set_tool(SandboxTool.SMOOTH_TERRAIN)
            if event.type == pygame.MOUSEWHEEL and layout["world"].collidepoint(pygame.mouse.get_pos()):
                self._zoom_camera(event.y)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (2, 3):
                if layout["world"].collidepoint(event.pos):
                    self._panning = True
            if event.type == pygame.MOUSEBUTTONUP and event.button in (2, 3):
                self._panning = False
            if event.type == pygame.MOUSEMOTION and self._panning:
                self.camera_pan += np.array(event.rel, dtype=float)
            if event.type == pygame.MOUSEMOTION and not self._panning:
                if layout["world"].collidepoint(event.pos) and event.buttons[0]:
                    if self.sandbox.active_tool in TOPOLOGY_TOOLS:
                        self._handle_world_click(event.pos, layout["world"])
            handled = False
            for button in self.buttons:
                if button.handle_event(event):
                    handled = True
                    break
            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if layout["world"].collidepoint(event.pos):
                    self._handle_world_click(event.pos, layout["world"])

    def _handle_world_click(self, pos, world_rect: pygame.Rect) -> None:
        world = self.engine.world
        self.renderer.configure_view(
            world_rect,
            world.config.world_width,
            world.config.world_height,
            self.camera_zoom,
            self.camera_pan,
        )
        world_pos = self.renderer.screen_to_world(pos)
        tool = self.sandbox.active_tool
        if tool == SandboxTool.SELECT:
            self._select_at(pos, world_rect)
        elif tool == SandboxTool.ADD_PLANT:
            world.spawn_plant(world_pos)
            world.refresh_indices()
        elif tool == SandboxTool.ADD_HERBIVORE:
            creature = world.spawn_creature("herbivore", world_pos, initial=True)
            self.selected_id = creature.id
            world.refresh_indices()
        elif tool == SandboxTool.ADD_PREDATOR:
            creature = world.spawn_creature("predator", world_pos, initial=True)
            self.selected_id = creature.id
            world.refresh_indices()
        elif tool == SandboxTool.ADD_OBSTACLE:
            world.add_obstacle_rect(
                world_pos,
                width=self.sandbox.obstacle_width,
                height=self.sandbox.obstacle_height,
            )
        elif tool in TOPOLOGY_TOOLS:
            world.apply_topology_brush(
                world_pos,
                radius=self.sandbox.topology_brush_radius,
                strength=self.sandbox.topology_brush_strength,
                mode=self._topology_mode(tool),
            )
        elif tool == SandboxTool.ERASE:
            removed = world.remove_entity_at(world_pos, radius=max(16.0 / max(self.renderer.scale, 1e-8), 14.0))
            if removed:
                self.selected_id = None

    def _topology_mode(self, tool: SandboxTool) -> str:
        if tool == SandboxTool.CARVE_VALLEY:
            return "valley"
        if tool == SandboxTool.RAISE_RIDGE:
            return "ridge"
        if tool == SandboxTool.SMOOTH_TERRAIN:
            return "smooth"
        raise ValueError("tool is not a topology tool: %s" % tool)

    def _select_at(self, pos, world_rect: pygame.Rect) -> None:
        world = self.engine.world
        self.renderer.configure_view(
            world_rect,
            world.config.world_width,
            world.config.world_height,
            self.camera_zoom,
            self.camera_pan,
        )
        world_pos = self.renderer.screen_to_world(pos)
        creatures = world.living_creatures()
        if not creatures:
            self.selected_id = None
            return
        nearest = min(creatures, key=lambda creature: creature.distance_to_position(world_pos))
        threshold = max(12.0 / max(self.renderer.scale, 1e-8), 14.0)
        self.selected_id = nearest.id if nearest.distance_to_position(world_pos) <= threshold else None

    def _reset(self) -> None:
        self.engine.reset()
        self.selected_id = None
        self.export_message = ""

    def _toggle_vision(self) -> None:
        self.show_vision = not self.show_vision

    def _toggle_states(self) -> None:
        self.show_states = not self.show_states

    def _toggle_death_chart_mode(self) -> None:
        self.death_chart_mode = "cause" if self.death_chart_mode == "species" else "species"

    def _set_tool(self, tool: SandboxTool) -> None:
        self.sandbox.active_tool = tool

    def _reset_camera(self) -> None:
        self.camera_zoom = 1.0
        self.camera_pan = np.zeros(2, dtype=float)

    def _zoom_camera(self, wheel_delta: int) -> None:
        factor = 1.12 if wheel_delta > 0 else 1.0 / 1.12
        self.camera_zoom = float(np.clip(self.camera_zoom * factor, 0.35, 6.0))

    def _export(self) -> None:
        self.engine.metrics.sample(self.engine.world, force=True)
        try:
            result = self.export_service.export_all(self.engine.preset, self.engine.metrics)
            self.export_message = "Export: %s" % result.metrics_path.name
        except Exception as exc:
            self.export_message = "Export failed: %s" % exc

    def _save_sandbox_state(self) -> None:
        output_dir = Path("exports")
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = output_dir / ("%s_sandbox_state.json" % stamp)
        payload = {
            "preset": self.engine.preset.model_dump(mode="json"),
            "world": self.engine.world.to_state_dict(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.export_message = "Saved: %s" % path.name

    def _draw(self, layout: Dict[str, pygame.Rect]) -> None:
        self.screen.fill(colors.BACKGROUND)
        self.renderer.draw(
            self.screen,
            self.engine.world,
            layout["world"],
            self.show_vision,
            self.show_states,
            self.selected_id,
            self.camera_zoom,
            self.camera_pan,
        )
        draw_species_config(self.screen, layout["species"], self.font, self.small_font, self.engine.preset)
        selected = self.engine.world.find_creature(self.selected_id) if self.selected_id is not None else None
        draw_inspector(self.screen, layout["inspector"], self.font, self.small_font, selected)
        draw_stats_panel(self.screen, layout["stats"], self.font, self.small_font, self.engine.metrics.latest() or {})
        draw_death_chart_panel(
            self.screen,
            layout["death_chart"],
            self.font,
            self.small_font,
            self.engine.metrics,
            self.death_chart_mode,
        )
        self._draw_controls(layout["controls"])
        pygame.display.flip()

    def _draw_controls(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, colors.PANEL_BG, rect)
        pygame.draw.rect(self.screen, colors.PANEL_BORDER, rect, 1)
        for button in self.buttons:
            button.draw(self.screen, self.font)
        status = "t=%.1fs  speed=%.2fx  agents=%s" % (
            self.engine.world.time,
            self.engine.speed_multiplier,
            self.engine.world.living_creature_count(),
        )
        status = "%s  tool=%s  topo=%s  zoom=%.2fx  fps=%.0f" % (
            status,
            TOOL_LABELS[self.sandbox.active_tool],
            "on" if self.engine.world.topology_enabled() else "off",
            self.camera_zoom,
            self.clock.get_fps(),
        )
        status_surf = self.small_font.render(status, True, colors.TEXT_MUTED)
        self.screen.blit(status_surf, (rect.right - status_surf.get_width() - 16, rect.y + 12))
        if self.export_message:
            msg = self.small_font.render(self.export_message, True, colors.ACCENT)
            self.screen.blit(msg, (rect.right - msg.get_width() - 16, rect.y + 34))
