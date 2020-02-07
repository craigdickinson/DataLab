"""Function to create custom exception logging to report errors to both the console."""

__author__ = "Craig Dickinson"

import logging
import os


def set_exception_logger():
    """Function to create a custom exception logger. Initially only a console logger is created."""

    # Create custom logger
    log = logging.getLogger("DataLab")
    log.setLevel(logging.DEBUG)

    # Add a console logger
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")
    ch.setFormatter(formatter)
    log.addHandler(ch)

    return log


def set_exception_logger_file_handler(log, log_path):
    """Create file logger and close any existing file logger."""

    log_file = os.path.join(log_path, "log.out")

    # Check number of handlers - if more than one it means a file logger already exists
    # (logger 1 being the console logger), close and remove the existing logger then create a new one
    if len(log.handlers) > 1:
        fh = log.handlers.pop()
        fh.close()

    # Add file logger (delay=True means the log.out file will not be created until an exception is first logged)
    fh = logging.FileHandler(log_file, delay=True)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s: %(name)s %(levelname)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S"
        #     "%(asctime)s: %(name)s %(levelname)s - %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p"
    )
    fh.setFormatter(formatter)
    log.addHandler(fh)

    return log


def remove_existing_handlers(log):
    """Remove any handlers in exception logger."""

    try:
        for handler in reversed(log.handlers):
            log.removeHandler(handler)
    except AttributeError:
        pass

    return log
