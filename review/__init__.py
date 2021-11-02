import logging
import os


def get_root_dir() -> str:
    """Returns parent directory of module. If structure is:
    parent/
        .git
        config.ini
        module/
            __init__.py
            code1.py
            code2.py

    Then will return top level 'parent' directory path

    Returns:
        str: path to directory path
    """
    script_location = os.path.realpath(__file__)
    root_dir = script_location.split("/")[:-2]
    return "/".join(root_dir)


def get_module_logger(mod_name: str) -> logging.Logger:
    """Creates logger instance for re-use within each module

    Args:
        mod_name (str): Name of the module to write

    Returns:
        logging.Logger: Logger instance to be used to write
    """
    # create logger
    logger = logging.getLogger(mod_name)
    # create file handler, get file address and add
    log_fd = get_root_dir() + "/logs/review.log"
    fd = logging.FileHandler(log_fd)
    logger.addHandler(fd)
    # create log format and add
    fmt = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
    formatter = logging.Formatter(fmt)
    fd.setFormatter(formatter)
    # set logging level
    logger.setLevel(logging.DEBUG)
    return logger
