import logging
import os
import sys
from datetime import datetime
from pathlib import Path


LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
LOG_FILENAME_PREFIX = 'application'


def configure_logging():
    log_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    log_dir = Path(os.environ.get('RSS_LOG_DIR', Path(__file__).resolve().parent.parent / 'logs'))

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'{LOG_FILENAME_PREFIX}-{log_timestamp}.log')

    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )
