import unittest
import tomllib
import os
import numpy as np
from datetime import datetime

import wingbeat_lidar.range_calibration as rangecal

class TestRangeCalibration(unittest.TestCase):

    def setUp(self):
        self.RANGE_CAL_DIR = "range-calibration-configs"
    
    def test_save_calibration(self):
        slope = 1.23
        offset = -0.53
        calibration_file = "test-calibration.toml"

        rangecal._save_calibration(slope, offset, calibration_file)

        with open(calibration_file, 'rb') as f:
            actual = tomllib.load(f)

        self.assertEqual(slope, actual['slope'])
        self.assertEqual(offset, actual['offset'])

        # Date format is YYYY-MM-DD HH:MM
        self.assertRegex(actual['date'], '\d{4}-\d{2}-\d{2} \d{2}:\d{2}')

        os.remove(calibration_file)
    
    def test_save_and_load_calibration(self):
        slope = -13.23
        offset = -4.53
        calibration_file = "test-calibration.toml"

        rangecal._save_calibration(slope, offset, calibration_file)
        
        rangecal.load_calibration(calibration_file)

        # XXX: this test relies on knowing that there is a module-wide calibration
        # variable in the range_calibration module
        actual = rangecal.calibration

        self.assertEqual(slope, actual['slope'])
        self.assertEqual(offset, actual['offset'])

        # Date format is YYYY-MM-DD HH:MM
        self.assertRegex(actual['date'], '\d{4}-\d{2}-\d{2} \d{2}:\d{2}')

        os.remove(calibration_file)

    def test_invalid_calibration_file_keys(self):
        with self.assertRaises(RuntimeError):
            rangecal.load_calibration(self.RANGE_CAL_DIR + '/invalid-keys.toml')

    def test_invalid_calibration_file_slope(self):
        with self.assertRaises(RuntimeError):
            rangecal.load_calibration(self.RANGE_CAL_DIR + '/invalid-slope-datatype.toml')

    def test_invalid_calibration_file_offset(self):
        with self.assertRaises(RuntimeError):
            rangecal.load_calibration(self.RANGE_CAL_DIR + '/invalid-offset-datatype.toml')

    def test_invalid_calibration_file_date(self):
        with self.assertRaises(RuntimeError):
            rangecal.load_calibration(self.RANGE_CAL_DIR + '/invalid-date-datatype.toml')

    def test_compute_range(self):
        range_bins = np.arange(0,128)
        slope = 2
        offset = 1
        expected = np.arange(1,128*2,2)

        # Must set calibration constants before computing range
        rangecal.calibration['slope'] = slope
        rangecal.calibration['offset'] = offset

        distance = rangecal.compute_range(range_bins)

        self.assertSequenceEqual(distance.tolist(), expected.tolist())

    def test_compute_range2(self):
        range_bins = np.arange(0,1024)
        slope = 0.4223
        offset = -0.5

        expected = slope * range_bins + offset

        # Must set calibration constants before computing range
        rangecal.calibration['slope'] = slope
        rangecal.calibration['offset'] = offset

        distance = rangecal.compute_range(range_bins)

        self.assertSequenceEqual(distance.tolist(), expected.tolist())

    def test_compute_range3(self):
        range_bins = np.arange(0,2048)
        slope = 0.123
        offset = 5.5

        expected = slope * range_bins + offset

        # Must set calibration constants before computing range
        rangecal.calibration['slope'] = slope
        rangecal.calibration['offset'] = offset

        distance = rangecal.compute_range(range_bins)

        self.assertSequenceEqual(distance.tolist(), expected.tolist())
    
    def test_compute_calibration_equation_synthetic_simple(self):
        N_CAPTURES = 9
        distances = range(0, N_CAPTURES)
        data = np.zeros((N_CAPTURES, N_CAPTURES, 64))

        # Create a hard target at each range bin.
        for i in range(0, N_CAPTURES):
            data[i,i,:] = -10

        expected_slope = 1
        expected_offset = 0

        (slope, offset) = rangecal.compute_calibration_equation(data, distances)

        self.assertAlmostEqual(slope, expected_slope)
        self.assertAlmostEqual(offset, expected_offset)
    
    def test_compute_calibration_equation_synthetic_simple_with_noise(self):
        rng = np.random.default_rng()

        N_CAPTURES = 9
        distances = np.arange(0, N_CAPTURES)
        data = np.zeros((N_CAPTURES, N_CAPTURES, 64))
        data = data + rng.normal(size=data.shape)

        # Create a hard target at each range bin.
        for i in range(0, N_CAPTURES):
            data[i,i,:] = -2

        expected_slope = 1
        expected_offset = 0

        (slope, offset) = rangecal.compute_calibration_equation(data, distances)

        self.assertAlmostEqual(slope, expected_slope)
        self.assertAlmostEqual(offset, expected_offset)

    def test_compute_calibration_equation_synthetic_float_slope_offset(self):
        rng = np.random.default_rng()

        expected_slope = 0.22
        expected_offset = 5.213

        N_CAPTURES = 16

        distances = np.arange(0, N_CAPTURES) * expected_slope + expected_offset

        data = np.zeros((N_CAPTURES, N_CAPTURES, 128))
        data = data + rng.normal(size=data.shape)

        # Create a hard target at each range bin.
        for i in range(0, N_CAPTURES):
            data[i,i,:] = -2

        (slope, offset) = rangecal.compute_calibration_equation(data, distances)

        self.assertAlmostEqual(slope, expected_slope)
        self.assertAlmostEqual(offset, expected_offset)

    def test_compute_calibration_equation_synthetic_not_every_range_bin(self):
        rng = np.random.default_rng()

        expected_slope = 1/4 
        expected_offset = 0

        N_CAPTURES = 32

        distances = np.arange(0, N_CAPTURES) 

        data = np.zeros((N_CAPTURES, N_CAPTURES * int(1/expected_slope), 1024))
        data = data + rng.normal(size=data.shape)

        # Create a hard target every fourth range bin.
        for i in range(0, N_CAPTURES):
            data[i,i * int(1/expected_slope),:] = -5

        (slope, offset) = rangecal.compute_calibration_equation(data, distances)

        self.assertAlmostEqual(slope, expected_slope)
        self.assertAlmostEqual(offset, expected_offset)
