#!/usr/bin/env python3
"""JARVIS — Personal AI Assistant (Ollama local)"""
import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def startup():
    from jarvis.memory.db import init
    await init()

    from jarvis.brain.ai import check_ollama, list_models
    if not await check_ollama():
        print("\n" + "="*50)
        print("  OLLAMA NÃO ESTÁ RODANDO!")
        print("="*50)
        print("\n1. Baixe o Ollama em: https://ollama.com/download")
        print("2. Instale e abra o Ollama")
        print("3. Abra um terminal e rode:")
        print("   ollama pull llama3.1:8b")
        print("4. Inicie o JARVIS novamente\n")
        input("Pressione Enter para sair...")
        sys.exit(1)

    models = await list_models()
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    if models and not any(model in m for m in models):
        print(f"\n⚠ Modelo '{model}' não encontrado.")
        print(f"Modelos disponíveis: {', '.join(models)}")
        print(f"\nRode: ollama pull {model}\n")
        input("Pressione Enter para sair...")
        sys.exit(1)

    print(f"[JARVIS] Ollama OK — modelo: {model}")


def main():
    asyncio.run(startup())
    from jarvis.gui.window import JarvisWindow
    app = JarvisWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
