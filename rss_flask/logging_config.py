import logging


def configure_logging():
    logging.basicConfig(
        filename="./log/application.log",
        encoding="utf-8",
        level=logging.INFO,
    )
