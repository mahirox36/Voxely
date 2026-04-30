import os
import platform
import shutil
import stat
import tarfile
import zipfile
import logging
import asyncio
from pathlib import Path
from typing import Optional

import aiohttp
import aiofiles
from rich import print
from rich.progress import Progress, DownloadColumn, TransferSpeedColumn
from packaging.version import Version

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
java_logger = logging.getLogger("java_manager")

os.makedirs("logs", exist_ok=True)
_fh = logging.FileHandler("logs/java_manager.log")
_fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
java_logger.addHandler(_fh)

# ---------------------------------------------------------------------------
# MC version → Java version mapping
# ---------------------------------------------------------------------------
_VERSION_MAP: list[tuple[str, int]] = [
    ("26.1", 25),
    ("1.20.5", 21),
    ("1.18", 17),
    ("1.17", 17),
    ("0.0", 8),
]

_OS_MAP = {
    "windows": "windows",
    "linux": "linux",
    "darwin": "mac",
}
_ARCH_MAP = {
    "x86_64": "x64",
    "amd64": "x64",
    "aarch64": "aarch64",
    "arm64": "aarch64",
}


class JavaManager:
    """
    Manages portable, version-specific Temurin JDKs for a Minecraft server.
    """

    BASE_DIR: Path = Path("bin/java")
    ADOPTIUM_URL = (
        "https://api.adoptium.net/v3/binary/latest"
        "/{version}/ga/{os}/{arch}/jdk/hotspot/normal/eclipse"
    )
    
    # Class-level state
    _init_done = False
    
    # Pre-compute system info once at class level
    _system = platform.system().lower()
    _machine = platform.machine().lower()
    _adoptium_os = _OS_MAP.get(_system, _system)
    _adoptium_arch = _ARCH_MAP.get(_machine, _machine)

    def __init__(self) -> None:
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        if not JavaManager._init_done:
            java_logger.info(
                "JavaManager initialized | system=%s arch=%s adoptium_os=%s adoptium_arch=%s",
                self._adoptium_os,
                self._adoptium_arch,
                self._system,
                self._machine,
            )
            JavaManager._init_done = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def required_java_version(self, mc_version: str) -> int:
        """Return the Java major version required for *mc_version* (pure, sync)."""
        try:
            mc = Version(mc_version)
        except Exception:
            java_logger.warning(
                "Cannot parse MC version '%s'; defaulting to Java 8", mc_version
            )
            return 8

        for breakpoint_str, java_ver in _VERSION_MAP:
            if mc >= Version(breakpoint_str):
                return java_ver
        return 8

    async def get_java_path(self, mc_version: str) -> Path:
        """
        Return the absolute path to the ``java`` executable suitable for
        *mc_version*, downloading the JDK first if it is not already present.

        :raises RuntimeError: If the JDK cannot be downloaded or extracted.
        """
        java_ver = self.required_java_version(mc_version)
        java_dir = self._java_dir(java_ver)
        executable = self._executable_path(java_dir)

        if executable.exists():
            java_logger.info("Java %d already present at %s", java_ver, executable)
            return executable.resolve()

        java_logger.info(
            "Java %d not found locally – downloading Temurin JDK…", java_ver
        )
        await self._download_jdk(java_ver, java_dir)

        if not executable.exists():
            raise RuntimeError(
                f"Java executable not found at {executable} after extraction."
            )
        return executable.resolve()

    def is_installed(self, java_version: int) -> bool:
        """Return *True* if the given Java version is already installed locally."""
        return self._executable_path(self._java_dir(java_version)).exists()

    # ------------------------------------------------------------------
    # Internal helpers (sync, path-only)
    # ------------------------------------------------------------------

    def _java_dir(self, java_version: int) -> Path:
        return self.BASE_DIR / f"java{java_version}"

    def _executable_path(self, java_dir: Path) -> Path:
        binary = "java.exe" if self._system == "windows" else "java"
        return java_dir / "bin" / binary

    def _build_download_url(self, java_version: int) -> str:
        return self.ADOPTIUM_URL.format(
            version=java_version,
            os=self._adoptium_os,
            arch=self._adoptium_arch,
        )

    # ------------------------------------------------------------------
    # Download + extraction (async, non-blocking)
    # ------------------------------------------------------------------

    async def _download_jdk(self, java_version: int, dest_dir: Path) -> None:
        """Download the Temurin JDK archive and extract it into *dest_dir*."""
        url = self._build_download_url(java_version)
        archive_ext = "zip" if self._system == "windows" else "tar.gz"
        archive_path = self.BASE_DIR / f"jdk{java_version}.{archive_ext}"

        java_logger.info("Downloading Java %d from %s", java_version, url)
        async with aiohttp.ClientSession() as session:
            await self._stream_download(url, archive_path, session)

        java_logger.info("Extracting %s → %s", archive_path, dest_dir)
        # Run the blocking extraction in a thread pool so the loop stays free
        await asyncio.get_event_loop().run_in_executor(
            None, self._extract_archive, archive_path, dest_dir, archive_ext
        )

        archive_path.unlink(missing_ok=True)
        java_logger.info("Java %d ready at %s", java_version, dest_dir)

    async def _stream_download(
        self,
        url: str,
        dest: Path,
        session: aiohttp.ClientSession,
    ) -> None:
        """Download *url* to *dest* with a rich progress bar (follows redirects)."""
        dest.parent.mkdir(parents=True, exist_ok=True)

        async with session.get(url, allow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))

            with Progress(
                *Progress.get_default_columns(),
                DownloadColumn(),
                TransferSpeedColumn(),
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Downloading Java {dest.stem}…", total=total or None
                )
                async with aiofiles.open(dest, "wb") as fh:
                    async for chunk in resp.content.iter_chunked(65_536):
                        if chunk:
                            await fh.write(chunk)
                            progress.update(task, advance=len(chunk))

        java_logger.info("Download complete: %s (%d bytes)", dest, dest.stat().st_size)

    # ------------------------------------------------------------------
    # Blocking extraction — always run via run_in_executor
    # ------------------------------------------------------------------

    def _extract_archive(
        self, archive_path: Path, dest_dir: Path, archive_ext: str
    ) -> None:
        """
        Extract the JDK archive into *dest_dir*, flattening the top-level
        root folder that Adoptium bundles.

        This method is intentionally synchronous; call it via
        ``run_in_executor`` to keep the event loop free.
        """
        tmp_dir = dest_dir.parent / f"_tmp_jdk_{dest_dir.name}"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)

        try:
            if archive_ext == "tar.gz":
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(tmp_dir)
            else:
                with zipfile.ZipFile(archive_path) as zf:
                    zf.extractall(tmp_dir)

            roots = [p for p in tmp_dir.iterdir() if p.is_dir()]
            if len(roots) != 1:
                raise RuntimeError(
                    f"Expected 1 root directory in JDK archive, found: {roots}"
                )
            jdk_root = roots[0]
            java_logger.debug("JDK root inside archive: %s", jdk_root.name)

            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.move(str(jdk_root), str(dest_dir))

        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

        if self._system != "windows":
            self._mark_executable(dest_dir)

    @staticmethod
    def _mark_executable(java_dir: Path) -> None:
        for sub in ("bin", "lib"):
            target = java_dir / sub
            if not target.exists():
                continue
            for path in target.rglob("*"):
                if path.is_file():
                    path.chmod(
                        path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )
        java_logger.debug(
            "chmod +x applied under %s/bin and %s/lib", java_dir, java_dir
        )


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------
async def main():
    manager = JavaManager()

    test_cases = [
        ("1.8.9", 8),
        ("1.12.2", 8),
        ("1.16.5", 8),
        ("1.17", 17),
        ("1.17.1", 17),
        ("1.18", 17),
        ("1.20.4", 17),
        ("1.20.5", 21),
        ("1.21", 21),
        ("26.1", 25),
    ]

    print("\n[bold cyan]Java Version Mapping Check[/bold cyan]")
    all_ok = True
    for mc_ver, expected in test_cases:
        got = manager.required_java_version(mc_ver)
        ok = got == expected
        colour = "green" if ok else "red"
        mark = "✓" if ok else "✗"
        print(
            f"  [{colour}]{mark}[/{colour}] MC {mc_ver:>8}  →  Java {got}  (expected {expected})"
        )
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("[green]All mappings correct.[/green]")
    else:
        print("[red]Some mappings are wrong![/red]")

    # Uncomment to test an actual download:
    # java_path = await manager.get_java_path("1.20.6")
    # print(f"\n[green]Java executable: {java_path}[/green]")


if __name__ == "__main__":
    asyncio.run(main())
