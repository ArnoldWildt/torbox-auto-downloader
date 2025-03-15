# TorBox Auto Downloader

This project automatically downloads torrents and NZBs from a watch directory using the TorBox API.

## Getting Started with Docker

### Prerequisites

*   Docker and Docker Compose installed.

### Configuration

1.  Set the `TORBOX_API_KEY` environment variable in your `docker-compose.yml` file. Replace the placeholder `YOUR_TORBOX_API_KEY` with your actual Torbox API key.
2.  Update the volume paths in your `docker-compose.yml` file. Replace the placeholders `/path/to/watch` and `/path/to/downloads` with your desired absolute paths.

### Running
1.  Clone Repo

    ```bash
    git clone https://github.com/ArnoldWildt/torbox-auto-downloader
    ```
    
1.  Build the Docker image:

    ```bash
    docker build -t torbox_auto_downloader:local .
    ```

2.  Start the container using Docker Compose:

    ```bash
    docker compose up
    ```

    To run in detached mode (in the background):

    ```bash
    docker compose up -d
    ```

## Configuration (Environment Variables)

| Variable             | Default Value             | Description                                                                                                                                                                                                                            |
| -------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TORBOX_API_KEY`     | **(Required)**            | Your TorBox API key.                                                                                                                                                                                                                   |
| `TORBOX_API_BASE`    | `https://api.torbox.app` | The base URL of the TorBox API.                                                                                                                                                                                                        |
| `TORBOX_API_VERSION` | `v1`                      | The version of the TorBox API.                                                                                                                                                                                                         |
| `WATCH_DIR`          | `/app/watch`              | The directory to watch for torrent, magnet, and NZB files.                                                                                                                                                                              |
| `DOWNLOAD_DIR`       | `/app/downloads`          | The directory where downloaded files will be stored.                                                                                                                                                                                   |
| `WATCH_INTERVAL`     | `60`                      | The interval (in seconds) between scans of the watch directory.                                                                                                                                                                       |
| `CHECK_INTERVAL`     | `300`                     | The interval (in seconds) between checks for the status of downloads.                                                                                                                                                                |
| `MAX_RETRIES`        | `2`                       | The maximum number of retries for API calls.                                                                                                                                                                                           |
| `ALLOW_ZIP`          | `true`                    | Whether to allow automatic ZIP compression of downloads.                                                                                                                                                                              |
| `SEED_PREFERENCE`    | `1`                       | Seed preference for torrents (specific to TorBox API).                                                                                                                                                                                 |
| `POST_PROCESSING`    | `-1`                      | Post-processing setting for usenet downloads (specific to TorBox API).                                                                                                                                                               |
| `QUEUE_IMMEDIATELY`  | `false`                   | Whether to queue downloads immediately or add them as paused (specific to TorBox API, behavior may depend on your Torbox subscription. If set to `false` downloads are added as paused, if `true` downloads are added to the queue). |
| `PROGRESS_INTERVAL`  | `15`                      | The interval (in seconds) for updating download/extraction progress.                                                                                                                                                                  |

## Local Development (without Docker)

1.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

2.  Set the `TORBOX_API_KEY` environment variable and other environment variables as needed, for example in your shell before running.

3.  Run the application:

    ```bash
    python main.py
    ```

    Make sure you have created the `watch`, and `downloads` directories in your project root.

## Integration with Sonarr/Radarr

This project can be integrated with Sonarr and Radarr using the "Blackhole" download client feature. This allows Sonarr/Radarr to drop torrent/magnet/NZB files into the `watch` directory, which will then be processed by this application.

**Configuration Steps (Repeat for both Sonarr and Radarr):**

1.  Go to **Settings** -> **Download Clients**.
2.  Click the **+** button to add a new download client.
3.  Select **Torrent Blackhole** or **Usenet Blackhole** (or both, repeating these steps for each).
4.  Give the download client a descriptive name (e.g., "TorBox Torrent Blackhole").
5.  Set the **Torrent/Usenet Folder** to the `watch` directory you configured for this application (e.g., `/app/watch` if using Docker, or the `watch` subdirectory if running locally). This path must match the `WATCH_DIR` environment variable.
6.  Set the **Watch Folder** to the `downloads` directory you configured for this application (e.g., `/app/downloads` if using Docker, or the `downloads` subdirectory if running locally). This path must match the `DOWNLOAD_DIR` environment variable.
