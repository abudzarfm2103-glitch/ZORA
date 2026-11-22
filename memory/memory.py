import sqlite3
import threading
from pathlib import Path
from datetime import datetime


class ZoraMemory:

    VALID_STATUSES = [
        "fakta",
        "rencana",
        "dugaan",
        "belum_diklasifikasikan"
    ]

    MAX_CONTENT_LENGTH = 10000
    MAX_CATEGORY_LENGTH = 100

    def __init__(self, db_path=None):
        root = Path(__file__).resolve().parent.parent

        self.db_path = (
            Path(db_path)
            if db_path is not None
            else root / "data" / "zora_memory.db"
        )

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Satu koneksi boleh digunakan lintas thread,
        # tetapi seluruh akses harus melalui lock.
        self.lock = threading.RLock()
        self.closed = False

        self.conn = sqlite3.connect(
            self.db_path,
            timeout=10,
            check_same_thread=False
        )

        self.conn.execute("PRAGMA busy_timeout = 10000")

        with self.lock:
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
                row[1]
                for row in self.conn.execute(
                    "PRAGMA table_info(memories)"
                )
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

    def ensure_open(self):
        if self.closed:
            raise RuntimeError("Koneksi memori ZORA sudah ditutup.")

    def save(
        self,
        content,
        category="lainnya",
        status="belum_diklasifikasikan"
    ):
        if not isinstance(content, str):
            return False

        if not isinstance(category, str):
            return False

        content = content.strip()
        category = category.strip()

        if not content or len(content) > self.MAX_CONTENT_LENGTH:
            return False

        if not category or len(category) > self.MAX_CATEGORY_LENGTH:
            return False

        if status not in self.VALID_STATUSES:
            status = "belum_diklasifikasikan"

        with self.lock:
            self.ensure_open()

            try:
                # Mengunci transaksi agar dua koneksi berbeda
                # tidak menyimpan informasi duplikat bersamaan.
                self.conn.execute("BEGIN IMMEDIATE")

                cursor = self.conn.execute("""
                    SELECT id FROM memories
                    WHERE LOWER(TRIM(content)) = LOWER(TRIM(?))
                """, (content,))

                if cursor.fetchone():
                    self.conn.rollback()
                    return False

                self.conn.execute("""
                    INSERT INTO memories
                    (content, category, created_at, status)
                    VALUES (?, ?, ?, ?)
                """, (
                    content,
                    category,
                    datetime.now().astimezone().isoformat(),
                    status
                ))

                self.conn.commit()
                return True

            except Exception:
                self.conn.rollback()
                raise

    def recall(self, category=None):
        with self.lock:
            self.ensure_open()

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
        with self.lock:
            self.ensure_open()

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
        with self.lock:
            if not self.closed:
                self.conn.close()
                self.closed = True


def main():
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    with tempfile.TemporaryDirectory() as folder:
        db_path = Path(folder) / "test_memory.db"

        memory = ZoraMemory(db_path)

        assert memory.save(
            "ZORA sedang diuji",
            "proyek",
            "fakta"
        )
        print("LULUS: penyimpanan memori")

        assert not memory.save(
            "ZORA sedang diuji",
            "proyek",
            "fakta"
        )
        print("LULUS: duplikasi memori ditolak")

        assert len(memory.recall()) == 1
        assert len(memory.recall_details("proyek")) == 1
        print("LULUS: pembacaan memori")

        def save_duplicate(_):
            connection = ZoraMemory(db_path)
            try:
                return connection.save(
                    "Informasi yang sama",
                    "proyek",
                    "fakta"
                )
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(save_duplicate, range(8)))

        assert sum(results) == 1
        print("LULUS: penyimpanan bersamaan tidak membuat duplikasi")

        assert not memory.save("x" * 10001)
        print("LULUS: batas ukuran memori")

        memory.close()

        try:
            memory.recall()
            raise AssertionError("Koneksi tertutup seharusnya ditolak")
        except RuntimeError:
            print("LULUS: koneksi tertutup ditangani")

        print("\nHASIL: 6/6 pengujian SQLite lulus")


if __name__ == "__main__":
    main()
