import os
import asyncio
from twitchio.ext import commands
from dotenv import load_dotenv

load_dotenv()

from src.ai.jarvis_brain import get_chat_response, generate_stream_event_response, analyze_sentiment
from src.memory.database import (
    init_db, get_or_create_user, update_user_activity,
    log_message, set_streamer_profile
)
from src.moderation.moderator import check_message, get_action_for_severity, build_warning_message
from src.tts.voice import speak
from src.games.trivia import start_trivia, check_answer, skip_trivia, get_trivia_leaderboard

CHANNELS = os.getenv("TWITCH_CHANNELS", "").split(",")
BOT_NICK = os.getenv("TWITCH_BOT_NICK", "JarvisBot")
AUTO_MOD = os.getenv("AUTO_MODERATION", "true").lower() == "true"
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"

# Rate limiting: max 1 AI response per 3 seconds
_last_response_time = 0
_response_cooldown = 3.0
_mention_cooldown = 1.5


class JarvisBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.getenv("TWITCH_BOT_TOKEN"),
            client_id=os.getenv("TWITCH_CLIENT_ID"),
            nick=BOT_NICK,
            prefix="!",
            initial_channels=CHANNELS,
        )

    async def event_ready(self):
        await init_db()
        print(f"[JARVIS] Online como {self.nick}")
        print(f"[JARVIS] Canais: {', '.join(CHANNELS)}")

        for channel_name in CHANNELS:
            channel = self.get_channel(channel_name.strip())
            if channel:
                await channel.send("JARVIS online. Sistemas operacionais. 🤖")

    async def event_message(self, message):
        if message.echo:
            return

        username = message.author.name.lower()
        display = message.author.display_name
        content = message.content

        # Update user memory
        await get_or_create_user(username, display)
        await update_user_activity(username)

        # Analyze sentiment
        sentiment = await analyze_sentiment(content)
        await log_message(username, content, sentiment)

        # Auto-moderation
        if AUTO_MOD:
            should_act, reason, severity = check_message(username, content)
            if should_act and severity > 0:
                warning = build_warning_message(display, reason)
                await message.channel.send(warning)
                if severity >= 2:
                    await message.channel.send(f"/timeout {username} {60 * severity}")
                if severity >= 3:
                    await message.channel.send(f"/ban {username}")
                return

        # Handle commands
        await self.handle_commands(message)

        # Respond to mentions
        bot_mentions = [BOT_NICK.lower(), "jarvis", "@jarvis"]
        is_mentioned = any(m in content.lower() for m in bot_mentions)

        if is_mentioned:
            await self._respond_to_mention(message, username, display, content)

    async def _respond_to_mention(self, message, username, display, content):
        global _last_response_time
        import time
        now = time.time()
        if now - _last_response_time < _mention_cooldown:
            return
        _last_response_time = now

        try:
            reply = await get_chat_response(display, content)
            await message.channel.send(f"@{display} {reply}")
            if TTS_ENABLED:
                await speak(f"{display} perguntou: {reply}")
        except Exception as e:
            print(f"[JARVIS Error] {e}")

    # ─── Commands ───────────────────────────────────────────────

    @commands.command(name="jarvis")
    async def cmd_jarvis(self, ctx: commands.Context):
        """Ask JARVIS anything."""
        query = ctx.message.content.replace("!jarvis", "").strip()
        if not query:
            await ctx.send(f"@{ctx.author.display_name} Como posso ajudar? Use: !jarvis <pergunta>")
            return
        reply = await get_chat_response(ctx.author.display_name, query)
        await ctx.send(f"@{ctx.author.display_name} {reply}")
        if TTS_ENABLED:
            await speak(reply)

    @commands.command(name="trivia")
    async def cmd_trivia(self, ctx: commands.Context):
        """Start a trivia game."""
        category = ctx.message.content.replace("!trivia", "").strip() or "geral"
        result = await start_trivia(category)
        await ctx.send(result)
        if TTS_ENABLED:
            await speak(result)

    @commands.command(name="resposta")
    async def cmd_answer(self, ctx: commands.Context):
        """Answer trivia question."""
        answer = ctx.message.content.replace("!resposta", "").strip()
        if not answer:
            return
        result = await check_answer(ctx.author.display_name, answer)
        if result:
            await ctx.send(result)
            if TTS_ENABLED and "acertou" in result:
                await speak(result)

    @commands.command(name="pular")
    async def cmd_skip(self, ctx: commands.Context):
        """Skip trivia."""
        result = await skip_trivia()
        await ctx.send(result)

    @commands.command(name="ranking")
    async def cmd_ranking(self, ctx: commands.Context):
        """Show trivia leaderboard."""
        result = await get_trivia_leaderboard()
        await ctx.send(result)

    @commands.command(name="sobre")
    async def cmd_about(self, ctx: commands.Context):
        """Info about JARVIS."""
        await ctx.send(
            "Sou o JARVIS 🤖 — IA de assistência para streams. "
            "Comandos: !jarvis, !trivia, !resposta, !ranking, !voz, !contexto"
        )

    @commands.command(name="voz")
    async def cmd_voice(self, ctx: commands.Context):
        """Change TTS voice (mods only)."""
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        from src.tts.voice import set_voice, AVAILABLE_VOICES
        voice_key = ctx.message.content.replace("!voz", "").strip()
        if voice_key in AVAILABLE_VOICES:
            set_voice(AVAILABLE_VOICES[voice_key])
            await ctx.send(f"Voz alterada para: {voice_key}")
        else:
            options = ", ".join(AVAILABLE_VOICES.keys())
            await ctx.send(f"Vozes disponíveis: {options}")

    @commands.command(name="contexto")
    async def cmd_context(self, ctx: commands.Context):
        """Set stream context (mods only)."""
        if not ctx.author.is_mod and not ctx.author.is_broadcaster:
            return
        context = ctx.message.content.replace("!contexto", "").strip()
        if context:
            await set_streamer_profile("current_context", context)
            await ctx.send(f"Contexto atualizado: {context}")

    @commands.command(name="aprenda")
    async def cmd_learn(self, ctx: commands.Context):
        """Teach JARVIS something (broadcaster only)."""
        if not ctx.author.is_broadcaster:
            return
        content = ctx.message.content.replace("!aprenda", "").strip()
        if content:
            from src.ai.jarvis_brain import learn_from_interaction
            await learn_from_interaction("broadcaster_input", content)
            await ctx.send(f"Aprendido! Vou lembrar disso. 🧠")

    # ─── Events ─────────────────────────────────────────────────

    async def event_follow(self, channel, user):
        msg = await generate_stream_event_response("follow", user.name)
        channel_obj = self.get_channel(channel.name)
        if channel_obj:
            await channel_obj.send(msg)
        if TTS_ENABLED:
            await speak(msg)

    async def event_subscription(self, channel, user, sub):
        msg = await generate_stream_event_response("sub", user.name, sub.tier or "Tier 1")
        channel_obj = self.get_channel(channel.name)
        if channel_obj:
            await channel_obj.send(msg)
        if TTS_ENABLED:
            await speak(msg)


def run():
    bot = JarvisBot()
    bot.run()
