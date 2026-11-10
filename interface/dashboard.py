"""
Pygame Dashboard - Main GUI window for UAV Target Tracking Simulation.

Layout:
  [Left: Simulation View] [Right Top: Telemetry] [Right Bottom: Control Panel]

Integrates: draw_objects, telemetry, control_panel, simulation_engine, interactive_target.
"""

import pygame
import sys
import os
import time
import math
import numpy as np
import yaml
from typing import Optional, Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.simulation_engine import SimulationEngine
from simulation.target_scenario import get_scenario_config, get_all_scenario_names
from simulation.interactive_target import InteractiveTargetController
from evaluation.estimation_evaluation import EstimationEvaluator
from evaluation.tracking_evaluation import TrackingEvaluator
from interface.draw_objects import (
    draw_grid, draw_uav, draw_target, draw_trail, draw_estimated_position,
    draw_fov, draw_velocity_vector, draw_distance_line, draw_desired_point,
    draw_measurement_point, draw_covariance_ellipse, world_to_screen,
    COLOR_UAV, COLOR_TARGET, COLOR_EKF_ESTIMATE, COLOR_UKF_ESTIMATE,
    COLOR_GT_TRAIL, COLOR_UAV_TRAIL, COLOR_BG, COLOR_WHITE, COLOR_TEXT,
    COLOR_VELOCITY
)
from interface.telemetry import TelemetryPanel
from interface.control_panel import ControlPanel


class Dashboard:
    """Main Pygame dashboard window."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        disp = self.config.get('display', {})
        self.win_w = disp.get('window_width', 1280)
        self.win_h = disp.get('window_height', 680)
        self.target_fps = disp.get('fps', 60)

        self.world_w = self.config.get('simulation', {}).get('world_width', 1200)
        self.world_h = self.config.get('simulation', {}).get('world_height', 800)

        # Layout rectangles (will be refined in _init_pygame based on actual display)
        panel_w = 230
        telemetry_w = 210
        sim_w = self.win_w - panel_w - telemetry_w
        self.sim_rect = pygame.Rect(0, 0, sim_w, self.win_h)
        self.telemetry_rect = pygame.Rect(sim_w, 0, telemetry_w, self.win_h)
        self.panel_rect = pygame.Rect(sim_w + telemetry_w, 0, panel_w, self.win_h)

        # State
        self.running = False
        self.sim_running = False
        self.sim_paused = False

        # Engine
        self.engine: Optional[SimulationEngine] = None
        self.interactive_ctrl: Optional[InteractiveTargetController] = None

        # Evaluators
        self.est_eval = EstimationEvaluator()
        self.track_eval: Optional[TrackingEvaluator] = None

        # Trails
        self.target_trail: List[Tuple[float, float]] = []
        self.uav_trail: List[Tuple[float, float]] = []
        self.ekf_trail: List[Tuple[float, float]] = []
        self.ukf_trail: List[Tuple[float, float]] = []
        self.measurement_points: List[Tuple[float, float]] = []

        # Current step data
        self.current_step = None

        # Realtime chart data
        self.chart_errors: List[float] = []
        self.chart_distances: List[float] = []

        # Pygame objects (initialized in run())
        self.screen = None
        self.clock = None
        self.font = None

    def _init_pygame(self):
        pygame.init()
        # Auto-detect screen resolution to guarantee GUI fits on screen without overflow
        info = pygame.display.Info()
        screen_w = info.current_w
        screen_h = info.current_h

        max_w = max(800, screen_w - 30)
        max_h = max(550, screen_h - 75)
        self.win_w = min(self.win_w, max_w)
        self.win_h = min(self.win_h, max_h)

        # Recalculate layout
        panel_w = 230
        telemetry_w = 210
        sim_w = max(400, self.win_w - panel_w - telemetry_w)
        self.sim_rect = pygame.Rect(0, 0, sim_w, self.win_h)
        self.telemetry_rect = pygame.Rect(sim_w, 0, telemetry_w, self.win_h)
        self.panel_rect = pygame.Rect(sim_w + telemetry_w, 0, panel_w, self.win_h)

        self.screen = pygame.display.set_mode((self.win_w, self.win_h))
        pygame.display.set_caption("UAV Target Tracking 2D Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 12)

        self.telemetry_panel = TelemetryPanel(self.telemetry_rect)
        self.control_panel = ControlPanel(self.panel_rect)

        # Wire button callbacks
        self.control_panel.buttons['start'].callback = self._on_start
        self.control_panel.buttons['pause'].callback = self._on_pause
        self.control_panel.buttons['reset'].callback = self._on_reset
        self.control_panel.buttons['save'].callback = self._on_save

    def _build_scenario_config(self, panel_state: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Build scenario config from panel state."""
        scenario_idx = panel_state['scenario']
        scenario_id = scenario_idx + 1
        scfg = get_scenario_config(scenario_id)
        is_interactive = scfg.get('is_interactive', False) or (scenario_id >= 8)

        if is_interactive:
            scfg['duration'] = 999.0  # Run continuously in GUI interactive mode
            if scenario_id != 12:
                scfg['target']['trajectory_type'] = 'interactive'
            # For scenario 12, preserve its autonomous evasive maneuvers so it runs automatically
            interactive_mode = scfg.get('interactive_mode', panel_state.get('interactive_mode', 'click'))
        else:
            # Override trajectory type if selected from dropdown on baseline
            traj = panel_state['trajectory']
            if traj != 'straight' and scenario_idx == 0:
                scfg['target']['trajectory_type'] = traj

        # Apply panel overrides
        scfg.setdefault('camera', {})
        if panel_state['noise_on']:
            scfg['camera']['noise_range_std'] = panel_state['noise_level']
            scfg['camera']['noise_bearing_std'] = panel_state['noise_level'] * 0.015
        else:
            scfg['camera']['noise_range_std'] = 0.01
            scfg['camera']['noise_bearing_std'] = 0.001

        if panel_state['dropout_on']:
            scfg.setdefault('dropout_events', [])
            if not scfg.get('dropout_events'):
                scfg['dropout_events'] = [{'start': 8.0, 'duration': panel_state['dropout_duration']}]

        if panel_state['delay_on']:
            scfg['camera']['delay'] = panel_state['delay_seconds']

        scfg['target']['max_speed'] = panel_state.get('target_speed', scfg['target'].get('max_speed', 60.0))

        return scfg, is_interactive

    def _on_start(self):
        """Start/restart simulation."""
        panel_state = self.control_panel.get_state()
        scfg, is_interactive = self._build_scenario_config(panel_state)

        # Configure filter mode
        self.config['filter'] = self.config.get('filter', {})
        self.config['filter']['selected'] = panel_state['filter']

        # Create engine
        self.engine = SimulationEngine(self.config)
        self.engine.setup(scfg)
        self.engine.filter_mode = panel_state['filter']

        # Update PID params
        if self.engine.pid:
            self.engine.pid.kp = panel_state['kp']
            self.engine.pid.ki = panel_state['ki']
            self.engine.pid.kd = panel_state['kd']
            self.engine.pid.desired_distance = panel_state['desired_distance']

        # Interactive controller
        if is_interactive:
            self.interactive_ctrl = InteractiveTargetController(
                self.engine.target_model,
                max_speed=panel_state['target_speed'],
                base_speed=panel_state['target_speed'] * 0.5,
            )
            imode = scfg.get('interactive_mode', panel_state.get('interactive_mode', 'click'))
            self.interactive_ctrl.set_control_mode(imode)
            if panel_state.get('recording'):
                self.interactive_ctrl.start_recording(0.0)
        else:
            self.interactive_ctrl = None

        # Reset evaluators
        self.est_eval.reset()
        self.track_eval = TrackingEvaluator(panel_state['desired_distance'])

        # Clear trails
        self.target_trail.clear()
        self.uav_trail.clear()
        self.ekf_trail.clear()
        self.ukf_trail.clear()
        self.measurement_points.clear()
        self.chart_errors.clear()
        self.chart_distances.clear()

        self.sim_running = True
        self.sim_paused = False
        self.control_panel.buttons['pause'].active = False

    def _on_pause(self):
        self.sim_paused = self.control_panel.buttons['pause'].active

    def _on_reset(self):
        self.sim_running = False
        self.sim_paused = False
        self.engine = None
        self.interactive_ctrl = None
        self.target_trail.clear()
        self.uav_trail.clear()
        self.ekf_trail.clear()
        self.ukf_trail.clear()
        self.measurement_points.clear()
        self.chart_errors.clear()
        self.chart_distances.clear()
        self.current_step = None
        self.control_panel.buttons['pause'].active = False

    def _on_save(self):
        if self.engine and self.engine.history:
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "results", "data", f"run_{ts}")
            self.engine.save_results(out_dir)
            metrics = self.engine.compute_metrics()
            if self.est_eval:
                metrics.update(self.est_eval.compute_metrics())
            if self.track_eval:
                metrics.update(self.track_eval.compute_metrics())
            self.engine.save_metrics(out_dir, metrics)
            # Save interactive recording
            if self.interactive_ctrl and self.interactive_ctrl.recording:
                self.interactive_ctrl.stop_recording()
                self.interactive_ctrl.save_recording(os.path.join(out_dir, "recording.json"))
            print(f"Results saved to {out_dir}")

    def _handle_interactive_input(self, event: pygame.event.Event):
        """Handle mouse/keyboard for interactive target control."""
        if not self.interactive_ctrl or not self.sim_running:
            return

        t = self.engine.time if self.engine else 0.0

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.sim_rect.collidepoint(event.pos):
                # Convert screen to world coordinates
                wx = (event.pos[0] - self.sim_rect.x) / self.sim_rect.width * self.world_w
                wy = (event.pos[1] - self.sim_rect.y) / self.sim_rect.height * self.world_h
                self.interactive_ctrl.handle_mouse_click(wx, wy, t)

        elif event.type == pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[0] and self.sim_rect.collidepoint(event.pos):
                wx = (event.pos[0] - self.sim_rect.x) / self.sim_rect.width * self.world_w
                wy = (event.pos[1] - self.sim_rect.y) / self.sim_rect.height * self.world_h
                self.interactive_ctrl.handle_mouse_drag(wx, wy, t)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.interactive_ctrl.handle_mouse_release(t)

        elif event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_w: 'w', pygame.K_a: 'a', pygame.K_s: 's', pygame.K_d: 'd',
                pygame.K_LSHIFT: 'shift', pygame.K_RSHIFT: 'shift',
                pygame.K_SPACE: 'space', pygame.K_r: 'r',
            }
            if event.key in key_map:
                self.interactive_ctrl.handle_key_press(key_map[event.key], t)
            elif event.key == pygame.K_c:
                self.interactive_ctrl.clear_waypoints(t)

        elif event.type == pygame.KEYUP:
            key_map = {
                pygame.K_w: 'w', pygame.K_a: 'a', pygame.K_s: 's', pygame.K_d: 'd',
                pygame.K_LSHIFT: 'shift', pygame.K_RSHIFT: 'shift',
                pygame.K_SPACE: 'space',
            }
            if event.key in key_map:
                self.interactive_ctrl.handle_key_release(key_map[event.key], t)

    def _sim_tick(self):
        """Advance simulation by one step."""
        if not self.engine or not self.sim_running or self.sim_paused:
            return

        step = self.engine.simulation_step()
        self.current_step = step

        # Update trails
        if step.target_gt:
            self.target_trail.append((step.target_gt.x, step.target_gt.y))
        if step.uav_state:
            self.uav_trail.append((step.uav_state.x, step.uav_state.y))
        if step.ekf_estimate:
            self.ekf_trail.append((step.ekf_estimate['x'], step.ekf_estimate['y']))
        if step.ukf_estimate:
            self.ukf_trail.append((step.ukf_estimate['x'], step.ukf_estimate['y']))
        if step.measurement and step.measurement.detected and step.measurement.data is not None:
            if step.measurement.measurement_type == 'xy':
                self.measurement_points.append((step.measurement.data[0], step.measurement.data[1]))
            elif step.uav_state:
                # Convert range/bearing back to XY for display
                r, theta = step.measurement.data
                heading = self.engine.uav_model.state.heading
                mx = step.uav_state.x + r * math.cos(theta + heading)
                my = step.uav_state.y + r * math.sin(theta + heading)
                self.measurement_points.append((mx, my))

        # Limit trail length
        max_trail = 300
        if len(self.target_trail) > max_trail:
            self.target_trail = self.target_trail[-max_trail:]
        if len(self.uav_trail) > max_trail:
            self.uav_trail = self.uav_trail[-max_trail:]
        if len(self.ekf_trail) > max_trail:
            self.ekf_trail = self.ekf_trail[-max_trail:]
        if len(self.ukf_trail) > max_trail:
            self.ukf_trail = self.ukf_trail[-max_trail:]
        if len(self.measurement_points) > max_trail:
            self.measurement_points = self.measurement_points[-max_trail:]

        # Update evaluators
        self.est_eval.add_step(step)
        if self.track_eval:
            self.track_eval.add_step(step)

        # Chart data
        self.chart_errors.append(step.estimation_error_ekf or step.estimation_error_ukf or 0)
        self.chart_distances.append(step.tracking_distance)

        # Update live PID params from sliders
        panel_state = self.control_panel.get_state()
        if self.engine.pid:
            self.engine.pid.kp = panel_state['kp']
            self.engine.pid.ki = panel_state['ki']
            self.engine.pid.kd = panel_state['kd']
            self.engine.pid.desired_distance = panel_state['desired_distance']
        if self.engine.camera:
            if panel_state['noise_on']:
                self.engine.camera.noise_multiplier = panel_state['noise_level'] / 2.0
            else:
                self.engine.camera.noise_multiplier = 0.01

        # Check if finished
        if self.engine.finished:
            self.sim_running = False

    def _draw_simulation(self):
        """Draw the simulation viewport."""
        # Background
        pygame.draw.rect(self.screen, COLOR_BG, self.sim_rect)
        draw_grid(self.screen, self.sim_rect, self.world_w, self.world_h, 50.0)

        # Border
        pygame.draw.rect(self.screen, (50, 55, 70), self.sim_rect, 1)

        if not self.engine or self.current_step is None:
            # Draw instructions
            font_big = pygame.font.SysFont("consolas", 20, bold=True)
            txt = font_big.render("Click START to begin simulation", True, (100, 110, 130))
            r = txt.get_rect(center=(self.sim_rect.centerx, self.sim_rect.centery))
            self.screen.blit(txt, r)
            return

        step = self.current_step
        ww, wh = self.world_w, self.world_h
        sr = self.sim_rect

        # FOV
        if self.engine.camera and step.uav_state:
            detected = step.measurement.detected if step.measurement else False
            draw_fov(self.screen, step.uav_state.x, step.uav_state.y,
                      step.uav_state.heading, self.engine.camera.fov_angle,
                      self.engine.camera.max_range, sr, ww, wh, detected)

        # Trails
        draw_trail(self.screen, self.target_trail, (100, 255, 100), sr, ww, wh)
        draw_trail(self.screen, self.uav_trail, (0, 140, 255), sr, ww, wh)
        if self.ekf_trail:
            draw_trail(self.screen, self.ekf_trail, COLOR_EKF_ESTIMATE, sr, ww, wh)
        if self.ukf_trail:
            draw_trail(self.screen, self.ukf_trail, COLOR_UKF_ESTIMATE, sr, ww, wh)

        # Measurement points (last N)
        for mp in self.measurement_points[-50:]:
            draw_measurement_point(self.screen, mp[0], mp[1], sr, ww, wh)

        # Distance line
        if step.target_gt and step.uav_state:
            draw_distance_line(self.screen, step.uav_state.x, step.uav_state.y,
                                step.target_gt.x, step.target_gt.y, sr, ww, wh)

        # Desired following point
        if step.desired_position is not None:
            draw_desired_point(self.screen, step.desired_position[0], step.desired_position[1],
                                sr, ww, wh)

        # Covariance ellipses
        if step.ekf_estimate and step.ekf_covariance is not None:
            draw_covariance_ellipse(self.screen, step.ekf_estimate['x'], step.ekf_estimate['y'],
                                     step.ekf_covariance, COLOR_EKF_ESTIMATE, sr, ww, wh)
        if step.ukf_estimate and step.ukf_covariance is not None:
            draw_covariance_ellipse(self.screen, step.ukf_estimate['x'], step.ukf_estimate['y'],
                                     step.ukf_covariance, COLOR_UKF_ESTIMATE, sr, ww, wh)

        # Estimated positions
        if step.ekf_estimate:
            draw_estimated_position(self.screen, step.ekf_estimate['x'], step.ekf_estimate['y'],
                                     COLOR_EKF_ESTIMATE, sr, ww, wh, "EKF")
        if step.ukf_estimate:
            draw_estimated_position(self.screen, step.ukf_estimate['x'], step.ukf_estimate['y'],
                                     COLOR_UKF_ESTIMATE, sr, ww, wh, "UKF")

        # Velocity vectors
        if step.target_gt:
            draw_velocity_vector(self.screen, step.target_gt.x, step.target_gt.y,
                                  step.target_gt.vx, step.target_gt.vy,
                                  (100, 255, 100), sr, ww, wh, 0.5)
        if step.uav_state:
            draw_velocity_vector(self.screen, step.uav_state.x, step.uav_state.y,
                                  step.uav_state.vx, step.uav_state.vy,
                                  COLOR_VELOCITY, sr, ww, wh, 0.5)

        # Target
        if step.target_gt:
            draw_target(self.screen, step.target_gt.x, step.target_gt.y, sr, ww, wh)

        # UAV
        if step.uav_state:
            draw_uav(self.screen, step.uav_state.x, step.uav_state.y,
                      step.uav_state.heading, sr, ww, wh)

        # Mini chart: tracking error
        self._draw_mini_chart(self.chart_distances, "Track Dist",
                               pygame.Rect(sr.x + 10, sr.bottom - 80, 200, 60),
                               (0, 180, 255))

        # Legend
        self._draw_legend()

        # Interactive mode label
        if self.interactive_ctrl:
            mode_font = pygame.font.SysFont("consolas", 14, bold=True)
            label = mode_font.render(f"INTERACTIVE: {self.interactive_ctrl.control_mode.upper()}", True, (255, 200, 0))
            self.screen.blit(label, (sr.x + 10, sr.y + 10))
            hint = self.font.render("Click/WASD to control target | C=clear waypoints", True, (180, 180, 180))
            self.screen.blit(hint, (sr.x + 10, sr.y + 28))

    def _draw_mini_chart(self, data: List[float], label: str,
                          rect: pygame.Rect, color: Tuple):
        """Draw a small real-time line chart."""
        if len(data) < 2:
            return
        # Background
        chart_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        chart_surf.fill((15, 15, 25, 180))
        
        pts = data[-rect.width:]
        if not pts:
            return
        max_val = max(pts) if max(pts) > 0 else 1
        min_val = min(pts)
        rng = max_val - min_val
        if rng < 1e-3:
            rng = 1.0

        points = []
        for i, v in enumerate(pts):
            px = int(i * rect.width / len(pts))
            py = rect.height - 5 - int((v - min_val) / rng * (rect.height - 10))
            points.append((px, py))

        if len(points) >= 2:
            pygame.draw.lines(chart_surf, color, False, points, 1)

        # Label
        lf = pygame.font.SysFont("consolas", 10)
        lt = lf.render(f"{label}: {pts[-1]:.1f}", True, (200, 200, 200))
        chart_surf.blit(lt, (4, 2))

        self.screen.blit(chart_surf, rect.topleft)

    def _draw_legend(self):
        """Draw color legend."""
        lx = self.sim_rect.right - 180
        ly = self.sim_rect.y + 10
        lf = pygame.font.SysFont("consolas", 10)
        items = [
            ((255, 60, 60), "Target (GT)"),
            ((0, 180, 255), "UAV"),
            ((100, 255, 100), "GT Trail"),
            ((255, 200, 0), "EKF Estimate"),
            ((200, 0, 255), "UKF Estimate"),
            ((255, 255, 100), "Measurement"),
            ((0, 255, 200), "Desired Point"),
        ]
        for color, text in items:
            pygame.draw.rect(self.screen, color, (lx, ly + 1, 10, 10))
            t = lf.render(text, True, (180, 180, 180))
            self.screen.blit(t, (lx + 14, ly))
            ly += 14

    def _build_telemetry_data(self) -> Dict[str, Any]:
        """Build telemetry data dict from current step."""
        data: Dict[str, Any] = {
            'time': 0, 'fps': 0, 'step': 0,
            'uav_x': 0, 'uav_y': 0, 'uav_vx': 0, 'uav_vy': 0, 'uav_speed': 0,
            'est_x': 0, 'est_y': 0, 'est_vx': 0, 'est_vy': 0,
            'tracking_distance': 0, 'desired_distance': 50,
            'camera_status': 'N/A',
            'filter_mode': 'ekf',
            'pid_ax': 0, 'pid_ay': 0,
        }

        if self.engine:
            data['time'] = self.engine.time
            data['step'] = self.engine.step_count
            data['filter_mode'] = self.engine.filter_mode
            if self.engine.pid:
                data['desired_distance'] = self.engine.pid.desired_distance

        data['fps'] = self.clock.get_fps() if self.clock else 0

        step = self.current_step
        if step:
            if step.uav_state:
                data.update({
                    'uav_x': step.uav_state.x, 'uav_y': step.uav_state.y,
                    'uav_vx': step.uav_state.vx, 'uav_vy': step.uav_state.vy,
                    'uav_speed': step.uav_state.speed(),
                })
            active_est = step.ekf_estimate or step.ukf_estimate
            if active_est:
                data.update({
                    'est_x': active_est['x'], 'est_y': active_est['y'],
                    'est_vx': active_est['vx'], 'est_vy': active_est['vy'],
                })
            data['tracking_distance'] = step.tracking_distance
            if step.measurement:
                data['camera_status'] = self.engine.camera.status if self.engine and self.engine.camera else 'N/A'
                if step.measurement.detected and step.measurement.data is not None:
                    if step.measurement.measurement_type == 'range_bearing':
                        data['measurement_r'] = step.measurement.data[0]
                        data['measurement_b'] = step.measurement.data[1]
            data['est_error_ekf'] = step.estimation_error_ekf if step.estimation_error_ekf else None
            data['est_error_ukf'] = step.estimation_error_ukf if step.estimation_error_ukf else None
            if step.pid_command is not None:
                data['pid_ax'] = step.pid_command[0]
                data['pid_ay'] = step.pid_command[1]

        return data

    def run(self):
        """Main GUI loop."""
        self._init_pygame()
        self.running = True

        while self.running:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        break
                    elif event.key == pygame.K_RETURN:
                        self._on_start()
                    elif event.key == pygame.K_SPACE and not self.interactive_ctrl:
                        self.control_panel.buttons['pause'].active = not self.control_panel.buttons['pause'].active
                        self._on_pause()
                    elif event.key == pygame.K_r and not self.interactive_ctrl:
                        self._on_reset()

                # Control panel events
                self.control_panel.handle_event(event)

                # Interactive input
                if self.interactive_ctrl and self.sim_running and not self.sim_paused:
                    self._handle_interactive_input(event)

            if not self.running:
                break

            # Simulation tick (multiple steps per frame for real-time)
            if self.sim_running and not self.sim_paused and self.engine:
                steps_per_frame = max(1, int(self.engine.dt * self.target_fps / 0.02))
                for _ in range(min(steps_per_frame, 5)):
                    if self.engine and self.engine.running:
                        self._sim_tick()

            # Draw
            self.screen.fill(COLOR_BG)
            self._draw_simulation()
            telemetry_data = self._build_telemetry_data()
            self.telemetry_panel.draw(self.screen, telemetry_data)
            self.control_panel.draw(self.screen)

            # Status bar
            if self.sim_running:
                status = "RUNNING" if not self.sim_paused else "PAUSED"
            elif self.engine and self.engine.finished:
                status = "FINISHED"
            else:
                status = "IDLE"
            st = self.font.render(f"Status: {status}", True, COLOR_TEXT)
            self.screen.blit(st, (5, self.win_h - 18))

            pygame.display.flip()
            self.clock.tick(self.target_fps)

        pygame.quit()


def run_dashboard(config_path: str = None):
    """Entry point for GUI mode."""
    config = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    else:
        # Try default
        default_cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
        if os.path.exists(default_cfg):
            with open(default_cfg, 'r') as f:
                config = yaml.safe_load(f) or {}

    dashboard = Dashboard(config)
    dashboard.run()


if __name__ == "__main__":
    run_dashboard()
