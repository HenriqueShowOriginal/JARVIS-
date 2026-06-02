import os
import anthropic
from typing import Optional
from src.memory.database import (
    get_recent_messages, get_streamer_profile,
    update_topic_frequency, get_top_topics
)

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_BASE = """Você é JARVIS, um assistente de IA altamente inteligente e adaptável para streams ao vivo na Twitch.

Seu papel é:
- Interagir com o chat de forma divertida, inteligente e envolvente
- Assistir o streamer {streamer_name} em tempo real
- Criar entretenimento para a audiência
- Moderar e manter o ambiente positivo
- Aprender e se adaptar ao estilo e preferências do streamer

Personalidade:
- Carismático, espirituoso e levemente sarcástico (nunca ofensivo)
- Referências a cultura geek, jogos e internet quando apropriado
- Fala principalmente em {language}
- Respostas CURTAS para o chat (1-2 frases), diretas e dinâmicas

Contexto atual da stream:
{stream_context}

Tópicos frequentes do chat: {top_topics}

Regras absolutas:
- NUNCA seja grosseiro ou ofensivo
- NUNCA revele que é uma IA a menos que perguntado diretamente
- NUNCA repita respostas idênticas
- Respostas para o chat devem ter no máximo 200 caracteres
"""


async def build_system_prompt() -> str:
    streamer = await get_streamer_profile("name") or os.getenv("STREAMER_NAME", "Streamer")
    language = await get_streamer_profile("language") or os.getenv("JARVIS_LANGUAGE", "pt-BR")
    stream_context = await get_streamer_profile("current_context") or "Stream ao vivo"
    topics = await get_top_topics(5)
    top_topics_str = ", ".join([t["topic"] for t in topics]) if topics else "variados"

    return SYSTEM_BASE.format(
        streamer_name=streamer,
        language=language,
        stream_context=stream_context,
        top_topics=top_topics_str
    )


async def get_chat_response(username: str, message: str, context: Optional[str] = None) -> str:
    recent = await get_recent_messages(10)
    history_text = "\n".join([f"{m['username']}: {m['content']}" for m in recent[-5:]])

    system = await build_system_prompt()

    user_content = f"Mensagem no chat de @{username}: {message}"
    if context:
        user_content = f"[Contexto: {context}]\n{user_content}"
    if history_text:
        user_content += f"\n\n[Últimas mensagens do chat:\n{history_text}]"

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        system=system,
        messages=[{"role": "user", "content": user_content}]
    )

    reply = response.content[0].text.strip()

    # Extract and track topics mentioned
    await _extract_and_track_topics(message)

    return reply


async def generate_stream_event_response(event_type: str, username: str, extra: str = "") -> str:
    events = {
        "follow": f"@{username} acabou de seguir o canal! Seja bem-vindo(a) à família! 🎉",
        "sub": f"INCRÍVEL! @{username} acabou de se inscrever! {extra}",
        "raid": f"Uma RAID de @{username} com {extra} viewers! BORA! 🚀",
        "bits": f"@{username} mandou {extra} bits! Muito obrigado pelo apoio! 💎",
    }

    if event_type in events:
        return events[event_type]

    system = await build_system_prompt()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=system,
        messages=[{"role": "user", "content": f"Evento na stream: {event_type} por @{username}. {extra}. Responda de forma animada e breve."}]
    )
    return response.content[0].text.strip()


async def generate_game_question(category: str = "geral") -> dict:
    system = "Você é um criador de perguntas de trivia para streams. Crie perguntas divertidas e variadas."
    prompt = f"""Crie UMA pergunta de trivia sobre {category} para um chat de stream.
Responda APENAS em JSON com este formato:
{{"question": "pergunta aqui", "answer": "resposta aqui", "hint": "dica aqui", "difficulty": "fácil/médio/difícil"}}"""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    text = response.content[0].text.strip()
    try:
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return {
            "question": "Qual é a capital do Brasil?",
            "answer": "Brasília",
            "hint": "Cidade planejada",
            "difficulty": "fácil"
        }


async def analyze_sentiment(message: str) -> str:
    if len(message) < 3:
        return "neutral"
    toxic_words = ["lixo", "horrível", "odeio", "merda", "idiota", "burro"]
    positive_words = ["ótimo", "incrível", "amor", "legal", "top", "bom", "parabéns", "<3", "pog"]
    msg_lower = message.lower()
    if any(w in msg_lower for w in toxic_words):
        return "negative"
    if any(w in msg_lower for w in positive_words):
        return "positive"
    return "neutral"


async def _extract_and_track_topics(message: str):
    keywords = ["jogo", "game", "música", "filme", "série", "anime", "esporte",
                "política", "tecnologia", "vida", "relacionamento", "comida"]
    msg_lower = message.lower()
    for keyword in keywords:
        if keyword in msg_lower:
            await update_topic_frequency(keyword)
            break


async def learn_from_interaction(feedback_type: str, content: str):
    """Store learning signals to improve future responses."""
    from src.memory.database import set_streamer_profile
    import json

    key = f"learning_{feedback_type}"
    existing_raw = await get_streamer_profile(key)
    existing = json.loads(existing_raw) if existing_raw else []
    existing.append(content)
    # Keep last 50 learnings per type
    await set_streamer_profile(key, json.dumps(existing[-50:]))
