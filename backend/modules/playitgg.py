import os
import platform
import sys
from pathlib import Path

import httpx

def get_playit_binary_name() -> str:
    os_name = platform.system().lower()
    arch = platform.machine().lower()

    if os_name == "windows":
        return "playit-windows-x86_64.exe"
    elif os_name == "linux":
        if "arm" in arch or "aarch64" in arch:
            return "playit-linux-aarch64" # For Raspberry Pi 4/5
        return "playit-linux-amd64"
    else:
        raise OSError(f"Unsupported OS: {os_name}")

async def download_playit(target_dir: Path):
    binary_name = get_playit_binary_name()
    target_path = target_dir / binary_name
    
    if target_path.exists():
        return target_path # Already downloaded

    # 1. Get the latest release info from GitHub
    repo = "playit-cloud/playit-agent"
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(api_url)
        resp.raise_for_status()
        assets = resp.json().get("assets", [])
        
        # 2. Find the asset that matches our binary name
        download_url = next((a["browser_download_url"] for a in assets if a["name"] == binary_name), None)
        
        if not download_url:
            raise FileNotFoundError(f"Could not find binary {binary_name} in GitHub releases.")

        # 3. Download the file
        print(f"Downloading playit from {download_url}...")
        file_resp = await client.get(download_url)
        target_path.write_bytes(file_resp.content)
        
        # 4. Make it executable (Critical for Linux!)
        if platform.system().lower() != "windows":
            os.chmod(target_path, 0o755)
            
    return target_path