
import sys
import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.skill_discovery import ZoraSkillDiscovery
from developer.skill_prioritization import ZoraSkillPrioritization


class ZoraDecisionTaskGenerator:

    def __init__(self):

        self.task_file = ROOT / "data" / "zora_generated_tasks.json"
        self.history_file = ROOT / "data" / "zora_task_history.json"

        self.allowed_names = {
            "planning": "Perencanaan",
            "source_evaluation": "Evaluasi sumber informasi",
            "decision_making": "Pengambilan keputusan",
            "code_debugging": "Perbaikan kesalahan kode"
        }

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

    def load_history(self):

        if not self.history_file.exists():
            return []

        try:
            data = json.loads(
                self.history_file.read_text(encoding="utf-8")
            )

            return data if isinstance(data, list) else []

        except (json.JSONDecodeError, OSError):
            return []

    def save_history(self, history):

        self.history_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.history_file.write_text(
            json.dumps(
                history,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    def create_prioritizer(self):

        from brain.zora import Zora
        from developer.self_development import ZoraSelfDevelopment
        from developer.development_planner import ZoraDevelopmentPlanner

        zora = Zora()
        developer = ZoraSelfDevelopment(zora)
        planner = ZoraDevelopmentPlanner(developer)
        discovery = ZoraSkillDiscovery(planner)

        return zora, ZoraSkillPrioritization(discovery)

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

        # Hanya menerima bilangan bulat dalam rentang aman.
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

        # Target dihitung sistem, bukan ditentukan AI.
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
            if isinstance(item.get("values"), list)
        ]

        prompt = f"""
Anda adalah perancang tugas pengembangan kemampuan AI ZORA.

Buat SATU tugas baru untuk kemampuan evaluasi sumber informasi.

Tentukan sendiri dua nilai bilangan bulat yang berbeda.
Gunakan nilai antara 1 sampai 100.

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

Jawab hanya JSON valid dengan format:
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
                print("AI menghasilkan rancangan yang tidak valid.")
                return None

            fingerprint = hashlib.sha256(
                json.dumps(
                    task["values"],
                    sort_keys=True
                ).encode("utf-8")
            ).hexdigest()

            used_fingerprints = {
                item.get("fingerprint")
                for item in history
                if item.get("skill_id") == "source_evaluation"
            }

            if fingerprint in used_fingerprints:
                print("AI menghasilkan nilai yang pernah digunakan.")
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

        zora, prioritizer = self.create_prioritizer()

        try:

            result = prioritizer.prioritize()
            selected = result.get("selected_skill")

            if not selected:
                return {
                    "success": False,
                    "message": "Tidak ditemukan kemampuan untuk dikembangkan."
                }

            selected_id = selected["id"]

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
                selected["name"]
            )

            task = self.create_task_with_ai(zora, skill_id)

            if task is None:
                return {
                    "success": False,
                    "message": (
                        "AI belum berhasil menghasilkan tugas baru "
                        "yang valid. Tidak menggunakan soal lama."
                    )
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
                "skill_name": selected["name"],
                "objective": task["objective"],
                "instruction": task["instruction"],
                "expected_output": task["expected_output"],
                "evaluation_criteria": criteria,
                "priority_score": selected["total"],
                "priority_rank": selected["rank"],
                "decision_reason": (
                    "Dipilih untuk memperbaiki hasil pengujian sebelumnya."
                    if is_improvement
                    else "Dipilih berdasarkan evaluasi kemampuan."
                ),
                "development_type": (
                    "perbaikan"
                    if is_improvement
                    else "pengembangan_baru"
                ),
                "task_source": "AI",
                "status": "menunggu_pengembangan"
            }

            self.task_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            self.task_file.write_text(
                json.dumps(
                    generated_task,
                    indent=4,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            return {
                "success": True,
                "task": generated_task,
                "fingerprint": task["fingerprint"]
            }

        finally:
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

        # Riwayat baru dicatat setelah tugas berhasil dibuat.
        history = self.load_history()

        history.append({
            "skill_id": task["skill_id"],
            "fingerprint": result["fingerprint"],
            "values": task["evaluation_criteria"][
                "semantic_parameters"
            ],
            "objective": task["objective"],
            "expected_output": task["expected_output"]
        })

        self.save_history(history)

        return result


def main():

    generator = ZoraDecisionTaskGenerator()
    generator.report()


if __name__ == "__main__":
    main()
