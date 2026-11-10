"""
Target Scenario Definitions.

Defines the 7 predefined test scenarios and trajectory configurations.
"""

import numpy as np
from typing import Dict, Any, List


def get_scenario_config(scenario_id: int, base_config: dict = None) -> Dict[str, Any]:
    """
    Get configuration for a scenario.
    
    Args:
        scenario_id: Scenario number (1-7 predefined, 8-12 interactive)
        base_config: Base configuration to modify
        
    Returns:
        Scenario configuration dictionary
    """
    scenarios = {
        1: scenario_1_baseline,
        2: scenario_2_sudden_maneuver,
        3: scenario_3_high_noise,
        4: scenario_4_lost_detection,
        5: scenario_5_normal_tracking,
        6: scenario_6_turning_tracking,
        7: scenario_7_combined_stress,
        8: scenario_8_interactive_click,
        9: scenario_9_interactive_waypoint,
        10: scenario_10_mouse_drag,
        11: scenario_11_keyboard_control,
        12: scenario_12_evasive_target,
    }
    
    if scenario_id not in scenarios:
        raise ValueError(f"Unknown scenario ID: {scenario_id}")
    
    return scenarios[scenario_id](base_config or {})


def scenario_1_baseline(cfg: dict) -> Dict[str, Any]:
    """Scenario 1: Normal/Baseline - straight line, low noise, no dropout."""
    return {
        'name': 'Baseline',
        'description': 'Target moves straight; low camera noise; no dropout/delay',
        'duration': 30.0,
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 30.0, 'initial_vy': 5.0,
            'max_speed': 80.0, 'max_acceleration': 20.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'straight',
        },
        'uav': {
            'initial_x': 100.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [],
    }


def scenario_2_sudden_maneuver(cfg: dict) -> Dict[str, Any]:
    """Scenario 2: Sudden target maneuver - 90 degree turn."""
    return {
        'name': 'Sudden Maneuver',
        'description': 'Target turns 90° at t=10s',
        'duration': 30.0,
        'target': {
            'initial_x': 200.0, 'initial_y': 400.0,
            'initial_vx': 40.0, 'initial_vy': 0.0,
            'max_speed': 80.0, 'max_acceleration': 30.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'straight',
        },
        'uav': {
            'initial_x': 100.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [
            {'time': 10.0, 'type': 'turn', 'angle': 90, 'duration': 0.5},
        ],
    }


def scenario_3_high_noise(cfg: dict) -> Dict[str, Any]:
    """Scenario 3: High measurement noise."""
    return {
        'name': 'High Noise',
        'description': 'Camera noise increases at t=5s, t=10s, t=15s',
        'duration': 30.0,
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 30.0, 'initial_vy': 5.0,
            'max_speed': 80.0, 'max_acceleration': 20.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'straight',
        },
        'uav': {
            'initial_x': 100.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'noise_schedule': [
            {'time': 0.0, 'multiplier': 1.0},
            {'time': 5.0, 'multiplier': 3.0},
            {'time': 10.0, 'multiplier': 5.0},
            {'time': 15.0, 'multiplier': 8.0},
            {'time': 20.0, 'multiplier': 1.0},
        ],
        'maneuvers': [],
    }


def scenario_4_lost_detection(cfg: dict) -> Dict[str, Any]:
    """Scenario 4: Camera loses detection for a period."""
    return {
        'name': 'Lost Detection',
        'description': 'Camera dropout from t=8s to t=13s',
        'duration': 30.0,
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 30.0, 'initial_vy': 5.0,
            'max_speed': 80.0, 'max_acceleration': 20.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'straight',
        },
        'uav': {
            'initial_x': 100.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'dropout_events': [
            {'start': 8.0, 'duration': 5.0},
        ],
        'maneuvers': [],
    }


def scenario_5_normal_tracking(cfg: dict) -> Dict[str, Any]:
    """Scenario 5: Normal tracking - UAV starts offset."""
    return {
        'name': 'Normal Tracking',
        'description': 'UAV starts offset; must track and maintain distance',
        'duration': 30.0,
        'target': {
            'initial_x': 400.0, 'initial_y': 300.0,
            'initial_vx': 25.0, 'initial_vy': 10.0,
            'max_speed': 60.0, 'max_acceleration': 15.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'sinusoidal',
            'sinusoidal_amplitude': 60.0,
            'sinusoidal_frequency': 0.15,
        },
        'uav': {
            'initial_x': 100.0, 'initial_y': 500.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [],
    }


def scenario_6_turning_tracking(cfg: dict) -> Dict[str, Any]:
    """Scenario 6: Target turns during tracking."""
    return {
        'name': 'Turning Tracking',
        'description': 'Target turns 90° at t=8s and t=16s while UAV tracks',
        'duration': 30.0,
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 35.0, 'initial_vy': 0.0,
            'max_speed': 80.0, 'max_acceleration': 25.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'straight',
        },
        'uav': {
            'initial_x': 150.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [
            {'time': 8.0, 'type': 'turn', 'angle': 90, 'duration': 0.5},
            {'time': 16.0, 'type': 'turn', 'angle': -90, 'duration': 0.5},
        ],
    }


def scenario_7_combined_stress(cfg: dict) -> Dict[str, Any]:
    """Scenario 7: Combined stress test."""
    return {
        'name': 'Combined Stress',
        'description': 'Turn + high noise + dropout + delay combined',
        'duration': 25.0,
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 35.0, 'initial_vy': 5.0,
            'max_speed': 80.0, 'max_acceleration': 25.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'straight',
        },
        'uav': {
            'initial_x': 150.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [
            {'time': 5.0, 'type': 'turn', 'angle': 90, 'duration': 0.5},
        ],
        'noise_schedule': [
            {'time': 0.0, 'multiplier': 1.0},
            {'time': 8.0, 'multiplier': 5.0},
            {'time': 12.0, 'multiplier': 1.0},
        ],
        'dropout_events': [
            {'start': 12.0, 'duration': 3.0},
        ],
        'delay_schedule': [
            {'time': 15.0, 'delay': 0.3},
        ],
    }


def scenario_8_interactive_click(cfg: dict) -> Dict[str, Any]:
    """Scenario 8: Interactive Straight/Point Command - click to set destination."""
    return {
        'name': 'Interactive Click',
        'description': 'Click to set target destination point; evaluate UAV tracking',
        'duration': 30.0,
        'is_interactive': True,
        'interactive_mode': 'click',
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 25.0, 'initial_vy': 0.0,
            'max_speed': 60.0, 'max_acceleration': 20.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'waypoint',
            'waypoints': [[500.0, 300.0], [600.0, 500.0], [350.0, 550.0]],
        },
        'uav': {
            'initial_x': 150.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [],
    }


def scenario_9_interactive_waypoint(cfg: dict) -> Dict[str, Any]:
    """Scenario 9: Interactive Waypoint - chain of waypoint destinations."""
    return {
        'name': 'Interactive Waypoint',
        'description': 'Multi-click waypoint chain; evaluate tracking through turns',
        'duration': 35.0,
        'is_interactive': True,
        'interactive_mode': 'waypoint',
        'target': {
            'initial_x': 250.0, 'initial_y': 350.0,
            'initial_vx': 30.0, 'initial_vy': 0.0,
            'max_speed': 65.0, 'max_acceleration': 25.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'waypoint',
            'waypoints': [
                [450.0, 250.0],
                [650.0, 350.0],
                [550.0, 550.0],
                [300.0, 500.0],
                [250.0, 350.0],
            ],
        },
        'uav': {
            'initial_x': 100.0, 'initial_y': 350.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [],
    }


def scenario_10_mouse_drag(cfg: dict) -> Dict[str, Any]:
    """Scenario 10: Mouse Drag Target - continuous destination update."""
    return {
        'name': 'Mouse Drag Target',
        'description': 'Continuous destination update via mouse drag; evaluate dynamic tracking',
        'duration': 30.0,
        'is_interactive': True,
        'interactive_mode': 'drag',
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 30.0, 'initial_vy': 10.0,
            'max_speed': 70.0, 'max_acceleration': 25.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'sinusoidal',
            'sinusoidal_amplitude': 80.0,
            'sinusoidal_frequency': 0.2,
        },
        'uav': {
            'initial_x': 150.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [],
    }


def scenario_11_keyboard_control(cfg: dict) -> Dict[str, Any]:
    """Scenario 11: Keyboard Controlled Target - WASD steering, Shift boost, Space stop."""
    return {
        'name': 'Keyboard Control',
        'description': 'WASD velocity commands, Shift boost, Space decelerate/stop',
        'duration': 30.0,
        'is_interactive': True,
        'interactive_mode': 'keyboard',
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 35.0, 'initial_vy': 0.0,
            'max_speed': 75.0, 'max_acceleration': 25.0,
            'process_noise_std': 0.5,
            'trajectory_type': 'straight',
        },
        'uav': {
            'initial_x': 150.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.0, 'noise_bearing_std': 0.03,
            'noise_xy_std': 2.0,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [
            {'time': 6.0, 'type': 'turn', 'angle': 60, 'duration': 0.5},
            {'time': 12.0, 'type': 'speed', 'target_speed': 60.0, 'duration': 1.0},
            {'time': 18.0, 'type': 'turn', 'angle': -90, 'duration': 0.5},
            {'time': 24.0, 'type': 'speed', 'target_speed': 20.0, 'duration': 1.0},
        ],
    }


def scenario_12_evasive_target(cfg: dict) -> Dict[str, Any]:
    """Scenario 12: Sudden Escape / Evasive Target - evasive maneuvers, bursts."""
    return {
        'name': 'Evasive Target',
        'description': 'High agility, rapid direction shifts, acceleration bursts',
        'duration': 30.0,
        'is_interactive': True,
        'interactive_mode': 'keyboard',
        'target': {
            'initial_x': 300.0, 'initial_y': 400.0,
            'initial_vx': 40.0, 'initial_vy': 0.0,
            'max_speed': 90.0, 'max_acceleration': 35.0,
            'process_noise_std': 0.8,
            'trajectory_type': 'zigzag',
            'zigzag_amplitude': 100.0,
            'zigzag_period': 4.0,
        },
        'uav': {
            'initial_x': 150.0, 'initial_y': 400.0,
            'initial_vx': 0.0, 'initial_vy': 0.0,
        },
        'camera': {
            'noise_range_std': 2.5, 'noise_bearing_std': 0.04,
            'noise_xy_std': 2.5,
            'dropout_probability': 0.0, 'dropout_duration': 0.0,
            'delay': 0.0,
        },
        'maneuvers': [
            {'time': 5.0, 'type': 'turn', 'angle': 120, 'duration': 0.4},
            {'time': 10.0, 'type': 'speed', 'target_speed': 85.0, 'duration': 0.5},
            {'time': 15.0, 'type': 'turn', 'angle': -135, 'duration': 0.4},
            {'time': 20.0, 'type': 'turn', 'angle': 90, 'duration': 0.4},
        ],
    }


def get_all_scenario_names() -> Dict[int, str]:
    """Get names of all predefined and interactive scenarios (1-12)."""
    return {
        1: 'Baseline',
        2: 'Sudden Maneuver',
        3: 'High Noise',
        4: 'Lost Detection',
        5: 'Normal Tracking',
        6: 'Turning Tracking',
        7: 'Combined Stress',
        8: 'Interactive Click',
        9: 'Interactive Waypoint',
        10: 'Mouse Drag Target',
        11: 'Keyboard Control',
        12: 'Evasive Target',
    }
