"""Text-to-speech with edge-tts (neural voices, free)."""
import os
import asyncio
import tempfile
import threading
import subprocess
import sys
import edge_tts

VOICE = os.getenv("TTS_VOICE", "pt-BR-AntonioNeural")
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"


def _play_mp3(path: str):
    """Play MP3 using the best available method for the platform."""
    try:
        # Try playsound first
        from playsound import playsound
        playsound(path, block=True)
        return
    except Exception:
        pass

    # Windows fallback: PowerShell
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["powershell", "-c",
                 f"(New-Object Media.SoundPlayer '{path}').PlaySync()"],
                timeout=30, capture_output=True
            )
            return
        except Exception:
            pass
        # Windows Media Player fallback
        try:
            subprocess.run(["wmplayer", "/play", "/close", path],
                           timeout=30, capture_output=True)
            return
        except Exception:
            pass

    # Linux/Mac fallback
    for player in ["mpg123", "mpg321", "ffplay", "afplay"]:
        try:
            subprocess.run([player, "-q", path], timeout=30, capture_output=True)
            return
        except FileNotFoundError:
            continue


async def speak_async(text: str):
    if not TTS_ENABLED or not text.strip():
        return

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name

    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(tmp)
        await asyncio.get_event_loop().run_in_executor(None, _play_mp3, tmp)
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def speak(text: str):
    """Fire-and-forget TTS in a background thread."""
    def _run():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(speak_async(text))
        loop.close()
    threading.Thread(target=_run, daemon=True).start()


def set_voice(voice: str):
    global VOICE
    VOICE = voice
