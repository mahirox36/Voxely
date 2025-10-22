from enum import StrEnum
import os
import requests
import json
import time
from rich import print
from rich.progress import Progress, DownloadColumn, TransferSpeedColumn
import logging
import shutil
from pathlib import Path

# Set up a dedicated logger for the JAR module
logging.basicConfig(level=logging.INFO)
jar_logger = logging.getLogger("jar_downloader")

# Create a file handler for the jar downloader
os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/jar_downloader.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
jar_logger.addHandler(file_handler)

class ServerType(StrEnum):
    VANILLA = "vanilla"
    FABRIC = "fabric"
    PAPER = "paper"
    PURPUR = "purpur"
    CUSTOM = "custom"

class MinecraftServerDownloader:
    def __init__(self):
        self.version_manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        self.paper_api_url = "https://api.papermc.io/v2/projects/paper"
        self.fabric_meta_url = "https://meta.fabricmc.net/v2/versions"
        self.forge_api_url = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
        self.purpur_api_url = "https://api.purpurmc.org/v2/purpur"
        
        self.cache_dir = "cache"
        self.versions_dir = "versions"
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)
        
        self._cache = {}
        self._cache_duration = 3600  # 1 hour cache
        jar_logger.info(f"MinecraftServerDownloader initialized with versions directory: {self.versions_dir}")

    def _get_cached_data(self, cache_key):
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        jar_logger.debug(f"Checking for cached data: {cache_key}")
        if os.path.exists(cache_file):
            jar_logger.debug(f"Cache file exists: {cache_file}")
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if time.time() - data['timestamp'] < self._cache_duration:
                        jar_logger.debug(f"Using cached data for {cache_key}")
                        return data['content']
                    jar_logger.debug(f"Cache expired for {cache_key}")
            except Exception as e:
                jar_logger.error(f"Error reading cache file {cache_file}: {str(e)}")
        else:
            jar_logger.debug(f"No cache file found for {cache_key}")
        return None

    def _save_cache(self, cache_key, content):
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        jar_logger.debug(f"Saving cache for {cache_key}")
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'content': content
                }, f)
            jar_logger.debug(f"Cache saved successfully to {cache_file}")
        except Exception as e:
            jar_logger.error(f"Error saving cache to {cache_file}: {str(e)}")

    def _download_with_progress(self, url, filename):
        jar_logger.info(f"Starting download from {url} to {filename}")
        try:
            with Progress(
                *Progress.get_default_columns(),
                DownloadColumn(),
                TransferSpeedColumn(),
            ) as progress:
                response = requests.get(url, stream=True)
                if response.status_code != 200:
                    jar_logger.error(f"Download failed with status code: {response.status_code}")
                    return False
                
                total_size = int(response.headers.get('content-length', 0))
                jar_logger.info(f"Download size: {total_size} bytes")
                task = progress.add_task("[cyan]Downloading...", total=total_size)
                
                with open(filename, 'wb') as f:
                    bytes_downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            progress.update(task, advance=len(chunk))
                    
                    jar_logger.info(f"Downloaded {bytes_downloaded} of {total_size} bytes to {filename}")
                
                # Verify the file was downloaded correctly
                if os.path.exists(filename):
                    file_size = os.path.getsize(filename)
                    jar_logger.info(f"Verifying download: file size is {file_size} bytes")
                    if total_size > 0 and file_size != total_size:
                        jar_logger.warning(f"Download size mismatch! Expected {total_size}, got {file_size}")
                else:
                    jar_logger.error(f"Downloaded file {filename} does not exist!")
                    return False
                
                return filename
        except Exception as e:
            jar_logger.error(f"Error downloading file: {str(e)}")
            return False

    def get_vanilla_versions(self, include_snapshots=False):
        """Get all available Vanilla Minecraft versions. Optionally include snapshots."""
        jar_logger.info(f"Getting vanilla versions (include_snapshots={include_snapshots})")
        cache_data = self._get_cached_data('vanilla_versions')
        if cache_data:
            jar_logger.info(f"Found {len(cache_data)} cached vanilla versions")
            return cache_data
        
        try:
            response = requests.get(self.version_manifest_url)
            if response.status_code == 200:
                version_data = response.json()
                if include_snapshots:
                    versions = [v['id'] for v in version_data['versions']]
                else:
                    versions = [v['id'] for v in version_data['versions'] if v['type'] == 'release']
                jar_logger.info(f"Retrieved {len(versions)} vanilla versions")
                self._save_cache('vanilla_versions', versions)
                return versions
            else:
                jar_logger.error(f"Failed to fetch Vanilla versions. Status code: {response.status_code}")
                return []
        except Exception as e:
            jar_logger.error(f"Error fetching vanilla versions: {str(e)}")
            return []

    def downloadVanilla(self, version: str):
        jar_logger.info(f"Downloading vanilla version {version}")
        versions = self.get_vanilla_versions(True)
        version = str(version)
        if version not in versions:
            jar_logger.error(f"Version {version} not found in available versions")
            return False
        
        try:
            response = requests.get(self.version_manifest_url)
            if response.status_code == 200:
                version_data = next((v for v in response.json()['versions'] if v['id'] == version), None)
                if not version_data:
                    jar_logger.error(f"Version {version} not found in manifest")
                    return False
                version_url = version_data['url']
                jar_logger.debug(f"Found version URL: {version_url}")
            else:
                jar_logger.error(f"Failed to fetch version manifest. Status code: {response.status_code}")
                return False
            
            response = requests.get(version_url)
            if response.status_code == 200:
                server_url = response.json()["downloads"]["server"]["url"]
                jar_logger.debug(f"Found server download URL: {server_url}")
            else:
                jar_logger.error(f"Failed to fetch version data. Status code: {response.status_code}")
                return False
            
            jar_file = f"versions/vanilla-{version}.jar"
            result = self._download_with_progress(server_url, jar_file)
            jar_logger.info(f"Download result: {result}")
            return result
        except Exception as e:
            jar_logger.error(f"Error in downloadVanilla: {str(e)}")
            return False

    def get_paper_versions(self):
        """Get all available Paper versions."""
        jar_logger.info("Getting Paper versions")
        cache_data = self._get_cached_data('paper_versions')
        if cache_data:
            jar_logger.info(f"Found {len(cache_data)} cached Paper versions")
            return cache_data

        try:
            response = requests.get(f"{self.paper_api_url}/")
            if response.status_code == 200:
                version_data = response.json()
                versions = version_data['versions']
                versions.reverse()
                jar_logger.info(f"Retrieved {len(versions)} Paper versions")
                self._save_cache('paper_versions', versions)
                return versions
            else:
                jar_logger.error(f"Failed to fetch Paper versions. Status code: {response.status_code}")
                return []
        except Exception as e:
            jar_logger.error(f"Error fetching Paper versions: {str(e)}")
            return []
    
    def downloadPaper(self, version: str, build='latest'):
        jar_logger.info(f"Downloading Paper version {version} (build={build})")
        versions = self.get_paper_versions()
        version = str(version)
        if version not in versions:
            jar_logger.error(f"Version {version} not found in available Paper versions")
            return False
        
        try:
            api_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
            jar_logger.debug(f"Fetching builds from: {api_url}")
            response = requests.get(api_url)
        
            if response.status_code == 200:
                builds = response.json()["builds"]
                if not builds:
                    jar_logger.error(f"No builds found for Paper version {version}")
                    return False
                
                latest_build = builds[-1]
                build_number = latest_build['build']
                jar_logger.info(f"Using build {build_number} for Paper version {version}")
                
                download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build_number}/downloads/paper-{version}-{build_number}.jar"
                jar_file = f"versions/paper-{version}-{build_number}.jar"
                
                jar_logger.debug(f"Downloading from: {download_url}")
                result = self._download_with_progress(download_url, jar_file)
                jar_logger.info(f"Download result: {result}")
                return result
            else:
                jar_logger.error(f"Failed to fetch Paper builds. Status code: {response.status_code}")
                return False
        except Exception as e:
            jar_logger.error(f"Error in downloadPaper: {str(e)}")
            return False

    def get_fabric_versions(self, include_snapshots=False):
        """Get all available Minecraft versions supported by Fabric. Optionally include snapshots."""
        jar_logger.info(f"Getting Fabric versions (include_snapshots={include_snapshots})")
        cache_data = self._get_cached_data('fabric_versions')
        if cache_data:
            jar_logger.info(f"Found {len(cache_data)} cached Fabric versions")
            return cache_data
        
        try:
            response = requests.get(f"{self.fabric_meta_url}/game")
            if response.status_code == 200:
                version_data = response.json()
                if include_snapshots:
                    versions = version_data  # The API already returns a list of versions
                else:
                    versions = [v for v in version_data if v.get('stable', False)]
                versions = [v['version'] for v in versions]
                jar_logger.info(f"Retrieved {len(versions)} Fabric versions")
                self._save_cache('fabric_versions', versions)
                return versions
            else:
                jar_logger.error(f"Failed to fetch Fabric supported versions. Status code: {response.status_code}")
                return []
        except Exception as e:
            jar_logger.error(f"Error fetching Fabric versions: {str(e)}")
            return []

    def downloadFabric(self, version: str):
        jar_logger.info(f"Downloading Fabric version {version}")
        versions = self.get_fabric_versions(True)
        version = str(version)
        if version not in versions:
            jar_logger.error(f"Version {version} not found in available Fabric versions")
            return False

        try:
            # Get the latest loader version
            loader_url = f"{self.fabric_meta_url}/loader/{version}"
            jar_logger.debug(f"Fetching loader version from: {loader_url}")
            loader_response = requests.get(loader_url)
            if loader_response.status_code != 200:
                jar_logger.error(f"Failed to fetch Fabric loader versions. Status code: {loader_response.status_code}")
                return False

            loader_data = loader_response.json()
            if not loader_data:
                jar_logger.error(f"No Fabric loader found for version {version}")
                return False

            loader_version = loader_data[0]['loader']['version']
            jar_logger.info(f"Using Fabric loader version: {loader_version}")

            # Get the latest installer version
            installer_url = f"{self.fabric_meta_url}/installer"
            jar_logger.debug(f"Fetching installer version from: {installer_url}")
            installer_response = requests.get(installer_url)
            if installer_response.status_code != 200:
                jar_logger.error(f"Failed to fetch Fabric installer versions. Status code: {installer_response.status_code}")
                return False

            installer_data = installer_response.json()
            if not installer_data:
                jar_logger.error("No Fabric installer versions found")
                return False

            installer_version = installer_data[0]['version']
            jar_logger.info(f"Using Fabric installer version: {installer_version}")

            # Construct the download URL for the Fabric server launcher
            download_url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_version}/{installer_version}/server/jar"
            jar_logger.debug(f"Downloading from: {download_url}")
            
            filename = f"versions/fabric-server-mc{version}-loader{loader_version}-launcher{installer_version}.jar"
            result = self._download_with_progress(download_url, filename)
            jar_logger.info(f"Download result: {result}")
            return result
        except Exception as e:
            jar_logger.error(f"Error in downloadFabric: {str(e)}")
            return False

    def get_purpur_versions(self):
        """Get all available Purpur versions."""
        jar_logger.info("Getting Purpur versions")
        cache_data = self._get_cached_data('purpur_versions')
        if cache_data:
            jar_logger.info(f"Found {len(cache_data)} cached Purpur versions")
            return cache_data

        try:
            response = requests.get(self.purpur_api_url)
            if response.status_code == 200:
                versions = response.json()['versions']
                jar_logger.info(f"Retrieved {len(versions)} Purpur versions")
                self._save_cache('purpur_versions', versions)
                return versions
            else:
                jar_logger.error(f"Failed to fetch Purpur versions. Status code: {response.status_code}")
                return []
        except Exception as e:
            jar_logger.error(f"Error fetching Purpur versions: {str(e)}")
            return []

    def downloadPurpur(self, version: str, build='latest'):
        """Download Purpur server jar."""
        jar_logger.info(f"Downloading Purpur version {version} (build={build})")
        versions = self.get_purpur_versions()
        if version not in versions:
            jar_logger.error(f"Version {version} not found in available Purpur versions")
            return False

        try:
            if build == 'latest':
                response = requests.get(f"{self.purpur_api_url}/{version}/latest")
                if response.status_code != 200:
                    jar_logger.error("Failed to fetch latest build")
                    return False
                build = response.json()['build']
                jar_logger.info(f"Using latest build: {build}")

            download_url = f"{self.purpur_api_url}/{version}/{build}/download"
            filename = f"versions/purpur-{version}-{build}.jar"
            jar_logger.debug(f"Downloading from: {download_url}")
            result = self._download_with_progress(download_url, filename)
            jar_logger.info(f"Download result: {result}")
            return result
        except Exception as e:
            jar_logger.error(f"Error in downloadPurpur: {str(e)}")
            return False