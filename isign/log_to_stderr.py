import sys
import logging


def log_to_stderr(log):
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(stream=sys.stderr,
                        format=format_str,
                        level=logging.INFO)
