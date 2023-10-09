import warnings
import tomllib
import numpy as np
from datetime import datetime
from typing import NamedTuple

import PyGage
import GageConstants as gc

class Digitizer:
    def __init__(self,config_filename=None):
        """Creates an instance of the Digitizer class.

        Args:
            config_filename (str|None):
                The filename of a digitizer TOML configuraton file that
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
        # destroyed, just in case the user doesn't call free() themsevles.
        # If the digitizer has already been freed, then the compuscope SDK
        # will return an error code, which we can ignore.
        self.free()

    def initialize(self):
        """Initializes the digitizer hardware."""
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
        """Loads a digitizer configuration from a TOML file.

        Parses a TOML configuration and puts the configuration values
        into the aquisition_config, trigger_config, and channel_config
        NamedTuples.

        Args:
            filename (str):
                Config filename.
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
                trigger_source = gc.CS_TRIG_SOURCE_EXT
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
                condition = gc.CS_TRIG_COND_POS_SLOPE
            elif condition in {'falling','f','negative','n'}:
                condition = gc.CS_TRIG_COND_NEG_SLOPE
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
        """Configures the digitizer with the instance's config parameters."""
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
        acquisition_config['Mode'] = gc.CS_MODE_SINGLE

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
            raise RuntimeError("Error starting capture:"
                + f"\nErrno = {status}, {PyGage.GetErrorString(status)}")
        
        # Save the time that we started the capture just so we have that
        # metadata later on after the data has been saved.
        capture_start_time = datetime.now().time()

        # Poll the digitizer until the capture is done
        status = PyGage.GetStatus(self._digitizer_handle)    
        while status != gc.ACQ_STATUS_READY:
            if status < 0:
                raise RuntimeError("Error getting digitizer status:"
                    + f"\nErrno = {status}, {PyGage.GetErrorString(status)}")

            status = PyGage.GetStatus(self._digitizer_handle)
        
        data = self._transfer_data_from_adc()

        timestamps = self._transfer_timestamps()

        return (data,timestamps,capture_start_time)


    def _transfer_data_from_adc(self):
        """Transfers data from the digitizer.

        Returns:
            data:
                The data matrix. The data array has size 
                (n_samples,segment_count).

        Raises:
            RuntimeError:
                An error occured when transferring the data from
                the digitizer.
        """

        n_segments = self.acquisition_config.SegmentCount
        segment_size = self.acquisition_config.SegmentSize
        start_address = self.acquisition_config.TriggerDelay

        data = np.empty(shape=(segment_size,n_segments),dtype=np.int16)

        # TransferData can only transfer one segment at a time, so we
        # have to call it for each segment that was collected.
        for segment in range(1,n_segments + 1):
            ret = PyGage.TransferData(
                self._digitizer_handle,self.channel_config.Channel,
                gc.TxMODE_DEFAULT,segment,start_address,segment_size
            )

            # If there was an error, the output will be a int error code;
            # on success, the output is a tuple.
            if isinstance(ret,int):
                raise RuntimeError("Error transferring data:"
                    + f"\nErrno = {ret}, {PyGage.GetErrorString(ret)}")
            else:
                # PyGage.TransferData returns the actual start address
                # and length of the data transfer, which might be
                # different from the requested start address or length
                # if the data had to be adjusted for alignment purposes.
                data[:,segment - 1] = ret[0]
                actual_start_address = ret[1]
                transfer_length = ret[2]
            
            # Warn the user if the start address and transfer length
            # were changed. This might imply that the transfered data
            # is invalid, or that the user needs to change their
            # digitizer settings.
            if start_address != actual_start_address:
                warnings.warn("Actual start address differs from requested:\n"
                    + f"actual={actual_start_address}, requested={start_address}",
                    RuntimeWarning)

            if transfer_length != self.acquisition_config.SegmentSize:
                warnings.warn("Actual transfer length differs from requested:\n"
                    + f"actual={transfer_length}, "
                    + f"requested={self.acquisition_config.SegmentSize}",
                    RuntimeWarning)
        
        return data

    def _transfer_timestamps(self):
        """Gets the digitizer timestamps for each trigger event.

        The timestamps start at 0.

        Returns:
            timestamps:
                Tigger timestamps in nanoseconds.
        
        Raises:
            RuntimeError:
                An error occurred when transferring the timestamps from
                the digitizer.
        """
        SEGMENT_START = 1

        # For some reason, the start address for transfering
        # timestamps is 1, not 0, even though the API documentation
        # says the trigger address is address 0. Using address 0 is
        # fine when transferring the data, but is not correct when
        # transferring the timestamps. When setting start address to 0,
        # TransferData returns an actual start address of 1 in this case.
        START_ADDRESS = 1

        ret = PyGage.TransferData(
            self._digitizer_handle,self.channel_config.Channel,
            gc.TxMODE_TIMESTAMP,SEGMENT_START,START_ADDRESS,
            self.acquisition_config.SegmentCount
        )
        if isinstance(ret,int):
            raise RuntimeError("Error transferring timestamps:"
                + f"\nErrno = {ret}, {PyGage.GetErrorString(ret)}")
        else:
            counts = ret[0]

        # Convert counts to timestamps in ns. Fractions of ns 
        # resolution is not needed, and is not possible at this time
        # because 1 GS/s is the fastest sampling rate any of the
        # Compuscope digitizer's support.
        NANOSECONDS_PER_SECOND = 1e9
        counts_per_second = PyGage.GetTimeStampFrequency(self._digitizer_handle)
        timestamps = np.round(counts / counts_per_second * NANOSECONDS_PER_SECOND).astype(np.int64)

        # The timestamp counter starts when the capture starts, not
        # when the first trigger event happens. Thus the first
        # timestamp will not be 0. We're not concerned with the actual
        # start time of the first trigger event---just the relative
        # time between trigger events and the total duration. Thus we
        # make the timestamps start at 0.
        timestamps = timestamps - timestamps[0]

        return timestamps
        

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
