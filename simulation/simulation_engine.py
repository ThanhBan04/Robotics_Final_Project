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
import copy
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
    raw_estimate: Optional[dict] = None
    ekf_covariance: Optional[np.ndarray] = None
    ukf_covariance: Optional[np.ndarray] = None
    # Innovations & Covariances (for consistency NEES/NIS)
    ekf_innovation: Optional[np.ndarray] = None
    ekf_innovation_cov: Optional[np.ndarray] = None
    ukf_innovation: Optional[np.ndarray] = None
    ukf_innovation_cov: Optional[np.ndarray] = None
    # Control
    pid_command: Optional[np.ndarray] = None
    desired_position: Optional[np.ndarray] = None
    # Metrics
    tracking_distance: float = 0.0
    estimation_error_ekf: float = 0.0
    estimation_error_ukf: float = 0.0
    estimation_error_raw: float = 0.0


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
        self.filter_mode = self.config.get('filter', {}).get('selected', 'ekf')  # 'ekf', 'ukf', 'both', 'none'
        
        # Performance & Timing
        self.ekf_step_times: List[float] = []
        self.ukf_step_times: List[float] = []
        self._last_raw_pos: Optional[tuple] = None
        self._last_raw_vel: Optional[tuple] = None
        self._smoothed_pos: Optional[tuple] = None
        self._smoothed_vel: Optional[tuple] = None
        self._filters_initialized_from_measurement = False
        self.camera_reacquire_with_estimate = True
        self.camera_search_enabled = True
        self.camera_no_detection_duration = 0.0
        self.initial_position_var = 100.0
        self.initial_velocity_var = 900.0
        
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

    def setup(self, scenario_config: Dict[str, Any] = None, random_seed: Optional[int] = None):
        """
        Set up all simulation modules.
        
        Args:
            scenario_config: Scenario-specific configuration overrides
            random_seed: Optional random seed override for reproducible variations
        """
        if random_seed is not None:
            self.random_seed = random_seed
        cfg = copy.deepcopy(self.config)
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
            world_bounds=tuple(cfg.get('simulation', {}).get('world_bounds', (1200, 800))),
        )
        
        # UAV model
        uav_cfg = cfg.get('uav', {})
        if scenario_config and 'uav' in scenario_config:
            uav_cfg = {**uav_cfg, **scenario_config['uav']}
        
        if scenario_config and scenario_config.get('steady_state_init', False):
            t_x = target_cfg.get('initial_x', 300.0)
            t_y = target_cfg.get('initial_y', 400.0)
            t_vx = target_cfg.get('initial_vx', 30.0)
            t_vy = target_cfg.get('initial_vy', 0.0)
            t_spd = np.sqrt(t_vx**2 + t_vy**2)
            t_hdg = np.arctan2(t_vy, t_vx) if t_spd > 1e-3 else 0.0
            des_dist = cfg.get('pid', {}).get('desired_distance', 50.0)
            uav_x0 = t_x - des_dist * np.cos(t_hdg)
            uav_y0 = t_y - des_dist * np.sin(t_hdg)
            uav_vx0 = t_vx
            uav_vy0 = t_vy
        else:
            uav_x0 = uav_cfg.get('initial_x', 100.0)
            uav_y0 = uav_cfg.get('initial_y', 400.0)
            uav_vx0 = uav_cfg.get('initial_vx', 0.0)
            uav_vy0 = uav_cfg.get('initial_vy', 0.0)

        self.uav_model = UAVModel(
            initial_x=uav_x0,
            initial_y=uav_y0,
            initial_vx=uav_vx0,
            initial_vy=uav_vy0,
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
        self.camera_reacquire_with_estimate = cam_cfg.get('reacquire_with_estimate', True)
        self.camera_search_enabled = cam_cfg.get('search_enabled', True)
        self.camera_no_detection_duration = 0.0
        
        # Filters
        filter_cfg = cfg.get('filter', {})
        process_noise_q = filter_cfg.get('process_noise_q', 5.0)
        self.initial_position_var = float(filter_cfg.get('initial_position_var', 100.0))
        self.initial_velocity_var = float(filter_cfg.get('initial_velocity_var', 900.0))
        
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
            # alpha=1 avoids a very large negative central sigma-point weight
            # for this 4D state when kappa=0.
            alpha=ukf_cfg.get('alpha', 1.0),
            beta=ukf_cfg.get('beta', 2.0),
            kappa=ukf_cfg.get('kappa', 0.0),
        )
        
        # Do not seed either filter from ground truth.  Both filters are
        # initialized lazily from the first valid camera measurement in the
        # simulation loop (velocity starts at zero with high uncertainty).
        P0 = np.diag([400, 400, 900, 900]).astype(float)
        R = self.camera.get_measurement_noise_covariance()
        self.ekf.set_measurement_noise(R)
        self.ukf.set_measurement_noise(R)
        self._filters_initialized_from_measurement = False
        
        # PID controller
        pid_cfg = cfg.get('pid', {})
        self.pid = PIDController(
            kp=pid_cfg.get('kp', 2.0),
            ki=pid_cfg.get('ki', 0.1),
            kd=pid_cfg.get('kd', 2.8),
            desired_distance=pid_cfg.get('desired_distance', 50.0),
            integral_limit=pid_cfg.get('integral_limit', 50.0),
            derivative_filter=pid_cfg.get('derivative_filter', 0.2),
            max_acceleration=uav_cfg.get('max_acceleration', 25.0),
            min_safety_distance=pid_cfg.get('min_safety_distance', 20.0),
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
            P0 = np.diag([self.initial_position_var, self.initial_position_var,
                          self.initial_velocity_var, self.initial_velocity_var]).astype(float)
            R = self.camera.get_measurement_noise_covariance()
            self.ekf.set_measurement_noise(R)
            self.ukf.set_measurement_noise(R)
            self._filters_initialized_from_measurement = False
        
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
        measurement_pose = dict(uav_pose)
        # A camera pointed along the UAV velocity can lose a maneuvering
        # target permanently.  When enabled, use the last filter estimate as
        # a bounded visual-search heading; this does not reveal ground truth.
        if self.filter_mode in ('none', 'raw', 'none_smoothed'):
            raw_for_heading = self._smoothed_pos if self.filter_mode == 'none_smoothed' else self._last_raw_pos
            if raw_for_heading is not None:
                measurement_pose['heading'] = float(np.arctan2(
                    raw_for_heading[1] - uav_pose['y'],
                    raw_for_heading[0] - uav_pose['x']))
        elif self.camera_reacquire_with_estimate and self._filters_initialized_from_measurement:
            estimate_for_camera = None
            if self.filter_mode == 'ukf' and self.ukf.initialized:
                estimate_for_camera = self.ukf.get_estimated_state()
            elif self.ekf.initialized:
                estimate_for_camera = self.ekf.get_estimated_state()
            if estimate_for_camera is not None:
                dx = estimate_for_camera['x'] - uav_pose['x']
                dy = estimate_for_camera['y'] - uav_pose['y']
                if dx * dx + dy * dy > 1e-6:
                    measurement_pose['heading'] = float(np.arctan2(dy, dx))

        # If the target has been absent for long enough, sweep around the
        # predicted/raw direction to reacquire it.  Forced camera dropout is
        # still respected by CameraModel; the sweep only affects FOV search.
        if self.camera_search_enabled and self.camera_no_detection_duration > 1.0:
            elapsed = self.camera_no_detection_duration - 1.0
            amplitude = np.radians(min(30.0 + 150.0 * elapsed / 4.0, 180.0))
            measurement_pose['heading'] += amplitude * np.sin(2.0 * np.pi * self.time / 2.0)

        measurement = self.camera.measure(target_gt, measurement_pose, self.time)
        if measurement.detected:
            self.camera_no_detection_duration = 0.0
        else:
            self.camera_no_detection_duration += self.dt
        step_data.measurement = measurement
        
        # 3. Filter estimation
        meas_data = measurement.data if measurement.detected else None
        filter_pose = measurement.sensor_pose or measurement_pose

        # Initialize filters from the first actual measurement.  This keeps
        # the experiment honest: the filter does not receive target ground
        # truth or the target's initial velocity.
        if not self._filters_initialized_from_measurement and meas_data is not None:
            r, theta = float(meas_data[0]), float(meas_data[1])
            capture_pose = measurement.sensor_pose or measurement_pose
            bearing = capture_pose['heading'] + theta
            init_state = np.array([
                capture_pose['x'] + r * np.cos(bearing),
                capture_pose['y'] + r * np.sin(bearing),
                0.0,
                0.0,
            ], dtype=float)
            P0 = np.diag([self.initial_position_var, self.initial_position_var,
                          self.initial_velocity_var, self.initial_velocity_var])
            self.ekf.initialize(init_state, P0)
            self.ukf.initialize(init_state.copy(), P0.copy())
            self._filters_initialized_from_measurement = True
        
        ekf_est_dict = None
        ukf_est_dict = None
        raw_est_dict = None
        
        if self.filter_mode in ('ekf', 'both') and self.ekf.initialized:
            t0 = time.perf_counter()
            ekf_result = self.ekf.step(meas_data, filter_pose, self.dt, self.time)
            self.ekf_step_times.append(time.perf_counter() - t0)
            
            ekf_est_dict = self.ekf.get_estimated_state()
            step_data.ekf_estimate = ekf_est_dict
            step_data.ekf_covariance = ekf_result.covariance.copy()
            if ekf_result.innovation is not None:
                step_data.ekf_innovation = ekf_result.innovation.copy()
            if ekf_result.innovation_covariance is not None:
                step_data.ekf_innovation_cov = ekf_result.innovation_covariance.copy()
            step_data.estimation_error_ekf = np.sqrt(
                (ekf_est_dict['x'] - target_gt.x)**2 + 
                (ekf_est_dict['y'] - target_gt.y)**2
            )
        
        if self.filter_mode in ('ukf', 'both') and self.ukf.initialized:
            t0 = time.perf_counter()
            ukf_result = self.ukf.step(meas_data, filter_pose, self.dt, self.time)
            self.ukf_step_times.append(time.perf_counter() - t0)
            
            ukf_est_dict = self.ukf.get_estimated_state()
            step_data.ukf_estimate = ukf_est_dict
            step_data.ukf_covariance = ukf_result.covariance.copy()
            if ukf_result.innovation is not None:
                step_data.ukf_innovation = ukf_result.innovation.copy()
            if ukf_result.innovation_covariance is not None:
                step_data.ukf_innovation_cov = ukf_result.innovation_covariance.copy()
            step_data.estimation_error_ukf = np.sqrt(
                (ukf_est_dict['x'] - target_gt.x)**2 + 
                (ukf_est_dict['y'] - target_gt.y)**2
            )
            
        if self.filter_mode in ('none', 'raw', 'none_smoothed'):
            # No-filter baseline: raw measurement converted to Cartesian
            if measurement.detected and meas_data is not None:
                r, theta = meas_data[0], meas_data[1]
                capture_pose = measurement.sensor_pose or measurement_pose
                bearing = capture_pose['heading'] + theta
                x_meas = capture_pose['x'] + r * np.cos(bearing)
                y_meas = capture_pose['y'] + r * np.sin(bearing)
                if self._last_raw_pos is not None:
                    vx_meas = (x_meas - self._last_raw_pos[0]) / max(self.dt, 1e-6)
                    vy_meas = (y_meas - self._last_raw_pos[1]) / max(self.dt, 1e-6)
                else:
                    vx_meas, vy_meas = 0.0, 0.0
                self._last_raw_pos = (x_meas, y_meas)
                self._last_raw_vel = (vx_meas, vy_meas)
                
                # Smoothed variant: exponential moving average
                if self.filter_mode == 'none_smoothed':
                    if self._smoothed_pos is None:
                        self._smoothed_pos = (x_meas, y_meas)
                        self._smoothed_vel = (vx_meas, vy_meas)
                    else:
                        sx = 0.3 * x_meas + 0.7 * self._smoothed_pos[0]
                        sy = 0.3 * y_meas + 0.7 * self._smoothed_pos[1]
                        svx = 0.2 * vx_meas + 0.8 * self._smoothed_vel[0]
                        svy = 0.2 * vy_meas + 0.8 * self._smoothed_vel[1]
                        self._smoothed_pos = (sx, sy)
                        self._smoothed_vel = (svx, svy)
                        x_meas, y_meas = sx, sy
                        vx_meas, vy_meas = svx, svy
            else:
                # Hold last raw measurement during dropout
                if self.filter_mode == 'none_smoothed' and self._smoothed_pos is not None:
                    x_meas, y_meas = self._smoothed_pos
                    vx_meas, vy_meas = self._smoothed_vel
                elif self._last_raw_pos is not None:
                    x_meas, y_meas = self._last_raw_pos
                    vx_meas, vy_meas = self._last_raw_vel
                else:
                    x_meas, y_meas = uav_pose['x'], uav_pose['y']
                    vx_meas, vy_meas = 0.0, 0.0
            
            raw_est_dict = {'x': x_meas, 'y': y_meas, 'vx': vx_meas, 'vy': vy_meas}
            step_data.raw_estimate = raw_est_dict
            step_data.estimation_error_raw = np.sqrt(
                (x_meas - target_gt.x)**2 + 
                (y_meas - target_gt.y)**2
            )
        
        # 4. PID control using active filter's estimate
        if self.filter_mode == 'ukf':
            active_estimate = ukf_est_dict
        elif self.filter_mode in ('none', 'raw', 'none_smoothed'):
            active_estimate = raw_est_dict
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
        raw_pos_errors = []
        ekf_vel_errors = []
        ukf_vel_errors = []
        raw_vel_errors = []
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
                
            if step.raw_estimate and step.target_gt:
                raw_pos_errors.append(np.sqrt(
                    (step.raw_estimate['x'] - step.target_gt.x)**2 +
                    (step.raw_estimate['y'] - step.target_gt.y)**2
                ))
                raw_vel_errors.append(np.sqrt(
                    (step.raw_estimate['vx'] - step.target_gt.vx)**2 +
                    (step.raw_estimate['vy'] - step.target_gt.vy)**2
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

        if raw_pos_errors:
            metrics['raw_position_rmse'] = np.sqrt(np.mean(np.array(raw_pos_errors)**2))
            metrics['raw_velocity_rmse'] = np.sqrt(np.mean(np.array(raw_vel_errors)**2))
            metrics['raw_max_position_error'] = np.max(raw_pos_errors)

        # Post-10s position RMSE (after initial transient approach)
        ekf_pos_p10 = [np.sqrt((s.ekf_estimate['x'] - s.target_gt.x)**2 + (s.ekf_estimate['y'] - s.target_gt.y)**2)
                       for s in self.history if s.time >= 10.0 and s.ekf_estimate and s.target_gt]
        ukf_pos_p10 = [np.sqrt((s.ukf_estimate['x'] - s.target_gt.x)**2 + (s.ukf_estimate['y'] - s.target_gt.y)**2)
                       for s in self.history if s.time >= 10.0 and s.ukf_estimate and s.target_gt]
        if ekf_pos_p10:
            metrics['ekf_pos_rmse_post10'] = float(np.sqrt(np.mean(np.array(ekf_pos_p10)**2)))
        if ukf_pos_p10:
            metrics['ukf_pos_rmse_post10'] = float(np.sqrt(np.mean(np.array(ukf_pos_p10)**2)))

        # Computation time (us)
        if self.ekf_step_times:
            metrics['ekf_mean_step_time_us'] = float(np.mean(self.ekf_step_times) * 1e6)
        if self.ukf_step_times:
            metrics['ukf_mean_step_time_us'] = float(np.mean(self.ukf_step_times) * 1e6)

        # PID acceleration metrics: step-to-step jerk/jitter and saturation ratio
        pid_cmds = [np.array(step.pid_command) for step in self.history if step.pid_command is not None]
        if len(pid_cmds) > 1:
            step_deltas = [np.linalg.norm(pid_cmds[i] - pid_cmds[i-1]) for i in range(1, len(pid_cmds))]
            metrics['pid_step_jitter'] = float(np.mean(step_deltas))
            metrics['pid_acceleration_jitter'] = float(np.mean(step_deltas))  # Mean step-to-step jerk
            max_a = self.uav_model.max_acceleration if self.uav_model else 25.0
            sat_count = sum(1 for c in pid_cmds if np.linalg.norm(c) >= 0.99 * max_a)
            metrics['pid_saturation_ratio'] = float(sat_count / len(pid_cmds) * 100.0)
        else:
            metrics['pid_step_jitter'] = 0.0
            metrics['pid_acceleration_jitter'] = 0.0
            metrics['pid_saturation_ratio'] = 0.0
        
        # Tracking metrics
        if tracking_errors:
            metrics['tracking_rmse'] = np.sqrt(np.mean(np.array(tracking_errors)**2))
            metrics['mean_tracking_distance'] = float(np.mean(tracking_distances))
            metrics['max_tracking_distance'] = float(np.max(tracking_distances))
            metrics['max_separation'] = float(np.max(tracking_distances))  # Explicit key for TN0/TN3
            metrics['min_tracking_distance'] = float(np.min(tracking_distances))
            metrics['mean_tracking_error'] = float(np.mean(tracking_errors))
            metrics['max_tracking_error'] = float(np.max(tracking_errors))
        else:
            metrics['max_separation'] = 0.0

        # Post-10s metrics (steady-state tracking phase after initial approach)
        post10_tracking_errors = [abs(step.tracking_distance - desired_dist) for step in self.history if step.time >= 10.0]
        if post10_tracking_errors:
            metrics['tracking_rmse_post10'] = float(np.sqrt(np.mean(np.array(post10_tracking_errors)**2)))
        else:
            metrics['tracking_rmse_post10'] = metrics.get('tracking_rmse', 0.0)
        
        # Settling time (time after which error remains within 10% of desired distance)
        threshold = desired_dist * 0.1
        settling_time = None
        if self.history and abs(self.history[-1].tracking_distance - desired_dist) < threshold:
            settling_time = self.history[0].time
            for i in range(len(self.history) - 1, -1, -1):
                if abs(self.history[i].tracking_distance - desired_dist) >= threshold:
                    settling_time = self.history[i + 1].time if i + 1 < len(self.history) else self.history[i].time
                    break
        metrics['settling_time'] = settling_time
        
        # Target loss criteria (TN4): Separated into camera dropout vs true estimation divergence
        has_lost = False
        lost_time = None
        had_estimation_divergence = False
        recovery_time = None
        active_loss_start = None
        camera_dropout_detected = False
        consecutive_high_error = 0
        consecutive_no_meas = 0
        dt = self.dt
        steps_2s = int(2.0 / dt)
        steps_3s = int(3.0 / dt)
        
        for step in self.history:
            if self.filter_mode == 'ukf':
                err = step.estimation_error_ukf
            elif self.filter_mode in ('none', 'raw', 'none_smoothed'):
                err = step.estimation_error_raw
            else:
                err = step.estimation_error_ekf
                
            if err > 50.0:
                consecutive_high_error += 1
            else:
                consecutive_high_error = 0
                
            if step.measurement is None or not step.measurement.detected:
                consecutive_no_meas += 1
            else:
                consecutive_no_meas = 0

            if consecutive_no_meas > steps_3s:
                camera_dropout_detected = True
                
            # Mark a divergence event only after it persists for 2 seconds.
            # A search/reacquisition that brings the estimate back is not an
            # unrecovered target loss, so it must not count as a failed run.
            if consecutive_high_error > steps_2s:
                had_estimation_divergence = True
                if active_loss_start is None:
                    active_loss_start = float(step.time - 2.0)
            elif active_loss_start is not None:
                recovery_time = float(step.time)
                active_loss_start = None

        if active_loss_start is not None:
            has_lost = True
            lost_time = active_loss_start
                
        metrics['has_lost_target'] = bool(has_lost)
        metrics['lost_target_time'] = lost_time
        metrics['had_estimation_divergence'] = bool(had_estimation_divergence)
        metrics['recovery_time'] = recovery_time
        metrics['camera_dropout_detected'] = bool(camera_dropout_detected)
        if self.target_model is not None:
            metrics['boundary_hits'] = int(self.target_model.boundary_hits)

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
