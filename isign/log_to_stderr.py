import logging

FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def log_to_stderr(level=logging.INFO):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(FORMATTER)
    root.addHandler(handler)
