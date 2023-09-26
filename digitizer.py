import warnings
import tomllib
from typing import NamedTuple

import PyGage
from GageConstants import CS_MODE_SINGLE,CS_TRIG_COND_POS_SLOPE,CS_TRIG_COND_NEG_SLOPE,CS_TRIG_SOURCE_EXT

class Digitizer:
    def __init__(self,config_filename=None):
        self._digitizer_handle = None
        self.system_info = None

        if config_filename:
            self.load_configuration(config_filename)
        else:
            self.acquistion_config = None
            self.channel_config = None
            self.trigger_config = None

    def __del__(self):
        # Explicitly free the digitizer before the instance is about to be
        # destroyed, just in case the user doesn't call free() themsevles.
        # If the digitizer has already been freed, then the compuscope SDK
        # will return an error code, which we can ignore.
        self.free()

    def initialize(self):
        """Initializes the digitizer"""
        status = PyGage.Initialize()
        if status < 0:
            raise RuntimeError(f"Failed to initialize digitizer.\nErrno = {status}, {PyGage.GetErrorString(status)}")

        # Get ownership of the digitizer so we can use it. Nobody else can
        # use the system once we have ownership of it.
        self._digitizer_handle = PyGage.GetSystem(0,0,0,0)
        if self._digitizer_handle < 0:
            raise RuntimeError(f"Failed to get ownership of digitizer.\nErrno = {self._digitizer_handle}, {PyGage.GetErrorString(self._digitizer_handle)}")

        # Get static informaton about the digitizer that's being used.
        # We will need some of the fields to convert the raw values
        # into voltages. The rest of the information is not necesarry,
        # but we might as well save that metadata.
        self.system_info = PyGage.GetSystemInfo(self._digitizer_handle)
        
        # GetSystemInfo returns a dict upon success; otherwise the return
        # an int error code. The error code should be negative.
        if not isinstance(self.system_info,dict):
            raise RuntimeError(f"Failed to get digitizer info.\nErrno = {self.system_info}, {PyGage.GetErrorString(self.system_info)}")
        

    def load_configuration(self,filename):
        """Loads a digitizer configuration from a TOML file

        Parses a TOML configuration and puts the configuration values
        into the aquisition_config, trigger_config, and channel_config
        NamedTuples.

        Args:
            filename (str): Config filename
        """

        # Parse toml file
        with open(filename,'rb') as f:
            config = tomllib.load(f)

        self.acquisition_config = AcquisitionConfig(
            SampleRate=int(config['acquisition']['sample_rate']),
            Depth=config['acquisition']['n_samples'],
            SegmentSize=config['acquisition']['n_samples'],
            TriggerDelay=config['acquisition']['trigger_delay'],
            SegmentCount=config['acquisition']['segment_count'],
        )

        self.channel_config = ChannelConfig(
            Channel=config['channel']['channel'],
            InputRange=config['channel']['range'],
            DcOffset=config['channel']['dc_offset']
        )

        # Parse trigger source
        if isinstance(config['trigger']['source'],str):
            if config['trigger']['source'].lower() == 'external':
                trigger_source = CS_TRIG_SOURCE_EXT
            else:
                raise ValueError("Invalid trigger source setting.\n"
                    + "Must be one of {\"external\",1,2}.")
        else:
            trigger_source = config['trigger']['source']

        # Parse the trigger condition. The trigger condition can be any of:
        # rising/r/positive/p/1 for positive-edge triggered, and
        # falling/f/negative/n/0 for negative-edge triggered
        if isinstance(config['trigger']['condition'],str):
            condition = config['trigger']['condition'].lower()
            if condition in {'rising','r','positive','p'}:
                condition = CS_TRIG_COND_POS_SLOPE
            elif condition in {'falling','f','negative','n'}:
                condition = CS_TRIG_COND_NEG_SLOPE
            else:
                raise ValueError("Invalid trigger condition setting.\n"
                    + "Must be one of {\"rising\", \"r\", \"positive\", \"p\", 1, \"falling\", \"f\", \"negative\", \"n\", 0}.")
        else:
            condition = config['trigger']['condition']

        self.trigger_config = TriggerConfig(
            Condition=condition,
            Level=config['trigger']['level'],
            Range=config['trigger']['range'],
            Source=trigger_source
        )


    def configure(self):
        pass

    def capture(self):
        pass

    def _transfer_data_from_adc(self):
        pass

    def convert_raw_to_volts(self,raw_value):
        pass

    def free(self):
        """Frees the digitizer so other applications can use it."""
        # Only free the system if we have a reference to it.
        if self._digitizer_handle:
            status = PyGage.FreeSystem(self._digitizer_handle)
            if status < 0:
                warnings.warn(f"Failed to free system.\nErrno = {status}, {PyGage.GetErrorString(status)}",RuntimeWarning)
            else:
                # Get rid of our handle value so we don't erroneously
                # think we still have ownership of a digitizer
                self._digitizer_handle = None
        else:
            warnings.warn("Not attempting to free system. We don't have a reference to any digitizer.",RuntimeWarning)


# NOTE: we do not support pre-trigger data, forced-trigger timeouts, non-default timestamp modes,
# dual-channel acquisition, or external clocking 
class AcquisitionConfig(NamedTuple):
    """Acquisition configuration values

    Attributes:
        SampleRate (int): 
            Digitizer sampling rate
        SegmentCount (int):
            Number of segments to acquire. This is the number of trigger
            events to acquire.
        Depth (int):
            Number of samples to acquire for each trigger event
        SegmentSize (int): 
            Number of samples to acquire for each trigger event. Should be
            the same as Depth since we don't support acquiring
            pre-trigger data. 
        TriggerDelay (int):
            Number of samples between the trigger event and the start of
            data acquisition.
        Mode (int):
            Acquisition mode. We only support single-channel acquisition,
            so this defaults to single-acquisition mode.

    Notes:
        Both Depth and SegmentSize are present because the digitizer needs both
        of those configuration parameters, even though we want them to be the same. 
    """
    # TODO: we could remove Depth or SegmentSize, then add it back to the dictionary
    # before we send the configuration to the driver. This would enforce the user to
    # make the Depth and SegmentSize the same. We could do the same thing with Mode.
    SampleRate: int
    SegmentCount: int
    Depth: int
    SegmentSize: int
    TriggerDelay: int
    Mode: int = CS_MODE_SINGLE

class ChannelConfig(NamedTuple):
    """Channel configuration values

    Attributes:
        Channel (int):
            Channel number
        InputRange (int):
            Input voltage range
        DcOffset (int):
            DC offset for the channel. This can span the full scale
            of the input voltage range, i.e. +/-(InputRange/2)
    """
    Channel: int
    InputRange: int
    DcOffset: int

# NOTE: we are only going to support "simple" triggering mode using 1 trigger engine
class TriggerConfig(NamedTuple):
    """Trigger configuration values

    Attributes:
        Condition (int):
            Trigger condition. 0 for negative-edge and 1 for positive-edge
        Level (int):
            Trigger level as a percentage of the input voltage range
        Range (int):
            Input voltage range
        Source (int):
            Trigger source. See GageConstants.py for valid values.
    """
    Condition: int
    Level: int
    Range: int
    Source: int
