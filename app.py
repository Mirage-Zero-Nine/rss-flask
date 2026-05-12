from utils.logging_config import configure_logging


configure_logging()

from application.factory import create_app, start_scheduler_if_needed

app = create_app()
start_scheduler_if_needed()


if __name__ == '__main__':
    app.run()
