import os
import re
from better_profanity import profanity
from typing import Tuple

profanity.load_censor_words()

SEVERITY = {
    "spam": 1,
    "caps": 1,
    "repetition": 1,
    "mild_profanity": 2,
    "hate_speech": 3,
    "extreme": 3,
}

SPAM_PATTERNS = [
    r"(.)\1{6,}",           # repeated characters
    r"(https?://\S+\s*){3,}",  # multiple links
]

HATE_PATTERNS = [
    r"\b(racis|nazista|fascis|terroris)\w*\b",
]


def check_message(username: str, message: str) -> Tuple[bool, str, int]:
    """
    Returns (should_action, reason, severity_level)
    severity: 1=warn, 2=timeout, 3=ban
    """
    msg = message.strip()

    # Spam: too many caps
    if len(msg) > 10 and sum(1 for c in msg if c.isupper()) / len(msg) > 0.8:
        return True, "caps_spam", 1

    # Spam patterns
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            return True, "spam_pattern", 1

    # Profanity check
    if profanity.contains_profanity(msg):
        return True, "profanity", 2

    # Hate speech
    for pattern in HATE_PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            return True, "hate_speech", 3

    return False, "", 0


def get_action_for_severity(severity: int) -> str:
    actions = {1: "warn", 2: "timeout", 3: "ban"}
    return actions.get(severity, "warn")


def build_warning_message(username: str, reason: str) -> str:
    messages = {
        "caps_spam": f"@{username} Por favor, evite escrever tudo em maiúsculas!",
        "spam_pattern": f"@{username} Sem spam no chat, por favor!",
        "profanity": f"@{username} Linguagem inapropriada não é permitida aqui!",
        "hate_speech": f"@{username} Discurso de ódio não é tolerado neste canal.",
    }
    return messages.get(reason, f"@{username} Por favor, siga as regras do chat!")
