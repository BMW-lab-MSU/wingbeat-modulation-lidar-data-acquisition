import warnings

import PyGage

# I don't think we need to put these imports under a namespace.
# The chances of us creating a variable with the same name is very small.
# from GageConstants import *

class Digitizer:
    def __init__(self,config_file=None):
        self._digitizer_handle = None
        self.system_info = None
        self.config = None

    def __del__(self):
        # Explicitly free the digitizer before the instance is about to be
        # destroyed, just in case the user doesn't call free() themsevles.
        # If the digitizer has already been freed, then the compuscope SDK
        # will return an error code, which we can ignore.
        self.free()

    def initialize(self):
        """Initialize the digitizer"""
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
        

    def load_configuration(self,config_file):
        pass

    def configure(self):
        pass

    def capture(self):
        pass

    def _transfer_data_from_adc(self):
        pass

    def convert_raw_to_volts(self,raw_value):
        pass

    def free(self):
        """Free the digitizer so other applications can use it."""
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
