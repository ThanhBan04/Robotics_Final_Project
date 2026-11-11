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
