"""
Unit tests for Scenario Configurations (1 to 12).
"""

import pytest
from simulation.target_scenario import get_scenario_config, get_all_scenario_names


def test_all_12_scenarios_exist():
    names = get_all_scenario_names()
    assert len(names) == 12
    for sc_id in range(1, 13):
        assert sc_id in names


@pytest.mark.parametrize("scenario_id", list(range(1, 13)))
def test_scenario_config_validity(scenario_id):
    cfg = get_scenario_config(scenario_id)
    assert 'name' in cfg
    assert 'description' in cfg
    assert 'duration' in cfg
    assert 'target' in cfg
    assert 'uav' in cfg
    assert 'camera' in cfg
    assert cfg['duration'] > 0
    assert 'initial_x' in cfg['target']
    assert 'initial_y' in cfg['target']
    assert 'initial_x' in cfg['uav']
    assert 'initial_y' in cfg['uav']


def test_invalid_scenario_id():
    with pytest.raises(ValueError):
        get_scenario_config(0)
    with pytest.raises(ValueError):
        get_scenario_config(13)


def test_simulation_with_no_filter():
    from simulation.simulation_engine import SimulationEngine
    scfg = get_scenario_config(1)
    engine = SimulationEngine()
    engine.setup(scfg)
    engine.filter_mode = 'none'
    for _ in range(50):
        engine.simulation_step()
    m = engine.compute_metrics()
    assert 'raw_position_rmse' in m
    assert 'pid_acceleration_jitter' in m
    assert 'has_lost_target' in m


def test_simulation_with_steady_state_init():
    from simulation.simulation_engine import SimulationEngine
    scfg = get_scenario_config(1)
    scfg['steady_state_init'] = True
    engine = SimulationEngine()
    engine.setup(scfg)
    step = engine.simulation_step()
    # At t=0, distance should be very close to 50m
    assert abs(step.tracking_distance - 50.0) < 5.0


def test_compute_metrics_required_keys():
    from simulation.simulation_engine import SimulationEngine
    scfg = get_scenario_config(1)
    engine = SimulationEngine()
    engine.setup(scfg)
    for _ in range(50):
        engine.simulation_step()
    m = engine.compute_metrics()
    required_keys = [
        'max_separation', 'pid_step_jitter', 'pid_saturation_ratio',
        'camera_dropout_detected', 'has_lost_target', 'tracking_rmse_post10'
    ]
    for k in required_keys:
        assert k in m, f"Key '{k}' missing from compute_metrics output"


def test_target_stays_within_bounds_all_12_scenarios():
    """Verify that in all 12 scenarios, target stays within [20, 1180] x [20, 780] and never touches boundaries."""
    from simulation.simulation_engine import SimulationEngine
    for sc_id in range(1, 13):
        scfg = get_scenario_config(sc_id)
        engine = SimulationEngine()
        engine.setup(scfg)
        w, h = engine.world_width, engine.world_height
        margin = 20.0
        
        # Run entire scenario
        while engine.running:
            step = engine.simulation_step()
            tgt = step.target_gt
            assert margin <= tgt.x <= w - margin, f"Target x={tgt.x:.1f} hit boundary in Scenario {sc_id}"
            assert margin <= tgt.y <= h - margin, f"Target y={tgt.y:.1f} hit boundary in Scenario {sc_id}"


def test_minimum_tracking_distance_safety():
    """Verify that PID controller maintains safe separation (no near collisions < 5m) on baseline & turning."""
    from simulation.simulation_engine import SimulationEngine
    for sc_id in [1, 2, 6]:
        scfg = get_scenario_config(sc_id)
        engine = SimulationEngine()
        engine.setup(scfg)
        engine.run_headless()
        m = engine.compute_metrics()
        assert m['min_tracking_distance'] >= 10.0, f"Scenario {sc_id} penetrated safety buffer: min dist = {m['min_tracking_distance']:.2f}m"
