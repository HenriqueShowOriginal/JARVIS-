#!/usr/bin/env python3
"""JARVIS - AI Stream Assistant"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

load_dotenv()

console = Console()


def check_env():
    required = ["ANTHROPIC_API_KEY", "TWITCH_BOT_TOKEN", "TWITCH_CHANNELS"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        console.print(f"[red]Variáveis de ambiente faltando: {', '.join(missing)}[/red]")
        console.print("[yellow]Copie .env.example para .env e preencha os valores.[/yellow]")
        sys.exit(1)


def main():
    console.print(Panel(
        Text("JARVIS - AI Stream Assistant", justify="center", style="bold cyan"),
        subtitle="Powered by Claude AI",
        border_style="cyan"
    ))

    check_env()

    console.print("[green]✓ Configuração OK[/green]")
    console.print(f"[cyan]Canal(is): {os.getenv('TWITCH_CHANNELS')}[/cyan]")
    console.print(f"[cyan]TTS: {os.getenv('TTS_ENABLED', 'true')}[/cyan]")
    console.print(f"[cyan]Moderação: {os.getenv('AUTO_MODERATION', 'true')}[/cyan]")
    console.print("[yellow]Iniciando bot...[/yellow]\n")

    from src.twitch.bot import run
    run()


if __name__ == "__main__":
    main()
