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

from wingbeat_lidar.digitizer import Digitizer

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


def compute_calibration_equation(data, distance):

    # Images are concatenated along the first dimension.
    N_CAPTURES = data.shape[0]

    target_bin = np.empty((N_CAPTURES, 1))

    # Find the calibration target in each data capture.
    for capture_num in range(0, N_CAPTURES):
        # The target should correspond to the largest negative return value.
        # We want to know the range bin where the minimum value occurred in
        # each column as this is where we assume the calibration target was at.
        target_bins = np.argmin(data[capture_num,:,:], axis=0)

        # Assume that the target is located at the median range bin.
        target_bin[capture_num] = np.median(target_bins)

    # Perform least-squares regression to determine the slope and offset.
    # The target range bin is the independent variable, and range/distance
    # is the dependent variable. We append a column of ones to the
    # "coefficient matrix" so we can solve for the offset.
    # The least squares solution is the first return value from lstsq.
    A = np.hstack((target_bin, np.ones((N_CAPTURES, 1))))
    x = np.linalg.lstsq(A, np.asarray(distance), rcond=None)[0]
    slope = x[0]
    offset = x[1]

    return (slope, offset)


def compute_range(range_bins):
    distance = calibration['slope'] * range_bins + calibration['offset']
    return distance


def collect_data(digitizer):
    distance = []
    data = None

    while True:
        user_input = input("Enter the target's range in meters. To exit, type n. Range: ")

        if user_input.lower() == 'n':
            break
        
        try:
            distance.append(float(user_input))
        except ValueError:
            print("Input could not be converted to a number")
        else:
            (d, timestamps, capture_time) = digitizer.capture()
            if data is not None:
                data = np.vstack(data, d)
            else:
                data = d

    return (data, distance)


def _configure_digitizer(digitizer_config):
    digitizer = Digitizer(digitizer_config)
    digitizer.initialize()
    digitizer.configure()

    return digitizer


def calibrate(digitizer_config, calibration_file):
    digitizer = _configure_digitizer(digitizer_config)

    (data, distance) = collect_data(digitizer)

    digitizer.free()

    (slope, offset) = compute_calibration_equation(data, distance)

    _save_calibration(slope, offset, calibration_file)


if __name__ == "__main__":
    calibrate()
