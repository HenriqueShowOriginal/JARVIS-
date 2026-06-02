"""Wake word detection + speech-to-text. pyaudio is optional."""
import os
import threading
from typing import Callable, Optional

WAKE_WORD = os.getenv("WAKE_WORD", "jarvis").lower()
WAKE_WORD_ENABLED = os.getenv("WAKE_WORD_ENABLED", "true").lower() == "true"

# Check if audio input is available
try:
    import speech_recognition as sr
    import pyaudio  # noqa — just checking availability
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

_stop_event = threading.Event()


def listen_once(timeout: int = 5) -> Optional[str]:
    if not AUDIO_AVAILABLE:
        return None
    try:
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
        return recognizer.recognize_google(audio, language="pt-BR")
    except Exception:
        return None


def start_wake_word_listener(on_wake: Callable[[], None]):
    if not WAKE_WORD_ENABLED or not AUDIO_AVAILABLE:
        return None

    def _loop():
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        while not _stop_event.is_set():
            try:
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=4)
                text = recognizer.recognize_google(audio, language="pt-BR").lower()
                if WAKE_WORD in text:
                    on_wake()
            except Exception:
                pass

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread


def stop_listener():
    _stop_event.set()


def is_audio_available() -> bool:
    return AUDIO_AVAILABLE
