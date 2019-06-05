"""
Tests for the routines used to read the control file.
"""
__author__ = "Craig Dickinson"

import datetime as dt
import io
import unittest
import pytest

from core.control_file import ControlFile


def example_control_file():
    """
    Create an example control file to test.
    """

    # Example format
    data = (
        "*PROJECT_NAME test project 101 \n"
        "*CAMPAIGN_NAME test campaign 1 \n"
        "*OUTPUT_FOLDER output \n"
        "*LOGGER_ID dd09_fugro \n"
        "*PATH test_data/dd09 \n"
        "*FILE_FORMAT fugro-csv \n"
        "*FILE_TIMESTAMP xxxxxYYYYxmmDDxHHMM \n"
        "*NUM_COLUMNS 5 \n"
        "*LOGGING_DURATION 1200 \n"
        "*STATS_COLUMNS 2 3 4 5 \n"
        "*STATS_INTERVAL 600 \n"
        "*STATS_START 2015-07-01 00:00 \n"
        "*STATS_END 2016-07-01 00:00 \n"
        "*LOGGER_ID dd09b \n"
        "*PATH test_data/dd09b \n"
        "*FILE_FORMAT general-csv \n"
        "*FILE_TIMESTAMP xxxxxxYYYYxmmDDxHHMM \n"
        "*EXTENSION csv \n"
        "*DELIMITER comma \n"
        "*TIMESTAMP %d-%b-%Y %H:%M:%S.%f \n"
        "*NUM_HEADERS 3 \n"
        "*NUM_COLUMNS 5 \n"
        "*CHANNEL_HEADER 2 \n"
        "*UNITS_HEADER 3 \n"
        "*LOGGING_FREQUENCY 10 \n"
        "*LOGGING_DURATION 1200 \n"
        "*STATS_COLUMNS 2 3 4 5 \n"
        "*STATS_INTERVAL 600 \n"
        "*STATS_START 2015-07-01 00:00 \n"
        "*STATS_END 2016-07-01 00:00 \n"
        "*SPECTROGRAMS \n"
        "*LOGGER_ID dd09c \n"
        "*PATH test_data/dd09b \n"
        "*COPY_FILE_FORMAT dd09b \n"
        "*COPY_STATS_FORMAT dd09b \n"
        "*LOGGER_ID dd09d \n"
        "*PATH test_data/dd09b \n"
        "*COPY_FILE_FORMAT dd09b \n"
        "*COPY_STATS_FORMAT dd09b \n"
    )
    return data


class TestControlFile(unittest.TestCase):
    def setUp(self):
        # Dummy input filename
        self.my_file = "my_file.dat"

        # Example input data
        self.example_dat = example_control_file()

        # Create a dummy example filestream
        self.test_stream = self.dummy_input_stream(self.example_dat)

        # Test data read from the filestream
        self.test_data = self.test_stream.readlines()

    def dummy_input_stream(self, text):
        """Create a dummy file stream to simulate reading text from a file."""

        test_stream = io.StringIO()
        test_stream.write(text)
        test_stream.seek(0)
        return test_stream

    def test_set_filename(self):
        """Check filename gets set properly."""

        # Simple check
        control = ControlFile()
        control.set_filename(self.my_file)
        self.assertEqual(control.control_file, self.my_file)

    def test_read_logger_names(self):
        """Test logger names are extracted correctly."""

        control = ControlFile()
        control.set_data(self.test_data)
        control.get_logger_ids()

        names = ["dd09_fugro", "dd09b", "dd09c", "dd09d"]
        self.assertEqual(names, control.logger_ids)

    def test_slice_control_file_data(self):
        """Test slice_data returns desired part of list based on a list of indices."""

        # Line numbers of logger ids are: 5, 14, 33, 39. Ignoring blank lines and as 0-index list this is:
        logger_id_lines = [3, 11, 29, 34]

        # Create lists of data lines for each logger id
        logger_id_data = []
        for i in range(len(logger_id_lines)):
            if i < len(logger_id_lines) - 1:
                logger_id_data.append(
                    self.test_data[logger_id_lines[i] : logger_id_lines[i + 1]]
                )
            else:
                logger_id_data.append(self.test_data[logger_id_lines[i] :])

        # Now test against ControlFile slice_data method
        control = ControlFile()

        for i in range(len(logger_id_lines)):
            logger_data = control.slice_data(i, logger_id_lines, self.test_data)
            self.assertEqual(logger_id_data[i], logger_data)

    def test_read_data_from_file_stream(self):
        """Test function that reads all data from a file stream."""

        str1 = "some test data"
        str2 = "this can be anything"
        test_stream = self.dummy_input_stream("\n".join([str1, str2]))
        control = ControlFile()
        data = control.read_data_from_filestream(test_stream)
        self.assertEqual("some test data\n", data[0])
        self.assertEqual("this can be anything", data[1])

    def test_extract_key_data(self):
        """Test keywords and values are successfully extracted from a list"""

        # Create a dummy control file object
        control = ControlFile()

        # Extract title
        key = "*PROJECT_NAME"
        line, title = control.get_key_data(key, self.test_data)
        self.assertEqual(title, "test project 101")
        self.assertEqual(line, 0)

        # Try it when no title exists
        line, no_title = control.get_key_data(key, self.test_data[1:])
        self.assertEqual("", no_title)
        self.assertEqual(line, -1)

        # Get output folder name
        key = "*OUTPUT_FOLDER"
        line, output_folder = control.get_key_data(key, self.test_data)
        self.assertEqual(output_folder, "output")
        self.assertEqual(line, 2)

        # Get the line number and text from the first logger id
        key = "*LOGGER_ID"
        line, logger_id = control.get_key_data(key, self.test_data)
        self.assertEqual(logger_id, "dd09_fugro")
        self.assertEqual(line, 3)

        # Test with data without a logger id
        line, logger_id = control.get_key_data(key, self.test_data[2])
        self.assertEqual(logger_id, "")
        self.assertEqual(line, -1)

    def test_logger_properties_correctly_set(self):
        """Check that logger properties get set correctly from control file."""

        # Create a control file object
        control = ControlFile()

        # set data to be test data
        control.set_data(self.test_data)
        control.get_project_name()
        control.get_campaign_name()
        control.get_output_folder()
        control.process_logger_names()
        control.add_loggers()
        logger0 = control.loggers[0]
        logger1 = control.loggers[1]
        logger2 = control.loggers[2]

        # Check all logger properties are read correctly
        self.assertEqual(logger0.logger_id, "dd09_fugro")
        self.assertEqual(logger0.logger_path, "test_data/dd09")
        self.assertEqual(logger0.file_timestamp_format, "xxxxxYYYYxmmDDxHHMM")
        self.assertEqual(logger0.file_ext, "csv")
        self.assertEqual(logger0.file_delimiter, ",")
        self.assertEqual(logger0.num_headers, 3)
        # self.assertEqual(logger0.num_columns, 5)
        self.assertEqual(logger0.channel_header_row, 2)
        self.assertEqual(logger0.units_header_row, 3)
        self.assertEqual(logger0.requested_cols, [2, 3, 4, 5])
        self.assertEqual(logger0.stats_start, dt.datetime(2015, 7, 1, 0, 0))
        self.assertEqual(logger0.stats_end, dt.datetime(2016, 7, 1, 0, 0))

        self.assertEqual(logger1.logger_path, "test_data/dd09b")
        self.assertEqual(logger1.file_timestamp_format, "xxxxxxYYYYxmmDDxHHMM")
        self.assertEqual(logger1.file_ext, "csv")
        self.assertEqual(logger1.file_delimiter, ",")
        self.assertEqual(logger1.num_headers, 3)
        # self.assertEqual(logger1.num_columns, 5)
        self.assertEqual(logger1.channel_header_row, 2)
        self.assertEqual(logger1.units_header_row, 3)
        self.assertEqual(logger1.requested_cols, [2, 3, 4, 5])

        self.assertEqual(logger2.channel_header_row, 2)


if __name__ == "__main__":
    pytest.main()
