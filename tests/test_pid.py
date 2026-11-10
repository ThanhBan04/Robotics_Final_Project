"""Unit tests for PID Controller."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import unittest
from control.pid_controller import PIDController
from models.uav_model import UAVState


class TestPIDController(unittest.TestCase):

    def _make_uav(self, x=0, y=0, vx=0, vy=0):
        return UAVState(x=x, y=y, vx=vx, vy=vy)

    def test_initial_output(self):
        pid = PIDController(kp=1.0, ki=0, kd=0, desired_distance=50)
        est = {'x': 100.0, 'y': 0.0, 'vx': 10.0, 'vy': 0.0}
        uav = self._make_uav(0, 0)
        acc = pid.compute(est, uav, 0.02)
        self.assertEqual(len(acc), 2)
        # Should accelerate towards desired position (behind target)
        self.assertGreater(acc[0], 0)

    def test_desired_position_behind_target(self):
        pid = PIDController(desired_distance=50)
        est = {'x': 200.0, 'y': 0.0, 'vx': 20.0, 'vy': 0.0}
        uav = self._make_uav(100, 0)
        desired = pid.compute_desired_position(est, uav)
        # Desired should be 50m behind target along velocity direction
        self.assertAlmostEqual(desired[0], 150.0, delta=1.0)
        self.assertAlmostEqual(desired[1], 0.0, delta=1.0)

    def test_desired_position_stationary_target(self):
        pid = PIDController(desired_distance=50)
        est = {'x': 200.0, 'y': 0.0, 'vx': 0.0, 'vy': 0.0}
        uav = self._make_uav(100, 0)
        desired = pid.compute_desired_position(est, uav)
        # Should be 50m from target towards UAV
        self.assertAlmostEqual(desired[0], 150.0, delta=1.0)

    def test_acceleration_saturation(self):
        pid = PIDController(kp=100, ki=0, kd=0, max_acceleration=10.0)
        est = {'x': 1000.0, 'y': 1000.0, 'vx': 0.0, 'vy': 0.0}
        uav = self._make_uav(0, 0)
        acc = pid.compute(est, uav, 0.02)
        self.assertLessEqual(np.linalg.norm(acc), 10.01)

    def test_anti_windup(self):
        pid = PIDController(kp=0, ki=1.0, kd=0, integral_limit=10.0)
        est = {'x': 1000.0, 'y': 0.0, 'vx': 0.0, 'vy': 0.0}
        uav = self._make_uav(0, 0)
        for _ in range(1000):
            pid.compute(est, uav, 0.02)
        self.assertLessEqual(abs(pid.integral_x), 10.01)
        self.assertLessEqual(abs(pid.integral_y), 10.01)

    def test_reset(self):
        pid = PIDController()
        est = {'x': 100.0, 'y': 0.0, 'vx': 10.0, 'vy': 0.0}
        uav = self._make_uav(0, 0)
        pid.compute(est, uav, 0.02)
        pid.reset()
        self.assertAlmostEqual(pid.integral_x, 0.0)
        self.assertAlmostEqual(pid.integral_y, 0.0)
        self.assertFalse(pid.initialized)

    def test_zero_dt_no_crash(self):
        pid = PIDController()
        est = {'x': 100.0, 'y': 0.0, 'vx': 10.0, 'vy': 0.0}
        uav = self._make_uav(0, 0)
        acc = pid.compute(est, uav, 0.0)
        np.testing.assert_array_equal(acc, [0.0, 0.0])

    def test_get_status(self):
        pid = PIDController(kp=2, ki=0.1, kd=1.5)
        status = pid.get_status()
        self.assertEqual(status['kp'], 2)
        self.assertEqual(status['ki'], 0.1)


if __name__ == '__main__':
    unittest.main()
