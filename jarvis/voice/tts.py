"""Text-to-speech with edge-tts (neural voices, free)."""
import os
import asyncio
import tempfile
import threading
import edge_tts
import pygame

VOICE = os.getenv("TTS_VOICE", "pt-BR-AntonioNeural")
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"

_queue: asyncio.Queue = None
_pygame_lock = threading.Lock()


def _init_pygame():
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)


async def speak_async(text: str):
    if not TTS_ENABLED or not text.strip():
        return
    _init_pygame()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name

    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(tmp)
        with _pygame_lock:
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
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
