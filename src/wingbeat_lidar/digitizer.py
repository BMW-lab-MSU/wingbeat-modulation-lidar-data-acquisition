"""This module provides an interface to Gage digitizers.

This module allows users to capture data from a Gage digitizer. The digitizer
is configured via a TOML configuration file. Once the configuration file has
been loaded and the digitizer has been configured, data can then be captured
and saved.

.. _Gage digitizers: https://vitrek.com/gage/digitizers/

Examples:
    Loading configuration in constructor:
        digitizer = Digitizer("config.toml")
        digitizer.initialize()
        digitizer.configure()
        (data,timestamps,capture_time) = digitizer.capture()

    Loading configuration separately:
        digitizer = Digitizer()
        digitizer.initialize()
        digitizer.load_configuration("config.toml")
        digitizer.configure()
        (data,timestamps,capture_time) = digitizer.capture()
"""

# SPDX-License-Identifier: BSD-3-Clause

import warnings
import tomllib
import h5py
import numpy as np
from datetime import datetime
from typing import NamedTuple

import PyGage
from gagesupport import GageConstants as gc


class Digitizer:
    def __init__(self, config_filename=None):
        """Creates an instance of the Digitizer class.

        Args:
            config_filename (str|None):
                The filename of a digitizer TOML configuration file that
                will be used to configure the digitizer settings.
        """

        # _digitizer_handle is a integer that refers to which compuscope
        # system we are using. This is returned from PyGage.GetSystem().
        self._digitizer_handle = None

        self.system_info = None

        if config_filename:
            self.load_configuration(config_filename)
        else:
            self.acquisition_config = None
            self.channel_config = None
            self.trigger_config = None

    def __del__(self):
        # Explicitly free the digitizer before the instance is about to be
        # destroyed, just in case the user doesn't call free() themselves.
        # If the digitizer has already been freed, then the compuscope SDK
        # will return an error code, which we can ignore.
        self.free()

    def initialize(self):
        """Initializes the digitizer hardware."""
        status = PyGage.Initialize()
        if status < 0:
            raise RuntimeError(
                f"Failed to initialize digitizer:\nErrno = {status}, {PyGage.GetErrorString(status)}"
            )

        # Get ownership of the digitizer so we can use it. Nobody else can
        # use the system once we have ownership of it.
        self._digitizer_handle = PyGage.GetSystem(0, 0, 0, 0)
        if self._digitizer_handle < 0:
            raise RuntimeError(
                f"Failed to get ownership of digitizer:\nErrno = {self._digitizer_handle}, {PyGage.GetErrorString(self._digitizer_handle)}"
            )

        # Get static information about the digitizer that's being used.
        # We will need some of the fields to convert the raw values
        # into voltages. The rest of the information is not necessary,
        # but we might as well save that metadata.
        self.system_info = PyGage.GetSystemInfo(self._digitizer_handle)

        # GetSystemInfo returns a dict upon success; otherwise the return
        # an int error code. The error code should be negative.
        if not isinstance(self.system_info, dict):
            raise RuntimeError(
                f"Failed to get digitizer info:\nErrno = {self.system_info}, {PyGage.GetErrorString(self.system_info)}"
            )

    def load_configuration(self, filename):
        """Loads a digitizer configuration from a TOML file.

        Parses a TOML configuration and puts the configuration values
        into the acquisition_config, trigger_config, and channel_config
        NamedTuples.

        Args:
            filename (str):
                Config filename.
        """

        # Parse toml file
        with open(filename, "rb") as f:
            config = tomllib.load(f)

        # Parse the acquisition mode. Acquisition mode can be one of:
        # - "single" / 1
        # - "dual" / 2
        # - "quad" / 4
        # - "oct" / 8
        # Not all digitizer cards support all modes, e.g. a dual-channel
        # card can't support 4 or 8 channel mode.
        if isinstance(config["acquisition"]["mode"], str):
            mode = config["acquisition"]["mode"].lower()
        else:
            mode = config["acquisition"]["mode"]

        if mode in {"single", 1}:
            mode = gc.CS_MODE_SINGLE
        elif mode in {"dual", 2}:
            mode = gc.CS_MODE_DUAL
        elif mode in {"quad", 4}:
            mode = gc.CS_MODE_QUAD
        elif mode in {"oct", 8}:
            mode = gc.CS_MODE_OCT

        self.acquisition_config = AcquisitionConfig(
            SampleRate=int(config["acquisition"]["sample_rate"]),
            SegmentSize=config["acquisition"]["n_samples"],
            TriggerDelay=config["acquisition"]["trigger_delay"],
            SegmentCount=config["acquisition"]["segment_count"],
            Mode=mode,
        )

        self.channel_config = ChannelConfig(
            Channel=config["channel"]["channel"],
            InputRange=config["channel"]["range"],
            DcOffset=config["channel"]["dc_offset"],
        )

        # Parse trigger source
        if isinstance(config["trigger"]["source"], str):
            if config["trigger"]["source"].lower() == "external":
                trigger_source = gc.CS_TRIG_SOURCE_EXT
            else:
                raise ValueError(
                    "Invalid trigger source setting.\n"
                    + 'Must be one of {"external",1,2}.'
                )
        else:
            trigger_source = config["trigger"]["source"]

        # Parse the trigger condition. The trigger condition can be any of:
        # rising/r/positive/p/1 for positive-edge triggered, and
        # falling/f/negative/n/0 for negative-edge triggered
        if isinstance(config["trigger"]["condition"], str):
            condition = config["trigger"]["condition"].lower()
            if condition in {"rising", "r", "positive", "p"}:
                condition = gc.CS_TRIG_COND_POS_SLOPE
            elif condition in {"falling", "f", "negative", "n"}:
                condition = gc.CS_TRIG_COND_NEG_SLOPE
            else:
                raise ValueError(
                    "Invalid trigger condition setting.\n"
                    + 'Must be one of {"rising", "r", "positive", "p", 1, "falling", "f", "negative", "n", 0}.'
                )
        else:
            condition = config["trigger"]["condition"]

        self.trigger_config = TriggerConfig(
            Condition=condition, Level=config["trigger"]["level"], Source=trigger_source
        )

    def configure(self):
        """Configures the digitizer with the instance's config parameters."""
        # Make sure config parameters have been set
        acq_config_is_empty = self.acquisition_config is None
        chan_config_is_empty = self.channel_config is None
        trig_config_is_empty = self.trigger_config is None
        config_is_empty = [
            acq_config_is_empty,
            chan_config_is_empty,
            trig_config_is_empty,
        ]

        if any(config_is_empty):
            config_strings = ["acquisition", "channel", "trigger"]

            # Get a list of which configs are empty so we can
            # print out the empty configs in the exception
            empty_configs = [
                config_string
                for (config_string, empty_config) in zip(
                    config_strings, config_is_empty
                )
                if empty_config
            ]

            raise RuntimeError(
                "Refusing to configure the digitizer because"
                + f"the following configs are empty: {','.join(empty_configs)}"
            )

        # The Set*Config() functions require a dictionary as their input,
        # so we convert the named tuples to dictionaries
        acquisition_config = self.acquisition_config._asdict()
        channel_config = self.channel_config._asdict()
        trigger_config = self.trigger_config._asdict()

        # The Compuscope driver expects both a SegmentSize and Depth parameter.
        # In our case, both of these parameters ae the same since we have no
        # reason to support capturing pre-trigger data (the pre-trigger data
        # would be data before the laser pulse fired); thus we set Depth
        # equal to the SegmentSize. We are forcing the depth and segment size
        # to be the same to simplify configuration.
        acquisition_config["Depth"] = acquisition_config["SegmentSize"]

        # We need to break out the Channel number parameter from the channel config
        # dictionary because SetChannelConfig doesn't accept the channel number as
        # part of the dictionary; the channel number is a separate input argument.
        channel = channel_config["Channel"]
        del channel_config["Channel"]

        # Set configuration parameters in the device driver
        status = PyGage.SetAcquisitionConfig(self._digitizer_handle, acquisition_config)
        if status < 0:
            raise RuntimeError(
                "Error setting acquisition config:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}"
            )

        status = PyGage.SetChannelConfig(
            self._digitizer_handle, channel, channel_config
        )
        if status < 0:
            raise RuntimeError(
                "Error setting channel config:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}"
            )

        # We only support using one trigger engine, so we hardcode the
        # trigger engine number to 1, which is the first trigger engine.
        trigger_engine = 1
        status = PyGage.SetTriggerConfig(
            self._digitizer_handle, trigger_engine, trigger_config
        )
        if status < 0:
            raise RuntimeError(
                "Error setting trigger config:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}"
            )

        # Commit configuration values from the driver into the hardware
        status = PyGage.Commit(self._digitizer_handle)
        if status < 0:
            raise RuntimeError(
                "Error committing settings to hardware:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}"
            )

    def capture(self):
        """Initiates a data capture and returns the data.

        Returns:
            data:
                The data matrix. The data array has size
                (n_samples,segment_count).
            timestamps:
                The timestamps of each trigger event, in ns.
            capture_start_time:
                The date and time when the data capture was initiated.

        Raises:
            RuntimeError:
                An error occurred when starting the capture, getting
                the digitizer's status, or transferring the data.
        """
        status = PyGage.StartCapture(self._digitizer_handle)
        if status < 0:
            raise RuntimeError(
                "Error starting capture:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}"
            )

        # Save the time that we started the capture just so we have that
        # metadata later on after the data has been saved.
        capture_start_time = str(datetime.now())

        # Poll the digitizer until the capture is done
        status = PyGage.GetStatus(self._digitizer_handle)
        while status != gc.ACQ_STATUS_READY:
            if status < 0:
                raise RuntimeError(
                    "Error getting digitizer status:"
                    + f"\nErrno = {status}, {PyGage.GetErrorString(status)}"
                )

            status = PyGage.GetStatus(self._digitizer_handle)

        data = self._transfer_data_from_adc()

        timestamps = self._transfer_timestamps()

        return (data, timestamps, capture_start_time)

    def _transfer_data_from_adc(self):
        """Transfers data from the digitizer.

        Returns:
            data:
                The data matrix. The data array has size
                (n_samples,segment_count).

        Raises:
            RuntimeError:
                An error occurred when transferring the data from
                the digitizer.
        """

        n_segments = self.acquisition_config.SegmentCount
        segment_size = self.acquisition_config.SegmentSize
        start_address = self.acquisition_config.TriggerDelay

        data = np.empty(shape=(segment_size, n_segments), dtype=np.int16)

        # TransferData can only transfer one segment at a time, so we
        # have to call it for each segment that was collected.
        for segment in range(1, n_segments + 1):
            ret = PyGage.TransferData(
                self._digitizer_handle,
                self.channel_config.Channel,
                gc.TxMODE_DEFAULT,
                segment,
                start_address,
                segment_size,
            )

            # If there was an error, the output will be a int error code;
            # on success, the output is a tuple.
            if isinstance(ret, int):
                raise RuntimeError(
                    "Error transferring data:"
                    + f"\nErrno = {ret}, {PyGage.GetErrorString(ret)}"
                )
            else:
                # PyGage.TransferData returns the actual start address
                # and length of the data transfer, which might be
                # different from the requested start address or length
                # if the data had to be adjusted for alignment purposes.
                data[:, segment - 1] = ret[0]
                actual_start_address = ret[1]
                transfer_length = ret[2]

            # Warn the user if the start address and transfer length
            # were changed. This might imply that the transferred data
            # is invalid, or that the user needs to change their
            # digitizer settings.
            if start_address != actual_start_address:
                warnings.warn(
                    "Actual start address differs from requested:\n"
                    + f"actual={actual_start_address}, requested={start_address}",
                    RuntimeWarning,
                )

            if transfer_length != self.acquisition_config.SegmentSize:
                warnings.warn(
                    "Actual transfer length differs from requested:\n"
                    + f"actual={transfer_length}, "
                    + f"requested={self.acquisition_config.SegmentSize}",
                    RuntimeWarning,
                )

        return data

    def _transfer_timestamps(self):
        """Gets the digitizer timestamps for each trigger event.

        The timestamps start at 0.

        Returns:
            timestamps:
                Trigger timestamps in nanoseconds.

        Raises:
            RuntimeError:
                An error occurred when transferring the timestamps from
                the digitizer.
        """
        SEGMENT_START = 1

        # For some reason, the start address for transferring
        # timestamps is 1, not 0, even though the API documentation
        # says the trigger address is address 0. Using address 0 is
        # fine when transferring the data, but is not correct when
        # transferring the timestamps. When setting start address to 0,
        # TransferData returns an actual start address of 1 in this case.
        START_ADDRESS = 1

        ret = PyGage.TransferData(
            self._digitizer_handle,
            self.channel_config.Channel,
            gc.TxMODE_TIMESTAMP,
            SEGMENT_START,
            START_ADDRESS,
            self.acquisition_config.SegmentCount,
        )
        if isinstance(ret, int):
            raise RuntimeError(
                "Error transferring timestamps:"
                + f"\nErrno = {ret}, {PyGage.GetErrorString(ret)}"
            )
        else:
            counts = ret[0]

        # Convert counts to timestamps in ns. Fractions of ns
        # resolution is not needed, and is not possible at this time
        # because 1 GS/s is the fastest sampling rate any of the
        # Compuscope digitizer's support.
        NANOSECONDS_PER_SECOND = 1e9
        counts_per_second = PyGage.GetTimeStampFrequency(self._digitizer_handle)
        timestamps = np.round(
            counts / counts_per_second * NANOSECONDS_PER_SECOND
        ).astype(np.int64)

        # The timestamp counter starts when the capture starts, not
        # when the first trigger event happens. Thus the first
        # timestamp will not be 0. We're not concerned with the actual
        # start time of the first trigger event---just the relative
        # time between trigger events and the total duration. Thus we
        # make the timestamps start at 0.
        timestamps = timestamps - timestamps[0]

        return timestamps

    def convert_to_volts(self, raw_data):
        """Converts raw ADC data to voltages

        Args:
            raw_data:
                The input data, with units of "ADC code"

        Returns:
            voltage_data:
                The input data, with units of Volts instead of "ADC code".

        Raises:
            RuntimeError:
                If the driver's acquisition configuration can't be returned.

        Notes:
            The voltage conversion equation is documented in the
            "Gage CompuScope SDK for C/C# Manual".

            Essentially, each digitizer has a particular resolution, defined by
            the data type (e.g. 16-bit signed integers), and a sample offset.
            The raw ADC code, which is an integer of the data type that the
            digitizer supports, is converted into a percentage of the ADC's
            full-scale input voltage range; the percentage is multiplied by the
            full-scale voltage range, and then the DC offset is added.

            The "resolution" in the equation is not actually the data type's
            resolution in the traditional sense; it's the maximum negative
            integer for the data type.
        """

        # Get the acquisition config from the driver. We need to query the
        # SampleOffset and SampleResolution values from the driver; we never
        # explicitly configure those values because they are constant for a
        # particular digitizer model.
        ret = PyGage.GetAcquisitionConfig(self._digitizer_handle)
        if isinstance(ret, int):
            raise RuntimeError(
                "Error getting acquisition config:"
                + f"\nErrno = {ret}, {PyGage.GetErrorString(ret)}"
            )
        else:
            acq_config = ret

        sample_offset = acq_config["SampleOffset"]
        sample_resolution = acq_config["SampleResolution"]

        # Voltage ranges are given and reported in millivolts in the config
        # and in the driver. However, we want our voltages to have units of
        # V, not mV, so we convert mV to V.
        input_range = self.channel_config.InputRange / 1000
        dc_offset = self.channel_config.DcOffset / 1000

        voltage_data = (sample_offset - raw_data) / sample_resolution * (
            input_range / 2
        ) + dc_offset

        return voltage_data

    def free(self):
        """Frees the digitizer so other applications can use it."""
        # Only free the system if we have a reference to it.
        if self._digitizer_handle:
            status = PyGage.FreeSystem(self._digitizer_handle)
            if status < 0:
                warnings.warn(
                    f"Failed to free system.\nErrno = {status}, {PyGage.GetErrorString(status)}",
                    RuntimeWarning,
                )
            else:
                # Get rid of our handle value so we don't erroneously
                # think we still have ownership of a digitizer
                self._digitizer_handle = None
        else:
            warnings.warn(
                "Not attempting to free system. We don't have a reference to any digitizer.",
                RuntimeWarning,
            )

    def save_data_in_h5(
        self,
        h5file,
        data,
        timestamps,
        capture_time,
        data_is_volts=False,
        distance=None,
    ):
        """Save data and metadata in an h5 file.

        Rather than creating an h5 file itself, this function requires the user
        to pass in an h5py.File object. This allows users to add additional
        groups, data, metadata, etc., to the h5 file before or after calling
        this function.

        Args:
            h5file:
                An h5py.File object to save the data to.
            data:
                The data array to save. Data must be 2- or 3-dimensional.
                If it is 2-dimensional, the data must be a single capture.
                If it is 3-dimensional, the first dimension should be the
                number of captures.
            timestamps:
                The timestamps corresponding to each trigger event.
                Timestamps can be 1- or 2-dimensional if the data is only
                a single capture. Otherwise, the timestamps must be
                2-dimensional, where the first dimensions is the number of
                captures. The 2nd dimension must be equal to the 3rd
                dimension of `data`.
            capture_time:
                Datetime strings corresponding to the start of each capture.
                The length of this argument must be equal to the number of
                captures taken, which is the first dimension of data and
                timestamps.
            data_is_volts:
                Whether or not the captured data has units of volts.
            distance:
                Vector that maps range bins to distances. If not `None`,
                this vector must be the same length as the 2nd dimension
                of `data`. This vector is created from the `range_calibration` module.

        Raises:
            ValueError:
                If dimensions of the input data do not match.

        Example:
            digitizer = Digitizer()

            # capture data
            # ...

            with h5py.File("data.hdf5", "w") as h5:
                digitizer.save_data_in_h5(h5, data, timestamps, capture_time)
        """

        # Ensure the input dimensions match. If multiple captures were
        # taken, then the first dimension of all the inputs must match;
        # if there is only one capture, then we add a new singleton
        # dimension to make it so the data is always 3-dimensional.
        # In general, we expect data to be an array of captures of shape
        # (# of captures,# of samples,# of segments). If the data is
        # only a single capture, rather than an array of captures, we need
        # to force the shape to (1,# of samples,# of segments)

        # Add a new singleton dimension if the data is for a single capture
        if data.ndim == 2:
            data = np.expand_dims(data, axis=0)
        if timestamps.ndim == 1:
            timestamps = np.expand_dims(timestamps, axis=0)
        if isinstance(capture_time, str):
            capture_time = np.array([capture_time], dtype=np.bytes_)
            capture_time = np.expand_dims(capture_time, axis=0)

        # Ensure that the first dimensions are all the same
        first_dimensions_match = (
            data.shape[0] == timestamps.shape[0]
            and data.shape[0] == capture_time.shape[0]
        )
        if not first_dimensions_match:
            raise ValueError(
                "First dimension of inputs must match.\n"
                + f"first dimensions: data={data.shape[0]}, "
                + f"timestamps={timestamps.shape[0]}, "
                + f"capture_time={capture_time.shape[0]}"
            )

        # Ensure that the length of the timestamps is equal to the
        # number of segments in each capture.
        if data.shape[2] != timestamps.shape[1]:
            raise ValueError(
                "Timestamp dimension doesn't match the"
                + f" number of segments.\ndata.shape[2]={data.shape[2]}"
                + f", timestamps.shape[1]={timestamps.shape[1]}"
            )

        # Ensure that the length of the distance vector is the same as
        # the number of sample / range bins.
        if distance is not None:
            if data.shape[1] != len(distance):
                raise ValueError(
                    "Distance dimension doesn't match the"
                    + " number of range bins.\n"
                    + f"# of range bins={data.shape[1]}"
                    + f", len(distance)={len(distance)}"
                )

        # Create datasets under the 'data' group
        h5file.create_group("data")
        h5file["data/data"] = data
        h5file["data/timestamps"] = timestamps
        h5file["data/capture_time"] = capture_time
        if distance is not None:
            h5file["data/distance"] = distance

        h5file["data/timestamps"].attrs["units"] = "ns"
        # TODO: the data could also be raw instead of volts.
        # Think more about how to handle this... There are a lot
        # of parameters being passed in here. The Digitizer class
        # doesn't dictate whether the user uses volts, does range calibration,
        # etc., which then puts the onus on the user to do all of that
        # and pass the appropriate arguments into this function...
        # The decision of making the digitizer only handle "mechanism",
        # and not "policy", has tradeoffs here.
        if data_is_volts:
            h5file["data/data"].attrs["units"] = "V"
        else:
            h5file["data/data"].attrs["units"] = "ADC count"

        if distance is not None:
            h5file["data/distance"].attrs["units"] = "m"

        # Add dimension labels
        h5file["data/data"].dims[0].label = "capture #"

        if distance is not None:
            h5file["data/data"].dims[1].label = "distance"
        else:
            h5file["data/data"].dims[1].label = "range bin"

        h5file["data/data"].dims[2].label = "time"

        # Link the distance dataset as a dimension scale, if it exists
        if distance is not None:
            h5file["data/distance"].make_scale("distance")
            h5file["data/data"].dims[1].attach_scale(h5file["data/distance"])

        # Add attributes for system info metadata
        h5file.create_group("digitizer/info")
        for key, val in self.system_info.items():
            h5file["digitizer/info"].attrs[key] = val

        # Add attributes for digitizer config
        h5file.create_group("digitizer/config/acquisition")
        for key, val in self.acquisition_config._asdict().items():
            h5file["digitizer/config/acquisition"].attrs[key] = val

        h5file.create_group("digitizer/config/channel")
        for key, val in self.channel_config._asdict().items():
            h5file["digitizer/config/channel"].attrs[key] = val

        h5file.create_group("digitizer/config/trigger")
        for key, val in self.trigger_config._asdict().items():
            h5file["digitizer/config/trigger"].attrs[key] = val


# NOTE: we do not support pre-trigger data, forced-trigger timeouts, non-default timestamp modes,
# dual-channel acquisition, or external clocking
class AcquisitionConfig(NamedTuple):
    """Acquisition configuration values.

    Attributes:
        SampleRate (int):
            Digitizer sampling rate.
        SegmentCount (int):
            Number of segments to acquire. This is the number of trigger
            events to acquire.
        SegmentSize (int):
            Number of samples to acquire for each trigger event.
        TriggerDelay (int):
            Number of samples between the trigger event and the start of
            data acquisition.
    """

    SampleRate: int
    SegmentCount: int
    SegmentSize: int
    TriggerDelay: int
    Mode: int


class ChannelConfig(NamedTuple):
    """Channel configuration values.

    Attributes:
        Channel (int):
            Channel number.
        InputRange (int):
            Input voltage range.
        DcOffset (int):
            DC offset for the channel. This can span the full scale
            of the input voltage range, i.e. +/-(InputRange/2).
    """

    Channel: int
    InputRange: int
    DcOffset: int


# NOTE: we are only going to support "simple" triggering mode using 1 trigger engine
class TriggerConfig(NamedTuple):
    """Trigger configuration values.

    Attributes:
        Condition (int):
            Trigger condition. 0 for negative-edge and 1 for positive-edge.
        Level (int):
            Trigger level as a percentage of the input voltage range.
        Source (int):
            Trigger source. See GageConstants.py for valid values.
    """

    Condition: int
    Level: int
    Source: int

