"""
PID Controller for UAV Target Tracking.

Implements discrete PID with:
- Two-axis control (X, Y)
- Anti-windup (integral clamping)
- Derivative filtering
- Acceleration saturation
- Desired following distance

The PID uses estimated target state (from EKF/UKF), NOT ground truth.
"""

import numpy as np
from typing import Optional


class PIDController:
    """
    Discrete PID controller for UAV pursuit/tracking.
    
    Computes acceleration commands to maintain desired following distance
    behind the target.
    
    Error:
        e_x = x_desired - x_uav
        e_y = y_desired - y_uav
    
    Control:
        a_x = Kp * e_x + Ki * integral(e_x) + Kd * d(e_x)/dt
        a_y = Kp * e_y + Ki * integral(e_y) + Kd * d(e_y)/dt
    """

    def __init__(self,
                 kp: float = 2.0,
                 ki: float = 0.1,
                 kd: float = 1.5,
                 desired_distance: float = 50.0,
                 integral_limit: float = 50.0,
                 derivative_filter: float = 0.1,
                 max_acceleration: float = 25.0):
        """
        Initialize PID controller.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            desired_distance: Desired following distance (m)
            integral_limit: Anti-windup integral clamp
            derivative_filter: Low-pass filter coefficient for derivative (0-1)
            max_acceleration: Maximum output acceleration
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.desired_distance = desired_distance
        self.integral_limit = integral_limit
        self.derivative_filter = derivative_filter
        self.max_acceleration = max_acceleration
        
        # Internal state
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.prev_error_x = 0.0
        self.prev_error_y = 0.0
        self.prev_derivative_x = 0.0
        self.prev_derivative_y = 0.0
        self.initialized = False

    def reset(self):
        """Reset PID internal state."""
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.prev_error_x = 0.0
        self.prev_error_y = 0.0
        self.prev_derivative_x = 0.0
        self.prev_derivative_y = 0.0
        self.initialized = False

    def compute_desired_position(self, estimated_target_state: dict, 
                                  uav_state) -> np.ndarray:
        """
        Compute the desired UAV position based on estimated target state.
        
        Desired position is behind the target at desired_distance along
        the target's velocity direction.
        
        p_desired = p_target - d_desired * v_hat_target
        
        If target speed is near zero, desired position is at target position
        minus desired_distance in the UAV-to-target direction.
        
        Args:
            estimated_target_state: dict with 'x', 'y', 'vx', 'vy'
            uav_state: UAV state with .x, .y attributes
            
        Returns:
            Desired position [x, y]
        """
        target_pos = np.array([estimated_target_state['x'], estimated_target_state['y']])
        target_vel = np.array([estimated_target_state['vx'], estimated_target_state['vy']])
        uav_pos = np.array([uav_state.x, uav_state.y])
        
        target_speed = np.linalg.norm(target_vel)
        
        if target_speed > 1.0:
            # Follow behind target along velocity direction
            v_hat = target_vel / target_speed
            desired_pos = target_pos - self.desired_distance * v_hat
        else:
            # Target nearly stationary: maintain distance from UAV direction
            direction = target_pos - uav_pos
            dist = np.linalg.norm(direction)
            if dist > 1e-3:
                d_hat = direction / dist
                desired_pos = target_pos - self.desired_distance * d_hat
            else:
                desired_pos = target_pos - np.array([self.desired_distance, 0])
        
        return desired_pos

    def compute(self, estimated_target_state: dict, uav_state, dt: float) -> np.ndarray:
        """
        Compute PID acceleration command.
        
        Args:
            estimated_target_state: dict with 'x', 'y', 'vx', 'vy'
                                     (from EKF or UKF, NOT ground truth)
            uav_state: UAV state with .x, .y, .vx, .vy
            dt: Timestep (seconds)
            
        Returns:
            Acceleration command [ax, ay] (m/s^2)
        """
        if dt < 1e-8:
            return np.array([0.0, 0.0])
        
        # Compute desired position
        desired_pos = self.compute_desired_position(estimated_target_state, uav_state)
        
        # Compute error
        error_x = desired_pos[0] - uav_state.x
        error_y = desired_pos[1] - uav_state.y
        
        if not self.initialized:
            self.prev_error_x = error_x
            self.prev_error_y = error_y
            self.initialized = True
        
        # --- Proportional ---
        p_x = self.kp * error_x
        p_y = self.kp * error_y
        
        # --- Integral with anti-windup ---
        self.integral_x += error_x * dt
        self.integral_y += error_y * dt
        
        # Clamp integral
        self.integral_x = np.clip(self.integral_x, -self.integral_limit, self.integral_limit)
        self.integral_y = np.clip(self.integral_y, -self.integral_limit, self.integral_limit)
        
        i_x = self.ki * self.integral_x
        i_y = self.ki * self.integral_y
        
        # --- Derivative with filtering ---
        raw_derivative_x = (error_x - self.prev_error_x) / dt
        raw_derivative_y = (error_y - self.prev_error_y) / dt
        
        # Low-pass filter on derivative
        alpha = self.derivative_filter
        filtered_derivative_x = alpha * raw_derivative_x + (1 - alpha) * self.prev_derivative_x
        filtered_derivative_y = alpha * raw_derivative_y + (1 - alpha) * self.prev_derivative_y
        
        d_x = self.kd * filtered_derivative_x
        d_y = self.kd * filtered_derivative_y
        
        # Store for next iteration
        self.prev_error_x = error_x
        self.prev_error_y = error_y
        self.prev_derivative_x = filtered_derivative_x
        self.prev_derivative_y = filtered_derivative_y
        
        # --- Total command ---
        ax = p_x + i_x + d_x
        ay = p_y + i_y + d_y
        
        # Saturate acceleration
        acc = np.array([ax, ay])
        mag = np.linalg.norm(acc)
        if mag > self.max_acceleration:
            acc = acc * (self.max_acceleration / mag)
        
        return acc

    def get_status(self) -> dict:
        """Get PID controller status for telemetry."""
        return {
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'integral_x': self.integral_x,
            'integral_y': self.integral_y,
            'prev_error_x': self.prev_error_x,
            'prev_error_y': self.prev_error_y,
            'desired_distance': self.desired_distance
        }
