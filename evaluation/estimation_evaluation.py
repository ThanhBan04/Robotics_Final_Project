"""
Estimation Evaluation Module.

Computes metrics for EKF/UKF comparison:
- Position RMSE, Velocity RMSE
- Per-axis errors, Recovery after dropout
"""

import numpy as np
from typing import List, Dict, Any


class EstimationEvaluator:
    """Evaluates filter estimation performance."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.ekf_pos_errors: List[float] = []
        self.ukf_pos_errors: List[float] = []
        self.ekf_vel_errors: List[float] = []
        self.ukf_vel_errors: List[float] = []
        self.ekf_x_errors: List[float] = []
        self.ekf_y_errors: List[float] = []
        self.ukf_x_errors: List[float] = []
        self.ukf_y_errors: List[float] = []
        self.timestamps: List[float] = []
        self.detection_status: List[bool] = []

    def add_step(self, step):
        """Add data from one simulation step."""
        self.timestamps.append(step.time)
        detected = step.measurement.detected if step.measurement else False
        self.detection_status.append(detected)
        gt = step.target_gt
        if gt is None:
            return

        if step.ekf_estimate:
            ex = step.ekf_estimate['x'] - gt.x
            ey = step.ekf_estimate['y'] - gt.y
            evx = step.ekf_estimate['vx'] - gt.vx
            evy = step.ekf_estimate['vy'] - gt.vy
            self.ekf_x_errors.append(ex)
            self.ekf_y_errors.append(ey)
            self.ekf_pos_errors.append(np.sqrt(ex**2 + ey**2))
            self.ekf_vel_errors.append(np.sqrt(evx**2 + evy**2))

        if step.ukf_estimate:
            ex = step.ukf_estimate['x'] - gt.x
            ey = step.ukf_estimate['y'] - gt.y
            evx = step.ukf_estimate['vx'] - gt.vx
            evy = step.ukf_estimate['vy'] - gt.vy
            self.ukf_x_errors.append(ex)
            self.ukf_y_errors.append(ey)
            self.ukf_pos_errors.append(np.sqrt(ex**2 + ey**2))
            self.ukf_vel_errors.append(np.sqrt(evx**2 + evy**2))

    def compute_metrics(self) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        if self.ekf_pos_errors:
            arr = np.array(self.ekf_pos_errors)
            metrics['ekf_position_rmse'] = float(np.sqrt(np.mean(arr**2)))
            metrics['ekf_position_max'] = float(np.max(arr))
            metrics['ekf_position_mean'] = float(np.mean(arr))
            metrics['ekf_velocity_rmse'] = float(np.sqrt(np.mean(np.array(self.ekf_vel_errors)**2)))
            metrics['ekf_x_rmse'] = float(np.sqrt(np.mean(np.array(self.ekf_x_errors)**2)))
            metrics['ekf_y_rmse'] = float(np.sqrt(np.mean(np.array(self.ekf_y_errors)**2)))
        if self.ukf_pos_errors:
            arr = np.array(self.ukf_pos_errors)
            metrics['ukf_position_rmse'] = float(np.sqrt(np.mean(arr**2)))
            metrics['ukf_position_max'] = float(np.max(arr))
            metrics['ukf_position_mean'] = float(np.mean(arr))
            metrics['ukf_velocity_rmse'] = float(np.sqrt(np.mean(np.array(self.ukf_vel_errors)**2)))
            metrics['ukf_x_rmse'] = float(np.sqrt(np.mean(np.array(self.ukf_x_errors)**2)))
            metrics['ukf_y_rmse'] = float(np.sqrt(np.mean(np.array(self.ukf_y_errors)**2)))
        metrics['dropout_recovery'] = self._analyze_dropout_recovery()
        return metrics

    def _analyze_dropout_recovery(self) -> Dict[str, Any]:
        recovery: Dict[str, Any] = {'periods': []}
        in_dropout = False
        dropout_start = 0
        for i, detected in enumerate(self.detection_status):
            if not detected and not in_dropout:
                in_dropout = True
                dropout_start = i
            elif detected and in_dropout:
                in_dropout = False
                dropout_end = i
                before_start = max(0, dropout_start - 50)
                after_end = min(len(self.detection_status), dropout_end + 100)
                period: Dict[str, Any] = {
                    'start_idx': dropout_start,
                    'end_idx': dropout_end,
                    'duration_steps': dropout_end - dropout_start,
                }
                if self.ekf_pos_errors and len(self.ekf_pos_errors) > dropout_end:
                    period['ekf_error_before'] = float(np.mean(self.ekf_pos_errors[before_start:dropout_start]) if dropout_start > before_start else 0)
                    period['ekf_error_during'] = float(np.mean(self.ekf_pos_errors[dropout_start:dropout_end]))
                    period['ekf_error_after'] = float(np.mean(self.ekf_pos_errors[dropout_end:after_end]) if after_end > dropout_end else 0)
                if self.ukf_pos_errors and len(self.ukf_pos_errors) > dropout_end:
                    period['ukf_error_before'] = float(np.mean(self.ukf_pos_errors[before_start:dropout_start]) if dropout_start > before_start else 0)
                    period['ukf_error_during'] = float(np.mean(self.ukf_pos_errors[dropout_start:dropout_end]))
                    period['ukf_error_after'] = float(np.mean(self.ukf_pos_errors[dropout_end:after_end]) if after_end > dropout_end else 0)
                recovery['periods'].append(period)
        return recovery

    def get_time_series(self) -> Dict[str, Any]:
        return {
            'timestamps': self.timestamps,
            'ekf_pos_errors': self.ekf_pos_errors,
            'ukf_pos_errors': self.ukf_pos_errors,
            'ekf_vel_errors': self.ekf_vel_errors,
            'ukf_vel_errors': self.ukf_vel_errors,
            'detection_status': self.detection_status,
        }
