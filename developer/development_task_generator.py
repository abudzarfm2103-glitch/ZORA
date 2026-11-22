import json
import os
import uuid
from pathlib import Path


class ZoraDevelopmentTaskGenerator:

    def __init__(self, prioritization):

        self.prioritization = prioritization

        self.task_file = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "zora_generated_tasks.json"
        )

        self.task_templates = {
            "problem_solving": {
                "objective": (
                    "Membangun kemampuan memecah masalah "
                    "menjadi langkah penyelesaian."
                ),
                "instruction": (
                    "Buat variabel total bernilai 20 dan "
                    "kelompok bernilai 4. "
                    "Hitung pembagian total dengan kelompok "
                    "menggunakan kedua variabel tersebut. "
                    "Tampilkan hasilnya dengan print."
                ),
                "expected_output": "5.0",
                "evaluation_criteria": {
                    "required_variables": ["total", "kelompok"],
                    "expected_variables": {
                        "total": 20,
                        "kelompok": 4
                    },
                    "required_operations": ["Div"],
                    "required_control_flow": [],
                    "require_print": True
                }
            },

            "data_analysis": {
                "objective": (
                    "Membangun kemampuan menghitung dan "
                    "menganalisis kumpulan data sederhana."
                ),
                "instruction": (
                    "Buat tiga variabel angka_1 bernilai 10, "
                    "angka_2 bernilai 20, dan angka_3 bernilai 30. "
                    "Hitung rata-rata ketiga angka tersebut "
                    "menggunakan penjumlahan dan pembagian. "
                    "Tampilkan hasilnya dengan print."
                ),
                "expected_output": "20.0",
                "evaluation_criteria": {
                    "required_variables": [
                        "angka_1",
                        "angka_2",
                        "angka_3"
                    ],
                    "expected_variables": {
                        "angka_1": 10,
                        "angka_2": 20,
                        "angka_3": 30
                    },
                    "required_operations": ["Add", "Div"],
                    "required_control_flow": [],
                    "require_print": True
                }
            },

            "pattern_recognition": {
                "objective": (
                    "Membangun kemampuan mengenali pola angka."
                ),
                "instruction": (
                    "Buat empat variabel angka_1, angka_2, "
                    "angka_3, dan angka_4 dengan nilai "
                    "2, 4, 6, dan 8. "
                    "Hitung angka berikutnya dengan menambahkan "
                    "2 pada angka_4. Tampilkan hasilnya dengan print."
                ),
                "expected_output": "10",
                "evaluation_criteria": {
                    "required_variables": [
                        "angka_1",
                        "angka_2",
                        "angka_3",
                        "angka_4"
                    ],
                    "expected_variables": {
                        "angka_1": 2,
                        "angka_2": 4,
                        "angka_3": 6,
                        "angka_4": 8
                    },
                    "required_operations": ["Add"],
                    "required_control_flow": [],
                    "require_print": True
                }
            }
        }

    def save_task(self, task):

        self.task_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary_file = self.task_file.with_name(
            f".{self.task_file.name}.{uuid.uuid4().hex}.tmp"
        )

        try:
            temporary_file.write_text(
                json.dumps(
                    task,
                    indent=4,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            os.replace(temporary_file, self.task_file)

        finally:
            try:
                temporary_file.unlink(missing_ok=True)
            except OSError:
                pass

    def generate(self):

        result = self.prioritization.prioritize()

        if not isinstance(result, dict):
            return {
                "success": False,
                "message": "Hasil prioritas tidak valid."
            }

        selected = result.get("selected_skill")

        if not isinstance(selected, dict):
            return {
                "success": False,
                "message": "Tidak ada kemampuan untuk dikembangkan."
            }

        skill_id = selected.get(
            "skill_id",
            selected.get("id")
        )

        template = self.task_templates.get(skill_id)

        if template is None:
            return {
                "success": False,
                "message": "Belum tersedia template tugas."
            }

        criteria = dict(template["evaluation_criteria"])

        task = {
            "skill_id": skill_id,
            "proposal_id": selected.get("id", skill_id),
            "skill_name": selected.get("name", skill_id),
            "objective": template["objective"],
            "instruction": template["instruction"],
            "expected_output": template["expected_output"],
            "evaluation_criteria": {
                **criteria,
                "expected_output": template["expected_output"]
            },
            "priority_score": selected.get("total", 0),
            "priority_rank": selected.get("rank"),
            "task_source": "template_terverifikasi",
            "status": "menunggu_pengembangan"
        }

        self.save_task(task)

        return {
            "success": True,
            "task": task
        }

    def report(self):

        result = self.generate()

        print("\nZORA AUTONOMOUS DEVELOPMENT TASK GENERATOR")
        print("------------------------------------------")

        if not result["success"]:
            print(result["message"])
            return result

        task = result["task"]

        print("Kemampuan:", task["skill_name"])
        print("Tujuan:", task["objective"])
        print("Instruksi:", task["instruction"])
        print("Target output:", task["expected_output"])
        print("Kriteria evaluasi:")
        print(json.dumps(
            task["evaluation_criteria"],
            indent=4,
            ensure_ascii=False
        ))
        print("Status:", task["status"])

        return result


def main():

    import sys

    ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ROOT))

    from brain.zora import Zora
    from developer.self_development import ZoraSelfDevelopment
    from developer.development_planner import ZoraDevelopmentPlanner
    from developer.skill_discovery import ZoraSkillDiscovery
    from developer.skill_prioritization import ZoraSkillPrioritization

    zora = Zora()

    try:
        developer = ZoraSelfDevelopment(zora)
        planner = ZoraDevelopmentPlanner(developer)
        discovery = ZoraSkillDiscovery(planner)
        prioritization = ZoraSkillPrioritization(discovery)

        generator = ZoraDevelopmentTaskGenerator(prioritization)
        generator.report()

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
