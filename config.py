import os
from pathlib import Path


class Config:
    """
    Configuration class to load settings from environment variables.
    """

    TORBOX_API_KEY = os.getenv("TORBOX_API_KEY")
    TORBOX_API_BASE = os.getenv("TORBOX_API_BASE", "https://api.torbox.app")
    TORBOX_API_VERSION = os.getenv("TORBOX_API_VERSION", "v1")
    WATCH_DIR = Path(os.getenv("WATCH_DIR", "/app/watch"))
    DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/app/downloads"))
    WATCH_INTERVAL = int(os.getenv("WATCH_INTERVAL", 60))
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))
    ALLOW_ZIP = os.getenv("ALLOW_ZIP", "true").lower() == "true"
    SEED_PREFERENCE = int(os.getenv("SEED_PREFERENCE", 1))
    POST_PROCESSING = int(os.getenv("POST_PROCESSING", -1))
    QUEUE_IMMEDIATELY = os.getenv("QUEUE_IMMEDIATELY", "false").lower() == "true"
    PROGRESS_INTERVAL = int(os.getenv("PROGRESS_INTERVAL", 15))

    @staticmethod
    def validate():
        """
        Validates that the required environment variables are set.

        Raises:
            ValueError: If the TORBOX_API_KEY is not set.
        """
        if not Config.TORBOX_API_KEY:
            raise ValueError(
                "TORBOX_API_KEY is not set. Please provide a valid API key."
            )
