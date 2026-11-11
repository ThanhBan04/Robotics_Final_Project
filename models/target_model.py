"""
Target Motion Model for UAV Target Tracking 2D Simulation.

Implements various trajectory types for the target:
- Constant Velocity (CV) with process noise
- Straight line, circular, sinusoidal, zigzag, waypoint, random trajectories

State vector: [x, y, vx, vy]
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class TargetState:
    """Represents the ground truth state of the target."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    timestamp: float = 0.0

    def position(self) -> np.ndarray:
        return np.array([self.x, self.y])

    def velocity(self) -> np.ndarray:
        return np.array([self.vx, self.vy])

    def speed(self) -> float:
        return np.sqrt(self.vx**2 + self.vy**2)

    def state_vector(self) -> np.ndarray:
        return np.array([self.x, self.y, self.vx, self.vy])

    def copy(self) -> 'TargetState':
        return TargetState(self.x, self.y, self.vx, self.vy, self.timestamp)


class TargetModel:
    """
    Target motion model using Constant Velocity (CV) dynamics.
    
    State transition: X_{k+1} = F * X_k + w_k
    where F is the state transition matrix and w_k is process noise.
    """

    def __init__(self, 
                 initial_x: float = 300.0,
                 initial_y: float = 400.0,
                 initial_vx: float = 30.0,
                 initial_vy: float = 0.0,
                 max_speed: float = 80.0,
                 max_acceleration: float = 20.0,
                 process_noise_std: float = 1.0,
                 trajectory_type: str = "straight",
                 random_seed: Optional[int] = None,
                 **kwargs):
        """
        Initialize target model.
        
        Args:
            initial_x: Initial X position (m)
            initial_y: Initial Y position (m)
            initial_vx: Initial X velocity (m/s)
            initial_vy: Initial Y velocity (m/s)
            max_speed: Maximum speed limit (m/s)
            max_acceleration: Maximum acceleration limit (m/s^2)
            process_noise_std: Process noise standard deviation
            trajectory_type: Type of trajectory (straight, circular, sinusoidal, zigzag, waypoint, random)
            random_seed: Random seed for reproducibility
        """
        self.initial_state = TargetState(initial_x, initial_y, initial_vx, initial_vy, 0.0)
        self.state = self.initial_state.copy()
        self.max_speed = max_speed
        self.max_acceleration = max_acceleration
        self.process_noise_std = process_noise_std
        self.trajectory_type = trajectory_type
        self.rng = np.random.default_rng(random_seed)
        
        # Trajectory-specific parameters
        self.kwargs = kwargs
        self.circular_radius = kwargs.get('circular_radius', 150.0)
        self.circular_omega = kwargs.get('circular_omega', 0.3)
        self.circular_center = kwargs.get('circular_center', None)
        
        self.sinusoidal_amplitude = kwargs.get('sinusoidal_amplitude', 100.0)
        self.sinusoidal_frequency = kwargs.get('sinusoidal_frequency', 0.2)
        self.sin_base_x = initial_x
        self.sin_base_y = initial_y
        self.sin_base_vx = initial_vx
        
        self.zigzag_amplitude = kwargs.get('zigzag_amplitude', 80.0)
        self.zigzag_period = kwargs.get('zigzag_period', 5.0)
        
        self.waypoints: List[np.ndarray] = []
        wp_list = kwargs.get('waypoints', [])
        for wp in wp_list:
            self.waypoints.append(np.array(wp, dtype=float))
        self.current_waypoint_idx = 0
        self.waypoint_reach_threshold = kwargs.get('waypoint_reach_threshold', 15.0)
        
        # Random trajectory
        self.random_turn_interval = kwargs.get('random_turn_interval', 3.0)
        self.last_turn_time = 0.0
        self.random_target_heading = 0.0
        
        # For interactive/command mode
        self.target_position: Optional[np.ndarray] = None  # Click destination
        self.command_velocity: Optional[np.ndarray] = None  # WASD command
        
        # Maneuver scheduling (for scenario testing)
        self.maneuvers: List[dict] = kwargs.get('maneuvers', [])
        self.world_bounds = kwargs.get('world_bounds', None)
        self.boundary_hits = 0
        self._maneuver_states: Dict[int, dict] = {}
        
        # Initialize circular trajectory center
        if self.trajectory_type == "circular" and self.circular_center is None:
            self.circular_center = np.array([initial_x, initial_y - self.circular_radius])
        
        self._time = 0.0

    def reset(self):
        """Reset target to initial state."""
        self.state = self.initial_state.copy()
        self._time = 0.0
        self.current_waypoint_idx = 0
        self.last_turn_time = 0.0
        self.target_position = None
        self.command_velocity = None
        self._maneuver_states = {}
        self.boundary_hits = 0

    def get_state_transition_matrix(self, dt: float) -> np.ndarray:
        """
        Get the state transition matrix F for CV model.
        
        F = [[1, 0, dt, 0 ],
             [0, 1, 0,  dt],
             [0, 0, 1,  0 ],
             [0, 0, 0,  1 ]]
        """
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        return F

    def get_process_noise_covariance(self, dt: float) -> np.ndarray:
        """
        Get process noise covariance matrix Q.
        
        Using continuous white noise acceleration model:
        Q = q * [[dt^3/3, 0,      dt^2/2, 0     ],
                  [0,      dt^3/3, 0,      dt^2/2],
                  [dt^2/2, 0,      dt,     0     ],
                  [0,      dt^2/2, 0,      dt    ]]
        where q is the spectral density of the acceleration noise.
        """
        q = self.process_noise_std ** 2
        Q = q * np.array([
            [dt**3 / 3, 0, dt**2 / 2, 0],
            [0, dt**3 / 3, 0, dt**2 / 2],
            [dt**2 / 2, 0, dt, 0],
            [0, dt**2 / 2, 0, dt]
        ])
        return Q

    def _compute_desired_acceleration(self, t: float, dt: float) -> np.ndarray:
        """
        Compute desired acceleration based on trajectory type.
        
        Returns:
            Desired acceleration [ax, ay] (m/s^2)
        """
        if self.trajectory_type == "straight":
            return self._straight_acceleration(t, dt)
        elif self.trajectory_type == "circular":
            return self._circular_acceleration(t, dt)
        elif self.trajectory_type == "sinusoidal":
            return self._sinusoidal_acceleration(t, dt)
        elif self.trajectory_type == "zigzag":
            return self._zigzag_acceleration(t, dt)
        elif self.trajectory_type == "waypoint":
            return self._waypoint_acceleration(t, dt)
        elif self.trajectory_type == "random":
            return self._random_acceleration(t, dt)
        elif self.trajectory_type == "interactive":
            return self._interactive_acceleration(t, dt)
        else:
            return np.array([0.0, 0.0])

    def _straight_acceleration(self, t: float, dt: float) -> np.ndarray:
        """Straight line: maintain initial velocity, no acceleration needed."""
        return np.array([0.0, 0.0])

    def _circular_acceleration(self, t: float, dt: float) -> np.ndarray:
        """Circular trajectory: centripetal acceleration."""
        center = self.circular_center
        pos = self.state.position()
        r_vec = pos - center
        r = np.linalg.norm(r_vec)
        if r < 1e-6:
            return np.array([0.0, 0.0])
        
        # Desired position on circle
        angle = np.arctan2(r_vec[1], r_vec[0]) + self.circular_omega * dt
        desired_pos = center + self.circular_radius * np.array([np.cos(angle), np.sin(angle)])
        
        # Desired velocity (tangent to circle)
        speed = self.circular_omega * self.circular_radius
        desired_vel = speed * np.array([-np.sin(angle), np.cos(angle)])
        
        # PD-like acceleration to track circular path
        pos_err = desired_pos - pos
        vel_err = desired_vel - self.state.velocity()
        acc = 3.0 * pos_err / dt + 2.0 * vel_err
        return acc

    def _sinusoidal_acceleration(self, t: float, dt: float) -> np.ndarray:
        """Sinusoidal trajectory: oscillating in Y while moving in X."""
        omega = 2 * np.pi * self.sinusoidal_frequency
        
        # Desired position
        desired_x = self.sin_base_x + self.sin_base_vx * t
        desired_y = self.sin_base_y + self.sinusoidal_amplitude * np.sin(omega * t)
        
        # Desired velocity
        desired_vx = self.sin_base_vx
        desired_vy = self.sinusoidal_amplitude * omega * np.cos(omega * t)
        
        pos_err = np.array([desired_x - self.state.x, desired_y - self.state.y])
        vel_err = np.array([desired_vx - self.state.vx, desired_vy - self.state.vy])
        
        acc = 3.0 * pos_err / max(dt, 1e-6) + 2.0 * vel_err
        return acc

    def _zigzag_acceleration(self, t: float, dt: float) -> np.ndarray:
        """Zigzag trajectory: triangular wave in Y while moving in X."""
        period = self.zigzag_period
        phase = (t % period) / period
        
        desired_x = self.sin_base_x + self.sin_base_vx * t
        if phase < 0.5:
            desired_y = self.sin_base_y + self.zigzag_amplitude * (4 * phase - 1)
            desired_vy = self.zigzag_amplitude * 4 / period
        else:
            desired_y = self.sin_base_y + self.zigzag_amplitude * (3 - 4 * phase)
            desired_vy = -self.zigzag_amplitude * 4 / period
        
        pos_err = np.array([desired_x - self.state.x, desired_y - self.state.y])
        vel_err = np.array([self.sin_base_vx - self.state.vx, desired_vy - self.state.vy])
        
        acc = 3.0 * pos_err / max(dt, 1e-6) + 2.0 * vel_err
        return acc

    def _waypoint_acceleration(self, t: float, dt: float) -> np.ndarray:
        """Navigate through waypoints sequentially."""
        if len(self.waypoints) == 0:
            return np.array([0.0, 0.0])
        
        # Get current waypoint
        if self.current_waypoint_idx >= len(self.waypoints):
            self.current_waypoint_idx = 0  # Loop waypoints
        
        target_wp = self.waypoints[self.current_waypoint_idx]
        pos = self.state.position()
        direction = target_wp - pos
        dist = np.linalg.norm(direction)
        
        # Check if reached waypoint
        if dist < self.waypoint_reach_threshold:
            self.current_waypoint_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
            target_wp = self.waypoints[self.current_waypoint_idx]
            direction = target_wp - pos
            dist = np.linalg.norm(direction)
        
        if dist < 1e-6:
            return np.array([0.0, 0.0])
        
        # Desired velocity towards waypoint
        desired_speed = min(self.max_speed * 0.6, dist * 0.5)
        desired_vel = (direction / dist) * desired_speed
        vel_err = desired_vel - self.state.velocity()
        
        acc = vel_err / max(dt, 1e-6) * 0.3
        return acc

    def _random_acceleration(self, t: float, dt: float) -> np.ndarray:
        """Random direction changes at intervals."""
        if t - self.last_turn_time >= self.random_turn_interval:
            self.random_target_heading = self.rng.uniform(0, 2 * np.pi)
            self.last_turn_time = t
        
        desired_speed = self.max_speed * 0.5
        desired_vel = desired_speed * np.array([
            np.cos(self.random_target_heading),
            np.sin(self.random_target_heading)
        ])
        vel_err = desired_vel - self.state.velocity()
        acc = vel_err / max(dt, 1e-6) * 0.3
        return acc

    def _interactive_acceleration(self, t: float, dt: float) -> np.ndarray:
        """
        Interactive mode: respond to user commands.
        - target_position: click destination 
        - command_velocity: WASD velocity command
        """
        if self.command_velocity is not None:
            # WASD mode: steer towards commanded velocity
            desired_vel = self.command_velocity
            vel_err = desired_vel - self.state.velocity()
            acc = vel_err / max(dt, 1e-6) * 0.3
            return acc
        
        if self.target_position is not None:
            # Click mode: navigate to target position
            pos = self.state.position()
            direction = self.target_position - pos
            dist = np.linalg.norm(direction)
            
            if dist < 5.0:
                # Slow down when close
                desired_vel = np.array([0.0, 0.0])
            else:
                desired_speed = min(self.max_speed * 0.6, dist * 0.3)
                desired_vel = (direction / dist) * desired_speed
            
            vel_err = desired_vel - self.state.velocity()
            acc = vel_err / max(dt, 1e-6) * 0.3
            return acc
        
        # No command: coast (decelerate slowly)
        speed = self.state.speed()
        if speed > 0.5:
            vel = self.state.velocity()
            acc = -vel * 0.5  # Gentle deceleration
            return acc
        return np.array([0.0, 0.0])

    def _apply_maneuvers(self, t: float, dt: float, acc: np.ndarray) -> np.ndarray:
        """Apply scheduled maneuvers (sudden turns, speed changes)."""
        for idx, maneuver in enumerate(self.maneuvers):
            m_time = maneuver.get('time', -1)
            m_type = maneuver.get('type')
            
            # Check for unknown maneuver type
            if m_type not in ('turn', 'speed', 'speed_change'):
                raise ValueError(f"Unknown maneuver type: '{m_type}' in maneuver {maneuver}")
                
            if t < m_time:
                continue
                
            state = self._maneuver_states.setdefault(idx, {'started': False, 'completed': False})
            
            if m_type == 'turn':
                if not state['started']:
                    # Latch target heading once when maneuver starts
                    vel = self.state.velocity()
                    speed = self.state.speed()
                    if speed > 1e-3:
                        current_heading = np.arctan2(vel[1], vel[0])
                    else:
                        current_heading = 0.0
                    angle_deg = maneuver.get('angle', 90)
                    target_heading = current_heading + np.radians(angle_deg)
                    target_heading = (target_heading + np.pi) % (2 * np.pi) - np.pi
                    state['started'] = True
                    state['target_heading'] = target_heading
                    state['speed'] = max(speed, 5.0)
                
                if not state['completed']:
                    vel = self.state.velocity()
                    speed = state['speed']
                    current_heading = np.arctan2(vel[1], vel[0]) if np.linalg.norm(vel) > 1e-3 else state['target_heading']
                    heading_err = (state['target_heading'] - current_heading + np.pi) % (2 * np.pi) - np.pi
                    
                    max_omega = self.max_acceleration / max(speed, 1.0)
                    max_dpsi = max_omega * dt
                    
                    if abs(heading_err) <= max_dpsi:
                        new_heading = state['target_heading']
                        state['completed'] = True
                    else:
                        new_heading = current_heading + np.sign(heading_err) * max_dpsi
                        
                    desired_vel = speed * np.array([np.cos(new_heading), np.sin(new_heading)])
                    turn_acc = (desired_vel - vel) / max(dt, 1e-6)
                    return turn_acc

            elif m_type in ('speed', 'speed_change'):
                m_duration = maneuver.get('duration', 1.0)
                if not state['started']:
                    current_speed = self.state.speed()
                    if m_type == 'speed':
                        target_spd = maneuver.get('target_speed', current_speed)
                    else:
                        target_spd = current_speed * maneuver.get('factor', 1.5)
                    state['started'] = True
                    state['target_speed'] = min(target_spd, self.max_speed)
                
                if t < m_time + m_duration:
                    vel = self.state.velocity()
                    current_spd = self.state.speed()
                    target_spd = state['target_speed']
                    heading = np.arctan2(vel[1], vel[0]) if current_spd > 1e-3 else 0.0
                    spd_err = target_spd - current_spd
                    max_d_spd = self.max_acceleration * dt
                    if abs(spd_err) <= max_d_spd:
                        new_spd = target_spd
                        state['completed'] = True
                    else:
                        new_spd = current_spd + np.sign(spd_err) * max_d_spd
                    desired_vel = new_spd * np.array([np.cos(heading), np.sin(heading)])
                    spd_acc = (desired_vel - vel) / max(dt, 1e-6)
                    return spd_acc
                else:
                    state['completed'] = True

        return acc

    def _saturate_acceleration(self, acc: np.ndarray) -> np.ndarray:
        """Limit acceleration magnitude."""
        mag = np.linalg.norm(acc)
        if mag > self.max_acceleration:
            acc = acc * (self.max_acceleration / mag)
        return acc

    def _saturate_velocity(self, vel: np.ndarray) -> np.ndarray:
        """Limit velocity magnitude."""
        speed = np.linalg.norm(vel)
        if speed > self.max_speed:
            vel = vel * (self.max_speed / speed)
        return vel

    def step(self, dt: float, t: float) -> TargetState:
        """
        Advance target state by one timestep.
        
        Args:
            dt: Timestep (seconds)
            t: Current simulation time (seconds)
            
        Returns:
            Updated TargetState (ground truth)
        """
        # Compute desired acceleration from trajectory
        acc = self._compute_desired_acceleration(t, dt)
        
        # Apply scheduled maneuvers
        acc = self._apply_maneuvers(t, dt, acc)
        
        # Saturate acceleration
        acc = self._saturate_acceleration(acc)
        
        # Add process noise
        noise = self.rng.normal(0, self.process_noise_std, 2)
        
        # Update velocity
        new_vx = self.state.vx + acc[0] * dt + noise[0] * dt
        new_vy = self.state.vy + acc[1] * dt + noise[1] * dt
        
        # Saturate velocity
        vel = self._saturate_velocity(np.array([new_vx, new_vy]))
        new_vx, new_vy = vel[0], vel[1]
        
        # Update position using updated velocity (Semi-implicit Euler, consistent with UAV)
        new_x = self.state.x + new_vx * dt
        new_y = self.state.y + new_vy * dt
        
        # Enforce world bounds if configured
        if self.world_bounds is not None:
            w, h = self.world_bounds
            margin = 20.0
            if new_x < margin:
                self.boundary_hits += 1
                new_x = margin
                new_vx = abs(new_vx) * 0.5
            elif new_x > w - margin:
                self.boundary_hits += 1
                new_x = w - margin
                new_vx = -abs(new_vx) * 0.5
            if new_y < margin:
                self.boundary_hits += 1
                new_y = margin
                new_vy = abs(new_vy) * 0.5
            elif new_y > h - margin:
                self.boundary_hits += 1
                new_y = h - margin
                new_vy = -abs(new_vy) * 0.5
        
        # Update state
        self.state.x = new_x
        self.state.y = new_y
        self.state.vx = new_vx
        self.state.vy = new_vy
        self.state.timestamp = t + dt
        self._time = t + dt
        
        return self.state.copy()

    def set_target_position(self, x: float, y: float):
        """Set click destination for interactive mode."""
        self.target_position = np.array([x, y])

    def set_command_velocity(self, vx: float, vy: float):
        """Set WASD velocity command for interactive mode."""
        self.command_velocity = np.array([vx, vy])

    def clear_command(self):
        """Clear interactive commands."""
        self.target_position = None
        self.command_velocity = None
        self._maneuver_states = {}

    def add_waypoint(self, x: float, y: float):
        """Add a waypoint for interactive waypoint mode."""
        self.waypoints.append(np.array([x, y]))

    def clear_waypoints(self):
        """Clear all waypoints."""
        self.waypoints.clear()
        self.current_waypoint_idx = 0
