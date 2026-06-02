import aiosqlite
import json
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "data/jarvis.db")


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                display_name TEXT,
                message_count INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT,
                is_banned INTEGER DEFAULT 0,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                content TEXT,
                timestamp TEXT,
                was_responded INTEGER DEFAULT 0,
                sentiment TEXT DEFAULT 'neutral'
            );

            CREATE TABLE IF NOT EXISTS streamer_profile (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS game_scores (
                username TEXT,
                game TEXT,
                score INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                PRIMARY KEY (username, game)
            );

            CREATE TABLE IF NOT EXISTS topics (
                topic TEXT PRIMARY KEY,
                frequency INTEGER DEFAULT 1,
                last_mentioned TEXT
            );
        """)
        await db.commit()


async def get_or_create_user(username: str, display_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "INSERT INTO users (username, display_name, first_seen, last_seen) VALUES (?, ?, ?, ?)",
                (username, display_name or username, now, now)
            )
            await db.commit()
            return {"username": username, "display_name": display_name, "message_count": 0, "first_seen": now}
        cols = ["username", "display_name", "message_count", "first_seen", "last_seen", "is_banned", "notes"]
        return dict(zip(cols, row))


async def update_user_activity(username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET message_count = message_count + 1, last_seen = ? WHERE username = ?",
            (datetime.utcnow().isoformat(), username)
        )
        await db.commit()


async def log_message(username: str, content: str, sentiment: str = "neutral"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (username, content, timestamp, sentiment) VALUES (?, ?, ?, ?)",
            (username, content, datetime.utcnow().isoformat(), sentiment)
        )
        await db.commit()


async def get_recent_messages(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT username, content, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"username": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]


async def set_streamer_profile(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO streamer_profile (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.utcnow().isoformat())
        )
        await db.commit()


async def get_streamer_profile(key: str) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM streamer_profile WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else None


async def update_topic_frequency(topic: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO topics (topic, frequency, last_mentioned)
            VALUES (?, 1, ?)
            ON CONFLICT(topic) DO UPDATE SET frequency = frequency + 1, last_mentioned = ?
        """, (topic, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        await db.commit()


async def get_top_topics(limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT topic, frequency FROM topics ORDER BY frequency DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"topic": r[0], "frequency": r[1]} for r in rows]


async def update_game_score(username: str, game: str, score_delta: int = 0, win: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO game_scores (username, game, score, wins)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username, game) DO UPDATE SET
                score = score + ?,
                wins = wins + ?
        """, (username, game, score_delta, 1 if win else 0, score_delta, 1 if win else 0))
        await db.commit()


async def get_game_leaderboard(game: str, limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT username, score, wins FROM game_scores WHERE game = ? ORDER BY score DESC LIMIT ?",
            (game, limit)
        ) as cursor:
            rows = await cursor.fetchall()
    return [{"username": r[0], "score": r[1], "wins": r[2]} for r in rows]
