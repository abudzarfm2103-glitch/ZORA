
import sqlite3
from pathlib import Path
from datetime import datetime


class ZoraMemory:

    VALID_STATUSES = [
        "fakta",
        "rencana",
        "dugaan",
        "belum_diklasifikasikan"
    ]

    def __init__(self):

        root = Path(__file__).resolve().parent.parent
        self.db_path = root / "data" / "zora_memory.db"

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.conn = sqlite3.connect(self.db_path)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'lainnya',
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'belum_diklasifikasikan'
            )
        """)

        columns = [
            row[1] for row in
            self.conn.execute("PRAGMA table_info(memories)")
        ]

        if "category" not in columns:
            self.conn.execute("""
                ALTER TABLE memories
                ADD COLUMN category TEXT DEFAULT 'lainnya'
            """)

        if "status" not in columns:
            self.conn.execute("""
                ALTER TABLE memories
                ADD COLUMN status TEXT
                DEFAULT 'belum_diklasifikasikan'
            """)

        self.conn.commit()

    def save(
        self,
        content,
        category="lainnya",
        status="belum_diklasifikasikan"
    ):

        content = content.strip()

        if not content:
            return False

        if status not in self.VALID_STATUSES:
            status = "belum_diklasifikasikan"

        cursor = self.conn.execute("""
            SELECT id FROM memories
            WHERE LOWER(TRIM(content)) = LOWER(TRIM(?))
        """, (content,))

        if cursor.fetchone():
            return False

        self.conn.execute("""
            INSERT INTO memories
            (content, category, created_at, status)
            VALUES (?, ?, ?, ?)
        """, (
            content,
            category,
            datetime.now().isoformat(),
            status
        ))

        self.conn.commit()
        return True

    def recall(self, category=None):

        if category:
            cursor = self.conn.execute("""
                SELECT content FROM memories
                WHERE category = ?
                ORDER BY id DESC
            """, (category,))
        else:
            cursor = self.conn.execute("""
                SELECT content FROM memories
                ORDER BY id DESC
            """)

        return cursor.fetchall()

    def recall_details(self, category=None):

        if category:
            cursor = self.conn.execute("""
                SELECT content, category, status, created_at
                FROM memories
                WHERE category = ?
                ORDER BY id DESC
            """, (category,))
        else:
            cursor = self.conn.execute("""
                SELECT content, category, status, created_at
                FROM memories
                ORDER BY id DESC
            """)

        return cursor.fetchall()

    def close(self):
        self.conn.close()
