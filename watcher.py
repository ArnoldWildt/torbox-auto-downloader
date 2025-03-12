import time
import logging
from pathlib import Path
import json
import os

from config import Config
from api_client import TorBoxAPIClient
from file_processor import FileProcessor
from download_tracker import DownloadTracker

# Configure logging (moved here as it's the main entry)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("TorBoxWatcher")
logger.setLevel(logging.DEBUG)  # Set global log level here if needed


class TorBoxWatcherApp:
    """
    Orchestrates the TorBox watching, processing, and downloading.
    """

    def __init__(self, config: Config):
        """
        Initializes the TorBoxWatcherApp with the given configuration.

        Args:
            config (Config): The configuration object.
        """
        self.config = config
        self.api_client = TorBoxAPIClient(
            config.TORBOX_API_BASE,
            config.TORBOX_API_VERSION,
            config.TORBOX_API_KEY,
            config.MAX_RETRIES,
        )
        self.file_processor = FileProcessor(
            config.DOWNLOAD_DIR,
            config.PROGRESS_INTERVAL,
        )
        self.download_tracker = DownloadTracker()
        self.active_downloads = (
            {}
        )  # Track active downloads here, passed to file_processor

        # Ensure directories exist
        config.WATCH_DIR.mkdir(exist_ok=True)
        config.DOWNLOAD_DIR.mkdir(exist_ok=True)

        logger.info(
            f"Initialized TorBox Watcher with API base: {self.api_client.api_base}"
        )
        logger.info(f"Watching directory: {config.WATCH_DIR}")
        logger.info(f"Download directory: {config.DOWNLOAD_DIR}")
        logger.info(f"Progress updates every {config.PROGRESS_INTERVAL} seconds")

    def scan_watch_directory(self):
        """
        Scans the watch directory for torrent, magnet, and NZB files.
        Processes each file found according to its type.
        """
        logger.info(f"Scanning watch directory: {self.config.WATCH_DIR}")
        results = []
        for file_path in self.config.WATCH_DIR.glob("*"):
            if file_path.is_file():
                file_extension = file_path.suffix.lower()
                if file_extension in [".torrent", ".magnet"]:
                    result = self.process_torrent_file(file_path)
                    results.append(result)
                elif file_extension == ".nzb":
                    result = self.process_nzb_file(file_path)
                    results.append(result)

        for success, file_path, download_id in results:
            if success:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")

    def process_torrent_file(self, file_path: Path):
        """
        Processes a torrent file or magnet link.

        Sends the torrent/magnet to the TorBox API and tracks the download.

        Args:
            file_path (Path): The path to the torrent file or magnet link.
        """
        file_name = file_path.name
        logger.info(f"Processing torrent file: {file_name}")
        payload = {
            "seed": self.config.SEED_PREFERENCE,
            "allow_zip": self.config.ALLOW_ZIP,
            "name": file_path.stem,
            "as_queued": self.config.QUEUE_IMMEDIATELY,
        }
        try:
            if file_path.suffix.lower() == ".torrent":
                response_data = self.api_client.create_torrent(
                    file_name, file_path, payload
                )
            else:  # .magnet
                with open(file_path, "r") as f:
                    magnet_link = f.read().strip()
                    payload["magnet"] = magnet_link
                response_data = self.api_client.create_torrent_from_magnet(payload)

            logger.debug(f"Torrent API response: {json.dumps(response_data)}")

            download_id = None
            torrent_hash = None
            if "data" in response_data and isinstance(response_data["data"], dict):
                if "torrent_id" in response_data["data"]:
                    download_id = response_data["data"]["torrent_id"]
                if "hash" in response_data["data"]:
                    torrent_hash = response_data["data"]["hash"]

            if download_id or torrent_hash:
                identifier = download_id if download_id else torrent_hash
                logger.info(
                    f"Successfully submitted torrent: {file_name}, ID: {identifier}"
                )
                self.download_tracker.track_download(
                    identifier,
                    "torrent",
                    file_path.stem,
                    file_path,
                    download_id,
                    torrent_hash,
                )
                return True, file_path, identifier
            else:
                logger.error(
                    f"Failed to get download ID for: {file_name}. Response: {json.dumps(response_data)}"
                )
                return False, file_path, None

        except Exception as e:
            logger.error(f"Error processing torrent file {file_name}: {e}")
            return False, file_path, None

    def check_torrent_status(self, download_id):
        """
        Checks the status of a torrent download.

        Args:
            download_id: The ID of the torrent download (can be torrent_id or hash).
        """
        tracking_info = self.download_tracker.get_download_info(download_id)
        if not tracking_info:
            logger.warning(f"No tracking info found for download ID: {download_id}")
            return

        torrent_id = tracking_info.get("id")
        query_param = f"id={torrent_id}" if torrent_id else f"id={download_id}"

        try:
            status_data = self.api_client.get_torrent_list(query_param)
            logger.debug(f"Torrent status response: {json.dumps(status_data)}")

            torrent_data = None
            if "data" in status_data:
                if isinstance(status_data["data"], dict):
                    torrent_data = status_data["data"]
                elif (
                    isinstance(status_data["data"], list)
                    and len(status_data["data"]) > 0
                ):
                    for torrent in status_data["data"]:
                        if (
                            torrent_id and str(torrent.get("id", "")) == str(torrent_id)
                        ) or (
                            tracking_info.get("hash")
                            and torrent.get("hash") == tracking_info.get("hash")
                        ):
                            torrent_data = torrent
                            break

            if torrent_data:
                download_state = torrent_data.get("download_state", "")
                progress = torrent_data.get("progress", 0)
                progress_percentage = float(progress) * 100
                size_formatted = torrent_data.get("size", 0)

                logger.info(
                    f"Torrent [{download_id}]: {tracking_info['name']} | Status: {download_state.upper()} | Progress: {progress_percentage:.1f}% | Size: {size_formatted}"
                )

                if torrent_data.get("download_present", False):
                    self.request_torrent_download(download_id)

            else:
                logger.warning(
                    f"Could not find torrent with ID {download_id} in status response."
                )

        except Exception as e:
            logger.error(f"Error checking torrent status for ID {download_id}: {e}")

    def request_torrent_download(self, download_id):
        """
        Requests a download link for a completed torrent.

        Args:
            download_id: The ID of the torrent download.
        """
        tracking_info = self.download_tracker.get_download_info(download_id)
        if not tracking_info:
            logger.warning(
                f"No tracking info found for download ID: {download_id} for download request."
            )
            return

        torrent_id = tracking_info.get("id")
        request_id = torrent_id if torrent_id else download_id

        try:
            download_link_data = self.api_client.request_torrent_download_link(
                request_id
            )

            if (
                download_link_data.get("success", False)
                and "data" in download_link_data
            ):
                download_url = download_link_data["data"]
                logger.info(
                    f"Got download URL for torrent ID {download_id}: {download_url}"
                )
                download_path = (
                    self.config.DOWNLOAD_DIR / tracking_info["name"]
                )  # Initial path, filename adjusted in downloader
                self.file_processor.download_file(
                    download_url,
                    download_path,
                    tracking_info["name"],
                    download_id,
                    self.download_tracker.get_tracked_downloads(),
                    self.active_downloads,
                )
            else:
                logger.error(
                    f"Failed to get download URL for torrent ID {download_id}: {json.dumps(download_link_data)}"
                )

        except Exception as e:
            logger.error(f"Error requesting torrent download for ID {download_id}: {e}")

    def process_nzb_file(self, file_path: Path):
        """
        Processes an NZB file.

        Sends the NZB file to the TorBox API and tracks the download.

        Args:
            file_path (Path): The path to the NZB file.
        """
        file_name = file_path.name
        logger.info(f"Processing NZB file: {file_name}")
        payload = {
            "name": file_path.stem,
            "post_processing": self.config.POST_PROCESSING,
            "as_queued": self.config.QUEUE_IMMEDIATELY,
        }
        try:
            response_data = self.api_client.create_usenet_download(
                file_name, file_path, payload
            )
            logger.debug(f"Usenet API response: {json.dumps(response_data)}")

            identifier = None
            download_id = None
            download_hash = None

            if "data" in response_data and isinstance(response_data["data"], dict):
                if "usenetdownload_id" in response_data["data"]:
                    identifier = response_data["data"]["usenetdownload_id"]
                    download_id = identifier
                elif "id" in response_data["data"]:
                    identifier = response_data["data"]["id"]
                    download_id = identifier
                elif "hash" in response_data["data"]:
                    identifier = response_data["data"]["hash"]
                    download_hash = identifier

            if identifier:
                logger.info(
                    f"Successfully submitted NZB: {file_name}, ID: {identifier}"
                )
                self.download_tracker.track_download(
                    identifier,
                    "usenet",
                    file_path.stem,
                    file_path,
                    download_id,
                    download_hash,
                )
                return True, file_path, identifier
            else:
                logger.error(
                    f"Failed to get download ID or hash for NZB: {file_name}. Response: {json.dumps(response_data)}"
                )
                return False, file_path, None

        except Exception as e:
            logger.error(f"Error processing NZB file {file_name}: {e}")
            return False, file_path, None

    def check_usenet_status(self, download_id):
        """
        Checks the status of a usenet download.

        Args:
            download_id: The ID of the usenet download (can be usenetdownload_id or hash).
        """
        tracking_info = self.download_tracker.get_download_info(download_id)
        if not tracking_info:
            logger.warning(
                f"No tracking info found for usenet download ID: {download_id}"
            )
            return

        usenet_id = tracking_info.get("id")
        query_param = f"id={usenet_id}" if usenet_id else f"id={download_id}"

        try:
            status_data = self.api_client.get_usenet_list(query_param)
            logger.debug(f"Usenet status response: {json.dumps(status_data)}")

            usenet_data = None
            if "data" in status_data:
                if isinstance(status_data["data"], dict):
                    usenet_data = status_data["data"]
                elif (
                    isinstance(status_data["data"], list)
                    and len(status_data["data"]) > 0
                ):
                    for usenet in status_data["data"]:
                        if (
                            usenet_id and str(usenet.get("id", "")) == str(usenet_id)
                        ) or (
                            tracking_info.get("hash")
                            and usenet.get("hash") == tracking_info.get("hash")
                        ):
                            usenet_data = usenet
                            break

            if usenet_data:
                download_state = usenet_data.get("download_state", "")
                download_present = usenet_data.get("download_present", False)
                download_finished = usenet_data.get("download_finished", False)
                progress = usenet_data.get("progress", 0)
                progress_percentage = float(progress) * 100
                size_formatted = usenet_data.get("size", 0)

                logger.info(
                    f"Usenet [{download_id}]: {tracking_info['name']} | Status: {download_state.upper()} | Progress: {progress_percentage:.1f}% | Size: {size_formatted}"
                )

                if download_present:
                    self.request_usenet_download(download_id)

            else:
                logger.warning(
                    f"Could not find usenet download with ID {download_id} in status response."
                )

        except Exception as e:
            logger.error(f"Error checking usenet status for ID {download_id}: {e}")

    def request_usenet_download(self, download_id):
        """
        Requests a download link for a completed usenet download.

        Args:
            download_id: The ID of the usenet download.
        """
        tracking_info = self.download_tracker.get_download_info(download_id)
        if not tracking_info:
            logger.warning(
                f"No tracking info found for usenet ID: {download_id} for download request."
            )
            return

        usenet_id = tracking_info.get("id")
        request_id = usenet_id if usenet_id else download_id

        try:
            download_link_data = self.api_client.request_usenet_download_link(
                request_id
            )

            if (
                download_link_data.get("success", False)
                and "data" in download_link_data
            ):
                download_url = download_link_data["data"]
                logger.info(
                    f"Got download URL for usenet ID {download_id}: {download_url}"
                )
                download_path = (
                    self.config.DOWNLOAD_DIR / tracking_info["name"]
                )  # Initial path, filename adjusted in downloader
                self.file_processor.download_file(
                    download_url,
                    download_path,
                    tracking_info["name"],
                    download_id,
                    self.download_tracker.get_tracked_downloads(),
                    self.active_downloads,
                )

            else:
                logger.error(
                    f"Failed to get download URL for usenet ID {download_id}: {json.dumps(download_link_data)}"
                )

        except Exception as e:
            logger.error(f"Error requesting usenet download for ID {download_id}: {e}")

    def check_download_status(self):
        """
        Checks the status of all tracked downloads (both torrent and usenet).
        """
        tracked_downloads = self.download_tracker.get_tracked_downloads()
        if not tracked_downloads:
            return

        logger.info(f"Checking status of {len(tracked_downloads)} downloads")
        download_ids = list(tracked_downloads.keys())  # Iterate over a copy of keys

        for download_id in download_ids:
            download_info = tracked_downloads[download_id]
            download_type = download_info["type"]

            try:
                if download_type == "torrent":
                    self.check_torrent_status(download_id)
                elif download_type == "usenet":
                    self.check_usenet_status(download_id)
            except Exception as e:
                logger.error(f"Error checking status for ID {download_id}: {e}")

    def run(self):
        """
        Main execution loop of the TorBoxWatcherApp.

        Continuously scans the watch directory, checks download statuses,
        and sleeps for a configured interval.
        """
        logger.info("Starting TorBox Watcher")
        while True:
            try:
                self.scan_watch_directory()
                self.check_download_status()
                logger.info(
                    f"Waiting {self.config.WATCH_INTERVAL} seconds until next scan"
                )
                time.sleep(self.config.WATCH_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt. Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)  # Wait before next loop in case of error
