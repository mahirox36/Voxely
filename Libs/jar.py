import os
import requests
from rich import print

class MinecraftServerDownloader:
    def __init__(self):
        self.version_manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        self.paper_api_url = "https://api.papermc.io/v2/projects/paper"
        self.fabric_meta_url = "https://meta.fabricmc.net/v2/versions"
        os.makedirs("versions", exist_ok=True)

    def get_vanilla_versions(self, include_snapshots=False):
        """Get all available Vanilla Minecraft versions. Optionally include snapshots."""
        response = requests.get(self.version_manifest_url)
        if response.status_code == 200:
            version_data = response.json()
            if include_snapshots:
                versions = [v['id'] for v in version_data['versions']]
            else:
                versions = [v['id'] for v in version_data['versions'] if v['type'] == 'release']
            return versions
        else:
            print(f"Failed to fetch Vanilla versions. Status code: {response.status_code}")
            return []

    def downloadVanilla(self, version: str):
        versions = self.get_vanilla_versions(True)
        if version not in versions:
            print(f"Version {version} not found.")
            return False
        
        response = requests.get(self.version_manifest_url)
        if response.status_code == 200:
            version_data = next((v for v in response.json()['versions'] if v['id'] == version), None)
            if not version_data:
                print(f"Version {version} not found in manifest.")
                return False
            version_url = version_data['url']
        else:
            print(f"Failed to fetch version manifest. Status code: {response.status_code}")
            return False
        
        response = requests.get(version_url)
        if response.status_code == 200:
            server_url = response.json()["downloads"]["server"]["url"]
        else:
            print(f"Failed to fetch version data. Status code: {response.status_code}")
            return False
        
        response = requests.get(server_url)
        if response.status_code == 200:
            with open(f"versions/vanilla-{version}.jar", "wb") as f:
                f.write(response.content)
            return f"versions/vanilla-{version}.jar"
        else:
            print(f"Failed to download Vanilla server JAR. Status code: {response.status_code}")
            return False

    def get_paper_versions(self):
        """Get all available Paper versions."""
        response = requests.get(f"{self.paper_api_url}/")
        if response.status_code == 200:
            version_data = response.json()
            versions = version_data['versions']
            return versions
        else:
            print(f"Failed to fetch Paper versions. Status code: {response.status_code}")
            return []
    
    def downloadPaper(self, version: str):
        versions = self.get_paper_versions()
        if version not in versions:
            print(f"Version {version} not found.")
            return False
        
        api_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
        response = requests.get(api_url)
    
        if response.status_code == 200:
            builds = response.json()["builds"]
            if not builds:
                print(f"No builds found for Paper version {version}.")
                return False
            
            latest_build = builds[-1]
            download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build['build']}/downloads/paper-{version}-{latest_build['build']}.jar"
            jar_response = requests.get(download_url)
            
            if jar_response.status_code == 200:
                with open(f"versions/paper-{version}-{latest_build['build']}.jar", "wb") as f:
                    f.write(jar_response.content)
                return f"versions/paper-{version}-{latest_build['build']}.jar"
            else:
                print(f"Failed to download Paper JAR. Status code: {jar_response.status_code}")
                return False
        else:
            print(f"Failed to fetch Paper builds. Status code: {response.status_code}")
            return False

    def get_fabric_versions(self, include_snapshots=False):
        """Get all available Minecraft versions supported by Fabric. Optionally include snapshots."""
        response = requests.get(f"{self.fabric_meta_url}/game")
        if response.status_code == 200:
            version_data = response.json()
            if include_snapshots:
                versions = version_data  # The API already returns a list of versions
            else:
                versions = [v for v in version_data if v.get('stable', False)]
            return versions
        else:
            print(f"Failed to fetch Fabric supported versions. Status code: {response.status_code}")
            return []

    def downloadFabric(self, version: str):
        versions = self.get_fabric_versions(True)
        if version not in [v['version'] for v in versions]:
            print(f"Version {version} not found.")
            return False

        # Get the latest loader version
        loader_response = requests.get(f"{self.fabric_meta_url}/loader/{version}")
        if loader_response.status_code != 200:
            print(f"Failed to fetch Fabric loader versions. Status code: {loader_response.status_code}")
            return False

        loader_data = loader_response.json()
        if not loader_data:
            print(f"No Fabric loader found for version {version}.")
            return False

        loader_version = loader_data[0]['loader']['version']

        # Get the latest installer version
        installer_response = requests.get(f"{self.fabric_meta_url}/installer")
        if installer_response.status_code != 200:
            print(f"Failed to fetch Fabric installer versions. Status code: {installer_response.status_code}")
            return False

        installer_data = installer_response.json()
        if not installer_data:
            print("No Fabric installer versions found.")
            return False

        installer_version = installer_data[0]['version']

        # Construct the download URL for the Fabric server launcher
        download_url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_version}/{installer_version}/server/jar"
        
        jar_response = requests.get(download_url)
        if jar_response.status_code == 200:
            filename = f"versions/fabric-server-mc{version}-loader{loader_version}-launcher{installer_version}.jar"
            with open(filename, 'wb') as file:
                file.write(jar_response.content)
            print(f"Successfully downloaded Fabric server launcher: {filename}")
            return filename
        else:
            print(f"Failed to download Fabric server launcher. Status code: {jar_response.status_code}")
            return False