"""Unit tests for UAV Model."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import unittest
from models.uav_model import UAVModel, UAVState


class TestUAVModel(unittest.TestCase):

    def test_initial_state(self):
        model = UAVModel(initial_x=50, initial_y=100)
        self.assertAlmostEqual(model.state.x, 50)
        self.assertAlmostEqual(model.state.y, 100)

    def test_acceleration_response(self):
        model = UAVModel(initial_x=0, initial_y=0, initial_vx=0, initial_vy=0)
        acc = np.array([10.0, 0.0])
        model.step(acc, 0.1, 0)
        self.assertGreater(model.state.vx, 0)
        self.assertGreater(model.state.x, 0)

    def test_acceleration_saturation(self):
        model = UAVModel(max_acceleration=10.0)
        acc = np.array([100.0, 100.0])
        sat = model._saturate_acceleration(acc)
        self.assertAlmostEqual(np.linalg.norm(sat), 10.0, places=5)

    def test_velocity_saturation(self):
        model = UAVModel(max_speed=50.0, initial_vx=0, initial_vy=0)
        # Apply large acceleration for many steps
        for i in range(100):
            model.step(np.array([25.0, 0.0]), 0.1, i * 0.1)
        self.assertLessEqual(model.state.speed(), 50.01)

    def test_reset(self):
        model = UAVModel(initial_x=10, initial_y=20)
        model.step(np.array([5.0, 5.0]), 0.1, 0)
        model.reset()
        self.assertAlmostEqual(model.state.x, 10)
        self.assertAlmostEqual(model.state.y, 20)

    def test_heading_update(self):
        model = UAVModel(initial_vx=10, initial_vy=0)
        model._update_heading()
        self.assertAlmostEqual(model.state.heading, 0.0, places=3)

    def test_world_bounds(self):
        model = UAVModel(initial_x=5, initial_y=5, world_bounds=(100, 100))
        model.step(np.array([-25.0, -25.0]), 1.0, 0)
        self.assertGreaterEqual(model.state.x, 0)
        self.assertGreaterEqual(model.state.y, 0)


if __name__ == '__main__':
    unittest.main()
