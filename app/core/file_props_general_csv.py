__author__ = "Craig Dickinson"


def set_general_csv_file_format(logger):
    """Return a LoggerProperties object populated with default file format properties of a General-csv file."""

    logger.file_format = "General-csv"
    logger.file_timestamp_embedded = True
    logger.first_col_data = "Timestamp"
    logger.file_ext = "csv"
    logger.file_delimiter = ","
    logger.num_headers = 2
    logger.channel_header_row = 1
    logger.units_header_row = 2

    return logger
