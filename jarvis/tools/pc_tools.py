"""Tools JARVIS can use to control the PC."""
import os
import sys
import subprocess
import platform
import webbrowser
import pyautogui
import psutil
import pyperclip
from datetime import datetime
from pathlib import Path
from typing import Any

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"


# ── Tool definitions for Claude ────────────────────────────────

TOOLS = [
    {
        "name": "open_app",
        "description": "Abre um aplicativo no PC do usuário pelo nome.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nome do aplicativo (ex: 'spotify', 'chrome', 'notepad', 'vscode')"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "open_url",
        "description": "Abre uma URL no navegador padrão.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL completa a abrir"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "web_search",
        "description": "Pesquisa algo no Google e abre no navegador.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "set_volume",
        "description": "Define o volume do sistema (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Nível de volume de 0 a 100"}
            },
            "required": ["level"]
        }
    },
    {
        "name": "take_screenshot",
        "description": "Tira uma captura de tela e salva.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Nome do arquivo (opcional, padrão: timestamp)"}
            }
        }
    },
    {
        "name": "create_file",
        "description": "Cria ou sobrescreve um arquivo com o conteúdo especificado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do arquivo"},
                "content": {"type": "string", "description": "Conteúdo do arquivo"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Lê o conteúdo de um arquivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do arquivo"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_directory",
        "description": "Lista arquivos e pastas em um diretório.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho da pasta (padrão: desktop)"}
            }
        }
    },
    {
        "name": "run_command",
        "description": "Executa um comando do terminal/shell.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Comando a executar"},
                "capture_output": {"type": "boolean", "description": "Se deve retornar a saída do comando"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "get_clipboard",
        "description": "Obtém o texto atualmente na área de transferência.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "set_clipboard",
        "description": "Copia texto para a área de transferência.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Texto a copiar"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "system_info",
        "description": "Retorna informações do sistema: CPU, memória, disco.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "shutdown_pc",
        "description": "Desliga ou reinicia o PC.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["shutdown", "restart", "sleep"], "description": "Ação a executar"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "remember",
        "description": "Salva uma preferência ou informação importante para lembrar no futuro.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Nome da informação"},
                "value": {"type": "string", "description": "Valor a lembrar"}
            },
            "required": ["key", "value"]
        }
    },
]


# ── Executors ──────────────────────────────────────────────────

def _get_desktop() -> str:
    return str(Path.home() / "Desktop")


def execute_tool(name: str, inputs: dict) -> Any:
    try:
        if name == "open_app":
            return _open_app(inputs["name"])
        elif name == "open_url":
            return _open_url(inputs["url"])
        elif name == "web_search":
            query = inputs["query"].replace(" ", "+")
            return _open_url(f"https://www.google.com/search?q={query}")
        elif name == "set_volume":
            return _set_volume(inputs["level"])
        elif name == "take_screenshot":
            return _take_screenshot(inputs.get("filename"))
        elif name == "create_file":
            return _create_file(inputs["path"], inputs["content"])
        elif name == "read_file":
            return _read_file(inputs["path"])
        elif name == "list_directory":
            return _list_directory(inputs.get("path", _get_desktop()))
        elif name == "run_command":
            return _run_command(inputs["command"], inputs.get("capture_output", True))
        elif name == "get_clipboard":
            return pyperclip.paste()
        elif name == "set_clipboard":
            pyperclip.copy(inputs["text"])
            return "Copiado para a área de transferência."
        elif name == "system_info":
            return _system_info()
        elif name == "shutdown_pc":
            return _shutdown(inputs["action"])
        elif name == "remember":
            import asyncio
            from jarvis.memory.db import set_pref
            asyncio.get_event_loop().run_until_complete(set_pref(inputs["key"], inputs["value"]))
            return f"Lembrado: {inputs['key']} = {inputs['value']}"
        else:
            return f"Ferramenta desconhecida: {name}"
    except Exception as e:
        return f"Erro ao executar {name}: {e}"


def _open_app(name: str) -> str:
    apps_windows = {
        "spotify": "spotify", "chrome": "chrome", "firefox": "firefox",
        "notepad": "notepad", "vscode": "code", "explorer": "explorer",
        "calculadora": "calc", "terminal": "cmd", "discord": "discord",
        "steam": "steam", "obs": "obs64",
    }
    apps_linux = {
        "spotify": "spotify", "chrome": "google-chrome", "firefox": "firefox",
        "vscode": "code", "terminal": "x-terminal-emulator", "discord": "discord",
        "nautilus": "nautilus", "calculadora": "gnome-calculator",
    }

    app_map = apps_windows if IS_WINDOWS else apps_linux
    cmd = app_map.get(name.lower(), name)

    try:
        if IS_WINDOWS:
            subprocess.Popen(cmd, shell=True)
        else:
            subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Abrindo {name}..."
    except Exception as e:
        return f"Não consegui abrir {name}: {e}"


def _open_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Abrindo {url}"


def _set_volume(level: int) -> str:
    level = max(0, min(100, level))
    if IS_WINDOWS:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        except ImportError:
            subprocess.run(f'nircmd.exe setsysvolume {int(level * 655.35)}', shell=True)
    elif IS_LINUX:
        subprocess.run(f"amixer -q sset Master {level}%", shell=True)
    elif IS_MAC:
        subprocess.run(f"osascript -e 'set volume output volume {level}'", shell=True)
    return f"Volume definido para {level}%"


def _take_screenshot(filename: str = None) -> str:
    if not filename:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = str(Path.home() / "Desktop" / filename)
    img = pyautogui.screenshot()
    img.save(path)
    return f"Screenshot salvo em: {path}"


def _create_file(path: str, content: str) -> str:
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Arquivo criado: {path}"


def _read_file(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"Arquivo não encontrado: {path}"
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read(10000)
    return content


def _list_directory(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"Pasta não encontrada: {path}"
    items = os.listdir(path)
    dirs = [f"📁 {i}" for i in items if os.path.isdir(os.path.join(path, i))]
    files = [f"📄 {i}" for i in items if os.path.isfile(os.path.join(path, i))]
    return "\n".join(dirs + files) or "Pasta vazia"


def _run_command(command: str, capture: bool = True) -> str:
    result = subprocess.run(
        command, shell=True, capture_output=capture,
        text=True, timeout=30
    )
    if capture:
        return (result.stdout + result.stderr).strip() or "Comando executado."
    return "Comando executado."


def _system_info() -> str:
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return (
        f"CPU: {cpu}% | "
        f"RAM: {mem.percent}% ({mem.used // 1024**3}GB/{mem.total // 1024**3}GB) | "
        f"Disco: {disk.percent}% ({disk.used // 1024**3}GB/{disk.total // 1024**3}GB)"
    )


def _shutdown(action: str) -> str:
    if action == "shutdown":
        cmd = "shutdown /s /t 5" if IS_WINDOWS else "shutdown -h now"
    elif action == "restart":
        cmd = "shutdown /r /t 5" if IS_WINDOWS else "reboot"
    elif action == "sleep":
        cmd = "rundll32.exe powrprof.dll,SetSuspendState 0,1,0" if IS_WINDOWS else "systemctl suspend"
    else:
        return "Ação inválida."
    subprocess.run(cmd, shell=True)
    return f"Executando {action}..."
