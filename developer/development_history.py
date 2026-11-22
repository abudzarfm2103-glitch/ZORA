import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


MAX_HISTORY_SIZE = 20 * 1024 * 1024
MAX_HISTORY_ITEMS = 5000
MAX_ENTRY_SIZE = 262144
MAX_CODE_SIZE = 65536
MAX_OUTPUT_SIZE = 10000


class ZoraDevelopmentHistory:

    def __init__(self, history_file=None):
        root = Path(__file__).resolve().parent.parent

        self.history_file = (
            Path(history_file)
            if history_file
            else root / "data" / "zora_autonomous_development_history.json"
        )

        self.lock_file = self.history_file.with_name(
            self.history_file.name + ".lock"
        )

    @contextmanager
    def _locked(self, exclusive=True):
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.lock_file, "a+b") as lock:
            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(lock.fileno(), mode)

            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _load_unlocked(self):
        if not self.history_file.exists():
            return []

        size = self.history_file.stat().st_size

        if size > MAX_HISTORY_SIZE:
            raise ValueError("Ukuran file riwayat melebihi batas.")

        try:
            raw = self.history_file.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeError) as error:
            raise ValueError("File riwayat rusak dan ditolak.") from error

        if not isinstance(data, list):
            raise ValueError("Format riwayat tidak valid.")

        if len(data) > MAX_HISTORY_ITEMS:
            raise ValueError("Jumlah catatan riwayat melebihi batas.")

        if not all(isinstance(item, dict) for item in data):
            raise ValueError("Struktur catatan riwayat tidak valid.")

        return data

    def load(self):
        with self._locked(exclusive=False):
            return self._load_unlocked()

    def _atomic_save_unlocked(self, history):
        serialized = json.dumps(
            history,
            indent=4,
            ensure_ascii=False
        )

        encoded = serialized.encode("utf-8")

        if len(encoded) > MAX_HISTORY_SIZE:
            raise ValueError("Ukuran riwayat melebihi batas.")

        fd, temporary_path = tempfile.mkstemp(
            prefix=self.history_file.name + ".",
            suffix=".tmp",
            dir=str(self.history_file.parent)
        )

        try:
            with os.fdopen(fd, "wb") as temporary:
                temporary.write(encoded)
                temporary.flush()
                os.fsync(temporary.fileno())

            os.replace(temporary_path, self.history_file)

            directory_fd = os.open(
                str(self.history_file.parent),
                os.O_RDONLY
            )

            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def record(self, result):
        if not isinstance(result, dict):
            raise ValueError("Data hasil pengembangan tidak valid.")

        task = result.get("task", {})
        evaluation = result.get("evaluation", {})

        if not isinstance(task, dict):
            raise ValueError("Data tugas tidak valid.")

        if not isinstance(evaluation, dict):
            raise ValueError("Data evaluasi tidak valid.")

        code = result.get("code", "")
        output = result.get("output", "")

        if not isinstance(code, str) or len(code.encode("utf-8")) > MAX_CODE_SIZE:
            raise ValueError("Ukuran kode tidak valid atau melebihi batas.")

        if not isinstance(output, str) or len(output) > MAX_OUTPUT_SIZE:
            raise ValueError("Ukuran output tidak valid atau melebihi batas.")

        success = bool(
            result.get("success")
            and evaluation.get("success", result.get("success"))
        )

        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "skill_id": task.get("skill_id", result.get("skill_id")),
            "skill_name": task.get("skill_name", result.get("skill_name")),
            "filename": result.get("filename"),
            "code": code,
            "output": output,
            "success": success,
            "evaluation": evaluation
        }

        entry_size = len(
            json.dumps(entry, ensure_ascii=False).encode("utf-8")
        )

        if entry_size > MAX_ENTRY_SIZE:
            raise ValueError("Ukuran catatan melebihi batas.")

        with self._locked(exclusive=True):
            history = self._load_unlocked()

            if len(history) >= MAX_HISTORY_ITEMS:
                raise ValueError("Kapasitas riwayat sudah penuh.")

            history.append(entry)
            self._atomic_save_unlocked(history)

        return entry

    def report(self):
        with self._locked(exclusive=False):
            history = self._load_unlocked()

            successful = sum(
                1 for item in history
                if item.get("success") is True
            )

            failed = len(history) - successful

            return {
                "total": len(history),
                "successful": successful,
                "failed": failed,
                "history": history
            }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        history = ZoraDevelopmentHistory(
            Path(folder) / "history.json"
        )

        history.record({
            "success": True,
            "skill_id": "problem_solving",
            "skill_name": "Pemecahan masalah",
            "code": "print(5)",
            "output": "5",
            "evaluation": {"success": True}
        })

        print("HASIL:", history.report()["total"])
