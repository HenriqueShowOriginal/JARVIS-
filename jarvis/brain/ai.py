"""JARVIS AI Brain — Claude with tool use, memory, and self-improvement."""
import os
import json
import asyncio
import anthropic
from typing import Callable, Optional, AsyncGenerator
from jarvis.memory.db import get_history, add_message, get_pref, get_learned_behaviors
from jarvis.tools.pc_tools import TOOLS, execute_tool

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Você é JARVIS, assistente pessoal de IA altamente capaz e adaptável.

Usuário: {user_name}
Idioma: Português Brasileiro
Data/hora atual: {datetime}

Você tem acesso a ferramentas para controlar o PC do usuário.

Personalidade:
- Inteligente, direto, ligeiramente sarcástico (como o JARVIS do Tony Stark)
- Eficiente: executa tarefas sem perguntas desnecessárias
- Aprende padrões: se o usuário sempre pede a mesma coisa, antecipe
- Fala de forma natural, não roboticamente

Comportamentos aprendidos do usuário:
{learned_behaviors}

Preferências salvas:
{preferences}

Regras:
- Execute ferramentas sempre que o usuário pedir para fazer algo no PC
- Respostas conversacionais curtas (1-3 frases)
- Se algo falhar, tente uma abordagem alternativa antes de desistir
- Nunca peça confirmação para tarefas simples — apenas execute
"""


async def _build_system() -> str:
    from datetime import datetime
    user_name = await get_pref("user_name") or os.getenv("USER_NAME", "usuário")
    behaviors = await get_learned_behaviors(10)
    behavior_text = (
        "\n".join([f"- Quando '{b['trigger']}': {b['action']}" for b in behaviors])
        if behaviors else "Nenhum ainda — aprendendo..."
    )
    prefs_keys = ["app_favorito", "pasta_projetos", "estilo_resposta", "hora_acorda"]
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


async def chat(
    user_message: str,
    on_text: Optional[Callable[[str], None]] = None,
    on_tool: Optional[Callable[[str, dict], None]] = None,
) -> str:
    """
    Send a message to JARVIS and get a response.
    Supports streaming via callbacks.
    """
    await add_message("user", user_message)

    history = await get_history(20)
    system = await _build_system()

    full_response = ""
    tool_results = []
    messages = list(history[:-1])  # exclude last (just added)
    messages.append({"role": "user", "content": user_message})

    # Agentic loop: keep going while JARVIS wants to use tools
    while True:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        assistant_content = []

        for block in response.content:
            if block.type == "text":
                full_response += block.text
                assistant_content.append({"type": "text", "text": block.text})
                if on_text:
                    on_text(block.text)

            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": tool_name,
                    "input": tool_input
                })

                if on_tool:
                    on_tool(tool_name, tool_input)

                # Execute the tool
                result = await asyncio.get_event_loop().run_in_executor(
                    None, execute_tool, tool_name, tool_input
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

                # Log learned behavior
                from jarvis.memory.db import learn_behavior, log_command
                await learn_behavior(user_message[:50], tool_name)
                await log_command(f"{tool_name}({json.dumps(tool_input)})", str(result))

        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "tool_use" and tool_results:
            messages.append({"role": "user", "content": tool_results})
            tool_results = []
        else:
            break

    await add_message("assistant", full_response)
    return full_response


async def chat_stream(
    user_message: str,
    on_chunk: Callable[[str], None],
    on_tool: Optional[Callable[[str, str], None]] = None,
) -> str:
    """Streaming version — calls on_chunk with each text chunk."""
    await add_message("user", user_message)
    history = await get_history(20)
    system = await _build_system()

    messages = list(history[:-1])
    messages.append({"role": "user", "content": user_message})
    full_response = ""

    while True:
        tool_calls = []
        assistant_content = []

        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            chunk = event.delta.text
                            full_response += chunk
                            on_chunk(chunk)

            final = await stream.get_final_message()

        for block in final.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
                tool_calls.append(block)

        messages.append({"role": "assistant", "content": assistant_content})

        if tool_calls:
            tool_results = []
            for tc in tool_calls:
                if on_tool:
                    on_tool(tc.name, json.dumps(tc.input, ensure_ascii=False))
                result = await asyncio.get_event_loop().run_in_executor(
                    None, execute_tool, tc.name, tc.input
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": str(result)
                })
                from jarvis.memory.db import learn_behavior, log_command
                await learn_behavior(user_message[:50], tc.name)
                await log_command(f"{tc.name}({json.dumps(tc.input)})", str(result))

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    await add_message("assistant", full_response)
    return full_response
