import requests
import json
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class TorBoxAPIClient:
    """
    Encapsulates communication with the TorBox API.
    """

    def __init__(self, api_base, api_version, api_key, max_retries):
        """
        Initializes the TorBoxAPIClient.

        Args:
            api_base (str): The base URL of the TorBox API.
            api_version (str): The version of the TorBox API.
            api_key (str): The API key for authentication.
            max_retries (int): The maximum number of retries for API calls.
        """
        self.api_base = f"{api_base}/{api_version}/api"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.max_retries = max_retries
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(lambda context: context.api_client.max_retries + 1),
        wait=wait_fixed(5),
        retry_error_callback=lambda retry_state: setattr(
            retry_state.outcome, "api_client", retry_state.args[0]
        ),
    )
    def _post(self, endpoint, payload=None, files=None):
        """
        Makes a POST request to the TorBox API.

        Args:
            endpoint (str): The API endpoint.
            payload (dict, optional): The request payload. Defaults to None.
            files (dict, optional): Files to upload. Defaults to None.

        Returns:
            dict: The JSON response from the API.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error (4xx or 5xx).
            requests.exceptions.RequestException: If there is a problem with the request.
        """
        url = f"{self.api_base}{endpoint}"
        try:
            response = requests.post(
                url, headers=self.headers, data=payload, files=files
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error calling API {url}: {e} - {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception calling API {url}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(lambda context: context.api_client.max_retries + 1),
        wait=wait_fixed(5),
        retry_error_callback=lambda retry_state: setattr(
            retry_state.outcome, "api_client", retry_state.args[0]
        ),
    )
    def _get(self, endpoint, params=None):
        """
        Makes a GET request to the TorBox API.

        Args:
            endpoint (str): The API endpoint.
            params (dict, optional): Query parameters. Defaults to None.

        Returns:
            dict: The JSON response from the API.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error (4xx or 5xx).
            requests.exceptions.RequestException: If there is a problem with the request.
        """
        url = f"{self.api_base}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error calling API {url}: {e} - {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception calling API {url}: {e}")
            raise

    def create_torrent(self, file_name, file_path, payload):
        """
        Creates a torrent download via the TorBox API.

        Args:
            file_name (str): The name of the torrent file.
            file_path (str): The path to the torrent file.
            payload (dict): Additional payload data.

        Returns:
            dict: The API response.
        """
        endpoint = "/torrents/createtorrent"
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, "application/x-bittorrent")}
            return self._post(endpoint, payload=payload, files=files)

    def create_torrent_from_magnet(self, payload):
        """
        Creates a torrent download from a magnet link via the TorBox API.

        Args:
            payload (dict): The request payload, including the magnet link.

        Returns:
            dict: The API response.
        """
        endpoint = "/torrents/createtorrent"
        return self._post(endpoint, payload=payload)

    def get_torrent_list(self, query_param):
        """
        Retrieves the list of torrents from the TorBox API.

        Args:
            query_param (str): Query parameters for filtering the list.

        Returns:
            dict: The API response.
        """
        endpoint = "/torrents/mylist"
        return self._get(f"{endpoint}?{query_param}")

    def request_torrent_download_link(self, torrent_id):
        """
        Requests a download link for a specific torrent from the TorBox API.

        Args:
            torrent_id (str): The ID of the torrent.

        Returns:
            dict: The API response.
        """
        endpoint = "/torrents/requestdl"
        params = {"torrent_id": torrent_id, "zip_link": "true", "token": self.api_key}
        return self._get(endpoint, params=params)

    def create_usenet_download(self, file_name, file_path, payload):
        """
        Creates a usenet download via the TorBox API.

        Args:
            file_name (str): The name of the NZB file.
            file_path (str): The path to the NZB file.
            payload (dict): Additional payload data.

        Returns:
            dict: The API response.
        """
        endpoint = "/usenet/createusenetdownload"
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, "application/x-nzb")}
            return self._post(endpoint, payload=payload, files=files)

    def get_usenet_list(self, query_param):
        """
        Retrieves the list of usenet downloads from the TorBox API.

        Args:
            query_param (str): Query parameters for filtering the list.

        Returns:
            dict: The API response.
        """
        endpoint = "/usenet/mylist"
        return self._get(f"{endpoint}?{query_param}")

    def request_usenet_download_link(self, usenet_id):
        """
        Requests a download link for a specific usenet download from the TorBox API.

        Args:
            usenet_id (str): The ID of the usenet download.

        Returns:
            dict: The API response.
        """
        endpoint = "/usenet/requestdl"
        params = {"usenet_id": usenet_id, "zip_link": "true", "token": self.api_key}
        return self._get(endpoint, params=params)
