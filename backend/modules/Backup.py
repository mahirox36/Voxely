import asyncio
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.ServerService import ServerInstance

logger = logging.getLogger("negomi.backups")


class BackupManager:
    def __init__(self, server_instance: "ServerInstance", backup_limit: int = 5):
        self.server = server_instance
        self.backup_root = server_instance.path / "backups"
        self.backup_limit = backup_limit
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.logger = self.server.logger.getChild("backup")

    async def create_backup(self):
        """Main entry point for the backup task."""
        try:
            self.logger.info(f"Starting backup for {self.server.config.name}...")
            await self.server.emit(
                "backup.started", {"timestamp": datetime.now().isoformat()}
            )
            if self.server.status == "running":
                await self.server.send_command("save-all flush")
                await self.server.send_command("save-off")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{timestamp}.tar.gz"
            dest_path = self.backup_root / filename

            await asyncio.to_thread(self._compress_files, dest_path)

            await self._rotate_backups()

            self.logger.info(
                f"Finished backup for {self.server.config.name}, file: {dest_path.name}"
            )
            await self.server.emit(
                "backup.created", {"filename": dest_path.name, "timestamp": timestamp}
            )

        finally:
            if self.server.status == "running":
                await self.server.send_command("save-on")

    def _compress_files(self, dest_path: Path):
        exclude_dirs = {"backups", "logs", "cache"}

        with tarfile.open(dest_path, "w:gz") as tar:
            for item in self.server.path.iterdir():
                if item.name not in exclude_dirs:
                    tar.add(item, arcname=item.name)

    async def _rotate_backups(self):
        """Delete oldest backups if we exceed the limit."""
        backups = sorted(
            self.backup_root.glob("*.tar.gz"), key=lambda x: x.stat().st_mtime
        )
        while len(backups) > self.backup_limit:
            old_backup = backups.pop(0)
            await asyncio.to_thread(old_backup.unlink)
            self.logger.info(f"Rotated old backup: {old_backup.name}")
    async def list_backups(self) -> list[dict[str, Any]]:
        """List existing backups with metadata."""
        backups = sorted(
            self.backup_root.glob("*.tar.gz"), key=lambda x: x.stat().st_mtime, reverse=True
        )
        return [
            {
                "filename": backup.name,
                "created_at": datetime.fromtimestamp(backup.stat().st_mtime).isoformat(),
                "size_mb": round(backup.stat().st_size / (1024 * 1024), 2),
            }
            for backup in backups
        ]
    
    async def restore_backup(self, filename: str):
        """Restore a backup by filename."""
        backup_path = self.backup_root / filename
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file {filename} not found")

        self.logger.info(f"Restoring backup {filename} for {self.server.config.name}...")
        await self.server.emit("backup.restoring", {"filename": filename, "timestamp": datetime.now().isoformat()})

        # Stop the server if it's running
        was_running = self.server.status == "running"
        if was_running:
            await self.server.stop(force=True)

        # Clear current server files (except backups)
        for item in self.server.path.iterdir():
            if item.name != "backups":
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Extract backup
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=self.server.path)

        self.logger.info(f"Restored backup {filename} for {self.server.config.name}")
        await self.server.emit("backup.restored", {"filename": filename, "timestamp": datetime.now().isoformat()})

        # Restart the server if it was running before
        if was_running:
            await self.server.start()