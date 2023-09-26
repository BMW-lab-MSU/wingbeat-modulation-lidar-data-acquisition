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

    # def test_valid_configuration(self):