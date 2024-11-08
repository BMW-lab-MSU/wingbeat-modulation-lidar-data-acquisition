import unittest
import h5py
import os


import PyGage

from gagesupport.GageConstants import *
from wingbeat_lidar.digitizer import *


class TestDigitizer(unittest.TestCase):

    def setUp(self):
        self.digitizer = Digitizer()
        self.digitizer.initialize()
        # self.mock = MagicMock(spec=PyGage)

    def test_free_valid_handle(self):
        self.digitizer.free()

        self.assertEqual(self.digitizer._digitizer_handle, None)

    def test_free_invalid_handle(self):
        self.digitizer._digitizer_handle = 2

        self.assertEqual(self.digitizer._digitizer_handle, 2)

        with self.assertWarnsRegex(RuntimeWarning, "Failed to free system"):
            self.digitizer.free()

    def test_double_free(self):
        self.digitizer.free()
        self.assertEqual(self.digitizer._digitizer_handle, None)

        self.digitizer.free()
        self.assertEqual(self.digitizer._digitizer_handle, None)

    def test_valid_configuration1(self):
        config_filename = "adc-configs/example-config-1.toml"

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuration dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle, CS_ACQUISITION_CONFIGURATION
        )
        actual_chan = PyGage.GetChannelConfig(
            self.digitizer._digitizer_handle,
            self.digitizer.channel_config.Channel,
            CS_ACQUISITION_CONFIGURATION,
        )
        actual_trig = PyGage.GetTriggerConfig(
            self.digitizer._digitizer_handle, 1, CS_ACQUISITION_CONFIGURATION
        )

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key], actual_trig[key])

        for key in expected_chan.keys():
            if key != "Channel":
                self.assertEqual(expected_chan[key], actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key], actual_acq[key])
        self.assertEqual(CS_MODE_SINGLE, actual_acq["Mode"])
        self.assertEqual(actual_acq["Depth"], actual_acq["SegmentSize"])

    def test_valid_configuration2(self):
        config_filename = "adc-configs/example-config-2.toml"

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuration dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle, CS_ACQUISITION_CONFIGURATION
        )
        actual_chan = PyGage.GetChannelConfig(
            self.digitizer._digitizer_handle,
            self.digitizer.channel_config.Channel,
            CS_ACQUISITION_CONFIGURATION,
        )
        actual_trig = PyGage.GetTriggerConfig(
            self.digitizer._digitizer_handle, 1, CS_ACQUISITION_CONFIGURATION
        )

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key], actual_trig[key])

        for key in expected_chan.keys():
            if key != "Channel":
                self.assertEqual(expected_chan[key], actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key], actual_acq[key])

        self.assertEqual(actual_acq["Depth"], actual_acq["SegmentSize"])

    def test_valid_configuration3(self):
        config_filename = "adc-configs/example-config-3.toml"

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuration dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle, CS_ACQUISITION_CONFIGURATION
        )
        actual_chan = PyGage.GetChannelConfig(
            self.digitizer._digitizer_handle,
            self.digitizer.channel_config.Channel,
            CS_ACQUISITION_CONFIGURATION,
        )
        actual_trig = PyGage.GetTriggerConfig(
            self.digitizer._digitizer_handle, 1, CS_ACQUISITION_CONFIGURATION
        )

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key], actual_trig[key])

        for key in expected_chan.keys():
            if key != "Channel":
                self.assertEqual(expected_chan[key], actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key], actual_acq[key])
        self.assertEqual(CS_MODE_SINGLE, actual_acq["Mode"])
        self.assertEqual(actual_acq["Depth"], actual_acq["SegmentSize"])

    def test_valid_configuration4(self):
        config_filename = "adc-configs/example-config-4.toml"

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuration dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle, CS_ACQUISITION_CONFIGURATION
        )
        actual_chan = PyGage.GetChannelConfig(
            self.digitizer._digitizer_handle,
            self.digitizer.channel_config.Channel,
            CS_ACQUISITION_CONFIGURATION,
        )
        actual_trig = PyGage.GetTriggerConfig(
            self.digitizer._digitizer_handle, 1, CS_ACQUISITION_CONFIGURATION
        )

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key], actual_trig[key])

        for key in expected_chan.keys():
            if key != "Channel":
                self.assertEqual(expected_chan[key], actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key], actual_acq[key])
        self.assertEqual(CS_MODE_SINGLE, actual_acq["Mode"])
        self.assertEqual(actual_acq["Depth"], actual_acq["SegmentSize"])

    def test_valid_configuration_trig_delay(self):
        config_filename = "adc-configs/example-config-trig-delay.toml"

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        # Grab the configuration dictionaries from the hardware
        actual_acq = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle, CS_ACQUISITION_CONFIGURATION
        )
        actual_chan = PyGage.GetChannelConfig(
            self.digitizer._digitizer_handle,
            self.digitizer.channel_config.Channel,
            CS_ACQUISITION_CONFIGURATION,
        )
        actual_trig = PyGage.GetTriggerConfig(
            self.digitizer._digitizer_handle, 1, CS_ACQUISITION_CONFIGURATION
        )

        expected_acq = self.digitizer.acquisition_config._asdict()
        expected_chan = self.digitizer.channel_config._asdict()
        expected_trig = self.digitizer.trigger_config._asdict()

        # Check that all values we set are as expected
        for key in expected_trig.keys():
            self.assertEqual(expected_trig[key], actual_trig[key])

        for key in expected_chan.keys():
            if key != "Channel":
                self.assertEqual(expected_chan[key], actual_chan[key])

        for key in expected_acq.keys():
            self.assertEqual(expected_acq[key], actual_acq[key])
        self.assertEqual(CS_MODE_SINGLE, actual_acq["Mode"])
        self.assertEqual(actual_acq["Depth"], actual_acq["SegmentSize"])

    def test_invalid_trig_delay_config(self):
        config_filename = "adc-configs/invalid-trig-delay-config.toml"

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError, "Trigger Delay is invalid"):
            self.digitizer.configure()

    def test_invalid_n_samples_config(self):
        config_filename = "adc-configs/invalid-n-samples-config.toml"

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError, "Invalid segment size"):
            self.digitizer.configure()

    def test_invalid_sample_rate_config1(self):
        config_filename = "adc-configs/invalid-sample-rate-config-1.toml"

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError, "Invalid sample rate"):
            self.digitizer.configure()

    def test_invalid_sample_rate_config2(self):
        config_filename = "adc-configs/invalid-sample-rate-config-2.toml"

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError, "Invalid sample rate"):
            self.digitizer.configure()

    def test_invalid_trigger_source_config(self):
        config_filename = "adc-configs/invalid-trig-source-config-2.toml"

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError, "Invalid trigger source"):
            self.digitizer.configure()

    def test_invalid_dc_offset_config(self):
        config_filename = "adc-configs/invalid-dc-offset-config.toml"

        self.digitizer.load_configuration(config_filename)

        with self.assertRaisesRegex(RuntimeError, "Invalid DC offset"):
            self.digitizer.configure()

    def test_voltage_conversion_no_dc_offset(self):
        config_filename = "adc-configs/example-config-1.toml"

        self.digitizer.load_configuration(config_filename)

        # Voltages are reported in mV, but we want them in V
        voltage_range = self.digitizer.channel_config.InputRange / 1000
        dc_offset = self.digitizer.channel_config.DcOffset / 1000

        # Get sample offset and resolution information from the digitizer. Sample resolution from
        # the digitizer is -2^(n_bits - 1)
        sample_offset = PyGage.GetAcquisitionConfig(self.digitizer._digitizer_handle)[
            "SampleOffset"
        ]
        sample_resolution = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle
        )["SampleResolution"]
        n_bits = np.log2(np.abs(sample_resolution)) + 1

        # Create all possible ADC codes that the digitizer's data type can represent
        adc_codes = np.linspace(
            -(2 ** (n_bits - 1)), 2 ** (n_bits - 1) - 1, int(2**n_bits)
        )

        # ADC code 0 is not necessarily 0 Volts. The code for sample_offset is 0 Volts.
        # Thus we need to adjust the voltage range based upon the sample offset.
        expected_voltages = (
            np.linspace(
                -voltage_range / 2 + (sample_offset / sample_resolution),
                voltage_range // 2 + (sample_offset // sample_resolution),
                int(2**n_bits),
            )
            + dc_offset
        )

        actual_voltages = self.digitizer.convert_to_volts(adc_codes)

        self.assertEqual(np.linalg.norm(expected_voltages - actual_voltages), 0)

    def test_voltage_conversion_no_dc_offset_zero_volts_matrix(self):
        config_filename = "adc-configs/example-config-1.toml"

        self.digitizer.load_configuration(config_filename)

        voltage_range = self.digitizer.channel_config.InputRange / 1000
        dc_offset = self.digitizer.channel_config.DcOffset / 1000

        sample_offset = PyGage.GetAcquisitionConfig(self.digitizer._digitizer_handle)[
            "SampleOffset"
        ]
        sample_resolution = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle
        )["SampleResolution"]
        n_bits = np.log2(np.abs(sample_resolution)) + 1

        # The sample offset is equal to 0 Volts
        adc_codes = np.ones((1024, 2048)) * sample_offset

        expected_voltages = np.zeros((1024, 2048))

        actual_voltages = self.digitizer.convert_to_volts(adc_codes)

        self.assertEqual(np.linalg.norm(expected_voltages - actual_voltages), 0)

    def test_voltage_conversion_dc_offset(self):
        config_filename = "adc-configs/example-config-2.toml"

        self.digitizer.load_configuration(config_filename)

        voltage_range = self.digitizer.channel_config.InputRange / 1000
        dc_offset = self.digitizer.channel_config.DcOffset / 1000

        sample_offset = PyGage.GetAcquisitionConfig(self.digitizer._digitizer_handle)[
            "SampleOffset"
        ]
        sample_resolution = PyGage.GetAcquisitionConfig(
            self.digitizer._digitizer_handle
        )["SampleResolution"]
        n_bits = np.log2(np.abs(sample_resolution)) + 1

        adc_codes = np.linspace(
            -(2 ** (n_bits - 1)), 2 ** (n_bits - 1) - 1, int(2**n_bits)
        )

        expected_voltages = (
            np.linspace(
                -voltage_range / 2 + (sample_offset / sample_resolution),
                voltage_range // 2 + (sample_offset // sample_resolution),
                int(2**n_bits),
            )
            + dc_offset
        )

        actual_voltages = self.digitizer.convert_to_volts(adc_codes)

        self.assertEqual(np.linalg.norm(expected_voltages - actual_voltages), 0)

    def test_save_h5_file_single_image(self):
        # NOTE: this could be written as a unit test with mock data
        # and config values instead of actually capturing an image
        # with the digitizer.
        config_filename = "adc-configs/example-config-1.toml"
        h5_filename = "test.h5"

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        (data, timestamps, capture_time) = self.digitizer.capture()

        save_as_h5(
            h5_filename,
            data,
            timestamps,
            capture_time,
            self.digitizer.system_info,
            self.digitizer.acquisition_config,
            self.digitizer.channel_config,
            self.digitizer.trigger_config,
        )

        with h5py.File(h5_filename, "r") as h5file:
            # Check system info metadata
            for key, val in h5file["digitizer/info"].attrs.items():
                self.assertIn(key, self.digitizer.system_info.keys())
                self.assertEqual(val, self.digitizer.system_info[key])

            # Check acquisition config
            for key, val in h5file["digitizer/config/acquisition"].attrs.items():
                self.assertIn(key, self.digitizer.acquisition_config._fields)
                self.assertEqual(val, getattr(self.digitizer.acquisition_config, key))

            # Check channel config
            for key, val in h5file["digitizer/config/channel"].attrs.items():
                self.assertIn(key, self.digitizer.channel_config._fields)
                self.assertEqual(val, getattr(self.digitizer.channel_config, key))

            # Check trigger config
            for key, val in h5file["digitizer/config/trigger"].attrs.items():
                self.assertIn(key, self.digitizer.trigger_config._fields)
                self.assertEqual(val, getattr(self.digitizer.trigger_config, key))

            # Check dataset dimensions
            # Since this is a single image acquisition, all of the first
            # dimensions should be singleton dimensions
            self.assertEqual(h5file["data/data"].shape[0], 1)
            self.assertEqual(h5file["data/data"].shape[1:], data.shape)
            self.assertEqual(h5file["data/timestamps"].shape[0], 1)
            self.assertEqual(h5file["data/timestamps"].shape[1], timestamps.shape[0])
            self.assertEqual(h5file["data/capture_time"].shape[0], 1)
            self.assertEqual(h5file["data/capture_time"].shape[1], 1)

            # Check units
            self.assertEqual(h5file["data/data"].attrs["units"], "ADC count")
            self.assertEqual(h5file["data/timestamps"].attrs["units"], "ns")

            # Check dimension labels
            self.assertEqual(h5file["data/data"].dims[0].label, "capture #")
            self.assertEqual(h5file["data/data"].dims[1].label, "range bin")
            self.assertEqual(h5file["data/data"].dims[2].label, "time")

            # Check dataset values
            self.assertTrue(np.array_equiv(h5file["data/data"], data))
            self.assertTrue(np.array_equiv(h5file["data/timestamps"], timestamps))
            self.assertEqual(h5file["data/capture_time"][0, 0].decode(), capture_time)

        os.remove(h5_filename)

    def test_save_h5_file_multiple_images(self):
        # NOTE: this could be written as a unit test with mock data
        # and config values instead of actually capturing an image
        # with the digitizer.
        config_filename = "adc-configs/example-config-1.toml"
        h5_filename = "test.h5"

        self.digitizer.load_configuration(config_filename)

        self.digitizer.configure()

        n_images = 16
        n_samples = self.digitizer.acquisition_config.SegmentSize
        n_segments = self.digitizer.acquisition_config.SegmentCount

        data = np.empty(shape=(n_images, n_samples, n_segments))
        timestamps = np.empty(shape=(n_images, n_segments))
        capture_time = np.empty(shape=n_images, dtype=np.bytes_)

        for image_num in range(0, n_images):
            (data[image_num, :], timestamps[image_num, :], capture_time[image_num]) = (
                self.digitizer.capture()
            )

        save_as_h5(
            h5_filename,
            data,
            timestamps,
            capture_time,
            self.digitizer.system_info,
            self.digitizer.acquisition_config,
            self.digitizer.channel_config,
            self.digitizer.trigger_config,
        )

        with h5py.File(h5_filename, "r") as h5file:
            # Check system info metadata
            for key, val in h5file["digitizer/info"].attrs.items():
                self.assertIn(key, self.digitizer.system_info.keys())
                self.assertEqual(val, self.digitizer.system_info[key])

            # Check acquisition config
            for key, val in h5file["digitizer/config/acquisition"].attrs.items():
                self.assertIn(key, self.digitizer.acquisition_config._fields)
                self.assertEqual(val, getattr(self.digitizer.acquisition_config, key))

            # Check channel config
            for key, val in h5file["digitizer/config/channel"].attrs.items():
                self.assertIn(key, self.digitizer.channel_config._fields)
                self.assertEqual(val, getattr(self.digitizer.channel_config, key))

            # Check trigger config
            for key, val in h5file["digitizer/config/trigger"].attrs.items():
                self.assertIn(key, self.digitizer.trigger_config._fields)
                self.assertEqual(val, getattr(self.digitizer.trigger_config, key))

            # Check dataset dimensions
            self.assertEqual(h5file["data/data"].shape, data.shape)
            self.assertEqual(h5file["data/timestamps"].shape, timestamps.shape)
            self.assertEqual(h5file["data/capture_time"].shape, capture_time.shape)

            # Check units
            self.assertEqual(h5file["data/data"].attrs["units"], "ADC count")
            self.assertEqual(h5file["data/timestamps"].attrs["units"], "ns")

            # Check dimension labels
            self.assertEqual(h5file["data/data"].dims[0].label, "capture #")
            self.assertEqual(h5file["data/data"].dims[1].label, "range bin")
            self.assertEqual(h5file["data/data"].dims[2].label, "time")

            # Check dataset values
            self.assertTrue(np.array_equal(h5file["data/data"], data))
            self.assertTrue(np.array_equal(h5file["data/timestamps"], timestamps))
            self.assertTrue(np.array_equal(h5file["data/capture_time"], capture_time))

        os.remove(h5_filename)

    def test_save_h5_file_first_dimensions_unequal(self):
        config_filename = "adc-configs/example-config-1.toml"
        h5_filename = "test.h5"

        self.digitizer.load_configuration(config_filename)
        self.digitizer.configure()

        data = np.zeros(shape=(2, 10, 32))
        timestamps = np.zeros(shape=(1, 32))
        capture_time = "1010-10-10 10:10:10.1010"

        with self.assertRaises(ValueError) as cm:
            save_as_h5(
                h5_filename,
                data,
                timestamps,
                capture_time,
                self.digitizer.system_info,
                self.digitizer.acquisition_config,
                self.digitizer.channel_config,
                self.digitizer.trigger_config,
            )

    def test_save_h5_file_bad_timestamp_dimension(self):
        config_filename = "adc-configs/example-config-1.toml"
        h5_filename = "test.h5"

        self.digitizer.load_configuration(config_filename)
        self.digitizer.configure()

        data = np.zeros(shape=(2, 10, 32))
        timestamps = np.zeros(shape=(2, 10))
        capture_time = np.array(
            ["1010-10-10 10:10:10.1010", "1010-10=10 11:11:11.1111"], dtype=np.bytes_
        )

        with self.assertRaises(ValueError) as cm:
            save_as_h5(
                h5_filename,
                data,
                timestamps,
                capture_time,
                self.digitizer.system_info,
                self.digitizer.acquisition_config,
                self.digitizer.channel_config,
                self.digitizer.trigger_config,
            )

    def test_save_h5_file_bad_distance_dimension(self):
        config_filename = "adc-configs/example-config-1.toml"
        h5_filename = "test.h5"

        self.digitizer.load_configuration(config_filename)
        self.digitizer.configure()

        data = np.zeros(shape=(2, 100, 32))
        timestamps = np.zeros(shape=(2, 32))
        capture_time = np.array(
            ["1010-10-10 10:10:10.1010", "1010-10=10 11:11:11.1111"], dtype=np.bytes_
        )
        distance = np.zeros(shape=123)

        with self.assertRaises(ValueError) as cm:
            save_as_h5(
                h5_filename,
                data,
                timestamps,
                capture_time,
                self.digitizer.system_info,
                self.digitizer.acquisition_config,
                self.digitizer.channel_config,
                self.digitizer.trigger_config,
                distance=distance,
            )

    # TODO: add save_h5 adc-configs for scenarios where we do range calibration
    # and voltage conversion
