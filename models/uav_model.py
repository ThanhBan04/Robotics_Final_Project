"""
UAV Motion Model for UAV Target Tracking 2D Simulation.

Implements 2D kinematic model with velocity and acceleration limits.
State vector: [x, y, vx, vy]
Input: acceleration command [ax, ay] from PID controller.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class UAVState:
    """Represents the state of the UAV."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    heading: float = 0.0  # yaw angle (rad), computed from velocity
    timestamp: float = 0.0

    def position(self) -> np.ndarray:
        return np.array([self.x, self.y])

    def velocity(self) -> np.ndarray:
        return np.array([self.vx, self.vy])

    def speed(self) -> float:
        return np.sqrt(self.vx**2 + self.vy**2)

    def state_vector(self) -> np.ndarray:
        return np.array([self.x, self.y, self.vx, self.vy])

    def copy(self) -> 'UAVState':
        return UAVState(self.x, self.y, self.vx, self.vy, self.heading, self.timestamp)


class UAVModel:
    """
    UAV kinematic model with acceleration/velocity saturation.
    
    Update equations:
        v_{x,k+1} = v_{x,k} + a_{x,k} * dt   (with saturation)
        v_{y,k+1} = v_{y,k} + a_{y,k} * dt   (with saturation)
        x_{k+1} = x_k + v_{x,k+1} * dt
        y_{k+1} = y_k + v_{y,k+1} * dt
    """

    def __init__(self,
                 initial_x: float = 100.0,
                 initial_y: float = 400.0,
                 initial_vx: float = 0.0,
                 initial_vy: float = 0.0,
                 max_speed: float = 100.0,
                 max_acceleration: float = 25.0,
                 world_bounds: tuple = None):
        """
        Initialize UAV model.
        
        Args:
            initial_x: Initial X position (m)
            initial_y: Initial Y position (m)
            initial_vx: Initial X velocity (m/s)
            initial_vy: Initial Y velocity (m/s)
            max_speed: Maximum speed limit (m/s)
            max_acceleration: Maximum acceleration limit (m/s^2)
            world_bounds: (width, height) for boundary enforcement, None for no bounds
        """
        self.initial_state = UAVState(initial_x, initial_y, initial_vx, initial_vy, 0.0, 0.0)
        self.state = self.initial_state.copy()
        self.max_speed = max_speed
        self.max_acceleration = max_acceleration
        self.world_bounds = world_bounds
        
        # Update heading from initial velocity
        self._update_heading()

    def reset(self):
        """Reset UAV to initial state."""
        self.state = self.initial_state.copy()
        self._update_heading()

    def _update_heading(self):
        """Update heading angle from velocity vector."""
        speed = self.state.speed()
        if speed > 0.1:
            self.state.heading = np.arctan2(self.state.vy, self.state.vx)

    def _saturate_acceleration(self, acc: np.ndarray) -> np.ndarray:
        """Limit acceleration magnitude to max_acceleration."""
        mag = np.linalg.norm(acc)
        if mag > self.max_acceleration:
            acc = acc * (self.max_acceleration / mag)
        return acc

    def _saturate_velocity(self, vel: np.ndarray) -> np.ndarray:
        """Limit velocity magnitude to max_speed."""
        speed = np.linalg.norm(vel)
        if speed > self.max_speed:
            vel = vel * (self.max_speed / speed)
        return vel

    def _enforce_bounds(self):
        """Keep UAV within world boundaries with elastic collision."""
        if self.world_bounds is None:
            return
        
        w, h = self.world_bounds
        margin = 10.0
        
        if self.state.x < margin:
            self.state.x = margin
            self.state.vx = abs(self.state.vx) * 0.5
        elif self.state.x > w - margin:
            self.state.x = w - margin
            self.state.vx = -abs(self.state.vx) * 0.5
        
        if self.state.y < margin:
            self.state.y = margin
            self.state.vy = abs(self.state.vy) * 0.5
        elif self.state.y > h - margin:
            self.state.y = h - margin
            self.state.vy = -abs(self.state.vy) * 0.5

    def step(self, acceleration_command: np.ndarray, dt: float, t: float) -> UAVState:
        """
        Advance UAV state by one timestep.
        
        Args:
            acceleration_command: [ax, ay] from PID controller (m/s^2)
            dt: Timestep (seconds)
            t: Current simulation time (seconds)
            
        Returns:
            Updated UAVState
        """
        # Saturate acceleration command
        acc = self._saturate_acceleration(acceleration_command)
        
        # Update velocity
        new_vx = self.state.vx + acc[0] * dt
        new_vy = self.state.vy + acc[1] * dt
        
        # Saturate velocity
        vel = self._saturate_velocity(np.array([new_vx, new_vy]))
        new_vx, new_vy = vel[0], vel[1]
        
        # Update position using new velocity
        new_x = self.state.x + new_vx * dt
        new_y = self.state.y + new_vy * dt
        
        # Update state
        self.state.x = new_x
        self.state.y = new_y
        self.state.vx = new_vx
        self.state.vy = new_vy
        self.state.timestamp = t + dt
        
        # Update heading
        self._update_heading()
        
        # Enforce world bounds
        self._enforce_bounds()
        
        return self.state.copy()

    def get_pose(self) -> dict:
        """Get UAV pose for camera model."""
        return {
            'x': self.state.x,
            'y': self.state.y,
            'heading': self.state.heading
        }
