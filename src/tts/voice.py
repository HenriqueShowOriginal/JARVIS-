import asyncio
import os
import tempfile
import edge_tts
import pygame

VOICE = os.getenv("TTS_VOICE", "pt-BR-FranciscaNeural")
RATE = os.getenv("TTS_RATE", "+0%")
VOLUME = os.getenv("TTS_VOLUME", "+0%")
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"

_tts_queue: asyncio.Queue = None
_initialized = False


def init_tts():
    global _initialized
    if not _initialized:
        pygame.mixer.init()
        _initialized = True


async def _speak_text(text: str):
    if not TTS_ENABLED:
        return
    init_tts()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, volume=VOLUME)
        await communicate.save(tmp_path)

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def speak(text: str):
    """Queue a TTS message."""
    global _tts_queue
    if _tts_queue is None:
        _tts_queue = asyncio.Queue()
        asyncio.create_task(_tts_worker())
    await _tts_queue.put(text)


async def _tts_worker():
    global _tts_queue
    while True:
        text = await _tts_queue.get()
        try:
            await _speak_text(text)
        except Exception as e:
            print(f"[TTS Error] {e}")
        finally:
            _tts_queue.task_done()


def set_voice(voice_name: str):
    global VOICE
    VOICE = voice_name


AVAILABLE_VOICES = {
    "pt-BR-feminino": "pt-BR-FranciscaNeural",
    "pt-BR-masculino": "pt-BR-AntonioNeural",
    "en-US-feminino": "en-US-JennyNeural",
    "en-US-masculino": "en-US-GuyNeural",
    "jarvis": "en-US-GuyNeural",
}
