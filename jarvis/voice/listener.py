"""Wake word detection + speech-to-text."""
import os
import threading
import speech_recognition as sr
from typing import Callable, Optional

WAKE_WORD = os.getenv("WAKE_WORD", "jarvis").lower()
WAKE_WORD_ENABLED = os.getenv("WAKE_WORD_ENABLED", "true").lower() == "true"

_recognizer = sr.Recognizer()
_mic = None
_listening = False
_stop_event = threading.Event()


def _get_mic():
    global _mic
    if _mic is None:
        _mic = sr.Microphone()
    return _mic


def listen_once(timeout: int = 5) -> Optional[str]:
    """Record audio and return transcribed text, or None on failure."""
    try:
        mic = _get_mic()
        with mic as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
        text = _recognizer.recognize_google(audio, language="pt-BR")
        return text
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print(f"[Voice] Erro: {e}")
        return None


def start_wake_word_listener(on_wake: Callable[[], None]):
    """Background thread that listens for wake word and calls on_wake()."""
    if not WAKE_WORD_ENABLED:
        return

    def _loop():
        global _listening
        mic = _get_mic()
        while not _stop_event.is_set():
            try:
                with mic as source:
                    _recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = _recognizer.listen(source, timeout=3, phrase_time_limit=4)
                text = _recognizer.recognize_google(audio, language="pt-BR").lower()
                if WAKE_WORD in text:
                    on_wake()
            except Exception:
                pass

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread


def stop_listener():
    _stop_event.set()
