"""Utilities for calibrating the lidar's range.

In order to assign physical distances to each range bin, a range calibration
needs to be performed. This module provides methods to help with range
calibration.

There are two common use cases for this module:
1. Performing a range calibration by running this module as a script.
2. Using a pre-existing calibration to convert range bins to distance.

Examples:
    Running the range calibration script:
        python range_calibration.py

    Printing usage information:
        python range_calibration.py -h

    Converting range bins to distance:
        from wingbeat_lidar.digitizer import Digitizer
        import wingbeat_lidar.range_calibration as rangecal

        rangecal.load_calibration('config/calibration.toml')

        # Collect data
        digitizer = Digitizer('config/digitizer.toml')
        digitizer.initialize()
        digitizer.configure()
        (data, timestamps, capture_time) = digitizer.capture()

        range_bins = np.arange(0,digitizer.acquisition_config.SegmentSize)
        distance = rangecal.compute_range(range_bins)
"""

import sys
import argparse
import tomllib
import tomli_w
import numpy as np
import warnings
from datetime import datetime

from wingbeat_lidar.digitizer import Digitizer

calibration = {'slope': None, 'offset': None, 'date': None}

def load_calibration(calibration_file):
    """Load an existing calibration file.

    Parses a TOML calibration configuration and loads the calibration
    constants for later use.

    Args:
        calibration_file:
            Path to the calibration TOML file.
    """
    global calibration

    # Load the configuration file
    with open(calibration_file, 'rb') as f:
        toml = tomllib.load(f)

    # Check that the configuration file has the correct fields
    EXPECTED_FIELDS = {'slope', 'offset', 'date', 'r-squared'}
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

    # Set the calibration settings. We don't use the r-squared value from the
    # configuration because it is not necessary for the calibration equation.
    # TODO: date is also not necessary, so maybe we should consider not loading
    # the date into the global calibration dictionary either. Or we just load
    # everything into the calibration dictionary because users might want to look
    # at the calibration metadata from python instead of opening the toml file?
    calibration['slope'] = toml['slope']
    calibration['offset'] = toml['offset']
    calibration['date'] = toml['date']


def _save_calibration(slope, offset, r2, calibration_file):
    """Save the calibration constants to a TOML calibration file.

    Args:
        slope:
            Slope of the calibration equation.
        offset:
            Offset of the calibration equation.
        calibration_file:
            Where to save the calibration file.
    """
    date = datetime.today().isoformat(sep=' ', timespec='minutes')

    calibration['slope'] = slope
    calibration['offset'] = offset
    calibration['r-squared'] = r2
    calibration['date'] = date

    with open(calibration_file, 'wb') as f:
        tomli_w.dump(calibration, f)


def compute_calibration_equation(data, distance):
    """Compute the calibration equation.

    The calibration equation is of the form:
    distance = slope * range_bin + offset

    Args:
        data:
            The data matrix. The matrix needs to be 3-D, where the first
            dimension is the number of images captured during calibration.
        distance:
            List of target distances. Length must be the number of images
            captured during calibration.

    Returns:
        slope:
            Slope of the best-fit line.
        offset:
            Offset of the best-fit line.
        r2:
            R^2 value of the fit.
    """
    distance = np.asarray(distance)

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
    fit, residuals = np.linalg.lstsq(A, distance, rcond=None)[0:2]
    slope = fit[0]
    offset = fit[1]

    # If not enough points were collected, residuals will be an empty array.
    # Only compute the goodness of fit when the residuals aren't empty.
    if residuals.size > 0:
        # Compute the goodness of fit using R^2 value:
        # https://en.wikipedia.org/wiki/Coefficient_of_determination
        total_sum_of_squares = N_CAPTURES * distance.var()
        r2 = (1 - (residuals / total_sum_of_squares))[0]
    else:
        warnings.warn("Residuals from fit were empty, indicating the fit was"
                      "not good. Please rerun the calibration. Perhaps you"
                      "need to collect more data points.")
        r2 = []

    return (slope, offset, r2)


def compute_range(range_bins):
    """Convert range bins into distances.

    Args:
        range_bins:
            Array of range bin indices. This must be the number of samples
            in each collected during each pulse, i.e. the number of rows
            in each data capture.

    Returns:
        distance:
            Array of distances, in meters, corresponding to the range bins.
    """
    distance = calibration['slope'] * range_bins + calibration['offset']
    return distance


def collect_data(digitizer):
    """Prompt for and collect calibration data.

    For each target distance, the user is prompted to enter the distance,
    as measured by a rangefinder. One data capture is collected at each
    target distance. Target distances should be in increments of about 0.5
    meters. Data should be collected at about 40 distances (or enough to
    get a good fit).

    Args:
        digitizer:
            The digitizer object used to collect data.

    Returns:
        data:
            3-D Matrix of collected data. The first dimension is the number of
            calibration points taken. The other two dimensions are the size
            of the data captures.
        distance:
            List of manually measured distances, as input by the user.
    """
    distance = []
    data_list = []

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
            data_list.append(d)

    if data_list:
        # Concatenate list of 2-D data arrays into 3-D
        data = np.stack(data_list, axis=0)
    else:
        # No data were collected, so we return an empty data array, which will
        # tells us to end the program and not comptue the calibration
        data = np.array([])

    return (data, distance)


def _configure_digitizer(digitizer_config):
    """Prepare the digitizer for data collection.

    Args:
        digitizer_config:
            Digitizer TOML configuration file.

    Returns:
        digitizer:
            The configured digitizer object.
    """
    digitizer = Digitizer(digitizer_config)
    digitizer.initialize()
    digitizer.configure()

    return digitizer


def calibrate(digitizer_config, calibration_file):
    """Main calibration routine.

    This is entry-point for running the calibration.

    Args:
        digitizer_config:
            Digitizer TOML configuration file.
        calibration_file:
            TOML file to save the calibration constants in.
    """
    digitizer = _configure_digitizer(digitizer_config)

    (data, distance) = collect_data(digitizer)

    # Only compute and save the calibration if data were collected
    if data.size > 0:
        (slope, offset, r2) = compute_calibration_equation(data, distance)

        _save_calibration(slope, offset, r2, calibration_file)

        print(f"Calibration results:\n\tslope = {slope}\n\toffset = {offset}\n\tR^2 = {r2}")
    else:
        warnings.warn("No data were collected, so the calibration was not be saved.")

def main():
    """Entry-point for running the range calibration script."""
    parser = argparse.ArgumentParser(
        description='Wingbeat-modulation lidar range calibration program.',
        epilog=('To use this program, you need a hard target and a rangefinder.'
            ' During each iteration, you measure how far the hard target'
            ' is away from the front of the lidar using a rangefinder.'
            ' The hard target should be moved in steps of ~0.5 meters.')
    )

    parser.add_argument('-d', '--digitizer-config', required=False,
        type=argparse.FileType('r'), default='./config/digitizer.toml',
        help=('Which digitizer configuration TOML file to use. '
            '(default: ./config/digitizer.toml)')
    )
    parser.add_argument('-c', '--calibration-file', required=False,
        type=argparse.FileType('w'), default='./config/calibration.toml',
        help=('Calibration file to save results to. '
            '(default: ./config/calibration.toml)')
    )

    args = parser.parse_args()

    calibrate(args.digitizer_config, args.calibration_file)

    return 0

if __name__ == "__main__":
    sys.exit(main())
