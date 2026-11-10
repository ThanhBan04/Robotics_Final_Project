"""
Simulation Engine - Core loop coordinating all modules.

Manages the simulation lifecycle:
1. Target Motion Model generates ground truth
2. UAV Model updates with acceleration commands
3. Camera Model creates measurements with noise/dropout/delay
4. EKF/UKF filters estimate target state
5. PID Controller computes acceleration commands
6. Data logging for evaluation

Supports: GUI mode, headless mode, and batch mode.
"""

import numpy as np
import time
import json
import os
import csv
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from models.target_model import TargetModel, TargetState
from models.uav_model import UAVModel, UAVState
from models.camera_model import CameraModel, Measurement
from filters.ekf import ExtendedKalmanFilter, EKFEstimate
from filters.ukf import UnscentedKalmanFilter, UKFEstimate
from control.pid_controller import PIDController
from simulation.target_scenario import get_scenario_config


@dataclass
class SimulationStep:
    """Data for one simulation timestep."""
    time: float
    dt: float
    # Ground truth
    target_gt: Optional[TargetState] = None
    uav_state: Optional[UAVState] = None
    # Measurement
    measurement: Optional[Measurement] = None
    # Estimates
    ekf_estimate: Optional[dict] = None
    ukf_estimate: Optional[dict] = None
    ekf_covariance: Optional[np.ndarray] = None
    ukf_covariance: Optional[np.ndarray] = None
    # Control
    pid_command: Optional[np.ndarray] = None
    desired_position: Optional[np.ndarray] = None
    # Metrics
    tracking_distance: float = 0.0
    estimation_error_ekf: float = 0.0
    estimation_error_ukf: float = 0.0


class SimulationEngine:
    """
    Main simulation engine coordinating all subsystems.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize simulation engine.
        
        Args:
            config: Configuration dictionary (from config.yaml or scenario)
        """
        self.config = config or {}
        
        # Simulation parameters
        self.dt = self.config.get('simulation', {}).get('dt', 0.02)
        self.duration = self.config.get('simulation', {}).get('duration', 30.0)
        self.random_seed = self.config.get('simulation', {}).get('random_seed', 42)
        self.world_width = self.config.get('simulation', {}).get('world_width', 1200)
        self.world_height = self.config.get('simulation', {}).get('world_height', 800)
        
        # State
        self.time = 0.0
        self.step_count = 0
        self.running = False
        self.paused = False
        self.finished = False
        
        # Data logging
        self.history: List[SimulationStep] = []
        
        # Active filter selection
        self.filter_mode = self.config.get('filter', {}).get('selected', 'ekf')  # 'ekf', 'ukf', 'both'
        
        # Scenario events
        self.noise_schedule: List[dict] = []
        self.dropout_events: List[dict] = []
        self.delay_schedule: List[dict] = []
        
        # Modules (initialized in setup)
        self.target_model: Optional[TargetModel] = None
        self.uav_model: Optional[UAVModel] = None
        self.camera: Optional[CameraModel] = None
        self.ekf: Optional[ExtendedKalmanFilter] = None
        self.ukf: Optional[UnscentedKalmanFilter] = None
        self.pid: Optional[PIDController] = None

    def setup(self, scenario_config: Dict[str, Any] = None):
        """
        Set up all simulation modules.
        
        Args:
            scenario_config: Scenario-specific configuration overrides
        """
        cfg = self.config.copy()
        if scenario_config:
            # Merge scenario config
            for key, val in scenario_config.items():
                if isinstance(val, dict) and key in cfg:
                    cfg[key] = {**cfg.get(key, {}), **val}
                else:
                    cfg[key] = val
        
        # Extract scenario events
        self.noise_schedule = scenario_config.get('noise_schedule', []) if scenario_config else []
        self.dropout_events = scenario_config.get('dropout_events', []) if scenario_config else []
        self.delay_schedule = scenario_config.get('delay_schedule', []) if scenario_config else []
        maneuvers = scenario_config.get('maneuvers', []) if scenario_config else []
        
        # Duration
        if scenario_config and 'duration' in scenario_config:
            self.duration = scenario_config['duration']
        
        # Target model
        target_cfg = cfg.get('target', {})
        if scenario_config and 'target' in scenario_config:
            target_cfg = {**target_cfg, **scenario_config['target']}
        
        self.target_model = TargetModel(
            initial_x=target_cfg.get('initial_x', 300.0),
            initial_y=target_cfg.get('initial_y', 400.0),
            initial_vx=target_cfg.get('initial_vx', 30.0),
            initial_vy=target_cfg.get('initial_vy', 0.0),
            max_speed=target_cfg.get('max_speed', 80.0),
            max_acceleration=target_cfg.get('max_acceleration', 20.0),
            process_noise_std=target_cfg.get('process_noise_std', 1.0),
            trajectory_type=target_cfg.get('trajectory_type', 'straight'),
            random_seed=self.random_seed,
            circular_radius=target_cfg.get('circular_radius', 150.0),
            circular_omega=target_cfg.get('circular_omega', 0.3),
            sinusoidal_amplitude=target_cfg.get('sinusoidal_amplitude', 100.0),
            sinusoidal_frequency=target_cfg.get('sinusoidal_frequency', 0.2),
            zigzag_amplitude=target_cfg.get('zigzag_amplitude', 80.0),
            zigzag_period=target_cfg.get('zigzag_period', 5.0),
            waypoints=target_cfg.get('waypoints', []),
            maneuvers=maneuvers,
        )
        
        # UAV model
        uav_cfg = cfg.get('uav', {})
        if scenario_config and 'uav' in scenario_config:
            uav_cfg = {**uav_cfg, **scenario_config['uav']}
        
        self.uav_model = UAVModel(
            initial_x=uav_cfg.get('initial_x', 100.0),
            initial_y=uav_cfg.get('initial_y', 400.0),
            initial_vx=uav_cfg.get('initial_vx', 0.0),
            initial_vy=uav_cfg.get('initial_vy', 0.0),
            max_speed=uav_cfg.get('max_speed', 100.0),
            max_acceleration=uav_cfg.get('max_acceleration', 25.0),
            world_bounds=(self.world_width, self.world_height),
        )
        
        # Camera model
        cam_cfg = cfg.get('camera', {})
        if scenario_config and 'camera' in scenario_config:
            cam_cfg = {**cam_cfg, **scenario_config['camera']}
        
        measurement_model = cam_cfg.get('measurement_model', 'range_bearing')
        
        self.camera = CameraModel(
            measurement_model=measurement_model,
            fov_angle=cam_cfg.get('fov_angle', 120.0),
            max_range=cam_cfg.get('max_range', 500.0),
            noise_range_std=cam_cfg.get('noise_range_std', 2.0),
            noise_bearing_std=cam_cfg.get('noise_bearing_std', 0.05),
            noise_xy_std=cam_cfg.get('noise_xy_std', 3.0),
            dropout_probability=cam_cfg.get('dropout_probability', 0.0),
            dropout_duration=cam_cfg.get('dropout_duration', 0.0),
            delay=cam_cfg.get('delay', 0.0),
            measurement_rate=cam_cfg.get('measurement_rate', 50.0),
            random_seed=self.random_seed + 1,
        )
        
        # Filters
        filter_cfg = cfg.get('filter', {})
        process_noise_q = filter_cfg.get('process_noise_q', 5.0)
        
        self.ekf = ExtendedKalmanFilter(
            state_dim=4, measurement_dim=2, dt=self.dt,
            process_noise_q=process_noise_q,
            measurement_model=measurement_model,
        )
        
        ukf_cfg = filter_cfg.get('ukf', {})
        self.ukf = UnscentedKalmanFilter(
            state_dim=4, measurement_dim=2, dt=self.dt,
            process_noise_q=process_noise_q,
            measurement_model=measurement_model,
            alpha=ukf_cfg.get('alpha', 0.1),
            beta=ukf_cfg.get('beta', 2.0),
            kappa=ukf_cfg.get('kappa', 0.0),
        )
        
        # Initialize filters with noisy initial estimate
        rng = np.random.default_rng(self.random_seed + 2)
        init_noise = rng.normal(0, 10, 4)
        init_state = np.array([
            target_cfg.get('initial_x', 300.0),
            target_cfg.get('initial_y', 400.0),
            target_cfg.get('initial_vx', 30.0),
            target_cfg.get('initial_vy', 0.0),
        ]) + init_noise
        
        P0 = np.diag([100, 100, 25, 25]).astype(float)
        R = self.camera.get_measurement_noise_covariance()
        
        self.ekf.initialize(init_state, P0)
        self.ekf.set_measurement_noise(R)
        
        self.ukf.initialize(init_state.copy(), P0.copy())
        self.ukf.set_measurement_noise(R)
        
        # PID controller
        pid_cfg = cfg.get('pid', {})
        self.pid = PIDController(
            kp=pid_cfg.get('kp', 2.0),
            ki=pid_cfg.get('ki', 0.1),
            kd=pid_cfg.get('kd', 1.5),
            desired_distance=pid_cfg.get('desired_distance', 50.0),
            integral_limit=pid_cfg.get('integral_limit', 50.0),
            derivative_filter=pid_cfg.get('derivative_filter', 0.1),
            max_acceleration=uav_cfg.get('max_acceleration', 25.0),
        )
        
        # Reset state
        self.time = 0.0
        self.step_count = 0
        self.running = True
        self.paused = False
        self.finished = False
        self.history = []
        
        # Trigger scheduled dropout events
        for event in self.dropout_events:
            self.camera.trigger_dropout(event['start'], event['duration'])

    def reset(self):
        """Reset simulation to initial state."""
        if self.target_model:
            self.target_model.reset()
        if self.uav_model:
            self.uav_model.reset()
        if self.camera:
            self.camera.reset()
        if self.pid:
            self.pid.reset()
        
        # Re-initialize filters
        if self.ekf and self.ukf:
            rng = np.random.default_rng(self.random_seed + 2)
            init_noise = rng.normal(0, 10, 4)
            init_state = self.target_model.initial_state.state_vector() + init_noise
            P0 = np.diag([100, 100, 25, 25]).astype(float)
            R = self.camera.get_measurement_noise_covariance()
            
            self.ekf.initialize(init_state, P0)
            self.ekf.set_measurement_noise(R)
            self.ukf.initialize(init_state.copy(), P0.copy())
            self.ukf.set_measurement_noise(R)
        
        self.time = 0.0
        self.step_count = 0
        self.running = True
        self.paused = False
        self.finished = False
        self.history = []
        
        # Re-trigger dropout events
        for event in self.dropout_events:
            self.camera.trigger_dropout(event['start'], event['duration'])

    def _apply_scheduled_events(self):
        """Apply noise schedule, dropout events, and delay schedule."""
        t = self.time
        
        # Noise schedule
        for i, ns in enumerate(self.noise_schedule):
            next_time = self.noise_schedule[i + 1]['time'] if i + 1 < len(self.noise_schedule) else float('inf')
            if ns['time'] <= t < next_time:
                self.camera.set_noise_multiplier(ns['multiplier'])
                break
        
        # Delay schedule
        for ds in self.delay_schedule:
            if t >= ds['time']:
                self.camera.delay = ds['delay']

    def simulation_step(self) -> SimulationStep:
        """
        Execute one simulation timestep.
        
        Returns:
            SimulationStep with all data for this step
        """
        step_data = SimulationStep(time=self.time, dt=self.dt)
        
        # Apply scheduled events
        self._apply_scheduled_events()
        
        # 1. Target motion (ground truth)
        target_gt = self.target_model.step(self.dt, self.time)
        step_data.target_gt = target_gt
        
        # 2. Camera measurement
        uav_pose = self.uav_model.get_pose()
        measurement = self.camera.measure(target_gt, uav_pose, self.time)
        step_data.measurement = measurement
        
        # 3. Filter estimation
        meas_data = measurement.data if measurement.detected else None
        
        ekf_est_dict = None
        ukf_est_dict = None
        
        if self.filter_mode in ('ekf', 'both'):
            ekf_result = self.ekf.step(meas_data, uav_pose, self.dt, self.time)
            ekf_est_dict = self.ekf.get_estimated_state()
            step_data.ekf_estimate = ekf_est_dict
            step_data.ekf_covariance = ekf_result.covariance.copy()
            step_data.estimation_error_ekf = np.sqrt(
                (ekf_est_dict['x'] - target_gt.x)**2 + 
                (ekf_est_dict['y'] - target_gt.y)**2
            )
        
        if self.filter_mode in ('ukf', 'both'):
            ukf_result = self.ukf.step(meas_data, uav_pose, self.dt, self.time)
            ukf_est_dict = self.ukf.get_estimated_state()
            step_data.ukf_estimate = ukf_est_dict
            step_data.ukf_covariance = ukf_result.covariance.copy()
            step_data.estimation_error_ukf = np.sqrt(
                (ukf_est_dict['x'] - target_gt.x)**2 + 
                (ukf_est_dict['y'] - target_gt.y)**2
            )
        
        # 4. PID control using active filter's estimate
        if self.filter_mode == 'ukf':
            active_estimate = ukf_est_dict
        else:
            active_estimate = ekf_est_dict  # Default to EKF
        
        if active_estimate is not None:
            acc_cmd = self.pid.compute(active_estimate, self.uav_model.state, self.dt)
            desired_pos = self.pid.compute_desired_position(active_estimate, self.uav_model.state)
        else:
            acc_cmd = np.array([0.0, 0.0])
            desired_pos = np.array([0.0, 0.0])
        
        step_data.pid_command = acc_cmd
        step_data.desired_position = desired_pos
        
        # 5. UAV dynamics update
        uav_state = self.uav_model.step(acc_cmd, self.dt, self.time)
        step_data.uav_state = uav_state
        
        # 6. Compute tracking distance
        tracking_dist = np.sqrt(
            (uav_state.x - target_gt.x)**2 + 
            (uav_state.y - target_gt.y)**2
        )
        step_data.tracking_distance = tracking_dist
        
        # Update time
        self.time += self.dt
        self.step_count += 1
        
        # Store history
        self.history.append(step_data)
        
        # Check if simulation is complete
        if self.time >= self.duration:
            self.finished = True
            self.running = False
        
        return step_data

    def run_headless(self) -> List[SimulationStep]:
        """
        Run complete simulation without GUI.
        
        Returns:
            List of all simulation steps
        """
        while self.running and not self.finished:
            self.simulation_step()
        return self.history

    def save_results(self, output_dir: str, run_id: str = "001"):
        """
        Save simulation results to CSV and JSON.
        
        Args:
            output_dir: Directory to save results
            run_id: Run identifier
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save data CSV
        csv_path = os.path.join(output_dir, f"data.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            header = [
                'time', 'dt',
                'target_x', 'target_y', 'target_vx', 'target_vy',
                'uav_x', 'uav_y', 'uav_vx', 'uav_vy',
                'measurement_detected', 'measurement_type',
                'measurement_0', 'measurement_1',
                'ekf_x', 'ekf_y', 'ekf_vx', 'ekf_vy',
                'ukf_x', 'ukf_y', 'ukf_vx', 'ukf_vy',
                'pid_ax', 'pid_ay',
                'tracking_distance',
                'estimation_error_ekf', 'estimation_error_ukf',
                'camera_status',
            ]
            writer.writerow(header)
            
            for step in self.history:
                row = [
                    f"{step.time:.4f}", f"{step.dt:.4f}",
                ]
                # Target GT
                if step.target_gt:
                    row.extend([f"{step.target_gt.x:.4f}", f"{step.target_gt.y:.4f}",
                               f"{step.target_gt.vx:.4f}", f"{step.target_gt.vy:.4f}"])
                else:
                    row.extend(['', '', '', ''])
                
                # UAV state
                if step.uav_state:
                    row.extend([f"{step.uav_state.x:.4f}", f"{step.uav_state.y:.4f}",
                               f"{step.uav_state.vx:.4f}", f"{step.uav_state.vy:.4f}"])
                else:
                    row.extend(['', '', '', ''])
                
                # Measurement
                if step.measurement:
                    row.append('1' if step.measurement.detected else '0')
                    row.append(step.measurement.measurement_type)
                    if step.measurement.data is not None:
                        row.extend([f"{step.measurement.data[0]:.4f}", f"{step.measurement.data[1]:.4f}"])
                    else:
                        row.extend(['', ''])
                else:
                    row.extend(['', '', '', ''])
                
                # EKF estimate
                if step.ekf_estimate:
                    row.extend([f"{step.ekf_estimate['x']:.4f}", f"{step.ekf_estimate['y']:.4f}",
                               f"{step.ekf_estimate['vx']:.4f}", f"{step.ekf_estimate['vy']:.4f}"])
                else:
                    row.extend(['', '', '', ''])
                
                # UKF estimate
                if step.ukf_estimate:
                    row.extend([f"{step.ukf_estimate['x']:.4f}", f"{step.ukf_estimate['y']:.4f}",
                               f"{step.ukf_estimate['vx']:.4f}", f"{step.ukf_estimate['vy']:.4f}"])
                else:
                    row.extend(['', '', '', ''])
                
                # PID
                if step.pid_command is not None:
                    row.extend([f"{step.pid_command[0]:.4f}", f"{step.pid_command[1]:.4f}"])
                else:
                    row.extend(['', ''])
                
                # Tracking
                row.append(f"{step.tracking_distance:.4f}")
                row.append(f"{step.estimation_error_ekf:.4f}")
                row.append(f"{step.estimation_error_ukf:.4f}")
                
                # Camera status
                row.append(self.camera.status if self.camera else '')
                
                writer.writerow(row)
        
        # Save config
        config_path = os.path.join(output_dir, "config.json")
        # Convert config to JSON-serializable format
        json_cfg = {}
        for k, v in self.config.items():
            if isinstance(v, dict):
                json_cfg[k] = {}
                for kk, vv in v.items():
                    if isinstance(vv, np.ndarray):
                        json_cfg[k][kk] = vv.tolist()
                    else:
                        json_cfg[k][kk] = vv
            elif isinstance(v, np.ndarray):
                json_cfg[k] = v.tolist()
            else:
                json_cfg[k] = v
        
        with open(config_path, 'w') as f:
            json.dump(json_cfg, f, indent=2, default=str)
        
        return csv_path

    def compute_metrics(self) -> Dict[str, Any]:
        """
        Compute evaluation metrics from simulation history.
        
        Returns:
            Dictionary of metrics
        """
        if not self.history:
            return {}
        
        metrics = {}
        
        # Estimation errors
        ekf_pos_errors = []
        ukf_pos_errors = []
        ekf_vel_errors = []
        ukf_vel_errors = []
        tracking_distances = []
        tracking_errors = []
        desired_dist = self.pid.desired_distance if self.pid else 50.0
        
        for step in self.history:
            if step.target_gt and step.uav_state:
                tracking_distances.append(step.tracking_distance)
                tracking_errors.append(abs(step.tracking_distance - desired_dist))
            
            if step.ekf_estimate and step.target_gt:
                ekf_pos_errors.append(np.sqrt(
                    (step.ekf_estimate['x'] - step.target_gt.x)**2 +
                    (step.ekf_estimate['y'] - step.target_gt.y)**2
                ))
                ekf_vel_errors.append(np.sqrt(
                    (step.ekf_estimate['vx'] - step.target_gt.vx)**2 +
                    (step.ekf_estimate['vy'] - step.target_gt.vy)**2
                ))
            
            if step.ukf_estimate and step.target_gt:
                ukf_pos_errors.append(np.sqrt(
                    (step.ukf_estimate['x'] - step.target_gt.x)**2 +
                    (step.ukf_estimate['y'] - step.target_gt.y)**2
                ))
                ukf_vel_errors.append(np.sqrt(
                    (step.ukf_estimate['vx'] - step.target_gt.vx)**2 +
                    (step.ukf_estimate['vy'] - step.target_gt.vy)**2
                ))
        
        # Position RMSE
        if ekf_pos_errors:
            metrics['ekf_position_rmse'] = np.sqrt(np.mean(np.array(ekf_pos_errors)**2))
            metrics['ekf_velocity_rmse'] = np.sqrt(np.mean(np.array(ekf_vel_errors)**2))
            metrics['ekf_max_position_error'] = np.max(ekf_pos_errors)
        
        if ukf_pos_errors:
            metrics['ukf_position_rmse'] = np.sqrt(np.mean(np.array(ukf_pos_errors)**2))
            metrics['ukf_velocity_rmse'] = np.sqrt(np.mean(np.array(ukf_vel_errors)**2))
            metrics['ukf_max_position_error'] = np.max(ukf_pos_errors)
        
        # Tracking metrics
        if tracking_errors:
            metrics['tracking_rmse'] = np.sqrt(np.mean(np.array(tracking_errors)**2))
            metrics['mean_tracking_distance'] = np.mean(tracking_distances)
            metrics['max_tracking_distance'] = np.max(tracking_distances)
            metrics['min_tracking_distance'] = np.min(tracking_distances)
            metrics['mean_tracking_error'] = np.mean(tracking_errors)
            metrics['max_tracking_error'] = np.max(tracking_errors)
        
        # Settling time (time to get within 10% of desired distance)
        threshold = desired_dist * 0.1
        settling_time = None
        for step in self.history:
            if abs(step.tracking_distance - desired_dist) < threshold:
                settling_time = step.time
                break
        metrics['settling_time'] = settling_time
        
        return metrics

    def save_metrics(self, output_dir: str, metrics: Dict[str, Any] = None):
        """Save computed metrics to JSON."""
        if metrics is None:
            metrics = self.compute_metrics()
        
        os.makedirs(output_dir, exist_ok=True)
        metrics_path = os.path.join(output_dir, "metrics.json")
        
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        return metrics_path
