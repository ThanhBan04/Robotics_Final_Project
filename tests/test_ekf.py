"""Unit tests for EKF."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import unittest
from filters.ekf import ExtendedKalmanFilter


class TestEKF(unittest.TestCase):

    def test_initialization(self):
        ekf = ExtendedKalmanFilter(measurement_model='range_bearing')
        x0 = np.array([100.0, 200.0, 10.0, 5.0])
        ekf.initialize(x0)
        np.testing.assert_array_almost_equal(ekf.x, x0)
        self.assertTrue(ekf.initialized)

    def test_predict_cv(self):
        ekf = ExtendedKalmanFilter(dt=0.1, measurement_model='xy')
        ekf.initialize(np.array([0.0, 0.0, 10.0, 5.0]))
        est = ekf.predict(0.1)
        self.assertAlmostEqual(ekf.x[0], 1.0, places=3)   # x = 0 + 10*0.1
        self.assertAlmostEqual(ekf.x[1], 0.5, places=3)   # y = 0 + 5*0.1
        self.assertAlmostEqual(ekf.x[2], 10.0, places=3)
        self.assertAlmostEqual(ekf.x[3], 5.0, places=3)

    def test_update_xy(self):
        ekf = ExtendedKalmanFilter(measurement_model='xy')
        ekf.initialize(np.array([0.0, 0.0, 0.0, 0.0]))
        ekf.set_measurement_noise(np.diag([1.0, 1.0]))
        z = np.array([10.0, 5.0])
        pose = {'x': 0, 'y': 0, 'heading': 0}
        est = ekf.update(z, pose)
        self.assertTrue(est.updated)
        # After update, state should move towards measurement
        self.assertGreater(ekf.x[0], 0)
        self.assertGreater(ekf.x[1], 0)

    def test_update_range_bearing(self):
        ekf = ExtendedKalmanFilter(measurement_model='range_bearing')
        ekf.initialize(np.array([100.0, 0.0, 0.0, 0.0]))
        ekf.set_measurement_noise(np.diag([1.0, 0.01]))
        z = np.array([100.0, 0.0])  # range=100, bearing=0
        pose = {'x': 0, 'y': 0, 'heading': 0}
        est = ekf.update(z, pose)
        self.assertTrue(est.updated)
        self.assertIsNotNone(est.innovation)

    def test_prediction_only_when_no_measurement(self):
        ekf = ExtendedKalmanFilter(dt=0.1, measurement_model='xy')
        ekf.initialize(np.array([0.0, 0.0, 10.0, 0.0]))
        pose = {'x': 0, 'y': 0, 'heading': 0}
        est = ekf.step(None, pose, 0.1, 0.1)
        self.assertFalse(est.updated)
        self.assertAlmostEqual(ekf.x[0], 1.0, places=3)

    def test_covariance_grows_without_update(self):
        ekf = ExtendedKalmanFilter(dt=0.1, measurement_model='xy')
        ekf.initialize(np.array([0.0, 0.0, 10.0, 0.0]), np.eye(4) * 10)
        P_before = np.trace(ekf.P)
        pose = {'x': 0, 'y': 0, 'heading': 0}
        for i in range(10):
            ekf.step(None, pose, 0.1, i * 0.1)
        P_after = np.trace(ekf.P)
        self.assertGreater(P_after, P_before)

    def test_covariance_symmetric(self):
        ekf = ExtendedKalmanFilter(measurement_model='range_bearing')
        ekf.initialize(np.array([100.0, 50.0, 10.0, 5.0]))
        pose = {'x': 0, 'y': 0, 'heading': 0}
        ekf.step(np.array([112.0, 0.46]), pose, 0.02, 0.02)
        np.testing.assert_array_almost_equal(ekf.P, ekf.P.T, decimal=10)

    def test_get_estimated_state(self):
        ekf = ExtendedKalmanFilter()
        ekf.initialize(np.array([1.0, 2.0, 3.0, 4.0]))
        est = ekf.get_estimated_state()
        self.assertAlmostEqual(est['x'], 1.0)
        self.assertAlmostEqual(est['vy'], 4.0)


if __name__ == '__main__':
    unittest.main()
