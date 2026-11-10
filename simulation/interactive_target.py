"""
Interactive Target Controller.

Handles mouse and keyboard input to control the target in Interactive Mode.
User commands only affect the Target Motion Model, NOT the UAV.
"""

import numpy as np
from typing import Optional, List, Tuple
import json
import os
from datetime import datetime


class InteractiveTargetController:
    """
    Manages interactive target control via mouse and keyboard.
    
    Control modes:
    - Click: set destination point
    - Multi-click: create waypoint queue
    - Drag: continuous destination update
    - WASD: velocity command
    - Shift: speed boost
    - Space: decelerate/stop
    
    All commands go to Target Motion Model only.
    """

    def __init__(self, 
                 target_model,
                 max_speed: float = 80.0,
                 boost_multiplier: float = 1.5,
                 base_speed: float = 40.0):
        """
        Initialize interactive controller.
        
        Args:
            target_model: Reference to target motion model
            max_speed: Maximum target speed
            boost_multiplier: Speed multiplier when Shift is held
            base_speed: Base speed for WASD control
        """
        self.target_model = target_model
        self.max_speed = max_speed
        self.boost_multiplier = boost_multiplier
        self.base_speed = base_speed
        
        # Waypoint queue
        self.waypoint_queue: List[np.ndarray] = []
        
        # Control state
        self.keys_pressed = set()
        self.mouse_dragging = False
        self.control_mode = "click"  # "click", "waypoint", "drag", "keyboard"
        
        # Recording
        self.recording = False
        self.recorded_commands: List[dict] = []
        self.record_start_time = 0.0

    def handle_mouse_click(self, x: float, y: float, t: float):
        """
        Handle mouse left click - set target destination.
        
        Args:
            x, y: World coordinates of click
            t: Current simulation time
        """
        if self.control_mode == "waypoint":
            self.waypoint_queue.append(np.array([x, y]))
            self.target_model.add_waypoint(x, y)
            self._record_command(t, 'waypoint_add', {'x': x, 'y': y})
        else:
            self.target_model.set_target_position(x, y)
            self._record_command(t, 'click', {'x': x, 'y': y})

    def handle_mouse_drag(self, x: float, y: float, t: float):
        """Handle mouse drag - continuous destination update."""
        self.mouse_dragging = True
        self.target_model.set_target_position(x, y)
        self._record_command(t, 'drag', {'x': x, 'y': y})

    def handle_mouse_release(self, t: float):
        """Handle mouse button release."""
        self.mouse_dragging = False

    def handle_key_press(self, key: str, t: float):
        """
        Handle key press for WASD/Space/Shift control.
        
        Args:
            key: Key identifier ('w', 'a', 's', 'd', 'shift', 'space', 'r')
            t: Current simulation time
        """
        self.keys_pressed.add(key)
        self._update_keyboard_command(t)
        self._record_command(t, 'key_press', {'key': key})

    def handle_key_release(self, key: str, t: float):
        """Handle key release."""
        self.keys_pressed.discard(key)
        self._update_keyboard_command(t)
        self._record_command(t, 'key_release', {'key': key})

    def _update_keyboard_command(self, t: float):
        """Update target command based on currently pressed keys."""
        vx, vy = 0.0, 0.0
        speed = self.base_speed
        
        if 'shift' in self.keys_pressed:
            speed *= self.boost_multiplier
        
        if 'space' in self.keys_pressed:
            # Decelerate
            self.target_model.set_command_velocity(0.0, 0.0)
            return
        
        if 'w' in self.keys_pressed:
            vy -= speed  # Up (Y decreases in screen coords, but model uses math coords)
        if 's' in self.keys_pressed:
            vy += speed
        if 'a' in self.keys_pressed:
            vx -= speed
        if 'd' in self.keys_pressed:
            vx += speed
        
        if abs(vx) > 0 or abs(vy) > 0:
            self.target_model.set_command_velocity(vx, vy)
        else:
            self.target_model.command_velocity = None

    def clear_waypoints(self, t: float):
        """Clear all waypoints."""
        self.waypoint_queue.clear()
        self.target_model.clear_waypoints()
        self._record_command(t, 'clear_waypoints', {})

    def set_control_mode(self, mode: str):
        """Set control mode."""
        self.control_mode = mode

    # --- Recording ---
    
    def start_recording(self, t: float):
        """Start recording user commands."""
        self.recording = True
        self.recorded_commands = []
        self.record_start_time = t

    def stop_recording(self) -> List[dict]:
        """Stop recording and return commands."""
        self.recording = False
        return self.recorded_commands.copy()

    def _record_command(self, t: float, cmd_type: str, data: dict):
        """Record a command with timestamp."""
        if self.recording:
            self.recorded_commands.append({
                'time': t - self.record_start_time,
                'type': cmd_type,
                'data': data
            })

    def save_recording(self, filepath: str):
        """Save recorded commands to JSON file."""
        with open(filepath, 'w') as f:
            json.dump({
                'commands': self.recorded_commands,
                'recorded_at': datetime.now().isoformat(),
                'base_speed': self.base_speed,
                'max_speed': self.max_speed,
            }, f, indent=2)

    def load_recording(self, filepath: str) -> List[dict]:
        """Load recorded commands from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.recorded_commands = data['commands']
        return self.recorded_commands


class RecordingPlayer:
    """Replays recorded interactive commands for batch testing."""

    def __init__(self, commands: List[dict], target_model):
        self.commands = sorted(commands, key=lambda c: c['time'])
        self.target_model = target_model
        self.cmd_index = 0

    def reset(self):
        self.cmd_index = 0

    def update(self, t: float):
        """Apply any commands that should fire at or before time t."""
        while self.cmd_index < len(self.commands):
            cmd = self.commands[self.cmd_index]
            if cmd['time'] <= t:
                self._apply_command(cmd)
                self.cmd_index += 1
            else:
                break

    def _apply_command(self, cmd: dict):
        """Apply a single recorded command."""
        cmd_type = cmd['type']
        data = cmd['data']
        
        if cmd_type == 'click':
            self.target_model.set_target_position(data['x'], data['y'])
        elif cmd_type == 'drag':
            self.target_model.set_target_position(data['x'], data['y'])
        elif cmd_type == 'waypoint_add':
            self.target_model.add_waypoint(data['x'], data['y'])
        elif cmd_type == 'key_press':
            pass  # Keyboard replay would need more complex handling
        elif cmd_type == 'clear_waypoints':
            self.target_model.clear_waypoints()

    def is_done(self) -> bool:
        return self.cmd_index >= len(self.commands)
