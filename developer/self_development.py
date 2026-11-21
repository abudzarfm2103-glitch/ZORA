import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.self_repair import ZoraSelfRepair
from developer.self_evaluation import ZoraSelfEvaluation


class ZoraSelfDevelopment:

    def __init__(self, zora):
        self.zora = zora
        self.repair = ZoraSelfRepair(zora, max_attempts=3)
        self.evaluator = ZoraSelfEvaluation()
        self.state_file = ROOT / "data" / "zora_self_development.json"

        self.roadmap = [
            {
                "id": "logical_reasoning",
                "name": "Penalaran logis",
                "instruction": (
                    "Buat program membandingkan angka 10 dan 20. "
                    "Gunakan if dan perbandingan. "
                    "Tampilkan angka terbesar yaitu 20."
                )
            },
            {
                "id": "calculation",
                "name": "Kemampuan perhitungan",
                "instruction": (
                    "Buat program dengan a=10 dan b=20. "
                    "Hitung a+b, a-b, a*b, dan a/b. "
                    "Simpan hasil dalam empat variabel. "
                    "Tampilkan hanya: 30, -10, 200, 0.5 "
                    "secara berurutan."
                )
            },
            {
                "id": "condition_analysis",
                "name": "Analisis kondisi",
                "instruction": (
                    "Periksa angka 10 menggunakan if dan perbandingan "
                    "untuk menentukan apakah angka positif. "
                    "Tampilkan hanya teks positif."
                )
            },
            {
                "id": "data_analysis",
                "name": "Analisis data",
                "instruction": (
                    "Buat program analisis data penjualan sederhana. "
                    "Buat variabel pagi=10, siang=20, sore=30. "
                    "Hitung total seluruh penjualan ke variabel total. "
                    "Hitung rata-rata ke variabel rata_rata. "
                    "Gunakan if untuk memeriksa apakah rata_rata "
                    "minimal 20. Jika tercapai, tampilkan "
                    "target tercapai. Jika tidak, tampilkan "
                    "target belum tercapai. "
                    "Output untuk data tersebut harus tepat: "
                    "target tercapai. "
                    "Gunakan hanya variabel, operasi matematika, "
                    "perbandingan, if/else, dan print."
                )
            }
        ]

    def load_state(self):
        import json

        if not self.state_file.exists():
            return {
                "completed_prototypes": [],
                "history": []
            }

        try:
            data = json.loads(
                self.state_file.read_text(encoding="utf-8")
            )

            if not isinstance(data, dict):
                raise ValueError("Format tidak valid.")

            data.setdefault("completed_prototypes", [])
            data.setdefault("history", [])
            return data

        except (ValueError, OSError):
            return {
                "completed_prototypes": [],
                "history": []
            }

    def save_state(self, state):
        import json

        self.state_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.state_file.write_text(
            json.dumps(
                state,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    def verify_previous_progress(self):

        state = self.load_state()
        verified = []

        print("ZORA sedang memeriksa prototype sebelumnya...")

        for task in self.roadmap:

            records = [
                item for item in state["history"]
                if item.get("task") == task["name"]
                and item.get("success") is True
            ]

            for record in reversed(records):

                filename = record.get("filename")

                if not filename:
                    continue

                try:
                    target = self.zora.execution.validate_path(
                        filename
                    )

                    if not target.is_file():
                        continue

                    code = target.read_text(encoding="utf-8")
                    execution = self.zora.execution.test_code(filename)

                    if not execution.get("success"):
                        continue

                    evaluation = self.evaluator.evaluate(
                        task["id"],
                        code,
                        execution.get("output", "")
                    )

                    if evaluation.get("success"):
                        verified.append(task["id"])
                        print("Terverifikasi:", task["name"])
                        break

                except (OSError, ValueError, PermissionError):
                    continue

        state["completed_prototypes"] = verified
        self.save_state(state)

        return state

    def evaluate_progress(self):

        state = self.verify_previous_progress()

        remaining = [
            task for task in self.roadmap
            if task["id"] not in state["completed_prototypes"]
        ]

        return {
            "completed": len(state["completed_prototypes"]),
            "remaining": len(remaining),
            "next_task": remaining[0] if remaining else None
        }

    def develop_next(self):

        progress = self.evaluate_progress()
        task = progress["next_task"]

        if task is None:
            return {
                "success": True,
                "message": "Seluruh prototype roadmap berhasil diverifikasi."
            }

        print("Kebutuhan berikutnya:", task["name"])

        folder = "developer_sandbox/pengujian"
        state = self.load_state()
        final_result = None
        final_filename = None
        success = False
        feedback = ""

        for attempt in range(1, 4):

            nomor = 1

            while True:
                filename = (
                    f"{folder}/self_development_"
                    f"{task['id']}_{nomor}.py"
                )

                target = self.zora.execution.validate_path(filename)

                if not target.exists():
                    break

                nomor += 1

            final_filename = filename

            print(f"\nPengembangan tujuan ke-{attempt}...")
            print("File prototype:", filename)

            instruction = task["instruction"]

            if feedback:
                instruction += (
                    "\n\nPERBAIKI KESALAHAN SEBELUMNYA:\n"
                    + feedback
                    + "\nBuat ulang seluruh kode dari awal. "
                    "Jangan mengulang kesalahan sebelumnya."
                )

            result = self.repair.run(
                instruction=instruction,
                filename=filename
            )

            if not result.get("success"):
                feedback = result.get(
                    "message",
                    "Prototype gagal melewati Sandbox."
                )
                print("Sandbox:", feedback)
                final_result = result
                continue

            evaluation = self.evaluator.evaluate(
                task["id"],
                result.get("code", ""),
                result.get("output", "")
            )

            print("HASIL SELF-EVALUATION:")
            print(evaluation)

            final_result = {
                "sandbox": result,
                "self_evaluation": evaluation
            }

            if evaluation.get("success"):
                success = True
                break

            feedback = evaluation.get(
                "message",
                "Hasil belum sesuai."
            )

        state["history"].append({
            "task": task["name"],
            "filename": final_filename,
            "success": success,
            "message": (
                "Prototype berhasil diverifikasi."
                if success
                else feedback
            )
        })

        if success:
            if task["id"] not in state["completed_prototypes"]:
                state["completed_prototypes"].append(task["id"])

        self.save_state(state)

        return {
            "success": success,
            "task": task["name"],
            "result": final_result,
            "progress": self.evaluate_progress()
        }

    def report(self):

        progress = self.evaluate_progress()

        return {
            "nama": "ZORA Self-Development",
            "prototype_terverifikasi": progress["completed"],
            "prototype_tersisa": progress["remaining"],
            "tugas_berikutnya": (
                progress["next_task"]["name"]
                if progress["next_task"]
                else "Tidak ada"
            )
        }


def main():

    from brain.zora import Zora

    zora = Zora()

    try:
        developer = ZoraSelfDevelopment(zora)

        print("STATUS PENGEMBANGAN ZORA:")
        print(developer.report())

        print("\nMEMULAI SIKLUS PENGEMBANGAN:")
        print(developer.develop_next())

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
