#!/usr/bin/env python3
"""JARVIS — Personal AI Assistant"""
import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()


def check_setup():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n[JARVIS] Chave da API não encontrada!")
        print("1. Copie o arquivo .env.example para .env")
        print("2. Adicione sua ANTHROPIC_API_KEY")
        print("3. Execute novamente\n")
        sys.exit(1)


async def startup():
    from jarvis.memory.db import init
    await init()


def main():
    check_setup()

    # Initialize database
    asyncio.run(startup())

    # Launch GUI
    from jarvis.gui.window import JarvisWindow
    app = JarvisWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
