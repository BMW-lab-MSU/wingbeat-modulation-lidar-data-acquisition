import unittest
import tomllib
import os
import numpy as np
from datetime import datetime

import wingbeat_lidar.range_calibration as rangecal


class TestRangeCalibration(unittest.TestCase):

    def setUp(self):
        self.RANGE_CAL_DIR = "range-calibration-configs"

    def test_calibration_procedure(self):
        DIGITIZER_CONFIG = "adc-configs/range-calibration-test-config.toml"
        CALIBRATION_CONFIG = self.RANGE_CAL_DIR + "/range-calibration.toml"

        rangecal.calibrate(DIGITIZER_CONFIG, CALIBRATION_CONFIG)
