"""
Control Panel - Interactive buttons, sliders and controls for the Pygame GUI.
"""

import pygame
from typing import Callable, Optional, Dict, Any, List, Tuple


COLOR_BTN = (40, 50, 70)
COLOR_BTN_HOVER = (55, 70, 95)
COLOR_BTN_ACTIVE = (70, 130, 200)
COLOR_BTN_TEXT = (220, 230, 240)
COLOR_PANEL_BG = (20, 22, 30)
COLOR_DIVIDER = (50, 55, 70)
COLOR_SLIDER_BG = (40, 45, 60)
COLOR_SLIDER_FILL = (70, 130, 200)
COLOR_SLIDER_KNOB = (180, 200, 230)
COLOR_LABEL = (140, 150, 170)
COLOR_VALUE = (220, 230, 240)


class Button:
    """Simple clickable button."""

    def __init__(self, rect: pygame.Rect, text: str, callback: Callable = None,
                 toggle: bool = False, active: bool = False, color=None):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.toggle = toggle
        self.active = active
        self.hovered = False
        self.color = color
        self._font = None

    def draw(self, surface: pygame.Surface):
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 12, bold=True)
        if self.active:
            bg = self.color or COLOR_BTN_ACTIVE
        elif self.hovered:
            bg = COLOR_BTN_HOVER
        else:
            bg = COLOR_BTN
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_DIVIDER, self.rect, 1, border_radius=4)
        txt = self._font.render(self.text, True, COLOR_BTN_TEXT)
        tr = txt.get_rect(center=self.rect.center)
        surface.blit(txt, tr)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.toggle:
                    self.active = not self.active
                if self.callback:
                    self.callback()
                return True
        return False


class Slider:
    """Horizontal slider control."""

    def __init__(self, rect: pygame.Rect, label: str,
                 min_val: float, max_val: float, value: float,
                 fmt: str = ".1f", callback: Callable = None):
        self.rect = rect
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.fmt = fmt
        self.callback = callback
        self.dragging = False
        self._font = None

    @property
    def normalized(self) -> float:
        r = self.max_val - self.min_val
        if r < 1e-9:
            return 0
        return (self.value - self.min_val) / r

    def draw(self, surface: pygame.Surface):
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 11)
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        # Label
        lbl = self._font.render(self.label, True, COLOR_LABEL)
        surface.blit(lbl, (x, y))
        # Value
        val_text = f"{self.value:{self.fmt}}"
        vt = self._font.render(val_text, True, COLOR_VALUE)
        surface.blit(vt, (x + w - vt.get_width(), y))
        # Track
        track_y = y + 14
        track_h = 5
        pygame.draw.rect(surface, COLOR_SLIDER_BG, (x, track_y, w, track_h), border_radius=2)
        fill_w = int(w * self.normalized)
        pygame.draw.rect(surface, COLOR_SLIDER_FILL, (x, track_y, fill_w, track_h), border_radius=2)
        # Knob
        knob_x = x + fill_w
        pygame.draw.circle(surface, COLOR_SLIDER_KNOB, (knob_x, track_y + track_h // 2), 5)

    def handle_event(self, event: pygame.event.Event) -> bool:
        track_y = self.rect.y + 14
        track_rect = pygame.Rect(self.rect.x - 6, track_y - 6, self.rect.width + 12, 16)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if track_rect.collidepoint(event.pos):
                self.dragging = True
                self._update_value(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])
            return True
        return False

    def _update_value(self, mouse_x: int):
        rel = (mouse_x - self.rect.x) / max(self.rect.width, 1)
        rel = max(0, min(1, rel))
        self.value = self.min_val + rel * (self.max_val - self.min_val)
        if self.callback:
            self.callback(self.value)


class DropdownSelect:
    """Simple dropdown selector."""

    def __init__(self, rect: pygame.Rect, label: str, options: List[str],
                 selected: int = 0, callback: Callable = None):
        self.rect = rect
        self.label = label
        self.options = options
        self.selected = selected
        self.callback = callback
        self.open = False
        self._font = None

    @property
    def value(self) -> str:
        return self.options[self.selected] if self.options else ""

    def draw(self, surface: pygame.Surface):
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 12)
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        # Label
        lbl = self._font.render(self.label, True, COLOR_LABEL)
        surface.blit(lbl, (x, y))
        # Box
        box_y = y + 16
        box_h = 22
        box_rect = pygame.Rect(x, box_y, w, box_h)
        pygame.draw.rect(surface, COLOR_BTN, box_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_DIVIDER, box_rect, 1, border_radius=3)
        txt = self._font.render(self.value, True, COLOR_VALUE)
        surface.blit(txt, (x + 6, box_y + 3))
        # Arrow
        arrow = self._font.render("▼" if not self.open else "▲", True, COLOR_LABEL)
        surface.blit(arrow, (x + w - 16, box_y + 3))
        # Dropdown
        if self.open:
            item_h = 19
            for i, opt in enumerate(self.options):
                opt_rect = pygame.Rect(x, box_y + box_h + i * item_h, w, item_h)
                bg = COLOR_BTN_ACTIVE if i == self.selected else COLOR_BTN_HOVER
                pygame.draw.rect(surface, bg, opt_rect)
                pygame.draw.rect(surface, COLOR_DIVIDER, opt_rect, 1)
                ot = self._font.render(opt, True, COLOR_BTN_TEXT)
                surface.blit(ot, (x + 6, opt_rect.y + 2))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        box_y = y + 16
        box_h = 22
        box_rect = pygame.Rect(x, box_y, w, box_h)
        if box_rect.collidepoint(event.pos):
            self.open = not self.open
            return True
        if self.open:
            item_h = 19
            for i in range(len(self.options)):
                opt_rect = pygame.Rect(x, box_y + box_h + i * item_h, w, item_h)
                if opt_rect.collidepoint(event.pos):
                    self.selected = i
                    self.open = False
                    if self.callback:
                        self.callback(self.value)
                    return True
            self.open = False
        return False


class ControlPanel:
    """Container for all control panel widgets."""

    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self.buttons: Dict[str, Button] = {}
        self.sliders: Dict[str, Slider] = {}
        self.dropdowns: Dict[str, DropdownSelect] = {}
        self._font_title = None

        self._build_controls()

    def _build_controls(self):
        x = self.rect.x + 8
        y = self.rect.y + 30
        w = self.rect.width - 16
        bw = (w - 8) // 3
        bh = 26

        # Simulation controls (START button highlighted in Green)
        self.buttons['start'] = Button(pygame.Rect(x, y, bw, bh), "START", color=(35, 145, 65))
        self.buttons['pause'] = Button(pygame.Rect(x + bw + 4, y, bw, bh), "PAUSE", toggle=True)
        self.buttons['reset'] = Button(pygame.Rect(x + 2 * (bw + 4), y, bw, bh), "RESET")
        y += bh + 8

        # Filter selection
        self.dropdowns['filter'] = DropdownSelect(
            pygame.Rect(x, y, w, 36), "Filter:", ["EKF", "UKF", "Both"], 0)
        y += 40

        # Scenario selection (12 scenarios as specified in handoff doc)
        scenarios = [
            "1-Baseline", "2-Sudden Maneuver", "3-High Noise",
            "4-Lost Detection", "5-Normal Tracking", "6-Turning Tracking",
            "7-Combined Stress", "8-Interactive Click", "9-Interactive Waypoint",
            "10-Mouse Drag", "11-Keyboard Control", "12-Evasive Target"
        ]
        self.dropdowns['scenario'] = DropdownSelect(
            pygame.Rect(x, y, w, 36), "Scenario:", scenarios, 0)
        y += 40

        # Trajectory type
        trajectories = ["straight", "circular", "sinusoidal", "zigzag", "waypoint", "random"]
        self.dropdowns['trajectory'] = DropdownSelect(
            pygame.Rect(x, y, w, 36), "Trajectory:", trajectories, 0)
        y += 40

        # Interactive mode
        imodes = ["click", "waypoint", "drag", "keyboard"]
        self.dropdowns['interactive_mode'] = DropdownSelect(
            pygame.Rect(x, y, w, 36), "Input Mode:", imodes, 0)
        y += 40

        # Noise ON/OFF
        self.buttons['noise'] = Button(pygame.Rect(x, y, w // 2 - 3, 24),
                                        "NOISE ON", toggle=True, active=True)
        self.buttons['dropout'] = Button(pygame.Rect(x + w // 2 + 3, y, w // 2 - 3, 24),
                                          "DROPOUT", toggle=True)
        y += 27
        self.buttons['delay'] = Button(pygame.Rect(x, y, w // 2 - 3, 24),
                                        "DELAY", toggle=True)
        self.buttons['record'] = Button(pygame.Rect(x + w // 2 + 3, y, w // 2 - 3, 24),
                                         "REC", toggle=True, color=(180, 40, 40))
        y += 29

        # Sliders (compact spacing)
        sh = 20
        step = 24
        self.sliders['noise_level'] = Slider(
            pygame.Rect(x, y, w, sh), "Noise Level", 0.5, 10.0, 2.0, ".1f")
        y += step
        self.sliders['desired_dist'] = Slider(
            pygame.Rect(x, y, w, sh), "Follow Dist", 10.0, 150.0, 50.0, ".0f")
        y += step
        self.sliders['kp'] = Slider(
            pygame.Rect(x, y, w, sh), "Kp", 0.1, 10.0, 2.0, ".1f")
        y += step
        self.sliders['ki'] = Slider(
            pygame.Rect(x, y, w, sh), "Ki", 0.0, 2.0, 0.1, ".2f")
        y += step
        self.sliders['kd'] = Slider(
            pygame.Rect(x, y, w, sh), "Kd", 0.0, 5.0, 1.5, ".1f")
        y += step
        self.sliders['target_speed'] = Slider(
            pygame.Rect(x, y, w, sh), "Tgt Speed", 5.0, 100.0, 30.0, ".0f")
        y += step
        self.sliders['dropout_dur'] = Slider(
            pygame.Rect(x, y, w, sh), "Drop Dur(s)", 0.5, 10.0, 3.0, ".1f")
        y += step
        self.sliders['delay_sec'] = Slider(
            pygame.Rect(x, y, w, sh), "Delay(s)", 0.05, 1.0, 0.2, ".2f")
        y += step + 6

        # Save results
        self.buttons['save'] = Button(pygame.Rect(x, y, w, bh), "SAVE RESULTS")

    def draw(self, surface: pygame.Surface):
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("consolas", 14, bold=True)
        pygame.draw.rect(surface, (20, 22, 30), self.rect)
        pygame.draw.rect(surface, COLOR_DIVIDER, self.rect, 1)
        title = self._font_title.render("CONTROL PANEL", True, COLOR_VALUE)
        surface.blit(title, (self.rect.x + 10, self.rect.y + 10))
        pygame.draw.line(surface, COLOR_DIVIDER,
                          (self.rect.x + 10, self.rect.y + 30),
                          (self.rect.right - 10, self.rect.y + 30))

        for btn in self.buttons.values():
            btn.draw(surface)
        for sl in self.sliders.values():
            sl.draw(surface)
        # Draw closed dropdowns first
        for dd in self.dropdowns.values():
            if not dd.open:
                dd.draw(surface)
        # Draw open dropdowns last so options render on top of buttons/sliders
        for dd in self.dropdowns.values():
            if dd.open:
                dd.draw(surface)

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Dropdowns first (they overlay)
        for dd in self.dropdowns.values():
            if dd.handle_event(event):
                return True
        for btn in self.buttons.values():
            if btn.handle_event(event):
                return True
        for sl in self.sliders.values():
            if sl.handle_event(event):
                return True
        return False

    def get_state(self) -> Dict[str, Any]:
        """Get current control panel state."""
        return {
            'filter': self.dropdowns['filter'].value.lower(),
            'scenario': self.dropdowns['scenario'].selected,
            'trajectory': self.dropdowns['trajectory'].value,
            'interactive_mode': self.dropdowns['interactive_mode'].value,
            'noise_on': self.buttons['noise'].active,
            'dropout_on': self.buttons['dropout'].active,
            'delay_on': self.buttons['delay'].active,
            'recording': self.buttons['record'].active,
            'noise_level': self.sliders['noise_level'].value,
            'desired_distance': self.sliders['desired_dist'].value,
            'kp': self.sliders['kp'].value,
            'ki': self.sliders['ki'].value,
            'kd': self.sliders['kd'].value,
            'target_speed': self.sliders['target_speed'].value,
            'dropout_duration': self.sliders['dropout_dur'].value,
            'delay_seconds': self.sliders['delay_sec'].value,
        }
