"""Unit tests for UKF."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import unittest
from filters.ukf import UnscentedKalmanFilter


class TestUKF(unittest.TestCase):

    def test_initialization(self):
        ukf = UnscentedKalmanFilter(measurement_model='range_bearing')
        x0 = np.array([100.0, 200.0, 10.0, 5.0])
        ukf.initialize(x0)
        np.testing.assert_array_almost_equal(ukf.x, x0)
        self.assertTrue(ukf.initialized)

    def test_sigma_points_count(self):
        ukf = UnscentedKalmanFilter(state_dim=4)
        self.assertEqual(ukf.n_sigma, 9)  # 2*4+1

    def test_weights_sum(self):
        ukf = UnscentedKalmanFilter(state_dim=4)
        self.assertAlmostEqual(np.sum(ukf.Wm), 1.0, places=5)

    def test_predict_cv(self):
        ukf = UnscentedKalmanFilter(dt=0.1, measurement_model='xy')
        ukf.initialize(np.array([0.0, 0.0, 10.0, 5.0]))
        ukf.predict(0.1)
        self.assertAlmostEqual(ukf.x[0], 1.0, delta=0.5)
        self.assertAlmostEqual(ukf.x[1], 0.5, delta=0.5)

    def test_update_xy(self):
        ukf = UnscentedKalmanFilter(measurement_model='xy')
        ukf.initialize(np.array([0.0, 0.0, 0.0, 0.0]))
        ukf.set_measurement_noise(np.diag([1.0, 1.0]))
        z = np.array([10.0, 5.0])
        pose = {'x': 0, 'y': 0, 'heading': 0}
        est = ukf.update(z, pose)
        self.assertTrue(est.updated)
        self.assertGreater(ukf.x[0], 0)

    def test_update_range_bearing(self):
        ukf = UnscentedKalmanFilter(measurement_model='range_bearing')
        ukf.initialize(np.array([100.0, 0.0, 0.0, 0.0]))
        ukf.set_measurement_noise(np.diag([1.0, 0.01]))
        z = np.array([100.0, 0.0])
        pose = {'x': 0, 'y': 0, 'heading': 0}
        est = ukf.update(z, pose)
        self.assertTrue(est.updated)

    def test_prediction_only_no_measurement(self):
        ukf = UnscentedKalmanFilter(dt=0.1, measurement_model='xy')
        ukf.initialize(np.array([0.0, 0.0, 10.0, 0.0]))
        pose = {'x': 0, 'y': 0, 'heading': 0}
        est = ukf.step(None, pose, 0.1, 0.1)
        self.assertFalse(est.updated)

    def test_covariance_grows_without_update(self):
        ukf = UnscentedKalmanFilter(dt=0.1, measurement_model='xy')
        ukf.initialize(np.array([0.0, 0.0, 10.0, 0.0]), np.eye(4) * 10)
        P_before = np.trace(ukf.P)
        pose = {'x': 0, 'y': 0, 'heading': 0}
        for i in range(10):
            ukf.step(None, pose, 0.1, i * 0.1)
        self.assertGreater(np.trace(ukf.P), P_before)

    def test_covariance_symmetric(self):
        ukf = UnscentedKalmanFilter(measurement_model='range_bearing')
        ukf.initialize(np.array([100.0, 50.0, 10.0, 5.0]))
        pose = {'x': 0, 'y': 0, 'heading': 0}
        ukf.step(np.array([112.0, 0.46]), pose, 0.02, 0.02)
        np.testing.assert_array_almost_equal(ukf.P, ukf.P.T, decimal=10)

    def test_get_estimated_state(self):
        ukf = UnscentedKalmanFilter()
        ukf.initialize(np.array([1.0, 2.0, 3.0, 4.0]))
        est = ukf.get_estimated_state()
        self.assertAlmostEqual(est['x'], 1.0)
        self.assertAlmostEqual(est['vy'], 4.0)


    def test_sigma_points_covariance_reconstruction(self):
        """Test that sigma points reconstruct the exact prior covariance P."""
        ukf = UnscentedKalmanFilter()
        x0 = np.array([10.0, 20.0, 5.0, -3.0])
        P0 = np.array([
            [25.0, 5.0, 1.0, 0.5],
            [5.0, 30.0, 2.0, 1.0],
            [1.0, 2.0, 10.0, 0.0],
            [0.5, 1.0, 0.0, 8.0]
        ])
        sigmas = ukf._generate_sigma_points(x0, P0)
        
        # Reconstruct covariance from sigma points
        P_recon = np.zeros((4, 4))
        for i in range(ukf.n_sigma):
            diff = sigmas[i] - x0
            P_recon += ukf.Wc[i] * np.outer(diff, diff)
            
        np.testing.assert_array_almost_equal(P_recon, P0, decimal=5)


if __name__ == '__main__':
    unittest.main()
