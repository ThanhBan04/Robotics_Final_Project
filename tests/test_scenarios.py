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
