"""Self-update: pulls latest code from GitHub and restarts."""
import os
import sys
import json
import subprocess
import requests
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
VERSION_FILE = ROOT / "version.json"


def get_current_version() -> dict:
    with open(VERSION_FILE) as f:
        return json.load(f)


def check_for_update() -> dict | None:
    """Returns new version info if update available, else None."""
    try:
        info = get_current_version()
        repo = info["repo"]
        branch = info.get("branch", "main")
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/version.json"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        remote = r.json()
        if _version_newer(remote["version"], info["version"]):
            return remote
        return None
    except Exception:
        return None


def apply_update(on_progress=None) -> bool:
    """Pull latest code via git and restart."""
    try:
        if on_progress:
            on_progress("Baixando atualização...")
        result = subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            if on_progress:
                on_progress(f"Erro ao atualizar: {result.stderr}")
            return False

        if on_progress:
            on_progress("Instalando dependências...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=str(ROOT), timeout=120
        )

        if on_progress:
            on_progress("Reiniciando JARVIS...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return True
    except Exception as e:
        if on_progress:
            on_progress(f"Falha na atualização: {e}")
        return False


def _version_newer(remote: str, local: str) -> bool:
    def parts(v):
        return [int(x) for x in v.split(".")]
    return parts(remote) > parts(local)
