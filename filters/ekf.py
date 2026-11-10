"""
Extended Kalman Filter (EKF) Implementation.

Self-implemented using NumPy for understanding and transparency.
Supports nonlinear measurement models (range/bearing).

State vector: [x, y, vx, vy] (4-dimensional)
Measurement: [range, bearing] or [x, y] depending on camera model.
"""

import numpy as np
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class EKFEstimate:
    """EKF estimation result."""
    state: np.ndarray        # [x, y, vx, vy]
    covariance: np.ndarray   # 4x4 covariance matrix
    timestamp: float
    innovation: Optional[np.ndarray] = None  # Innovation (residual)
    innovation_covariance: Optional[np.ndarray] = None
    kalman_gain: Optional[np.ndarray] = None
    updated: bool = False    # Whether measurement update was performed


class ExtendedKalmanFilter:
    """
    Extended Kalman Filter for target state estimation.
    
    Prediction:
        x_pred = F * x + B * u (if applicable)
        P_pred = F * P * F^T + Q
    
    Update (linearized):
        H = dh/dx |_{x_pred}  (Jacobian)
        y = z - h(x_pred)     (innovation)
        S = H * P_pred * H^T + R
        K = P_pred * H^T * S^{-1}
        x_upd = x_pred + K * y
        P_upd = (I - K * H) * P_pred * (I - K * H)^T + K * R * K^T  (Joseph form)
    """

    def __init__(self,
                 state_dim: int = 4,
                 measurement_dim: int = 2,
                 dt: float = 0.02,
                 process_noise_q: float = 5.0,
                 measurement_model: str = "range_bearing"):
        """
        Initialize EKF.
        
        Args:
            state_dim: Dimension of state vector
            measurement_dim: Dimension of measurement vector
            dt: Default timestep
            process_noise_q: Process noise intensity parameter
            measurement_model: "range_bearing" or "xy"
        """
        self.n = state_dim
        self.m = measurement_dim
        self.dt = dt
        self.process_noise_q = process_noise_q
        self.measurement_model = measurement_model
        
        # State and covariance
        self.x = np.zeros(self.n)       # State estimate
        self.P = np.eye(self.n) * 100   # State covariance (initially large)
        
        # Noise covariance matrices
        self.Q = self._compute_Q(dt)    # Process noise
        self.R = np.eye(self.m)         # Measurement noise (set externally)
        
        self.initialized = False

    def initialize(self, x0: np.ndarray, P0: Optional[np.ndarray] = None):
        """
        Initialize filter state and covariance.
        
        Args:
            x0: Initial state estimate [x, y, vx, vy]
            P0: Initial covariance (4x4), or None for default
        """
        self.x = x0.copy()
        if P0 is not None:
            self.P = P0.copy()
        else:
            self.P = np.diag([50, 50, 10, 10]).astype(float)
        self.initialized = True

    def set_measurement_noise(self, R: np.ndarray):
        """Set measurement noise covariance matrix R."""
        self.R = R.copy()

    def _compute_Q(self, dt: float) -> np.ndarray:
        """
        Compute process noise covariance matrix Q.
        Uses continuous white noise acceleration model.
        """
        q = self.process_noise_q
        Q = q * np.array([
            [dt**3 / 3, 0, dt**2 / 2, 0],
            [0, dt**3 / 3, 0, dt**2 / 2],
            [dt**2 / 2, 0, dt, 0],
            [0, dt**2 / 2, 0, dt]
        ])
        return Q

    def _state_transition(self, x: np.ndarray, dt: float) -> np.ndarray:
        """
        State transition function f(x): Constant Velocity model.
        
        x_{k+1} = F * x_k
        """
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        return F @ x

    def _state_transition_jacobian(self, dt: float) -> np.ndarray:
        """Jacobian of state transition (F matrix for CV model)."""
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        return F

    def _measurement_function(self, x: np.ndarray, uav_pose: dict) -> np.ndarray:
        """
        Measurement function h(x).
        
        For range/bearing:
            h(x) = [sqrt((x-xu)^2 + (y-yu)^2), atan2(y-yu, x-xu) - heading]
        For xy:
            h(x) = [x, y]
        """
        if self.measurement_model == "range_bearing":
            dx = x[0] - uav_pose['x']
            dy = x[1] - uav_pose['y']
            r = np.sqrt(dx**2 + dy**2)
            theta = np.arctan2(dy, dx) - uav_pose['heading']
            theta = self._wrap_angle(theta)
            return np.array([r, theta])
        else:
            return np.array([x[0], x[1]])

    def _measurement_jacobian(self, x: np.ndarray, uav_pose: dict) -> np.ndarray:
        """
        Jacobian of measurement function H = dh/dx.
        """
        if self.measurement_model == "range_bearing":
            dx = x[0] - uav_pose['x']
            dy = x[1] - uav_pose['y']
            r_sq = dx**2 + dy**2
            r = np.sqrt(r_sq)
            
            if r < 1e-6:
                return np.zeros((2, 4))
            
            H = np.array([
                [dx / r, dy / r, 0, 0],
                [-dy / r_sq, dx / r_sq, 0, 0]
            ])
            return H
        else:
            return np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0]
            ], dtype=float)

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        """Wrap angle to [-pi, pi]."""
        return (angle + np.pi) % (2 * np.pi) - np.pi

    def predict(self, dt: Optional[float] = None) -> EKFEstimate:
        """
        EKF Prediction step.
        
        x_pred = f(x)
        P_pred = F * P * F^T + Q
        
        Args:
            dt: Timestep (uses default if None)
            
        Returns:
            Predicted EKF estimate
        """
        if dt is None:
            dt = self.dt
        
        # State prediction
        F = self._state_transition_jacobian(dt)
        self.x = self._state_transition(self.x, dt)
        
        # Covariance prediction
        Q = self._compute_Q(dt)
        self.P = F @ self.P @ F.T + Q
        
        # Ensure symmetry
        self.P = (self.P + self.P.T) / 2
        
        return EKFEstimate(
            state=self.x.copy(),
            covariance=self.P.copy(),
            timestamp=0.0,
            updated=False
        )

    def update(self, z: np.ndarray, uav_pose: dict, timestamp: float = 0.0) -> EKFEstimate:
        """
        EKF Measurement Update step.
        
        Args:
            z: Measurement vector [range, bearing] or [x, y]
            uav_pose: UAV pose dict with 'x', 'y', 'heading'
            timestamp: Measurement timestamp
            
        Returns:
            Updated EKF estimate
        """
        # Predicted measurement
        z_pred = self._measurement_function(self.x, uav_pose)
        
        # Innovation (residual)
        y = z - z_pred
        
        # Wrap bearing angle in innovation if range/bearing model
        if self.measurement_model == "range_bearing":
            y[1] = self._wrap_angle(y[1])
        
        # Measurement Jacobian
        H = self._measurement_jacobian(self.x, uav_pose)
        
        # Innovation covariance
        S = H @ self.P @ H.T + self.R
        
        # Kalman gain
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            # Fallback: use pseudoinverse
            K = self.P @ H.T @ np.linalg.pinv(S)
        
        # State update
        self.x = self.x + K @ y
        
        # Covariance update (Joseph form for numerical stability)
        I_KH = np.eye(self.n) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ self.R @ K.T
        
        # Ensure symmetry
        self.P = (self.P + self.P.T) / 2
        
        return EKFEstimate(
            state=self.x.copy(),
            covariance=self.P.copy(),
            timestamp=timestamp,
            innovation=y.copy(),
            innovation_covariance=S.copy(),
            kalman_gain=K.copy(),
            updated=True
        )

    def step(self, measurement_data: Optional[np.ndarray], uav_pose: dict,
             dt: Optional[float] = None, timestamp: float = 0.0) -> EKFEstimate:
        """
        Complete EKF step: predict + update (if measurement available).
        
        Args:
            measurement_data: Measurement vector, or None if no detection
            uav_pose: UAV pose dict
            dt: Timestep
            timestamp: Current time
            
        Returns:
            EKF estimate
        """
        # Prediction
        estimate = self.predict(dt)
        
        # Update only if measurement is available
        if measurement_data is not None:
            estimate = self.update(measurement_data, uav_pose, timestamp)
        
        estimate.timestamp = timestamp
        return estimate

    def get_estimated_state(self) -> dict:
        """Get estimated state as dictionary."""
        return {
            'x': self.x[0],
            'y': self.x[1],
            'vx': self.x[2],
            'vy': self.x[3]
        }
