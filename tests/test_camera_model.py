"""Unit tests for Camera Model."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import unittest
from models.camera_model import CameraModel, Measurement
from models.target_model import TargetState


class TestCameraModel(unittest.TestCase):

    def _make_uav_pose(self, x=0, y=0, heading=0):
        return {'x': x, 'y': y, 'heading': heading}

    def test_range_bearing_measurement(self):
        cam = CameraModel(measurement_model='range_bearing', noise_range_std=0.01,
                          noise_bearing_std=0.001, random_seed=42)
        target = TargetState(x=100, y=0)
        uav_pose = self._make_uav_pose(0, 0, 0)
        m = cam.measure(target, uav_pose, 0.0)
        self.assertTrue(m.detected)
        self.assertAlmostEqual(m.data[0], 100.0, delta=1.0)  # range ~100
        self.assertAlmostEqual(m.data[1], 0.0, delta=0.1)    # bearing ~0

    def test_xy_measurement(self):
        cam = CameraModel(measurement_model='xy', noise_xy_std=0.01, random_seed=42)
        target = TargetState(x=50, y=30)
        uav_pose = self._make_uav_pose(0, 0, 0)
        m = cam.measure(target, uav_pose, 0.0)
        self.assertTrue(m.detected)
        self.assertAlmostEqual(m.data[0], 50.0, delta=1.0)
        self.assertAlmostEqual(m.data[1], 30.0, delta=1.0)

    def test_fov_check_in(self):
        cam = CameraModel(fov_angle=90, max_range=200)
        self.assertTrue(cam._check_fov(np.array([100, 0]), np.array([0, 0]), 0.0))

    def test_fov_check_out_range(self):
        cam = CameraModel(fov_angle=90, max_range=50)
        self.assertFalse(cam._check_fov(np.array([100, 0]), np.array([0, 0]), 0.0))

    def test_fov_check_out_angle(self):
        cam = CameraModel(fov_angle=30, max_range=500)
        # Target behind UAV
        self.assertFalse(cam._check_fov(np.array([-100, 0]), np.array([0, 0]), 0.0))

    def test_dropout(self):
        cam = CameraModel(random_seed=42)
        cam.trigger_dropout(0.0, 1.0)
        target = TargetState(x=100, y=0)
        uav_pose = self._make_uav_pose(0, 0, 0)
        m = cam.measure(target, uav_pose, 0.5)
        self.assertFalse(m.detected)

    def test_no_dropout_after_duration(self):
        cam = CameraModel(random_seed=42)
        cam.trigger_dropout(0.0, 0.5)
        target = TargetState(x=100, y=0)
        uav_pose = self._make_uav_pose(0, 0, 0)
        m = cam.measure(target, uav_pose, 1.0)
        self.assertTrue(m.detected)

    def test_measurement_noise_covariance(self):
        cam = CameraModel(measurement_model='range_bearing', noise_range_std=2.0,
                          noise_bearing_std=0.05)
        R = cam.get_measurement_noise_covariance()
        self.assertAlmostEqual(R[0, 0], 4.0)
        self.assertAlmostEqual(R[1, 1], 0.0025)

    def test_jacobian_range_bearing(self):
        state = np.array([100.0, 0.0, 0.0, 0.0])
        pose = {'x': 0, 'y': 0, 'heading': 0}
        H = CameraModel.measurement_jacobian_range_bearing(state, pose)
        self.assertEqual(H.shape, (2, 4))
        self.assertAlmostEqual(H[0, 0], 1.0, places=3)  # dr/dx when target at (100,0)


if __name__ == '__main__':
    unittest.main()
