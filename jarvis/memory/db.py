"""
JARVIS Memory — SQLite ultra-leve com auto-compressão.

Estratégia para economizar espaço:
- Histórico de conversa: máximo 500 mensagens (depois comprime antigas com IA)
- Preferências: chave-valor simples
- Comportamentos aprendidos: top 50 por frequência
- DB comprimido automaticamente com VACUUM

Tamanho esperado: < 5MB mesmo após meses de uso.
"""
import aiosqlite
import json
import os
from datetime import datetime
from typing import Optional, List

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/jarvis.db")

MAX_MESSAGES = 500       # máximo de mensagens guardadas
COMPACT_THRESHOLD = 450  # comprime quando chegar a este número


async def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA auto_vacuum=INCREMENTAL;

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_summary INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS learned_behaviors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(trigger, action)
            );

            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                result TEXT,
                success INTEGER DEFAULT 1,
                timestamp TEXT NOT NULL
            );
        """)
        await db.commit()
    await _maybe_compact()


async def add_message(role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content[:2000], datetime.utcnow().isoformat())  # truncate huge messages
        )
        await db.commit()
    await _maybe_compact()


async def get_history(limit: int = 20) -> List[dict]:
    """Returns last N messages for context window."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


async def set_pref(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
            (key, str(value)[:500], datetime.utcnow().isoformat())
        )
        await db.commit()


async def get_pref(key: str, default: str = None) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM preferences WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else default


async def learn_behavior(trigger: str, action: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO learned_behaviors (trigger, action, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(trigger, action) DO UPDATE SET
                usage_count = usage_count + 1,
                confidence = MIN(1.0, confidence + 0.05)
        """, (trigger[:100], action[:100], datetime.utcnow().isoformat()))
        # Keep only top 50 behaviors
        await db.execute("""
            DELETE FROM learned_behaviors WHERE id NOT IN (
                SELECT id FROM learned_behaviors ORDER BY usage_count DESC LIMIT 50
            )
        """)
        await db.commit()


async def get_learned_behaviors(limit: int = 10) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT trigger, action, confidence FROM learned_behaviors ORDER BY usage_count DESC LIMIT ?",
            (limit,)
        ) as cur:
            rows = await cur.fetchall()
    return [{"trigger": r[0], "action": r[1], "confidence": r[2]} for r in rows]


async def log_command(command: str, result: str = "", success: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO command_history (command, result, success, timestamp) VALUES (?, ?, ?, ?)",
            (command[:200], result[:500], 1 if success else 0, datetime.utcnow().isoformat())
        )
        # Keep only last 100 commands
        await db.execute("""
            DELETE FROM command_history WHERE id NOT IN (
                SELECT id FROM command_history ORDER BY id DESC LIMIT 100
            )
        """)
        await db.commit()


async def get_db_size_kb() -> float:
    """Returns database size in KB."""
    try:
        return os.path.getsize(DB_PATH) / 1024
    except Exception:
        return 0


async def _maybe_compact():
    """Compact old messages when approaching limit — keeps DB tiny."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM conversations WHERE is_summary=0") as cur:
            count = (await cur.fetchone())[0]

        if count >= COMPACT_THRESHOLD:
            # Summarize oldest 200 messages into a single summary row
            async with db.execute(
                "SELECT role, content FROM conversations WHERE is_summary=0 ORDER BY id ASC LIMIT 200"
            ) as cur:
                old_rows = await cur.fetchall()

            if old_rows:
                summary = _make_local_summary(old_rows)
                # Delete the old messages
                async with db.execute(
                    "SELECT id FROM conversations WHERE is_summary=0 ORDER BY id ASC LIMIT 200"
                ) as cur:
                    ids = [r[0] for r in await cur.fetchall()]
                await db.execute(
                    f"DELETE FROM conversations WHERE id IN ({','.join('?'*len(ids))})",
                    ids
                )
                # Insert summary
                await db.execute(
                    "INSERT INTO conversations (role, content, timestamp, is_summary) VALUES (?, ?, ?, 1)",
                    ("assistant", f"[RESUMO DE CONVERSA ANTERIOR: {summary}]", datetime.utcnow().isoformat())
                )
                # VACUUM to reclaim space
                await db.execute("PRAGMA incremental_vacuum(100)")
                await db.commit()


def _make_local_summary(rows: list) -> str:
    """Quick local summary without API call — just key facts."""
    topics = set()
    for role, content in rows:
        words = content.lower().split()
        for w in words:
            if len(w) > 5 and w.isalpha():
                topics.add(w)
    top = list(topics)[:20]
    return f"{len(rows)} mensagens sobre: {', '.join(top)}"
