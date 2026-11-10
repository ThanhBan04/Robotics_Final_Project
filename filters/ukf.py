"""
Unscented Kalman Filter (UKF) Implementation.

Self-implemented using NumPy with Unscented Transform.
Uses sigma points instead of Jacobian linearization.

State vector: [x, y, vx, vy] (4-dimensional)
Measurement: [range, bearing] or [x, y] depending on camera model.
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class UKFEstimate:
    """UKF estimation result."""
    state: np.ndarray        # [x, y, vx, vy]
    covariance: np.ndarray   # 4x4 covariance matrix
    timestamp: float
    innovation: Optional[np.ndarray] = None
    innovation_covariance: Optional[np.ndarray] = None
    kalman_gain: Optional[np.ndarray] = None
    updated: bool = False


class UnscentedKalmanFilter:
    """
    Unscented Kalman Filter for target state estimation.
    
    Uses the Unscented Transform to propagate mean and covariance
    through nonlinear functions, avoiding Jacobian computation.
    
    Sigma points: 2n+1 points where n is state dimension.
    """

    def __init__(self,
                 state_dim: int = 4,
                 measurement_dim: int = 2,
                 dt: float = 0.02,
                 process_noise_q: float = 5.0,
                 measurement_model: str = "range_bearing",
                 alpha: float = 0.1,
                 beta: float = 2.0,
                 kappa: float = 0.0):
        """
        Initialize UKF.
        
        Args:
            state_dim: Dimension of state vector
            measurement_dim: Dimension of measurement vector
            dt: Default timestep
            process_noise_q: Process noise intensity
            measurement_model: "range_bearing" or "xy"
            alpha: Spread of sigma points (small positive, e.g. 1e-3 to 1)
            beta: Prior knowledge about distribution (2 is optimal for Gaussian)
            kappa: Secondary scaling parameter (usually 0 or 3-n)
        """
        self.n = state_dim
        self.m = measurement_dim
        self.dt = dt
        self.process_noise_q = process_noise_q
        self.measurement_model = measurement_model
        
        # UKF scaling parameters
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        self.lam = alpha**2 * (self.n + kappa) - self.n  # Lambda
        
        # Compute sigma point weights
        self.n_sigma = 2 * self.n + 1
        self.Wm, self.Wc = self._compute_weights()
        
        # State and covariance
        self.x = np.zeros(self.n)
        self.P = np.eye(self.n) * 100
        
        # Noise covariance
        self.Q = self._compute_Q(dt)
        self.R = np.eye(self.m)
        
        self.initialized = False

    def _compute_weights(self):
        """
        Compute sigma point weights for mean (Wm) and covariance (Wc).
        """
        n = self.n
        lam = self.lam
        
        Wm = np.zeros(self.n_sigma)
        Wc = np.zeros(self.n_sigma)
        
        # Weight for central sigma point
        Wm[0] = lam / (n + lam)
        Wc[0] = lam / (n + lam) + (1 - self.alpha**2 + self.beta)
        
        # Weights for other sigma points
        w = 1.0 / (2 * (n + lam))
        for i in range(1, self.n_sigma):
            Wm[i] = w
            Wc[i] = w
        
        return Wm, Wc

    def initialize(self, x0: np.ndarray, P0: Optional[np.ndarray] = None):
        """Initialize filter state and covariance."""
        self.x = x0.copy()
        if P0 is not None:
            self.P = P0.copy()
        else:
            self.P = np.diag([50, 50, 10, 10]).astype(float)
        self.initialized = True

    def set_measurement_noise(self, R: np.ndarray):
        """Set measurement noise covariance R."""
        self.R = R.copy()

    def _compute_Q(self, dt: float) -> np.ndarray:
        """Compute process noise covariance Q."""
        q = self.process_noise_q
        Q = q * np.array([
            [dt**3 / 3, 0, dt**2 / 2, 0],
            [0, dt**3 / 3, 0, dt**2 / 2],
            [dt**2 / 2, 0, dt, 0],
            [0, dt**2 / 2, 0, dt]
        ])
        return Q

    def _generate_sigma_points(self, x: np.ndarray, P: np.ndarray) -> np.ndarray:
        """
        Generate sigma points using the scaled unscented transform.
        
        Sigma points: 
            X_0 = x
            X_i = x + sqrt((n + lambda) * P)_i   for i = 1,...,n
            X_{i+n} = x - sqrt((n + lambda) * P)_i   for i = 1,...,n
        
        Returns:
            Sigma points matrix (n_sigma x n)
        """
        n = self.n
        sigma_points = np.zeros((self.n_sigma, n))
        
        # Matrix square root with robust regularization
        scale = (n + self.lam)
        scaled_P = scale * P
        # Ensure symmetry
        scaled_P = (scaled_P + scaled_P.T) / 2
        for attempt in range(5):
            try:
                sqrt_P = np.linalg.cholesky(scaled_P)
                break
            except np.linalg.LinAlgError:
                # Progressively stronger regularization
                reg = 10 ** (attempt - 5)
                scaled_P = scaled_P + np.eye(n) * reg
                # Force positive eigenvalues
                eigvals, eigvecs = np.linalg.eigh(scaled_P)
                eigvals = np.maximum(eigvals, reg)
                scaled_P = eigvecs @ np.diag(eigvals) @ eigvecs.T
        else:
            # Last resort: use diagonal
            sqrt_P = np.diag(np.sqrt(np.maximum(np.diag(scaled_P), 1e-6)))
        
        sigma_points[0] = x
        
        for i in range(n):
            sigma_points[i + 1] = x + sqrt_P[i]
            sigma_points[i + 1 + n] = x - sqrt_P[i]
        
        return sigma_points

    def _state_transition(self, x: np.ndarray, dt: float) -> np.ndarray:
        """State transition function f(x): Constant Velocity model."""
        x_new = np.zeros_like(x)
        x_new[0] = x[0] + x[2] * dt
        x_new[1] = x[1] + x[3] * dt
        x_new[2] = x[2]
        x_new[3] = x[3]
        return x_new

    def _measurement_function(self, x: np.ndarray, uav_pose: dict) -> np.ndarray:
        """Measurement function h(x)."""
        if self.measurement_model == "range_bearing":
            dx = x[0] - uav_pose['x']
            dy = x[1] - uav_pose['y']
            r = np.sqrt(dx**2 + dy**2)
            theta = np.arctan2(dy, dx) - uav_pose['heading']
            theta = self._wrap_angle(theta)
            return np.array([r, theta])
        else:
            return np.array([x[0], x[1]])

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        """Wrap angle to [-pi, pi]."""
        return (angle + np.pi) % (2 * np.pi) - np.pi

    def _compute_weighted_mean(self, sigma_points: np.ndarray, 
                                has_angle: bool = False,
                                angle_idx: int = -1) -> np.ndarray:
        """
        Compute weighted mean of sigma points.
        For circular quantities (angles), use circular mean.
        """
        mean = np.zeros(sigma_points.shape[1])
        
        if has_angle and angle_idx >= 0:
            # Handle circular mean for angle component
            sin_sum = 0.0
            cos_sum = 0.0
            for i in range(self.n_sigma):
                if sigma_points.shape[1] > angle_idx:
                    sin_sum += self.Wm[i] * np.sin(sigma_points[i, angle_idx])
                    cos_sum += self.Wm[i] * np.cos(sigma_points[i, angle_idx])
            
            for j in range(sigma_points.shape[1]):
                if j == angle_idx:
                    mean[j] = np.arctan2(sin_sum, cos_sum)
                else:
                    mean[j] = np.sum(self.Wm * sigma_points[:, j])
        else:
            for j in range(sigma_points.shape[1]):
                mean[j] = np.sum(self.Wm * sigma_points[:, j])
        
        return mean

    def _compute_weighted_covariance(self, sigma_points: np.ndarray, mean: np.ndarray,
                                      has_angle: bool = False,
                                      angle_idx: int = -1) -> np.ndarray:
        """Compute weighted covariance of sigma points."""
        dim = sigma_points.shape[1]
        cov = np.zeros((dim, dim))
        
        for i in range(self.n_sigma):
            diff = sigma_points[i] - mean
            if has_angle and angle_idx >= 0:
                diff[angle_idx] = self._wrap_angle(diff[angle_idx])
            cov += self.Wc[i] * np.outer(diff, diff)
        
        return cov

    def predict(self, dt: Optional[float] = None) -> UKFEstimate:
        """
        UKF Prediction step using sigma points.
        
        1. Generate sigma points
        2. Propagate through state transition
        3. Compute predicted mean and covariance
        """
        if dt is None:
            dt = self.dt
        
        # Generate sigma points
        sigma_points = self._generate_sigma_points(self.x, self.P)
        
        # Propagate sigma points through state transition
        sigma_pred = np.zeros_like(sigma_points)
        for i in range(self.n_sigma):
            sigma_pred[i] = self._state_transition(sigma_points[i], dt)
        
        # Compute predicted mean
        self.x = self._compute_weighted_mean(sigma_pred)
        
        # Compute predicted covariance
        Q = self._compute_Q(dt)
        self.P = self._compute_weighted_covariance(sigma_pred, self.x) + Q
        
        # Ensure symmetry and positive definiteness
        self.P = (self.P + self.P.T) / 2
        # Enforce minimum eigenvalues
        eigvals, eigvecs = np.linalg.eigh(self.P)
        eigvals = np.maximum(eigvals, 1e-8)
        self.P = eigvecs @ np.diag(eigvals) @ eigvecs.T
        
        # Store predicted sigma points for update step
        self._sigma_pred = sigma_pred
        
        return UKFEstimate(
            state=self.x.copy(),
            covariance=self.P.copy(),
            timestamp=0.0,
            updated=False
        )

    def update(self, z: np.ndarray, uav_pose: dict, timestamp: float = 0.0) -> UKFEstimate:
        """
        UKF Measurement Update step.
        
        1. Regenerate sigma points from predicted state
        2. Transform through measurement function
        3. Compute innovation, cross-covariance, and Kalman gain
        4. Update state and covariance
        """
        has_bearing = (self.measurement_model == "range_bearing")
        bearing_idx = 1 if has_bearing else -1
        
        # Generate fresh sigma points from predicted state
        sigma_points = self._generate_sigma_points(self.x, self.P)
        
        # Transform sigma points through measurement function
        sigma_z = np.zeros((self.n_sigma, self.m))
        for i in range(self.n_sigma):
            sigma_z[i] = self._measurement_function(sigma_points[i], uav_pose)
        
        # Predicted measurement mean
        z_pred = self._compute_weighted_mean(sigma_z, has_angle=has_bearing, angle_idx=bearing_idx)
        
        # Innovation covariance S
        S = self.R.copy()
        for i in range(self.n_sigma):
            diff_z = sigma_z[i] - z_pred
            if has_bearing:
                diff_z[bearing_idx] = self._wrap_angle(diff_z[bearing_idx])
            S += self.Wc[i] * np.outer(diff_z, diff_z)
        
        # Cross covariance Pxz
        Pxz = np.zeros((self.n, self.m))
        for i in range(self.n_sigma):
            diff_x = sigma_points[i] - self.x
            diff_z = sigma_z[i] - z_pred
            if has_bearing:
                diff_z[bearing_idx] = self._wrap_angle(diff_z[bearing_idx])
            Pxz += self.Wc[i] * np.outer(diff_x, diff_z)
        
        # Kalman gain
        try:
            K = Pxz @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            K = Pxz @ np.linalg.pinv(S)
        
        # Innovation
        y = z - z_pred
        if has_bearing:
            y[bearing_idx] = self._wrap_angle(y[bearing_idx])
        
        # State update
        self.x = self.x + K @ y
        
        # Covariance update
        self.P = self.P - K @ S @ K.T
        
        # Ensure symmetry and positive definiteness
        self.P = (self.P + self.P.T) / 2
        eigvals, eigvecs = np.linalg.eigh(self.P)
        eigvals = np.maximum(eigvals, 1e-8)
        self.P = eigvecs @ np.diag(eigvals) @ eigvecs.T
        
        return UKFEstimate(
            state=self.x.copy(),
            covariance=self.P.copy(),
            timestamp=timestamp,
            innovation=y.copy(),
            innovation_covariance=S.copy(),
            kalman_gain=K.copy(),
            updated=True
        )

    def step(self, measurement_data: Optional[np.ndarray], uav_pose: dict,
             dt: Optional[float] = None, timestamp: float = 0.0) -> UKFEstimate:
        """
        Complete UKF step: predict + update (if measurement available).
        """
        estimate = self.predict(dt)
        
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
