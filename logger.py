import logging

def get_logger():
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    return log

logger = get_logger()
