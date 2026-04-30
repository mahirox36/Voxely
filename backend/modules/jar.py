from enum import StrEnum
import os
from typing import Optional
import json
import time
import asyncio
import zipfile
from pathlib import Path
from modules.models import ServerType
import aiohttp
import aiofiles
from rich import print
from rich.progress import Progress, DownloadColumn, TransferSpeedColumn
import logging

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
jar_logger = logging.getLogger("jar_downloader")

os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/jar_downloader.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
jar_logger.addHandler(file_handler)


class JarDownloader:
    # Class-level constants (Static URLs)
    version_manifest_url = (
        "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    )
    paper_api_url = "https://api.papermc.io/v2/projects/paper"
    fabric_meta_url = "https://meta.fabricmc.net/v2/versions"
    forge_promotions_url = (
        "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
    )
    forge_maven_url = "https://maven.minecraftforge.net/net/minecraftforge/forge"
    neoforge_maven_url = "https://maven.neoforged.net/releases/net/neoforged/neoforge"
    purpur_api_url = "https://api.purpurmc.org/v2/purpur"

    _init_done = False

    def __init__(self) -> None:
        # Configuration
        self.cache_dir = "cache"
        self.versions_dir = "versions"
        self._cache_duration = 3600  # seconds

        # Ensure directories exist for every instance
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)

        # Global initialization log (runs only once)
        if not JarDownloader._init_done:
            jar_logger.info(
                "JarDownloader initialised | versions_dir=%s cache_dir=%s",
                self.versions_dir,
                self.cache_dir,
            )
            JarDownloader._init_done = True

    # ------------------------------------------------------------------
    # Cache helpers (I/O kept async)
    # ------------------------------------------------------------------

    async def _get_cached_data(self, cache_key: str):
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if not os.path.exists(cache_file):
            return None
        try:
            async with aiofiles.open(cache_file, "r") as f:
                data = json.loads(await f.read())
            if time.time() - data["timestamp"] < self._cache_duration:
                jar_logger.debug("Cache hit: %s", cache_key)
                return data["content"]
            jar_logger.debug("Cache expired: %s", cache_key)
        except Exception as e:
            jar_logger.error("Error reading cache %s: %s", cache_file, e)
        return None

    async def _save_cache(self, cache_key: str, content) -> None:
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            async with aiofiles.open(cache_file, "w") as f:
                await f.write(
                    json.dumps({"timestamp": time.time(), "content": content})
                )
            jar_logger.debug("Cache saved: %s", cache_key)
        except Exception as e:
            jar_logger.error("Error saving cache %s: %s", cache_file, e)

    # ------------------------------------------------------------------
    # Core download helper (non-blocking)
    # ------------------------------------------------------------------

    async def _download_with_progress(
        self, url: str, filename: str, session: aiohttp.ClientSession
    ) -> Optional[str]:
        jar_logger.info("Downloading %s → %s", url, filename)
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    jar_logger.error("HTTP %d for %s", response.status, url)
                    return None

                total_size = int(response.headers.get("content-length", 0))

                with Progress(
                    *Progress.get_default_columns(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                ) as progress:
                    task = progress.add_task(
                        "[cyan]Downloading…", total=total_size or None
                    )

                    async with aiofiles.open(filename, "wb") as f:
                        bytes_downloaded = 0
                        async for chunk in response.content.iter_chunked(65_536):
                            if chunk:
                                await f.write(chunk)
                                bytes_downloaded += len(chunk)
                                progress.update(task, advance=len(chunk))

                    jar_logger.info(
                        "Downloaded %d / %d bytes → %s",
                        bytes_downloaded,
                        total_size,
                        filename,
                    )

            # Integrity check
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                if total_size and file_size != total_size:
                    jar_logger.warning(
                        "Size mismatch! expected=%d got=%d", total_size, file_size
                    )
            else:
                jar_logger.error("File missing after download: %s", filename)
                return None

            return filename

        except Exception as e:
            jar_logger.error("Error downloading %s: %s", url, e)
            return None

    # ------------------------------------------------------------------
    # Public: unified entry point
    # ------------------------------------------------------------------

    async def download_jar(
        self,
        version: str,
        type: ServerType,
        destination: Path,
    ) -> Optional[Path]:
        """Download the appropriate server JAR without blocking the event loop."""
        jar_logger.info("download_jar | version=%s type=%s", version, type)
        async with aiohttp.ClientSession() as session:
            try:
                if type == ServerType.VANILLA:
                    result = await self.download_vanilla(version, session)
                elif type == ServerType.PAPER:
                    result = await self.download_paper(version, session)
                elif type == ServerType.FABRIC:
                    result = await self.download_fabric(version, session)
                elif type == ServerType.PURPUR:
                    result = await self.download_purpur(version, session)
                elif type == ServerType.FORGE:
                    result = await self.download_forge(version, session)
                elif type == ServerType.NEOFORGE:
                    result = await self.download_neoforge(version, session)
                else:
                    jar_logger.error("Unsupported server type: %s", type)
                    return None

                if result:
                    dest_path = destination / os.path.basename(result)
                    os.makedirs(destination, exist_ok=True)
                    os.replace(result, dest_path)
                    jar_logger.info("JAR ready at %s", dest_path)
                    return dest_path
                else:
                    jar_logger.error("Failed to download JAR for version %s", version)
                    return None

            except Exception as e:
                jar_logger.error("Error in download_jar: %s", e)
                return None

    # ------------------------------------------------------------------
    # Vanilla
    # ------------------------------------------------------------------

    async def get_vanilla_versions(
        self,
        session: aiohttp.ClientSession,
        include_snapshots: bool = False,
    ):
        cached = await self._get_cached_data("vanilla_versions")
        if cached:
            return cached
        try:
            async with session.get(self.version_manifest_url) as resp:
                if resp.status != 200:
                    jar_logger.error("Vanilla manifest HTTP %d", resp.status)
                    return []
                data = await resp.json(content_type=None)
            if include_snapshots:
                versions = [v["id"] for v in data["versions"]]
            else:
                versions = [v["id"] for v in data["versions"] if v["type"] == "release"]
            await self._save_cache("vanilla_versions", versions)
            return versions
        except Exception as e:
            jar_logger.error("get_vanilla_versions: %s", e)
            return []

    async def download_vanilla(
        self, version: str, session: aiohttp.ClientSession
    ) -> Optional[str]:
        versions = await self.get_vanilla_versions(session, include_snapshots=True)
        if str(version) not in versions:
            jar_logger.error("Vanilla version %s not found", version)
            return None
        try:
            async with session.get(self.version_manifest_url) as resp:
                manifest = await resp.json(content_type=None)

            version_meta = next(
                (v for v in manifest["versions"] if v["id"] == version), None
            )
            if not version_meta:
                return None

            async with session.get(version_meta["url"]) as resp:
                version_data = await resp.json(content_type=None)

            server_url = version_data["downloads"]["server"]["url"]
            jar_file = f"versions/vanilla-{version}.jar"
            return await self._download_with_progress(server_url, jar_file, session)
        except Exception as e:
            jar_logger.error("download_vanilla: %s", e)
            return None

    # ------------------------------------------------------------------
    # Paper
    # ------------------------------------------------------------------

    async def get_paper_versions(self, session: aiohttp.ClientSession):
        cached = await self._get_cached_data("paper_versions")
        if cached:
            return cached
        try:
            async with session.get(f"{self.paper_api_url}/") as resp:
                if resp.status != 200:
                    return []
                data = await resp.json(content_type=None)
            versions = list(reversed(data["versions"]))
            await self._save_cache("paper_versions", versions)
            return versions
        except Exception as e:
            jar_logger.error("get_paper_versions: %s", e)
            return []

    async def download_paper(
        self, version: str, session: aiohttp.ClientSession, build: str = "latest"
    ) -> Optional[str]:
        versions = await self.get_paper_versions(session)
        if str(version) not in versions:
            jar_logger.error("Paper version %s not found", version)
            return None
        try:
            async with session.get(
                f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
            ) as resp:
                if resp.status != 200:
                    return None
                builds = (await resp.json(content_type=None))["builds"]

            if not builds:
                return None
            build_number = builds[-1]["build"]
            download_url = (
                f"https://api.papermc.io/v2/projects/paper/versions/{version}"
                f"/builds/{build_number}/downloads/paper-{version}-{build_number}.jar"
            )
            jar_file = f"versions/paper-{version}-{build_number}.jar"
            return await self._download_with_progress(download_url, jar_file, session)
        except Exception as e:
            jar_logger.error("download_paper: %s", e)
            return None

    # ------------------------------------------------------------------
    # Fabric
    # ------------------------------------------------------------------

    async def get_fabric_versions(
        self,
        session: aiohttp.ClientSession,
        include_snapshots: bool = False,
    ):
        cached = await self._get_cached_data("fabric_versions")
        if cached:
            return cached
        try:
            async with session.get(f"{self.fabric_meta_url}/game") as resp:
                if resp.status != 200:
                    return []
                data = await resp.json(content_type=None)
            versions = (
                data if include_snapshots else [v for v in data if v.get("stable")]
            )
            versions = [v["version"] for v in versions]
            await self._save_cache("fabric_versions", versions)
            return versions
        except Exception as e:
            jar_logger.error("get_fabric_versions: %s", e)
            return []

    async def download_fabric(
        self, version: str, session: aiohttp.ClientSession
    ) -> Optional[str]:
        versions = await self.get_fabric_versions(session, include_snapshots=True)
        if str(version) not in versions:
            jar_logger.error("Fabric version %s not found", version)
            return None
        try:
            async with session.get(f"{self.fabric_meta_url}/loader/{version}") as resp:
                if resp.status != 200:
                    return None
                loader_data = await resp.json(content_type=None)
            if not loader_data:
                return None
            loader_version = loader_data[0]["loader"]["version"]

            async with session.get(f"{self.fabric_meta_url}/installer") as resp:
                if resp.status != 200:
                    return None
                installer_data = await resp.json(content_type=None)
            if not installer_data:
                return None
            installer_version = installer_data[0]["version"]

            download_url = (
                f"https://meta.fabricmc.net/v2/versions/loader"
                f"/{version}/{loader_version}/{installer_version}/server/jar"
            )
            filename = (
                f"versions/fabric-server-mc{version}"
                f"-loader{loader_version}-launcher{installer_version}.jar"
            )
            return await self._download_with_progress(download_url, filename, session)
        except Exception as e:
            jar_logger.error("download_fabric: %s", e)
            return None

    # ------------------------------------------------------------------
    # Purpur
    # ------------------------------------------------------------------

    async def get_purpur_versions(self, session: aiohttp.ClientSession):
        cached = await self._get_cached_data("purpur_versions")
        if cached:
            return cached
        try:
            async with session.get(self.purpur_api_url) as resp:
                if resp.status != 200:
                    return []
                versions = (await resp.json(content_type=None))["versions"]
            await self._save_cache("purpur_versions", versions)
            return versions
        except Exception as e:
            jar_logger.error("get_purpur_versions: %s", e)
            return []

    async def download_purpur(
        self, version: str, session: aiohttp.ClientSession, build: str = "latest"
    ) -> Optional[str]:
        versions = await self.get_purpur_versions(session)
        if version not in versions:
            jar_logger.error("Purpur version %s not found", version)
            return None
        try:
            if build == "latest":
                async with session.get(
                    f"{self.purpur_api_url}/{version}/latest"
                ) as resp:
                    if resp.status != 200:
                        return None
                    build = (await resp.json(content_type=None))["build"]

            download_url = f"{self.purpur_api_url}/{version}/{build}/download"
            filename = f"versions/purpur-{version}-{build}.jar"
            return await self._download_with_progress(download_url, filename, session)
        except Exception as e:
            jar_logger.error("download_purpur: %s", e)
            return None

    # ------------------------------------------------------------------
    # Forge
    # ------------------------------------------------------------------

    async def get_forge_versions(self, session: aiohttp.ClientSession):
        cached = await self._get_cached_data("forge_versions")
        if cached:
            return cached
        try:
            async with session.get(self.forge_promotions_url) as resp:
                if resp.status != 200:
                    return {}
                promotions = await resp.json(content_type=None)
            versions: dict[str, str] = {}
            for key, forge_ver in promotions["promos"].items():
                if "-" in key:
                    mc_ver = key.split("-")[0]
                    versions[mc_ver] = forge_ver
            await self._save_cache("forge_versions", versions)
            return versions
        except Exception as e:
            jar_logger.error("get_forge_versions: %s", e)
            return {}

    async def download_forge(
        self,
        mc_version: str,
        session: aiohttp.ClientSession,
        forge_version: Optional[str] = None,
    ) -> Optional[str]:
        try:
            if not forge_version:
                versions = await self.get_forge_versions(session)
                if mc_version not in versions:
                    jar_logger.error("No Forge version for MC %s", mc_version)
                    return None
                forge_version = versions[mc_version]

            full_version = f"{mc_version}-{forge_version}"
            download_url = (
                f"{self.forge_maven_url}/{full_version}"
                f"/forge-{full_version}-installer.jar"
            )
            installer_path = f"versions/forge-{full_version}-installer.jar"
            return await self._download_with_progress(
                download_url, installer_path, session
            )
        except Exception as e:
            jar_logger.error("download_forge: %s", e)
            return None

    # ------------------------------------------------------------------
    # NeoForge
    # ------------------------------------------------------------------

    async def get_neoforge_versions(self, session: aiohttp.ClientSession):
        cached = await self._get_cached_data("neoforge_versions")
        if cached:
            return cached
        try:
            metadata_url = f"{self.neoforge_maven_url}/maven-metadata.xml"
            async with session.get(metadata_url) as resp:
                if resp.status != 200:
                    return []
                content = await resp.text()

            import xml.etree.ElementTree as ET

            root = ET.fromstring(content)
            versions = [v.text for v in root.findall(".//version") if v.text]
            await self._save_cache("neoforge_versions", versions)
            return versions
        except Exception as e:
            jar_logger.error("get_neoforge_versions: %s", e)
            return []

    async def download_neoforge(
        self, neoforge_version: str, session: aiohttp.ClientSession
    ) -> Optional[str]:
        try:
            download_url = (
                f"{self.neoforge_maven_url}/{neoforge_version}"
                f"/neoforge-{neoforge_version}-installer.jar"
            )
            installer_path = f"versions/neoforge-{neoforge_version}-installer.jar"
            return await self._download_with_progress(
                download_url, installer_path, session
            )
        except Exception as e:
            jar_logger.error("download_neoforge: %s", e)
            return None


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
async def main():
    downloader = JarDownloader()

    print("[bold cyan]Minecraft Server Downloader[/bold cyan]\n")

    print("[yellow]Downloading Fabric 1.20.1…[/yellow]")
    result = await downloader.download_jar("1.20.1", ServerType.FABRIC, Path("servers"))
    if result:
        print(f"[green]✓ Fabric ready: {result}[/green]")

    print("\n[yellow]Downloading Forge 1.20.1…[/yellow]")
    result = await downloader.download_jar("1.20.1", ServerType.FORGE, Path("servers"))
    if result:
        print(f"[green]✓ Forge installer: {result}[/green]")

    print("\n[yellow]Downloading NeoForge 21.0.167…[/yellow]")
    result = await downloader.download_jar(
        "21.0.167", ServerType.NEOFORGE, Path("servers")
    )
    if result:
        print(f"[green]✓ NeoForge installer: {result}[/green]")


if __name__ == "__main__":
    asyncio.run(main())
