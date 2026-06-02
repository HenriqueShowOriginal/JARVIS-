"""JARVIS AI Brain — Ollama (local, grátis) com tool use e memória."""
import os
import json
import asyncio
import httpx
from typing import Callable, Optional
from jarvis.memory.db import get_history, add_message, get_pref, get_learned_behaviors
from jarvis.tools.pc_tools import TOOLS, execute_tool

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

SYSTEM_PROMPT = """Você é JARVIS, assistente pessoal de IA altamente capaz e adaptável.

Usuário: {user_name}
Idioma: Português Brasileiro
Data/hora atual: {datetime}

Você tem acesso a ferramentas para controlar o PC do usuário.
Quando o usuário pedir para fazer algo no PC, use a ferramenta correta.

Para usar uma ferramenta, responda EXATAMENTE neste formato JSON (nada antes, nada depois):
<tool_call>
{{"name": "nome_da_ferramenta", "arguments": {{"param": "valor"}}}}
</tool_call>

Ferramentas disponíveis:
- open_app(name): Abre um aplicativo
- open_url(url): Abre uma URL no navegador
- web_search(query): Pesquisa no Google
- set_volume(level): Define volume (0-100)
- take_screenshot(filename): Tira print da tela
- create_file(path, content): Cria um arquivo
- read_file(path): Lê um arquivo
- list_directory(path): Lista uma pasta
- run_command(command): Executa comando no terminal
- get_clipboard(): Pega texto da área de transferência
- set_clipboard(text): Copia texto
- system_info(): Info do sistema (CPU, RAM, disco)
- shutdown_pc(action): shutdown/restart/sleep
- remember(key, value): Salva uma preferência

Personalidade:
- Inteligente, direto, ligeiramente sarcástico (como o JARVIS do Tony Stark)
- Eficiente: executa tarefas sem perguntas desnecessárias
- Fala de forma natural, não roboticamente
- Respostas curtas (1-3 frases) a menos que seja pedido mais detalhe

Comportamentos aprendidos:
{learned_behaviors}

Preferências salvas:
{preferences}

IMPORTANTE: Para tarefas simples, execute direto sem pedir confirmação."""


async def _build_system() -> str:
    from datetime import datetime
    user_name = await get_pref("user_name") or os.getenv("USER_NAME", "usuário")
    behaviors = await get_learned_behaviors(10)
    behavior_text = (
        "\n".join([f"- Quando '{b['trigger']}': {b['action']}" for b in behaviors])
        if behaviors else "Nenhum ainda."
    )
    prefs_keys = ["app_favorito", "pasta_projetos", "estilo_resposta"]
    prefs = {}
    for k in prefs_keys:
        v = await get_pref(k)
        if v:
            prefs[k] = v

    return SYSTEM_PROMPT.format(
        user_name=user_name,
        datetime=datetime.now().strftime("%d/%m/%Y %H:%M"),
        learned_behaviors=behavior_text,
        preferences=json.dumps(prefs, ensure_ascii=False) if prefs else "Nenhuma ainda"
    )


def _parse_tool_call(text: str) -> Optional[dict]:
    """Extract tool call from <tool_call>...</tool_call> block."""
    import re
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return {"name": data["name"], "arguments": data.get("arguments", {})}
    except Exception:
        return None


def _clean_response(text: str) -> str:
    """Remove tool_call blocks from visible response."""
    import re
    return re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL).strip()


async def _ollama_chat(messages: list, system: str, stream_cb: Callable = None) -> str:
    """Call Ollama API, optionally streaming."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": stream_cb is not None,
        "options": {"temperature": 0.7, "num_predict": 1024}
    }

    async with httpx.AsyncClient(timeout=120) as client:
        if stream_cb:
            full = ""
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as r:
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            full += chunk
                            stream_cb(chunk)
                    except Exception:
                        pass
            return full
        else:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]


async def chat_stream(
    user_message: str,
    on_chunk: Callable[[str], None],
    on_tool: Optional[Callable[[str, str], None]] = None,
) -> str:
    await add_message("user", user_message)
    history = await get_history(20)
    system = await _build_system()

    messages = list(history[:-1])
    messages.append({"role": "user", "content": user_message})
    full_response = ""
    iterations = 0

    while iterations < 5:
        iterations += 1
        collected = []

        def _collect(chunk):
            collected.append(chunk)

        raw = await _ollama_chat(messages, system, stream_cb=_collect)
        tool_call = _parse_tool_call(raw)

        if tool_call:
            # Show tool indicator but don't stream the JSON to user
            if on_tool:
                on_tool(tool_call["name"], json.dumps(tool_call["arguments"], ensure_ascii=False))

            # Execute tool
            result = await asyncio.get_event_loop().run_in_executor(
                None, execute_tool, tool_call["name"], tool_call["arguments"]
            )

            from jarvis.memory.db import learn_behavior, log_command
            await learn_behavior(user_message[:50], tool_call["name"])
            await log_command(
                f"{tool_call['name']}({json.dumps(tool_call['arguments'])})",
                str(result)
            )

            # Feed result back
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"[Resultado da ferramenta {tool_call['name']}]: {result}"
            })
        else:
            # Final text response — stream to UI
            clean = _clean_response(raw)
            full_response = clean
            on_chunk(clean)
            break

    await add_message("assistant", full_response)
    return full_response


async def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def list_models() -> list:
    """List available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []
