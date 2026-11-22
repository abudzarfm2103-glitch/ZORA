import json
import os
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from developer.self_repair import ZoraSelfRepair
from developer.self_evaluation import ZoraSelfEvaluation


class ZoraSelfDevelopment:

    MAX_ATTEMPTS = 3
    MAX_HISTORY = 5000
    MAX_STATE_SIZE = 5 * 1024 * 1024
    MAX_FILENAME_ATTEMPTS = 10000
    MAX_ERROR_MESSAGE = 2000

    def __init__(self, zora, state_file=None):
        self.zora = zora
        self.repair = ZoraSelfRepair(
            zora,
            max_attempts=self.MAX_ATTEMPTS
        )
        self.evaluator = ZoraSelfEvaluation()

        self.state_file = (
            Path(state_file)
            if state_file is not None
            else ROOT / "data" / "zora_self_development.json"
        )

        self.lock = threading.RLock()

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

        self.task_map = {
            task["id"]: task
            for task in self.roadmap
        }

    def _empty_state(self):
        return {
            "completed_prototypes": [],
            "history": []
        }

    def _validate_state(self, data):
        if not isinstance(data, dict):
            raise ValueError(
                "Format data pengembangan tidak valid."
            )

        completed = data.get("completed_prototypes", [])
        history = data.get("history", [])

        if not isinstance(completed, list):
            raise ValueError(
                "Daftar prototype selesai tidak valid."
            )

        if not isinstance(history, list):
            raise ValueError(
                "Riwayat pengembangan tidak valid."
            )

        if len(history) > self.MAX_HISTORY:
            raise ValueError(
                "Riwayat pengembangan melewati batas."
            )

        valid_ids = set(self.task_map)

        for item in completed:
            if not isinstance(item, str) or item not in valid_ids:
                raise ValueError(
                    "ID prototype dalam progres tidak valid."
                )

        for item in history:
            if not isinstance(item, dict):
                raise ValueError(
                    "Format catatan riwayat tidak valid."
                )

        return {
            "completed_prototypes": list(dict.fromkeys(completed)),
            "history": history
        }

    def load_state(self):
        with self.lock:
            if not self.state_file.exists():
                return self._empty_state()

            try:
                size = self.state_file.stat().st_size

                if size > self.MAX_STATE_SIZE:
                    raise ValueError(
                        "File progres pengembangan terlalu besar."
                    )

                raw = self.state_file.read_text(encoding="utf-8")
                data = json.loads(raw)

                return self._validate_state(data)

            except json.JSONDecodeError as error:
                raise ValueError(
                    "File progres pengembangan rusak. "
                    "Data tidak akan direset atau ditimpa."
                ) from error

            except UnicodeError as error:
                raise ValueError(
                    "Encoding file progres pengembangan tidak valid."
                ) from error

            except OSError as error:
                raise RuntimeError(
                    f"Progres pengembangan tidak dapat dibaca: {error}"
                ) from error

    def save_state(self, state):
        validated = self._validate_state(state)

        serialized = json.dumps(
            validated,
            indent=4,
            ensure_ascii=False
        )

        encoded = serialized.encode("utf-8")

        if len(encoded) > self.MAX_STATE_SIZE:
            raise ValueError(
                "Ukuran progres pengembangan melewati batas."
            )

        if not self.state_file.parent.exists():
            self.state_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

        temporary_path = None

        with self.lock:
            try:
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=".zora_self_development_",
                    suffix=".tmp",
                    dir=str(self.state_file.parent)
                )

                temporary_path = Path(temporary_name)

                with os.fdopen(
                    descriptor,
                    "w",
                    encoding="utf-8"
                ) as file:
                    file.write(serialized)
                    file.flush()
                    os.fsync(file.fileno())

                os.replace(temporary_path, self.state_file)

            except OSError:
                if temporary_path and temporary_path.exists():
                    temporary_path.unlink()
                raise

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

                if not isinstance(filename, str) or not filename:
                    continue

                try:
                    target = self.zora.execution.validate_path(filename)

                    if not target.is_file():
                        continue

                    max_size = getattr(
                        self.zora.execution.sandbox,
                        "MAX_FILE_SIZE",
                        65536
                    )

                    if target.stat().st_size > max_size:
                        continue

                    code = target.read_text(encoding="utf-8")

                    execution = self.zora.execution.test_code(filename)

                    if not isinstance(execution, dict):
                        continue

                    if execution.get("success") is not True:
                        continue

                    evaluation = self.evaluator.evaluate(
                        task["id"],
                        code,
                        execution.get("output", "")
                    )

                    if not isinstance(evaluation, dict):
                        continue

                    if evaluation.get("success") is True:
                        verified.append(task["id"])
                        print("Terverifikasi:", task["name"])
                        break

                except Exception as error:
                    print(
                        "Peringatan verifikasi prototype:",
                        type(error).__name__
                    )
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

    def _next_filename(self, task):
        folder = "developer_sandbox/pengujian"

        for nomor in range(1, self.MAX_FILENAME_ATTEMPTS + 1):
            filename = (
                f"{folder}/self_development_"
                f"{task['id']}_{nomor}.py"
            )

            target = self.zora.execution.validate_path(filename)

            if not target.exists():
                return filename

        raise RuntimeError(
            "Batas pencarian nama file prototype tercapai."
        )

    def _remove_failed_prototype(self, filename):
        try:
            target = self.zora.execution.validate_path(filename)

            if target.is_file():
                target.unlink()

            return not target.exists()

        except (OSError, ValueError, PermissionError):
            return False

    def _error_message(self, stage, error):
        message = (
            f"{stage} mengalami exception "
            f"({type(error).__name__}): {error}"
        )

        return message[:self.MAX_ERROR_MESSAGE]

    def _develop_next_locked(self):

        progress = self.evaluate_progress()
        task = progress["next_task"]

        if task is None:
            return {
                "success": True,
                "message": (
                    "Seluruh prototype roadmap berhasil diverifikasi."
                )
            }

        print("Kebutuhan berikutnya:", task["name"])

        final_result = None
        final_filename = None
        success = False
        feedback = ""
        attempts_used = 0

        for attempt in range(1, self.MAX_ATTEMPTS + 1):

            attempts_used = attempt

            try:
                filename = self._next_filename(task)

            except (OSError, ValueError, RuntimeError) as error:
                feedback = self._error_message(
                    "Pembuatan nama file",
                    error
                )
                final_result = {
                    "success": False,
                    "stage": "filename",
                    "message": feedback
                }
                break

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

            # Tahap 1: pembuatan dan pengujian sandbox.
            try:
                result = self.repair.run(
                    instruction=instruction,
                    filename=filename
                )

            except Exception as error:
                feedback = self._error_message(
                    "Repair",
                    error
                )

                final_result = {
                    "success": False,
                    "stage": "repair",
                    "message": feedback
                }

                self._remove_failed_prototype(filename)
                print("Sandbox:", feedback)
                continue

            if not isinstance(result, dict):
                feedback = "Repair memberikan hasil dengan format tidak valid."

                final_result = {
                    "success": False,
                    "stage": "repair",
                    "message": feedback
                }

                self._remove_failed_prototype(filename)
                print("Sandbox:", feedback)
                continue

            if result.get("success") is not True:
                feedback = str(
                    result.get(
                        "message",
                        "Prototype gagal melewati Sandbox."
                    )
                )[:self.MAX_ERROR_MESSAGE]

                final_result = {
                    "success": False,
                    "stage": "repair",
                    "message": feedback
                }

                self._remove_failed_prototype(filename)
                print("Sandbox:", feedback)
                continue

            code = result.get("code", "")
            output = result.get("output", "")

            if not isinstance(code, str) or not isinstance(output, str):
                feedback = "Repair menghasilkan kode atau output tidak valid."

                final_result = {
                    "success": False,
                    "stage": "repair",
                    "message": feedback
                }

                self._remove_failed_prototype(filename)
                continue

            # Tahap 2: evaluasi hasil prototype.
            try:
                evaluation = self.evaluator.evaluate(
                    task["id"],
                    code,
                    output
                )

            except Exception as error:
                feedback = self._error_message(
                    "Self-evaluation",
                    error
                )

                final_result = {
                    "success": False,
                    "stage": "evaluation",
                    "message": feedback
                }

                self._remove_failed_prototype(filename)
                print("Evaluasi:", feedback)
                continue

            if not isinstance(evaluation, dict):
                feedback = (
                    "Self-evaluation memberikan format hasil tidak valid."
                )

                final_result = {
                    "success": False,
                    "stage": "evaluation",
                    "message": feedback
                }

                self._remove_failed_prototype(filename)
                continue

            print("HASIL SELF-EVALUATION:")
            print(evaluation)

            final_result = {
                "sandbox": result,
                "self_evaluation": evaluation
            }

            if evaluation.get("success") is True:
                success = True
                final_filename = filename
                feedback = ""
                break

            feedback = str(
                evaluation.get(
                    "message",
                    "Hasil belum sesuai."
                )
            )[:self.MAX_ERROR_MESSAGE]

            self._remove_failed_prototype(filename)

        # Catat hasil akhir, termasuk kegagalan akibat exception.
        state = self.load_state()

        state["history"].append({
            "task": task["name"],
            "task_id": task["id"],
            "filename": final_filename,
            "success": success,
            "attempts": attempts_used,
            "message": (
                "Prototype berhasil diverifikasi."
                if success
                else feedback or "Pengembangan gagal."
            )
        })

        state["history"] = state["history"][-self.MAX_HISTORY:]

        if success and task["id"] not in state["completed_prototypes"]:
            state["completed_prototypes"].append(task["id"])

        self.save_state(state)

        return {
            "success": success,
            "task": task["name"],
            "result": final_result,
            "progress": self.evaluate_progress()
        }

    def develop_next(self):
        with self.lock:
            return self._develop_next_locked()

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
