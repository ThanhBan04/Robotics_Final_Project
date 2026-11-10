"""
Tracking Evaluation Module.

Computes PID / UAV tracking performance metrics:
- Tracking RMSE, settling time, overshoot
- Recovery time after dropout
- Maximum separation, tracking success rate
"""

import numpy as np
from typing import List, Dict, Any


class TrackingEvaluator:
    """Evaluates UAV tracking performance."""

    def __init__(self, desired_distance: float = 50.0):
        self.desired_distance = desired_distance
        self.reset()

    def reset(self):
        self.timestamps: List[float] = []
        self.tracking_distances: List[float] = []
        self.tracking_errors: List[float] = []
        self.uav_speeds: List[float] = []
        self.target_speeds: List[float] = []
        self.pid_commands_x: List[float] = []
        self.pid_commands_y: List[float] = []

    def add_step(self, step):
        """Add data from one simulation step."""
        self.timestamps.append(step.time)
        if step.target_gt and step.uav_state:
            self.tracking_distances.append(step.tracking_distance)
            self.tracking_errors.append(abs(step.tracking_distance - self.desired_distance))
            self.uav_speeds.append(step.uav_state.speed())
            self.target_speeds.append(step.target_gt.speed())
        if step.pid_command is not None:
            self.pid_commands_x.append(step.pid_command[0])
            self.pid_commands_y.append(step.pid_command[1])

    def compute_metrics(self) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        if not self.tracking_errors:
            return metrics
        arr_err = np.array(self.tracking_errors)
        arr_dist = np.array(self.tracking_distances)
        metrics['tracking_rmse'] = float(np.sqrt(np.mean(arr_err**2)))
        metrics['mean_tracking_error'] = float(np.mean(arr_err))
        metrics['max_tracking_error'] = float(np.max(arr_err))
        metrics['mean_tracking_distance'] = float(np.mean(arr_dist))
        metrics['max_tracking_distance'] = float(np.max(arr_dist))
        metrics['min_tracking_distance'] = float(np.min(arr_dist))
        metrics['max_separation'] = float(np.max(arr_dist))

        # Settling time: first time tracking error < 10% of desired_distance
        threshold = self.desired_distance * 0.1
        settling = None
        for i, e in enumerate(self.tracking_errors):
            if e < threshold:
                settling = self.timestamps[i]
                break
        metrics['settling_time'] = settling

        # Tracking success rate: fraction of time within threshold
        within = np.sum(arr_err < threshold)
        metrics['tracking_success_rate'] = float(within / len(arr_err)) if len(arr_err) > 0 else 0.0

        if self.uav_speeds:
            metrics['mean_uav_speed'] = float(np.mean(self.uav_speeds))
            metrics['max_uav_speed'] = float(np.max(self.uav_speeds))
        if self.target_speeds:
            metrics['mean_target_speed'] = float(np.mean(self.target_speeds))
            metrics['max_target_speed'] = float(np.max(self.target_speeds))

        return metrics

    def get_time_series(self) -> Dict[str, Any]:
        return {
            'timestamps': self.timestamps,
            'tracking_distances': self.tracking_distances,
            'tracking_errors': self.tracking_errors,
            'uav_speeds': self.uav_speeds,
            'target_speeds': self.target_speeds,
            'pid_commands_x': self.pid_commands_x,
            'pid_commands_y': self.pid_commands_y,
        }
