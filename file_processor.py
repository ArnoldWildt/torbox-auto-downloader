import os
import shutil
import zipfile
import logging
import re
import requests
from pathlib import Path
import humanize
import time
import threading

logger = logging.getLogger(__name__)


class DownloadStats:
    """
    Manages and displays download statistics.
    """

    def __init__(self, filename, total_size=None):
        """
        Initializes a DownloadStats object.

        Args:
            filename (str): The name of the file being downloaded.
            total_size (int, optional): The total size of the file in bytes. Defaults to None.
        """
        self.filename = filename
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_downloaded = 0
        self.should_stop = False  # Flag to signal the stats thread to stop
        self.download_complete = False

    def update(self, chunk_size):
        """
        Updates the downloaded amount with the size of the latest chunk.

        Args:
            chunk_size (int): The size of the downloaded chunk in bytes.
        """
        self.downloaded += chunk_size

    def get_speed(self):
        """
        Calculates the download speed.

        Returns:
            float: The download speed in bytes per second.
        """
        now = time.time()
        time_diff = now - self.last_update_time
        if time_diff > 0:
            bytes_diff = self.downloaded - self.last_downloaded
            speed = bytes_diff / time_diff
            self.last_update_time = now
            self.last_downloaded = self.downloaded
            return speed
        return 0

    def get_progress(self):
        """
        Calculates the download progress.

        Returns:
            float: The download progress as a percentage (0-100), or None if total_size is not available.
        """
        if self.total_size:
            return (self.downloaded / self.total_size) * 100
        return None

    def get_elapsed(self):
        """
        Calculates the elapsed download time.

        Returns:
            float: The elapsed time in seconds.
        """
        return time.time() - self.start_time

    def get_eta(self):
        """
        Calculates the estimated time remaining for the download.

        Returns:
            float: The estimated time remaining in seconds, or None if total_size or speed is not available.
        """
        if self.total_size and self.get_speed() > 0:
            remaining_bytes = self.total_size - self.downloaded
            return remaining_bytes / self.get_speed()
        return None

    def print_stats(self):
        """Prints the download statistics to the logger."""
        speed = self.get_speed()
        elapsed = self.get_elapsed()
        progress = self.get_progress()
        eta = self.get_eta()

        stats = [
            f"File: {self.filename}",
            f"Elapsed: {humanize.naturaldelta(elapsed)}",
        ]

        if progress is not None:
            stats.append(f"Progress: {progress:.1f}%")
            bar_length = 20
            filled_length = int(bar_length * progress / 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            stats.append(f"[{bar}]")

        stats.append(f"Downloaded: {humanize.naturalsize(self.downloaded)}")
        if self.total_size:
            stats.append(f"Total: {humanize.naturalsize(self.total_size)}")
        stats.append(f"Speed: {humanize.naturalsize(speed)}/s")
        if eta:
            stats.append(f"ETA: {humanize.naturaldelta(eta)}")

        logger.info(" | ".join(stats))


class ExtractStats:
    """
    Manages and displays ZIP extraction statistics.
    """

    def __init__(self, zip_path, total_files=None, total_size=None):
        """
        Initializes an ExtractStats object.

        Args:
            zip_path (Path): The path to the ZIP file.
            total_files (int, optional): The total number of files in the ZIP. Defaults to None.
            total_size (int, optional): The total size of all files in the ZIP in bytes. Defaults to None.
        """
        self.zip_path = zip_path
        self.total_files = total_files
        self.total_size = total_size
        self.extracted_files = 0
        self.extracted_size = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.should_stop = False  # Flag to signal the stats thread to stop

    def update(self, file_size):
        """
        Updates the extraction statistics.

        Args:
            file_size (int): The size of the extracted file in bytes.
        """
        self.extracted_files += 1
        self.extracted_size += file_size

    def get_progress(self):
        """
        Calculates the extraction progress.

        Returns:
            float: The extraction progress as a percentage (0-100), or None if total_files and total_size are not available.
        """
        if self.total_files:
            return (self.extracted_files / self.total_files) * 100
        if self.total_size:
            return (self.extracted_size / self.total_size) * 100
        return None

    def get_elapsed(self):
        """
        Calculates the elapsed extraction time.

        Returns:
            float: The elapsed time in seconds.
        """
        return time.time() - self.start_time

    def get_speed(self):
        """
        Calculates the extraction speed.

        Returns:
            float: The extraction speed in bytes per second.
        """
        elapsed = self.get_elapsed()
        if elapsed > 0:
            return self.extracted_size / elapsed
        return 0

    def print_stats(self):
        """Prints the extraction statistics to the logger."""
        elapsed = self.get_elapsed()
        progress = self.get_progress()
        speed = self.get_speed()

        stats = [
            f"Extracting: {self.zip_path.name}",
            f"Elapsed: {humanize.naturaldelta(elapsed)}",
        ]

        # if progress is not None:
        #     stats.append(f"Progress: {progress:.1f}%")
        #     bar_length = 20
        #     filled_length = int(bar_length * progress / 100)
        #     bar = "█" * filled_length + "░" * (bar_length - filled_length)
        #     stats.append(f"[{bar}]")

        # stats.append(f"Files: {self.extracted_files}")
        if self.total_files:
            stats.append(f"Total files: {self.total_files}")
        # stats.append(f"Extracted: {humanize.naturalsize(self.extracted_size)}")
        # if self.total_size:
        #     stats.append(f"Total size: {humanize.naturalsize(self.total_size)}")
        # stats.append(f"Speed: {humanize.naturalsize(speed)}/s")

        logger.info(" | ".join(stats))


class FileProcessor:
    """
    Handles file system operations like downloading and extracting files.
    """

    def __init__(self, download_dir, progress_interval):
        """
        Initializes a FileProcessor object.

        Args:
            download_dir (Path): The directory where downloaded files are stored.
            progress_interval (int): The interval in seconds for updating download/extraction progress.
        """
        self.download_dir = download_dir
        self.progress_interval = progress_interval
        self.active_extract_stats = {}  # Track active extractions

    def download_file(
        self,
        download_url,
        download_path,
        download_name,
        download_id,
        download_tracking,
        active_downloads,
    ):
        """
        Downloads a file from a URL with progress tracking.

        Args:
            download_url (str): The URL of the file to download.
            download_path (Path): The destination path for the downloaded file.
            download_name (str): name of the download.
            download_id (str): The ID of the download.
            download_tracking (dict): download tracker
            active_downloads (dict): active downloads
        """
        logger.info(f"Starting download: {download_name} to {download_path}")
        try:
            head_response = requests.head(download_url)
            total_size = int(head_response.headers.get("content-length", 0))

            content_disposition = head_response.headers.get("Content-Disposition", "")
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if filename_match:
                filename = filename_match.group(1)
            else:
                content_type = head_response.headers.get("Content-Type", "")
                if "zip" in content_type:
                    filename = f"{download_name}.zip"
                else:
                    filename = download_name
            download_path = (
                download_path.parent / filename
            )  # Ensure filename respects content disposition
            download_stats = DownloadStats(filename, total_size)
            active_downloads[download_id] = download_stats

            stats_thread = threading.Thread(
                target=self._stats_update_thread,
                args=(download_id, download_stats, active_downloads),
                daemon=True,
            )
            stats_thread.start()

            with requests.get(download_url, stream=True) as response:
                response.raise_for_status()
                download_path.parent.mkdir(
                    parents=True, exist_ok=True
                )  # Ensure download dir exists
                with open(download_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            download_stats.update(len(chunk))

            logger.info(f"Downloaded {filename} successfully to {download_path}")
            download_stats.download_complete = True
            if download_path.suffix.lower() == ".zip":
                download_stats.should_stop = (
                    True  # Stop download stats before extraction
                )
                self.extract_zip(download_path, active_downloads)

        except requests.exceptions.RequestException as e:
            logger.error(f"Download error for ID {download_id}: {e}")
            if download_id in active_downloads:
                active_downloads[download_id].should_stop = True
        except Exception as e:
            logger.error(f"Unexpected error during download for ID {download_id}: {e}")
            if download_id in active_downloads:
                active_downloads[download_id].should_stop = True
        finally:
            if download_id in active_downloads:
                active_downloads[download_id].should_stop = True
            if download_id in download_tracking:  # Moved from try block
                del download_tracking[download_id]

    def _stats_update_thread(self, download_id, stats, active_downloads):
        """
        Thread to periodically update download/extract statistics.

        Args:
            download_id: download id
            stats (DownloadStats or ExtractStats): The statistics object.
            active_downloads (dict): active downloads
        """
        while not stats.should_stop:
            if not stats.should_stop:  # Check before printing
                stats.print_stats()
            time.sleep(self.progress_interval)

        if download_id in active_downloads:
            del active_downloads[download_id]

    def extract_zip(self, zip_path, active_downloads):
        """
        Extracts a ZIP file with progress tracking.

        Args:
            zip_path (Path): The path to the ZIP file.
            active_downloads: active downloads
        """
        logger.info(f"Extracting ZIP file: {zip_path}")
        extract_dir = self.download_dir / zip_path.stem
        extract_dir.mkdir(exist_ok=True)

        try:
            total_size = 0
            total_files = 0
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                for file_info in zip_ref.infolist():
                    if not file_info.is_dir():
                        total_size += file_info.file_size
                        total_files += 1

            logger.info(
                f"ZIP contains {total_files} files, total size {humanize.naturalsize(total_size)}"
            )
            extract_stats = ExtractStats(zip_path, total_files, total_size)
            extract_id = "extract_" + str(zip_path)  # Unique ID for extraction stats
            active_downloads[extract_id] = (
                extract_stats  # Reuse active_downloads for extract stats
            )
            stats_thread = threading.Thread(
                target=self._stats_update_thread,
                args=(
                    extract_id,
                    extract_stats,
                    active_downloads,
                ),  # Pass active_downloads
                daemon=True,
            )
            stats_thread.start()

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                for file_info in zip_ref.infolist():
                    if not file_info.is_dir():
                        zip_ref.extract(file_info, extract_dir)
                        extract_stats.update(file_info.file_size)

            logger.info(f"Successfully extracted ZIP to {extract_dir}")
            extract_stats.should_stop = True

            elapsed = extract_stats.get_elapsed()
            size = humanize.naturalsize(extract_stats.extracted_size)
            avg_speed = humanize.naturalsize(extract_stats.get_speed()) + "/s"
            logger.info(
                f"Extraction complete: {zip_path.name} | Files: {extract_stats.extracted_files} | Size: {size} | Time: {humanize.naturaldelta(elapsed)} | Avg speed: {avg_speed}"
            )
            zip_path.unlink()  # Delete ZIP after extraction
            logger.info(f"Deleted ZIP file: {zip_path}")

        except Exception as e:
            logger.error(f"ZIP extraction error {zip_path}: {e}")
            extract_id = "extract_" + str(zip_path)  # Re-calculate ID in case of error
            if extract_id in active_downloads:
                active_downloads[extract_id].should_stop = True
        finally:
            extract_id = "extract_" + str(zip_path)  # Re-calculate ID for final cleanup
            if extract_id in active_downloads:
                del active_downloads[extract_id]  # Ensure cleanup even on error
