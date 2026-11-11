"""
Simulated Camera Model for UAV Target Tracking 2D Simulation.

Implements:
- Range/Bearing measurement model (nonlinear, suitable for EKF/UKF)
- XY direct measurement model (linear, for baseline comparison)
- Gaussian measurement noise
- Field of View (FOV) check
- Detection dropout
- Measurement delay
- Configurable measurement rate

Measurement model (Range/Bearing):
    z_k = [r_k, theta_k] + v_k
    r_k = sqrt((x_t - x_u)^2 + (y_t - y_u)^2)
    theta_k = atan2(y_t - y_u, x_t - x_u) - psi_u

Assumption: Range is obtained via known target size and perspective model
(simulated sensor with range capability).
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from collections import deque


@dataclass
class Measurement:
    """Represents a camera measurement."""
    data: Optional[np.ndarray]  # None if no detection
    timestamp: float
    detected: bool
    measurement_type: str  # "range_bearing" or "xy"
    raw_data: Optional[np.ndarray] = None  # Without noise for debugging
    sensor_pose: Optional[dict] = None  # Camera pose at capture time

    def copy(self):
        return Measurement(
            data=self.data.copy() if self.data is not None else None,
            timestamp=self.timestamp,
            detected=self.detected,
            measurement_type=self.measurement_type,
            raw_data=self.raw_data.copy() if self.raw_data is not None else None,
            sensor_pose=dict(self.sensor_pose) if self.sensor_pose is not None else None,
        )


class CameraModel:
    """
    Simulated camera sensor for target observation.
    
    Supports two measurement models:
    1. Range/Bearing (nonlinear) - Primary model for EKF/UKF research
    2. XY direct (linear) - Baseline for comparison
    """

    def __init__(self,
                 measurement_model: str = "range_bearing",
                 fov_angle: float = 120.0,
                 max_range: float = 500.0,
                 noise_range_std: float = 2.0,
                 noise_bearing_std: float = 0.05,
                 noise_xy_std: float = 3.0,
                 dropout_probability: float = 0.0,
                 dropout_duration: float = 0.0,
                 delay: float = 0.0,
                 measurement_rate: float = 50.0,
                 random_seed: Optional[int] = None):
        """
        Initialize camera model.
        
        Args:
            measurement_model: "range_bearing" or "xy"
            fov_angle: Field of view angle (degrees, total)
            max_range: Maximum detection range (meters)
            noise_range_std: Range measurement noise std (meters)
            noise_bearing_std: Bearing measurement noise std (radians)
            noise_xy_std: XY measurement noise std (meters)
            dropout_probability: Probability of random dropout per frame
            dropout_duration: Duration of forced dropout (seconds), 0 = no forced dropout
            delay: Measurement delay (seconds)
            measurement_rate: Measurements per second (Hz)
            random_seed: Random seed for reproducibility
        """
        self.measurement_model = measurement_model
        self.fov_angle = np.radians(fov_angle)  # Convert to radians
        self.max_range = max_range
        self.noise_range_std = noise_range_std
        self.noise_bearing_std = noise_bearing_std
        self.noise_xy_std = noise_xy_std
        self.dropout_probability = dropout_probability
        self.dropout_duration = dropout_duration
        self.delay = delay
        self.measurement_rate = measurement_rate
        self.measurement_period = 1.0 / measurement_rate if measurement_rate > 0 else 0.02
        
        self.rng = np.random.default_rng(random_seed)
        
        # Noise multiplier for dynamic noise changes
        self.noise_multiplier = 1.0
        
        # Dropout state
        self.forced_dropout_active = False
        self.forced_dropout_start = -1.0
        self.forced_dropout_end = -1.0
        
        # Delay buffer
        self.delay_buffer: deque = deque()
        
        # Timing
        self.last_measurement_time = -1.0
        
        # Status
        self.status = "Tracking"  # "Tracking", "Lost", "Delayed"

    def reset(self):
        """Reset camera state."""
        self.last_measurement_time = -1.0
        self.forced_dropout_active = False
        self.forced_dropout_start = -1.0
        self.forced_dropout_end = -1.0
        self.delay_buffer.clear()
        self.noise_multiplier = 1.0
        self.status = "Tracking"

    def set_noise_multiplier(self, multiplier: float):
        """Set noise multiplier for dynamic noise adjustment."""
        self.noise_multiplier = max(0.0, multiplier)

    def trigger_dropout(self, start_time: float, duration: float):
        """Trigger a forced detection dropout."""
        self.forced_dropout_start = start_time
        self.forced_dropout_end = start_time + duration
        self.forced_dropout_active = True

    def _check_fov(self, target_pos: np.ndarray, uav_pos: np.ndarray, uav_heading: float) -> bool:
        """
        Check if target is within camera field of view.
        
        Args:
            target_pos: [x, y] target position
            uav_pos: [x, y] UAV position  
            uav_heading: UAV heading angle (radians)
            
        Returns:
            True if target is within FOV
        """
        direction = target_pos - uav_pos
        distance = np.linalg.norm(direction)
        
        # Check range
        if distance > self.max_range:
            return False
        
        if distance < 1e-6:
            return True
        
        # Check angle
        bearing_to_target = np.arctan2(direction[1], direction[0])
        relative_angle = self._wrap_angle(bearing_to_target - uav_heading)
        
        return abs(relative_angle) <= self.fov_angle / 2

    def _check_dropout(self, t: float) -> bool:
        """
        Check if detection dropout is active.
        
        Returns:
            True if dropout is active (no detection available)
        """
        # Check forced dropout
        if self.forced_dropout_active:
            if self.forced_dropout_start <= t < self.forced_dropout_end:
                return True
            elif t >= self.forced_dropout_end:
                self.forced_dropout_active = False
        
        # Random dropout
        if self.dropout_probability > 0:
            if self.rng.random() < self.dropout_probability:
                return True
        
        return False

    def _compute_range_bearing(self, target_pos: np.ndarray, uav_pos: np.ndarray, 
                                uav_heading: float) -> np.ndarray:
        """
        Compute range and bearing measurement (without noise).
        
        Args:
            target_pos: [x, y] target position
            uav_pos: [x, y] UAV position
            uav_heading: UAV heading (radians)
            
        Returns:
            [range, bearing] measurement
        """
        diff = target_pos - uav_pos
        r = np.linalg.norm(diff)
        theta = np.arctan2(diff[1], diff[0]) - uav_heading
        theta = self._wrap_angle(theta)
        return np.array([r, theta])

    def _compute_xy(self, target_pos: np.ndarray) -> np.ndarray:
        """Compute direct XY measurement (without noise)."""
        return target_pos.copy()

    def _add_noise_range_bearing(self, measurement: np.ndarray) -> np.ndarray:
        """Add Gaussian noise to range/bearing measurement."""
        noise_r = self.rng.normal(0, self.noise_range_std * self.noise_multiplier)
        noise_theta = self.rng.normal(0, self.noise_bearing_std * self.noise_multiplier)
        noisy = measurement.copy()
        noisy[0] += noise_r
        noisy[0] = max(noisy[0], 0.01)  # Range must be positive
        noisy[1] += noise_theta
        noisy[1] = self._wrap_angle(noisy[1])
        return noisy

    def _add_noise_xy(self, measurement: np.ndarray) -> np.ndarray:
        """Add Gaussian noise to XY measurement."""
        noise = self.rng.normal(0, self.noise_xy_std * self.noise_multiplier, 2)
        return measurement + noise

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        """Wrap angle to [-pi, pi]."""
        return (angle + np.pi) % (2 * np.pi) - np.pi

    def measure(self, target_state, uav_pose: dict, t: float) -> Measurement:
        """
        Generate a camera measurement.
        
        Args:
            target_state: Target state with .x, .y attributes
            uav_pose: dict with 'x', 'y', 'heading' keys
            t: Current simulation time
            
        Returns:
            Measurement object
        """
        # Check measurement rate
        if t - self.last_measurement_time < self.measurement_period - 1e-6:
            return Measurement(data=None, timestamp=t, detected=False,
                             measurement_type=self.measurement_model,
                             sensor_pose=dict(uav_pose))
        
        self.last_measurement_time = t
        
        target_pos = np.array([target_state.x, target_state.y])
        uav_pos = np.array([uav_pose['x'], uav_pose['y']])
        uav_heading = uav_pose['heading']
        
        # Check FOV
        in_fov = self._check_fov(target_pos, uav_pos, uav_heading)
        if not in_fov:
            self.status = "Lost"
            return Measurement(data=None, timestamp=t, detected=False,
                             measurement_type=self.measurement_model,
                             sensor_pose=dict(uav_pose))
        
        # Check dropout
        if self._check_dropout(t):
            self.status = "Lost"
            return Measurement(data=None, timestamp=t, detected=False,
                             measurement_type=self.measurement_model,
                             sensor_pose=dict(uav_pose))
        
        # Compute measurement
        if self.measurement_model == "range_bearing":
            raw = self._compute_range_bearing(target_pos, uav_pos, uav_heading)
            noisy = self._add_noise_range_bearing(raw)
        else:  # "xy"
            raw = self._compute_xy(target_pos)
            noisy = self._add_noise_xy(raw)
        
        measurement = Measurement(
            data=noisy,
            timestamp=t,
            detected=True,
            measurement_type=self.measurement_model,
            raw_data=raw,
            sensor_pose=dict(uav_pose)
        )
        
        # Handle delay
        if self.delay > 0:
            self.delay_buffer.append(measurement.copy())
            self.status = "Delayed"
            
            # Return delayed measurement if available
            while len(self.delay_buffer) > 0:
                oldest = self.delay_buffer[0]
                if t - oldest.timestamp >= self.delay:
                    delayed_meas = self.delay_buffer.popleft()
                    delayed_meas.timestamp = oldest.timestamp  # Keep original timestamp
                    return delayed_meas
                break
            
            # No measurement available yet due to delay
            return Measurement(data=None, timestamp=t, detected=False,
                             measurement_type=self.measurement_model,
                             sensor_pose=dict(uav_pose))
        
        self.status = "Tracking"
        return measurement

    def get_measurement_noise_covariance(self) -> np.ndarray:
        """
        Get measurement noise covariance matrix R.
        
        Returns:
            R matrix (2x2)
        """
        if self.measurement_model == "range_bearing":
            R = np.diag([
                (self.noise_range_std * self.noise_multiplier) ** 2,
                (self.noise_bearing_std * self.noise_multiplier) ** 2
            ])
        else:
            R = np.diag([
                (self.noise_xy_std * self.noise_multiplier) ** 2,
                (self.noise_xy_std * self.noise_multiplier) ** 2
            ])
        return R

    @staticmethod
    def measurement_function_range_bearing(state: np.ndarray, uav_pose: dict) -> np.ndarray:
        """
        Nonlinear measurement function h(x) for range/bearing.
        
        Args:
            state: [x, y, vx, vy] target state
            uav_pose: dict with 'x', 'y', 'heading'
            
        Returns:
            [range, bearing] predicted measurement
        """
        dx = state[0] - uav_pose['x']
        dy = state[1] - uav_pose['y']
        r = np.sqrt(dx**2 + dy**2)
        theta = np.arctan2(dy, dx) - uav_pose['heading']
        theta = (theta + np.pi) % (2 * np.pi) - np.pi
        return np.array([r, theta])

    @staticmethod
    def measurement_jacobian_range_bearing(state: np.ndarray, uav_pose: dict) -> np.ndarray:
        """
        Jacobian of the range/bearing measurement function.
        
        H = dh/dx evaluated at current state.
        
        Args:
            state: [x, y, vx, vy] target state
            uav_pose: dict with 'x', 'y', 'heading'
            
        Returns:
            H matrix (2x4) Jacobian
        """
        dx = state[0] - uav_pose['x']
        dy = state[1] - uav_pose['y']
        r_sq = dx**2 + dy**2
        r = np.sqrt(r_sq)
        
        if r < 1e-6:
            return np.zeros((2, 4))
        
        H = np.array([
            [dx / r, dy / r, 0, 0],
            [-dy / r_sq, dx / r_sq, 0, 0]
        ])
        return H

    @staticmethod
    def measurement_function_xy(state: np.ndarray, uav_pose: dict) -> np.ndarray:
        """Linear measurement function h(x) for XY model."""
        return np.array([state[0], state[1]])

    @staticmethod
    def measurement_jacobian_xy(state: np.ndarray, uav_pose: dict) -> np.ndarray:
        """Jacobian for XY measurement (constant)."""
        return np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
