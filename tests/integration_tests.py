import unittest
from unittest.mock import Mock, MagicMock, patch

# import PyGage

from GageConstants import *
from digitizer import *

class TestDigitizer(unittest.TestCase):

    def setUp(self):
        self.digitizer = Digitizer()
        self.digitizer.initialize()
        # self.mock = MagicMock(spec=PyGage)
    
    def test_free_valid_handle(self):
        self.digitizer.free()

        self.assertEqual(self.digitizer._digitizer_handle,None)

    def test_free_invalid_handle(self):
        self.digitizer._digitizer_handle = 2

        self.assertEqual(self.digitizer._digitizer_handle,2)

        with self.assertWarnsRegex(RuntimeWarning,"Failed to free system"):
            self.digitizer.free()
    
    def test_double_free(self):
        self.digitizer.free()
        self.assertEqual(self.digitizer._digitizer_handle,None)

        self.digitizer.free()
        self.assertEqual(self.digitizer._digitizer_handle,None)

    def test_valid_configuration1(self):
        config_filename = 'tests/example-config-1.toml'

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuraton dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(self.digitizer._digitizer_handle,CS_ACQUISITION_CONFIGURATION)
        actual_chan = PyGage.GetChannelConfig(self.digitizer._digitizer_handle,self.digitizer.channel_config.Channel,CS_ACQUISITION_CONFIGURATION)
        actual_trig = PyGage.GetTriggerConfig(self.digitizer._digitizer_handle,1,CS_ACQUISITION_CONFIGURATION)

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key],actual_trig[key])

        for key in expected_chan.keys():
            if key != 'Channel':
                self.assertEqual(expected_chan[key],actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key],actual_acq[key])
        self.assertEqual(CS_MODE_SINGLE,actual_acq['Mode'])
        self.assertEqual(actual_acq['Depth'],actual_acq['SegmentSize'])

    def test_valid_configuration2(self):
        config_filename = 'tests/example-config-2.toml'

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuraton dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(self.digitizer._digitizer_handle,CS_ACQUISITION_CONFIGURATION)
        actual_chan = PyGage.GetChannelConfig(self.digitizer._digitizer_handle,self.digitizer.channel_config.Channel,CS_ACQUISITION_CONFIGURATION)
        actual_trig = PyGage.GetTriggerConfig(self.digitizer._digitizer_handle,1,CS_ACQUISITION_CONFIGURATION)

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key],actual_trig[key])

        for key in expected_chan.keys():
            if key != 'Channel':
                self.assertEqual(expected_chan[key],actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key],actual_acq[key])
        self.assertEqual(CS_MODE_SINGLE,actual_acq['Mode'])
        self.assertEqual(actual_acq['Depth'],actual_acq['SegmentSize'])

    def test_valid_configuration_trig_delay(self):
        config_filename = 'tests/example-config-trig-delay.toml'

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuraton dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(self.digitizer._digitizer_handle,CS_ACQUISITION_CONFIGURATION)
        actual_chan = PyGage.GetChannelConfig(self.digitizer._digitizer_handle,self.digitizer.channel_config.Channel,CS_ACQUISITION_CONFIGURATION)
        actual_trig = PyGage.GetTriggerConfig(self.digitizer._digitizer_handle,1,CS_ACQUISITION_CONFIGURATION)

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key],actual_trig[key])

        for key in expected_chan.keys():
            if key != 'Channel':
                self.assertEqual(expected_chan[key],actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key],actual_acq[key])
        self.assertEqual(CS_MODE_SINGLE,actual_acq['Mode'])
        self.assertEqual(actual_acq['Depth'],actual_acq['SegmentSize'])

    def test_invalid_trig_delay_config(self):
        config_filename = 'tests/invalid-trig-delay-config.toml'

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError,'Trigger Delay is invalid'):
            self.digitizer.configure()


    def test_invalid_trigger_source_config(self):
        config_filename = 'tests/invalid-trig-source-config-2.toml'

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError,'Invalid trigger source'):
            self.digitizer.configure()

    def test_invalid_dc_offset_config(self):
        config_filename = 'tests/invalid-dc-offset-config.toml'

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError,'Invalid DC offset'):
            self.digitizer.configure()
