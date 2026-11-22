import sys
import json
import hashlib
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.skill_discovery import ZoraSkillDiscovery
from developer.skill_prioritization import ZoraSkillPrioritization


class ZoraDecisionTaskGenerator:

    MAX_HISTORY_BYTES = 2 * 1024 * 1024
    MAX_HISTORY_ITEMS = 5000
    MAX_TASK_BYTES = 65536

    def __init__(self, task_file=None, history_file=None):

        data_dir = ROOT / "data"

        self.task_file = (
            Path(task_file) if task_file
            else data_dir / "zora_generated_tasks.json"
        )

        self.history_file = (
            Path(history_file) if history_file
            else data_dir / "zora_task_history.json"
        )

        self.criteria = {
            "source_evaluation": {
                "required_variables": [
                    "nilai_sumber_a",
                    "nilai_sumber_b"
                ],
                "required_operations": ["Gt"],
                "required_control_flow": ["If"],
                "require_print": True,
                "semantic_type": "source_evaluation"
            }
        }

    def _validate_history(self, history):

        if not isinstance(history, list):
            raise ValueError("Format riwayat tugas harus berupa daftar.")

        if len(history) > self.MAX_HISTORY_ITEMS:
            raise ValueError("Jumlah riwayat tugas melebihi batas.")

        for item in history:

            if not isinstance(item, dict):
                raise ValueError("Ditemukan data riwayat yang tidak valid.")

            skill_id = item.get("skill_id")
            fingerprint = item.get("fingerprint")

            if not isinstance(skill_id, str) or not skill_id.strip():
                raise ValueError("ID kemampuan pada riwayat tidak valid.")

            if not isinstance(fingerprint, str):
                raise ValueError("Fingerprint riwayat tidak valid.")

            if len(fingerprint) != 64 or not re.fullmatch(
                r"[a-fA-F0-9]{64}", fingerprint
            ):
                raise ValueError("Format fingerprint riwayat tidak valid.")

            values = item.get("values")

            # Mendukung format daftar baru dan format kamus lama.
            if not isinstance(values, (list, dict)):
                raise ValueError("Nilai tugas pada riwayat tidak valid.")

            objective = item.get("objective", "")
            expected_output = item.get("expected_output", "")

            if not isinstance(objective, str):
                raise ValueError("Tujuan tugas pada riwayat tidak valid.")

            if not isinstance(expected_output, str):
                raise ValueError("Target tugas pada riwayat tidak valid.")

        return history

    def load_history(self):

        if not self.history_file.exists():
            return []

        try:
            size = self.history_file.stat().st_size

            if size > self.MAX_HISTORY_BYTES:
                raise ValueError("File riwayat melebihi batas ukuran.")

            content = self.history_file.read_text(encoding="utf-8")
            history = json.loads(content)

            return self._validate_history(history)

        except (json.JSONDecodeError, UnicodeError, OSError) as error:
            raise ValueError(
                "Riwayat tugas tidak dapat dibaca. "
                "Data asli tidak akan dianggap kosong."
            ) from error

    def _atomic_write_json(self, path, data, max_size):

        path = Path(path)

        content = json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )

        encoded = content.encode("utf-8")

        if len(encoded) > max_size:
            raise ValueError("Data yang akan disimpan melebihi batas ukuran.")

        path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path = None

        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=path.name + ".",
                suffix=".tmp",
                dir=str(path.parent)
            )

            temporary_path = Path(temporary_name)

            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, path)
            temporary_path = None

        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def save_history(self, history):

        self._validate_history(history)

        self._atomic_write_json(
            self.history_file,
            history,
            self.MAX_HISTORY_BYTES
        )

    def create_prioritizer(self):

        from brain.zora import Zora
        from developer.self_development import ZoraSelfDevelopment
        from developer.development_planner import ZoraDevelopmentPlanner

        zora = Zora()

        try:
            developer = ZoraSelfDevelopment(zora)
            planner = ZoraDevelopmentPlanner(developer)
            discovery = ZoraSkillDiscovery(planner)

            return zora, ZoraSkillPrioritization(discovery)

        except Exception:
            zora.memory.close()
            raise

    def extract_json(self, response):

        if not isinstance(response, str):
            return None

        start = response.find("{")
        end = response.rfind("}")

        if start < 0 or end <= start:
            return None

        try:
            result = json.loads(response[start:end + 1])
            return result if isinstance(result, dict) else None

        except json.JSONDecodeError:
            return None

    def validate_source_task(self, proposal):

        if not isinstance(proposal, dict):
            return None

        value_a = proposal.get("nilai_sumber_a")
        value_b = proposal.get("nilai_sumber_b")

        if (
            not isinstance(value_a, int)
            or isinstance(value_a, bool)
            or not isinstance(value_b, int)
            or isinstance(value_b, bool)
        ):
            return None

        if not (1 <= value_a <= 100):
            return None

        if not (1 <= value_b <= 100):
            return None

        if value_a == value_b:
            return None

        objective = proposal.get("objective")

        if not isinstance(objective, str):
            return None

        objective = objective.strip()

        if len(objective) < 10 or len(objective) > 200:
            return None

        expected_output = (
            "sumber_a" if value_a > value_b else "sumber_b"
        )

        instruction = (
            f"Buat nilai_sumber_a bernilai {value_a} dan "
            f"nilai_sumber_b bernilai {value_b}. "
            "Bandingkan kedua nilai menggunakan if/else. "
            "Cetak sumber_a jika nilainya lebih tinggi, "
            "selain itu cetak sumber_b."
        )

        return {
            "objective": objective,
            "instruction": instruction,
            "expected_output": expected_output,
            "values": [value_a, value_b]
        }

    def create_source_task_with_ai(self, zora):

        history = self.load_history()

        previous_tasks = [
            item for item in history
            if item.get("skill_id") == "source_evaluation"
        ][-10:]

        previous_values = [
            item.get("values")
            for item in previous_tasks
        ]

        prompt = f"""
Anda adalah perancang tugas pengembangan kemampuan AI ZORA.

Buat SATU tugas baru untuk kemampuan evaluasi sumber informasi.

Tentukan dua nilai bilangan bulat berbeda antara 1 sampai 100.

Syarat:
1. Tugas membandingkan dua sumber informasi.
2. Nama variabel adalah nilai_sumber_a dan nilai_sumber_b.
3. Kedua nilai harus berbeda.
4. Jangan menggunakan pasangan nilai yang sudah digunakan.
5. Objective harus menjelaskan tujuan tugas.
6. Jangan membuat kode Python.
7. Jangan menentukan target output.
8. Jangan menambahkan kriteria kelulusan.

Pasangan nilai yang sudah digunakan:
{json.dumps(previous_values, ensure_ascii=False)}

Jawab hanya JSON valid:
{{
    "objective": "Tujuan tugas",
    "nilai_sumber_a": 12,
    "nilai_sumber_b": 25
}}
"""

        try:
            response = zora.brain.think([
                {"role": "user", "content": prompt}
            ])

            proposal = self.extract_json(response)
            task = self.validate_source_task(proposal)

            if task is None:
                return None

            fingerprint = hashlib.sha256(
                json.dumps(
                    task["values"],
                    separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()

            used_fingerprints = {
                item["fingerprint"]
                for item in history
                if item.get("skill_id") == "source_evaluation"
            }

            if fingerprint in used_fingerprints:
                return None

            task["fingerprint"] = fingerprint
            return task

        except Exception as error:
            print("Pembuatan tugas AI gagal:", str(error))
            return None

    def create_task_with_ai(self, zora, skill_id):

        if skill_id == "source_evaluation":
            return self.create_source_task_with_ai(zora)

        return None

    def generate(self):

        zora = None

        try:
            zora, prioritizer = self.create_prioritizer()

            result = prioritizer.prioritize()

            if not isinstance(result, dict):
                raise ValueError("Hasil prioritas tidak valid.")

            selected = result.get("selected_skill")

            if not isinstance(selected, dict):
                return {
                    "success": False,
                    "message": "Tidak ditemukan kemampuan untuk dikembangkan."
                }

            selected_id = selected.get("id")
            selected_name = selected.get("name")

            if (
                not isinstance(selected_id, str)
                or not isinstance(selected_name, str)
            ):
                raise ValueError("Identitas kemampuan tidak valid.")

            is_improvement = selected_id.startswith("improve_")

            skill_id = (
                selected_id[len("improve_"):]
                if is_improvement
                else selected_id
            )

            if skill_id not in self.criteria:
                return {
                    "success": False,
                    "message": (
                        "Belum tersedia evaluator dinamis untuk kemampuan "
                        + skill_id
                    )
                }

            print(
                "\nZORA sedang merancang tugas baru untuk:",
                selected_name
            )

            task = self.create_task_with_ai(zora, skill_id)

            if task is None:
                return {
                    "success": False,
                    "message": (
                        "AI belum menghasilkan tugas baru yang valid. "
                        "Tidak menggunakan soal lama."
                    )
                }

            history = self.load_history()

            if any(
                item.get("fingerprint") == task["fingerprint"]
                and item.get("skill_id") == skill_id
                for item in history
            ):
                return {
                    "success": False,
                    "message": "Tugas tersebut sudah pernah digunakan."
                }

            if len(history) >= self.MAX_HISTORY_ITEMS:
                return {
                    "success": False,
                    "message": "Riwayat tugas sudah mencapai batas."
                }

            criteria = dict(self.criteria[skill_id])
            criteria["expected_output"] = task["expected_output"]
            criteria["semantic_parameters"] = {
                "nilai_sumber_a": task["values"][0],
                "nilai_sumber_b": task["values"][1]
            }

            generated_task = {
                "skill_id": skill_id,
                "proposal_id": selected_id,
                "skill_name": selected_name,
                "objective": task["objective"],
                "instruction": task["instruction"],
                "expected_output": task["expected_output"],
                "evaluation_criteria": criteria,
                "priority_score": selected.get("total", 0),
                "priority_rank": selected.get("rank", 0),
                "decision_reason": (
                    "Dipilih untuk memperbaiki hasil pengujian sebelumnya."
                    if is_improvement
                    else "Dipilih berdasarkan evaluasi kemampuan."
                ),
                "development_type": (
                    "perbaikan" if is_improvement
                    else "pengembangan_baru"
                ),
                "task_source": "AI",
                "status": "menunggu_pengembangan"
            }

            # Catat fingerprint sebelum tugas dinyatakan berhasil dibuat.
            history.append({
                "skill_id": skill_id,
                "fingerprint": task["fingerprint"],
                "values": task["values"],
                "objective": task["objective"],
                "expected_output": task["expected_output"]
            })

            self.save_history(history)

            self._atomic_write_json(
                self.task_file,
                generated_task,
                self.MAX_TASK_BYTES
            )

            return {
                "success": True,
                "task": generated_task,
                "fingerprint": task["fingerprint"]
            }

        except (ValueError, OSError) as error:
            return {
                "success": False,
                "message": str(error)
            }

        finally:
            if zora is not None:
                zora.memory.close()

    def report(self):

        result = self.generate()

        print("\nZORA AUTONOMOUS TASK GENERATOR")
        print("==============================")

        if not result["success"]:
            print(result["message"])
            return result

        task = result["task"]

        print("Kemampuan:", task["skill_name"])
        print("Sumber tugas:", task["task_source"])
        print("Jenis:", task["development_type"])
        print("Tujuan:", task["objective"])
        print("Instruksi:", task["instruction"])
        print("Target:", task["expected_output"])
        print("Kriteria evaluasi:")
        print(json.dumps(
            task["evaluation_criteria"],
            indent=4,
            ensure_ascii=False
        ))
        print("Nilai prioritas:", task["priority_score"])
        print("Status:", task["status"])
        print("Riwayat tugas berhasil disimpan.")

        return result


if __name__ == "__main__":
    generator = ZoraDecisionTaskGenerator()
    generator.report()
