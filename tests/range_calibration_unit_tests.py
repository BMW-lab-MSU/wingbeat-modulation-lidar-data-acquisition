import unittest
import tomllib
import os
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
        
        
