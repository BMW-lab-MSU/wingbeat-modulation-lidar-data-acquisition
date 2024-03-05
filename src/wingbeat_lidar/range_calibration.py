"""Utilities for calibrating the lidar's range.

In order to assign physical distances to each range bin, a range calibration
needs to be performed. This module provides methods to help with range
calibration. 

"""

import argparse
import tomllib
import tomli_w
import numpy as np
import warnings
from datetime import datetime

# from wingbeat_lidar.digitizer import Digitizer

calibration = {'slope': None, 'offset': None, 'date': None}

def load_calibration(calibration_file):
    global calibration

    # Load the configuration file
    with open(calibration_file, 'rb') as f:
        toml = tomllib.load(f)

    # Check that the configuration file has the correct fields
    EXPECTED_FIELDS = {'slope','offset','date'}
    if toml.keys() != EXPECTED_FIELDS:
        raise RuntimeError("Range calibration file has an invalid set of keys:" +
            f"\nkeys = {toml.keys()}, expected = {EXPECTED_FIELDS}")

    # Check that the fields have the correct data types
    if not isinstance(toml['slope'],(int, float)):
        raise RuntimeError("slope must be an int or a float.")
    if not isinstance(toml['offset'],(int, float)):
        raise RuntimeError("offset must be an int or a float.")
    if not isinstance(toml['date'],(str)):
        raise RuntimeError("date must be a string.")

    # Set the calibration settings
    calibration['slope'] = toml['slope']
    calibration['offset'] = toml['offset']
    calibration['date'] = toml['date']


def _save_calibration(slope, offset, calibration_file):
    global calibration

    date = datetime.today().isoformat(sep=' ', timespec='minutes')

    calibration['slope'] = slope
    calibration['offset'] =offset
    calibration['date'] = date
    
    with open(calibration_file, 'wb') as f:
        tomli_w.dump(calibration, f)


def compute_calibration_equation():
    pass


def compute_range(range_bins):
    distance = calibration['slope'] * range_bins + calibration['offset']
    return distance


def collect_data(digitizer):
    pass


def _configure_digitizer(digitizer_config):
    digitizer = Digitizer(digitizer_config)
    digitizer.initialize()
    digitizer.configure()

    return digitizer


def calibrate(digitizer_config):
    digitizer = _configure_digitizer(digitizer_config)

    (data, distance) = collect_data(digitizer)

    (slope, offset) = compute_calibration_equation()

    _save_calibration()

    pass


if __name__ == "__main__":
    calibrate()
