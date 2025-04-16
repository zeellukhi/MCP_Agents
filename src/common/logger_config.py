# logger_config.py
import logging
import logging.config
import os

def setup_logging(default_level=logging.INFO):
    config_path = os.getenv('LOG_CONFIG', None)
    if config_path and os.path.exists(config_path):
        logging.config.fileConfig(config_path)
    else:
        logging.basicConfig(level=default_level,
                            format='%(asctime)s %(levelname)s %(name)s %(message)s')

# Usage: from logger_config import setup_logging; setup_logging()
