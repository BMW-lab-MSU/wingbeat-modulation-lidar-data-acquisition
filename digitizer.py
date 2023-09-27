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
            self.acquisition_config = None
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
            raise RuntimeError(f"Failed to initialize digitizer:\nErrno = {status}, {PyGage.GetErrorString(status)}")

        # Get ownership of the digitizer so we can use it. Nobody else can
        # use the system once we have ownership of it.
        self._digitizer_handle = PyGage.GetSystem(0,0,0,0)
        if self._digitizer_handle < 0:
            raise RuntimeError(f"Failed to get ownership of digitizer:\nErrno = {self._digitizer_handle}, {PyGage.GetErrorString(self._digitizer_handle)}")

        # Get static informaton about the digitizer that's being used.
        # We will need some of the fields to convert the raw values
        # into voltages. The rest of the information is not necesarry,
        # but we might as well save that metadata.
        self.system_info = PyGage.GetSystemInfo(self._digitizer_handle)
        
        # GetSystemInfo returns a dict upon success; otherwise the return
        # an int error code. The error code should be negative.
        if not isinstance(self.system_info,dict):
            raise RuntimeError(f"Failed to get digitizer info:\nErrno = {self.system_info}, {PyGage.GetErrorString(self.system_info)}")
        

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
            Source=trigger_source
        )


    def configure(self):
        """Configures the digitizer with the instance's config parameters

        """
        # Make sure config parameters have been set
        acq_config_is_empty = self.acquisition_config is None
        chan_config_is_empty = self.channel_config is None
        trig_config_is_empty = self.trigger_config is None
        config_is_empty = [acq_config_is_empty,chan_config_is_empty,trig_config_is_empty]

        if any(config_is_empty):
            config_strings = ["acquisition","channel","trigger"]

            # Get a list of which configs are empty so we can
            # print out the empty configs in the exception
            empty_configs = [config_string for (config_string,empty_config) 
                in zip(config_strings,config_is_empty) if empty_config]
            
            raise RuntimeError("Refusing to configure the digitizer because"
                + f"the following configs are empty: {','.join(empty_configs)}")


        # The Set*Config() functions require a dictionary as their input,
        # so we convert the named tuples to dictionaries
        acquisition_config = self.acquisition_config._asdict()
        channel_config = self.channel_config._asdict()
        trigger_config = self.trigger_config._asdict()

        # Hardcode the acquisition mode to single-channel since we don't
        # have any reason to support dual-channel mode.
        acquisition_config['Mode'] = CS_MODE_SINGLE

        # The Compuscope driver expects both a SegmentSize and Depth parameter.
        # In our case, both of these parameters ae the same since we have no
        # reason to support capturing pre-trigger data (the pre-trigger data
        # would be data before the laser pulse fired); thus we set Depth
        # equal to the SegmentSize. We are forcing the depth and segment size
        # to be the same to simplify configuration.
        acquisition_config['Depth'] = acquisition_config['SegmentSize']

        # We need to break out the Channel number parameter from the channel config
        # dictionary because SetChannelConfig doesn't accept the channel number as
        # part of the dictionary; the channel number is a separate input argument.
        channel = channel_config['Channel']
        del channel_config['Channel']

        # Set configuraton parameters in the device driver
        status = PyGage.SetAcquisitionConfig(self._digitizer_handle,acquisition_config)
        if status < 0:
            raise RuntimeError("Error setting acquisition config:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}")

        status = PyGage.SetChannelConfig(self._digitizer_handle,channel,channel_config)
        if status < 0:
            raise RuntimeError("Error setting channel config:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}")

        # We only support using one trigger engine, so we hardcode the
        # trigger engine number to 1, which is the first trigger engine.
        trigger_engine = 1
        status = PyGage.SetTriggerConfig(self._digitizer_handle,trigger_engine,trigger_config)
        if status < 0:
            raise RuntimeError("Error setting trigger config:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}")
            
        # Commit configuration values from the driver into the hardware
        status = PyGage.Commit(self._digitizer_handle)
        if status < 0:
            raise RuntimeError("Error committing settings to hardware:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}")

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
