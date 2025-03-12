import logging
from config import Config
from watcher import TorBoxWatcherApp

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the TorBox Watcher application.

    This function initializes and runs the TorBoxWatcherApp. It handles
    configuration validation and potential startup errors.

    Raises:
        ValueError: If there is a configuration error.
        Exception: For any other application startup errors.
    """
    try:
        Config.validate()
        config = Config()
        watcher_app = TorBoxWatcherApp(config)
        watcher_app.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"Application startup error: {e}")


if __name__ == "__main__":
    main()
