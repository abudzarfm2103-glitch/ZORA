
import json
from datetime import datetime
from pathlib import Path


class ZoraDevelopmentHistory:

    def __init__(self, history_file=None):

        root = Path(__file__).resolve().parent.parent

        self.history_file = (
            Path(history_file)
            if history_file
            else root / "data" / "zora_autonomous_development_history.json"
        )

    def load(self):

        if not self.history_file.exists():
            return []

        try:
            data = json.loads(
                self.history_file.read_text(encoding="utf-8")
            )

            return data if isinstance(data, list) else []

        except (json.JSONDecodeError, OSError):
            return []

    def record(self, result):

        task = result.get("task", {})
        evaluation = result.get("evaluation", {})

        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "skill_id": task.get("skill_id", result.get("skill_id")),
            "skill_name": task.get("skill_name", result.get("skill_name")),
            "filename": result.get("filename"),
            "code": result.get("code"),
            "output": result.get("output"),
            "success": bool(
                result.get("success")
                and evaluation.get("success", result.get("success"))
            ),
            "evaluation": evaluation
        }

        history = self.load()
        history.append(entry)

        self.history_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary_file = self.history_file.with_suffix(".tmp")

        temporary_file.write_text(
            json.dumps(
                history,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        temporary_file.replace(self.history_file)

        return entry

    def report(self):

        history = self.load()

        successful = sum(
            1 for item in history
            if item.get("success")
        )

        failed = len(history) - successful

        return {
            "total": len(history),
            "successful": successful,
            "failed": failed,
            "history": history
        }


def main():

    import tempfile

    with tempfile.TemporaryDirectory() as temporary_folder:

        test_file = (
            Path(temporary_folder)
            / "test_history.json"
        )

        history = ZoraDevelopmentHistory(test_file)

        sample = {
            "success": True,
            "skill_id": "problem_solving",
            "skill_name": "Pemecahan masalah",
            "filename": "prototype_test.py",
            "code": "print(5)",
            "output": "5",
            "evaluation": {
                "success": True,
                "message": "Pengujian berhasil."
            }
        }

        history.record(sample)

        result = history.report()

        print("\nZORA DEVELOPMENT HISTORY TEST")
        print("------------------------------")
        print("Total pengembangan:", result["total"])
        print("Berhasil:", result["successful"])
        print("Gagal:", result["failed"])

        if result["total"] == 1 and result["successful"] == 1:
            print("\nPENGUJIAN BERHASIL.")
        else:
            print("\nPENGUJIAN GAGAL.")


if __name__ == "__main__":
    main()
