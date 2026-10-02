import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "jarvis_memory.db"


def _conn():
    c = sqlite3.connect(DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, fact TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    return c


def add_memory(fact: str):
    with _conn() as c:
        c.execute("INSERT INTO memories (fact) VALUES (?)", (fact,))


def get_memories(limit: int = 20) -> list[str]:
    with _conn() as c:
        rows = c.execute("SELECT fact FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [r[0] for r in rows]
