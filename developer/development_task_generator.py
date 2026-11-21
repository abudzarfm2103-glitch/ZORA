
import json
from pathlib import Path


class ZoraDevelopmentTaskGenerator:

    def __init__(self, prioritization):

        self.prioritization = prioritization

        self.task_file = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "zora_generated_tasks.json"
        )

    def generate(self):

        result = self.prioritization.prioritize()
        selected = result["selected_skill"]

        if not selected:
            return {
                "success": False,
                "message": "Tidak ada kemampuan untuk dikembangkan."
            }

        task_templates = {
            "problem_solving": {
                "objective": (
                    "Membangun kemampuan memecah masalah "
                    "menjadi langkah penyelesaian."
                ),
                "instruction": (
                    "Diberikan total = 20 dan kelompok = 4. "
                    "Buat program menggunakan kedua variabel tersebut "
                    "untuk menghitung pembagian rata. "
                    "Gunakan operasi pembagian total / kelompok. "
                    "Tampilkan hasilnya dengan print. "
                    "Jangan mengganti nilai variabel."
                ),
                "expected_output": "5"
            },
            "data_analysis": {
                "objective": (
                    "Membangun kemampuan menghitung dan "
                    "menganalisis kumpulan data sederhana."
                ),
                "instruction": (
                    "Buat program menghitung rata-rata "
                    "dari tiga angka 10, 20, dan 30."
                ),
                "expected_output": "20.0"
            },
            "pattern_recognition": {
                "objective": (
                    "Membangun kemampuan mengenali pola angka."
                ),
                "instruction": (
                    "Buat program menghitung angka berikutnya "
                    "dalam pola 2, 4, 6, 8 dengan menambahkan 2."
                ),
                "expected_output": "10"
            }
        }

        template = task_templates.get(selected["id"])

        if not template:
            return {
                "success": False,
                "message": "Belum tersedia template tugas."
            }

        task = {
            "skill_id": selected["id"],
            "skill_name": selected["name"],
            "objective": template["objective"],
            "instruction": template["instruction"],
            "expected_output": template["expected_output"],
            "status": "menunggu_pengembangan"
        }

        self.task_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.task_file.write_text(
            json.dumps(
                task,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

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
        print("Status:", task["status"])

        return result


def main():

    import sys
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent)
    )

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
