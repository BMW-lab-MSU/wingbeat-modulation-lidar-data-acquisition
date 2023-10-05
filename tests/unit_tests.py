import unittest
from unittest.mock import Mock, MagicMock, patch

# import PyGage

from GageConstants import *
from digitizer import *

class TestDigitizer(unittest.TestCase):

    def setUp(self):
        self.digitizer = Digitizer()
        # self.mock = MagicMock(spec=PyGage)
    

    def test_free_no_handle(self):
        with self.assertWarnsRegex(RuntimeWarning,"Not attempting to free system. We don't have a reference to any digitizer.") as cm:
            self.digitizer.free()
        

    def test_valid_config_file1(self):
        config_filename = 'tests/example-config-1.toml'

        self.digitizer.load_configuration(config_filename)

        # Create expected config tuples
        expected_acq_config = AcquisitionConfig(
            SampleRate=int(1e9),
            SegmentCount=32,
            SegmentSize=32768,
            TriggerDelay=0
        )

        expected_trig_config = TriggerConfig(
            Condition=CS_TRIG_COND_POS_SLOPE,
            Level=50,
            Source=CS_TRIG_SOURCE_EXT
        )

        expected_chan_config = ChannelConfig(
            Channel=1,
            InputRange=2000,
            DcOffset=0
        )

        self.assertEqual(expected_acq_config,self.digitizer.acquisition_config)
        self.assertEqual(expected_trig_config,self.digitizer.trigger_config)
        self.assertEqual(expected_chan_config,self.digitizer.channel_config)
    

    def test_valid_config_file2(self):
        config_filename = 'tests/example-config-2.toml'

        self.digitizer.load_configuration(config_filename)

        # Create expected config tuples
        expected_acq_config = AcquisitionConfig(
            SampleRate=int(500e6),
            SegmentCount=32,
            SegmentSize=1024,
            TriggerDelay=0
        )

        expected_trig_config = TriggerConfig(
            Condition=CS_TRIG_COND_NEG_SLOPE,
            Level=30,
            Source=CS_TRIG_SOURCE_CHAN_1
        )

        expected_chan_config = ChannelConfig(
            Channel=1,
            InputRange=2000,
            DcOffset=500
        )

        self.assertEqual(expected_acq_config,self.digitizer.acquisition_config)
        self.assertEqual(expected_trig_config,self.digitizer.trigger_config)
        self.assertEqual(expected_chan_config,self.digitizer.channel_config)

    def test_valid_config_file3(self):
        config_filename = 'tests/example-config-3.toml'

        self.digitizer.load_configuration(config_filename)

        # Create expected config tuples
        expected_acq_config = AcquisitionConfig(
            SampleRate=int(875e6),
            SegmentCount=10,
            SegmentSize=40000,
            TriggerDelay=0
        )

        expected_trig_config = TriggerConfig(
            Condition=CS_TRIG_COND_POS_SLOPE,
            Level=50,
            Source=CS_TRIG_SOURCE_EXT
        )

        expected_chan_config = ChannelConfig(
            Channel=1,
            InputRange=2000,
            DcOffset=0
        )

        self.assertEqual(expected_acq_config,self.digitizer.acquisition_config)
        self.assertEqual(expected_trig_config,self.digitizer.trigger_config)
        self.assertEqual(expected_chan_config,self.digitizer.channel_config)

    def test_valid_config_file4(self):
        config_filename = 'tests/example-config-4.toml'

        self.digitizer.load_configuration(config_filename)

        # Create expected config tuples
        expected_acq_config = AcquisitionConfig(
            SampleRate=int(750e6),
            SegmentCount=16,
            SegmentSize=8192,
            TriggerDelay=14592
        )

        expected_trig_config = TriggerConfig(
            Condition=CS_TRIG_COND_POS_SLOPE,
            Level=50,
            Source=CS_TRIG_SOURCE_EXT
        )

        expected_chan_config = ChannelConfig(
            Channel=1,
            InputRange=2000,
            DcOffset=0
        )

        self.assertEqual(expected_acq_config,self.digitizer.acquisition_config)
        self.assertEqual(expected_trig_config,self.digitizer.trigger_config)
        self.assertEqual(expected_chan_config,self.digitizer.channel_config)


    def test_config_file_invalid_trig_condition(self):
        config_filename = 'tests/invalid-trig-condition-config.toml'

        with self.assertRaises(ValueError):
            self.digitizer.load_configuration(config_filename)


    def test_config_file_invalid_trig_source(self):
        config_filename = 'tests/invalid-trig-source-config.toml'

        with self.assertRaises(ValueError):
            self.digitizer.load_configuration(config_filename)

    def test_valid_config_file_load_with_constructor(self):
        config_filename = 'tests/example-config-1.toml'

        self.digitizer = Digitizer(config_filename)

        # Create expected config tuples
        expected_acq_config = AcquisitionConfig(
            SampleRate=int(1e9),
            SegmentCount=32,
            SegmentSize=32768,
            TriggerDelay=0
        )

        expected_trig_config = TriggerConfig(
            Condition=CS_TRIG_COND_POS_SLOPE,
            Level=50,
            Source=CS_TRIG_SOURCE_EXT
        )

        expected_chan_config = ChannelConfig(
            Channel=1,
            InputRange=2000,
            DcOffset=0
        )

        self.assertEqual(expected_acq_config,self.digitizer.acquisition_config)
        self.assertEqual(expected_trig_config,self.digitizer.trigger_config)
        self.assertEqual(expected_chan_config,self.digitizer.channel_config)


    def test_empty_config_exception(self):
        with self.assertRaises(RuntimeError):
            self.digitizer.configure()
        
    def test_one_empty_config_exception(self):
        config_filename = 'tests/example-config-1.toml'

        self.digitizer.load_configuration(config_filename)

        # manually set the config to None to simulate the config being
        # empty. In practice, nobody should do this. But it is possible
        # to manually set the config parameters by manually creating
        # the NamedTuples, in which case it is possible to forget to set
        # some of the config parameters
        self.digitizer.channel_config = None

        with self.assertRaises(RuntimeError):
            self.digitizer.configure()