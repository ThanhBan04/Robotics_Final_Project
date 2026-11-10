"""
Telemetry Panel - Displays real-time system monitoring data.
"""

import pygame
from typing import Optional, Dict, Any


COLOR_PANEL_BG = (20, 22, 30)
COLOR_LABEL = (140, 150, 170)
COLOR_VALUE = (220, 230, 240)
COLOR_GOOD = (80, 220, 120)
COLOR_WARN = (255, 200, 60)
COLOR_BAD = (255, 70, 70)
COLOR_EKF = (255, 200, 0)
COLOR_UKF = (200, 0, 255)
COLOR_DIVIDER = (50, 55, 70)


class TelemetryPanel:
    """Displays real-time simulation telemetry data."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self.font = None
        self.font_small = None
        self.font_title = None
        self._initialized = False

    def _init_fonts(self):
        if not self._initialized:
            self.font = pygame.font.SysFont("consolas", 13)
            self.font_small = pygame.font.SysFont("consolas", 11)
            self.font_title = pygame.font.SysFont("consolas", 14, bold=True)
            self._initialized = True

    def draw(self, surface: pygame.Surface, sim_data: Dict[str, Any]):
        """Draw telemetry panel."""
        self._init_fonts()

        # Background
        pygame.draw.rect(surface, COLOR_PANEL_BG, self.rect)
        pygame.draw.rect(surface, COLOR_DIVIDER, self.rect, 1)

        x = self.rect.x + 10
        y = self.rect.y + 8
        line_h = 18
        section_gap = 8

        # Title
        self._draw_text(surface, "SYSTEM TELEMETRY", x, y, self.font_title, COLOR_VALUE)
        y += line_h + 4
        pygame.draw.line(surface, COLOR_DIVIDER, (x, y), (self.rect.right - 10, y))
        y += 6

        # Simulation info
        self._draw_label_value(surface, "Time", f"{sim_data.get('time', 0):.2f} s", x, y)
        y += line_h
        self._draw_label_value(surface, "FPS", f"{sim_data.get('fps', 0):.0f}", x, y)
        y += line_h
        self._draw_label_value(surface, "Step", f"{sim_data.get('step', 0)}", x, y)
        y += line_h + section_gap

        # UAV
        self._draw_text(surface, "— UAV —", x, y, self.font_small, COLOR_LABEL)
        y += line_h
        self._draw_label_value(surface, "X", f"{sim_data.get('uav_x', 0):.1f} m", x, y)
        y += line_h
        self._draw_label_value(surface, "Y", f"{sim_data.get('uav_y', 0):.1f} m", x, y)
        y += line_h
        self._draw_label_value(surface, "Vx", f"{sim_data.get('uav_vx', 0):.1f} m/s", x, y)
        y += line_h
        self._draw_label_value(surface, "Vy", f"{sim_data.get('uav_vy', 0):.1f} m/s", x, y)
        y += line_h
        speed = sim_data.get('uav_speed', 0)
        self._draw_label_value(surface, "Speed", f"{speed:.1f} m/s", x, y,
                                COLOR_WARN if speed > 80 else COLOR_VALUE)
        y += line_h + section_gap

        # Target (estimated)
        self._draw_text(surface, "— Target (Est.) —", x, y, self.font_small, COLOR_LABEL)
        y += line_h
        self._draw_label_value(surface, "X", f"{sim_data.get('est_x', 0):.1f} m", x, y)
        y += line_h
        self._draw_label_value(surface, "Y", f"{sim_data.get('est_y', 0):.1f} m", x, y)
        y += line_h
        self._draw_label_value(surface, "Vx", f"{sim_data.get('est_vx', 0):.1f} m/s", x, y)
        y += line_h
        self._draw_label_value(surface, "Vy", f"{sim_data.get('est_vy', 0):.1f} m/s", x, y)
        y += line_h + section_gap

        # Tracking
        self._draw_text(surface, "— Tracking —", x, y, self.font_small, COLOR_LABEL)
        y += line_h
        dist = sim_data.get('tracking_distance', 0)
        desired = sim_data.get('desired_distance', 50)
        err = abs(dist - desired)
        dist_color = COLOR_GOOD if err < desired * 0.15 else (COLOR_WARN if err < desired * 0.4 else COLOR_BAD)
        self._draw_label_value(surface, "Distance", f"{dist:.1f} m", x, y, dist_color)
        y += line_h
        self._draw_label_value(surface, "Desired", f"{desired:.1f} m", x, y)
        y += line_h
        self._draw_label_value(surface, "Error", f"{err:.1f} m", x, y, dist_color)
        y += line_h + section_gap

        # Camera
        self._draw_text(surface, "— Camera —", x, y, self.font_small, COLOR_LABEL)
        y += line_h
        status = sim_data.get('camera_status', 'N/A')
        sc = COLOR_GOOD if status == "Tracking" else (COLOR_WARN if status == "Delayed" else COLOR_BAD)
        self._draw_label_value(surface, "Status", status, x, y, sc)
        y += line_h

        if sim_data.get('measurement_r') is not None:
            self._draw_label_value(surface, "Range", f"{sim_data['measurement_r']:.1f} m", x, y)
            y += line_h
        if sim_data.get('measurement_b') is not None:
            self._draw_label_value(surface, "Bearing", f"{sim_data['measurement_b']:.3f} rad", x, y)
            y += line_h
        y += section_gap

        # Filter
        self._draw_text(surface, "— Filter —", x, y, self.font_small, COLOR_LABEL)
        y += line_h
        fmode = sim_data.get('filter_mode', 'ekf')
        fc = COLOR_EKF if fmode in ('ekf', 'both') else COLOR_UKF
        self._draw_label_value(surface, "Active", fmode.upper(), x, y, fc)
        y += line_h
        if sim_data.get('est_error_ekf') is not None:
            self._draw_label_value(surface, "EKF Err", f"{sim_data['est_error_ekf']:.2f} m", x, y, COLOR_EKF)
            y += line_h
        if sim_data.get('est_error_ukf') is not None:
            self._draw_label_value(surface, "UKF Err", f"{sim_data['est_error_ukf']:.2f} m", x, y, COLOR_UKF)
            y += line_h
        y += section_gap

        # PID
        self._draw_text(surface, "— PID —", x, y, self.font_small, COLOR_LABEL)
        y += line_h
        self._draw_label_value(surface, "Cmd Ax", f"{sim_data.get('pid_ax', 0):.2f}", x, y)
        y += line_h
        self._draw_label_value(surface, "Cmd Ay", f"{sim_data.get('pid_ay', 0):.2f}", x, y)

    def _draw_text(self, surface, text, x, y, font, color):
        txt = font.render(text, True, color)
        surface.blit(txt, (x, y))

    def _draw_label_value(self, surface, label, value, x, y, value_color=None):
        if value_color is None:
            value_color = COLOR_VALUE
        lbl = self.font_small.render(f"{label}:", True, COLOR_LABEL)
        val = self.font_small.render(str(value), True, value_color)
        surface.blit(lbl, (x, y))
        surface.blit(val, (x + 90, y))
