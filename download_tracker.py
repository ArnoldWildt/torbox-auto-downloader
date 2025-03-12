import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DownloadTracker:
    """
    Tracks submitted downloads and their types.
    """

    def __init__(self):
        """
        Initializes the DownloadTracker with an empty download tracking dictionary.
        """
        self.download_tracking = {}  # {download_id: tracking_info}

    def track_download(
        self,
        identifier,
        download_type,
        file_stem,
        original_file,
        download_id=None,
        download_hash=None,
    ):
        """
        Tracks a new download.

        Args:
            identifier (str): A unique identifier for the download (e.g., torrent ID or hash).
            download_type (str): The type of download ("torrent" or "usenet").
            file_stem (str): The original file name without extension.
            original_file (str): The path to the original file.
            download_id (str, optional): The download ID from the API. Defaults to None.
            download_hash (str, optional): The download hash from the API. Defaults to None.
        """
        self.download_tracking[str(identifier)] = {
            "type": download_type,
            "name": file_stem,
            "submitted_at": datetime.now().isoformat(),
            "original_file": str(original_file),
            "id": download_id,
            "hash": download_hash,
        }
        logger.info(
            f"Tracking new {download_type} download: ID: {identifier}, Name: {file_stem}"
        )

    def get_tracked_downloads(self):
        """
        Returns all tracked downloads.

        Returns:
            dict: A dictionary containing tracking information for all downloads.
        """
        return self.download_tracking

    def remove_tracked_download(self, download_id):
        """
        Removes a download from tracking.

        Args:
            download_id (str): The identifier of the download to remove.
        """
        if download_id in self.download_tracking:
            del self.download_tracking[download_id]
            logger.info(f"Stopped tracking download ID: {download_id}")

    def get_download_info(self, download_id):
        """
        Retrieves tracking information for a given download ID.

        Args:
            download_id (str): The identifier of the download.

        Returns:
            dict: Tracking information for the download, or None if not found.
        """
        return self.download_tracking.get(download_id)
