"""Unit tests for Target Model."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import unittest
from models.target_model import TargetModel, TargetState


class TestTargetModel(unittest.TestCase):

    def test_initial_state(self):
        model = TargetModel(initial_x=100, initial_y=200, initial_vx=10, initial_vy=5)
        self.assertAlmostEqual(model.state.x, 100)
        self.assertAlmostEqual(model.state.y, 200)

    def test_straight_trajectory(self):
        model = TargetModel(initial_x=0, initial_y=0, initial_vx=10, initial_vy=0,
                            trajectory_type='straight', process_noise_std=0, random_seed=42)
        dt = 0.02
        for i in range(100):
            model.step(dt, i * dt)
        # After 2 seconds at 10 m/s, x should be ~20
        self.assertAlmostEqual(model.state.x, 20.0, delta=2.0)

    def test_velocity_saturation(self):
        model = TargetModel(max_speed=50, initial_vx=100, initial_vy=0,
                            trajectory_type='straight', process_noise_std=0, random_seed=42)
        model.step(0.02, 0)
        speed = model.state.speed()
        self.assertLessEqual(speed, 50.1)

    def test_reset(self):
        model = TargetModel(initial_x=100, initial_y=200, random_seed=42)
        model.step(0.02, 0)
        model.reset()
        self.assertAlmostEqual(model.state.x, 100)

    def test_state_vector(self):
        state = TargetState(1, 2, 3, 4)
        vec = state.state_vector()
        np.testing.assert_array_equal(vec, [1, 2, 3, 4])

    def test_interactive_click(self):
        model = TargetModel(trajectory_type='interactive', process_noise_std=0, random_seed=42)
        model.set_target_position(500, 500)
        for i in range(200):
            model.step(0.02, i * 0.02)
        # Should have moved towards target
        dist = np.sqrt((model.state.x - 500)**2 + (model.state.y - 500)**2)
        self.assertLess(dist, 300)

    def test_circular_trajectory(self):
        model = TargetModel(trajectory_type='circular', circular_radius=100,
                            circular_omega=0.5, process_noise_std=0, random_seed=42)
        for i in range(500):
            model.step(0.02, i * 0.02)
        # Should stay roughly within circular area
        self.assertLess(abs(model.state.x), 500)


class TestStateTransitionMatrix(unittest.TestCase):

    def test_cv_matrix(self):
        model = TargetModel()
        dt = 0.1
        F = model.get_state_transition_matrix(dt)
        expected = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])
        np.testing.assert_array_almost_equal(F, expected)

    def test_process_noise_symmetric(self):
        model = TargetModel()
        Q = model.get_process_noise_covariance(0.02)
        np.testing.assert_array_almost_equal(Q, Q.T)


if __name__ == '__main__':
    unittest.main()
