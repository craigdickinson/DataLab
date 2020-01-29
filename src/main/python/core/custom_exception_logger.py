"""Function to create custom exception logging to report errors to both the console."""

__author__ = "Craig Dickinson"

import logging
import os


def set_exception_logger(log_path=""):
    """
    Function to create a custom exception logging instance.
    Two handlers are created for reporting exceptions to the console and a log file.
    """

    if log_path == "":
        log_path = os.getcwd()

    log_file = os.path.join(log_path, "log.out")
    # logging.basicConfig(filename=log_file)

    log = logging.getLogger("DataLab")
    log.setLevel(logging.DEBUG)

    # Console logger
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")
    ch.setFormatter(formatter)

    # File logger
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s: %(name)s %(levelname)s - %(message)s", datefmt="%m/%d/%Y %H:%M:%S"
        #     "%(asctime)s: %(name)s %(levelname)s - %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p"
    )
    fh.setFormatter(formatter)

    log.addHandler(ch)
    log.addHandler(fh)

    return log


def set_exception_logger_file_handler_path(log, log_path):
    """
    Update the file handler path.
    Pop file handler from logger list, close previous log file, update file path and insert back to logger.
    """

    fh: logging.FileHandler
    fh = log.handlers.pop()
    fh.close()
    fh.baseFilename = os.path.join(log_path, "log.out")
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
