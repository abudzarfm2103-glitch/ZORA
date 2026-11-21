
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ZoraSkillPrioritization:

    def __init__(self, discovery):

        self.discovery = discovery

        self.result_file = (
            ROOT / "data" / "zora_skill_priorities.json"
        )

        self.history_file = (
            ROOT / "data" / "zora_autonomous_development_history.json"
        )

        self.capability_file = (
            ROOT / "data" / "zora_capability_report.json"
        )

        self.dependency_map = {
            "language_understanding": [
                "planning",
                "decision_making"
            ],
            "planning": [
                "decision_making",
                "problem_solving"
            ],
            "code_debugging": [
                "problem_solving",
                "logical_reasoning"
            ],
            "source_evaluation": [
                "decision_making",
                "data_analysis"
            ],
            "decision_making": [
                "planning",
                "logical_reasoning"
            ]
        }

    def read_json(self, path, default):

        try:
            if path.exists():
                return json.loads(
                    path.read_text(encoding="utf-8")
                )
        except (OSError, json.JSONDecodeError):
            pass

        return default

    def evaluate_skill(self, skill):

        skill_id = skill["id"]

        history = self.read_json(
            self.history_file, []
        )

        capability_report = self.read_json(
            self.capability_file, {}
        )

        if not isinstance(history, list):
            history = []

        if not isinstance(capability_report, dict):
            capability_report = {}

        records = [
            item for item in history
            if isinstance(item, dict)
            and item.get("skill_id") == skill_id
        ]

        capability = capability_report.get(
            skill_id, {}
        )

        status = capability.get(
            "status", "belum_diuji"
        )

        successful = sum(
            1 for item in records
            if item.get("success") is True
        )

        failed = sum(
            1 for item in records
            if item.get("success") is False
        )

        latest_failed = (
            bool(records)
            and records[-1].get("success") is False
        )

        # Nilai manfaat berdasarkan jenis kebutuhan.
        usefulness_map = {
            "language_understanding": 10,
            "planning": 10,
            "code_debugging": 10,
            "source_evaluation": 9,
            "decision_making": 10,
            "problem_solving": 10,
            "data_analysis": 9
        }

        usefulness = usefulness_map.get(skill_id, 7)

        # Tingkat kebutuhan berdasarkan hasil evaluasi.
        if latest_failed:
            importance = 10

        elif status == "perlu_perbaikan":
            importance = 10

        elif status == "belum_diuji":
            importance = 9

        elif status == "terverifikasi":
            importance = 3

        else:
            importance = 7

        dependencies = self.dependency_map.get(
            skill_id, []
        )

        verified_dependencies = sum(
            1 for dependency in dependencies
            if capability_report.get(
                dependency, {}
            ).get("status") == "terverifikasi"
        )

        if dependencies:
            dependency_score = (
                5 + verified_dependencies * 2
            )
        else:
            dependency_score = 5

        dependency_score = min(
            10, dependency_score
        )

        # Tambahkan perhatian jika ada kegagalan.
        failure_score = min(10, failed * 2)

        # Nilai akhir.
        total = (
            usefulness * 0.30
            + importance * 0.35
            + dependency_score * 0.20
            + failure_score * 0.15
        )

        return {
            "id": skill_id,
            "name": skill["name"],
            "status": status,
            "scores": {
                "usefulness": usefulness,
                "importance": importance,
                "dependency": dependency_score,
                "failure": failure_score
            },
            "evidence": {
                "successful_tests": successful,
                "failed_tests": failed,
                "latest_failed": latest_failed,
                "verified_dependencies": verified_dependencies,
                "dependency_count": len(dependencies),
                "history_records": len(records)
            },
            "dependencies": dependencies,
            "total": round(total, 2)
        }

    def prioritize(self):

        candidates = self.discovery.discover()

        evaluated = [
            self.evaluate_skill(skill)
            for skill in candidates
        ]

        evaluated.sort(
            key=lambda item: (
                item["status"] == "terverifikasi",
                -item["total"]
            )
        )

        for index, item in enumerate(
            evaluated, start=1
        ):
            item["rank"] = index

        result = {
            "selected_skill": (
                evaluated[0] if evaluated else None
            ),
            "all_priorities": evaluated
        }

        self.result_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.result_file.write_text(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        return result

    def report(self):

        result = self.prioritize()

        print("\nZORA AUTONOMOUS SKILL PRIORITIZATION")
        print("------------------------------------")

        for item in result["all_priorities"]:

            print(
                f"\nPeringkat {item['rank']}: "
                f"{item['name']}"
            )

            print("Status:", item["status"])
            print("Nilai:", item["total"])
            print("Dasar penilaian:", item["scores"])
            print("Bukti:", item["evidence"])
            print("Ketergantungan:", item["dependencies"])

        selected = result["selected_skill"]

        if selected:

            print("\nKemampuan yang dipilih ZORA:")
            print(selected["name"])

        else:

            print("\nTidak ada kandidat pengembangan.")

        return result


def main():

    import sys

    sys.path.insert(0, str(ROOT))

    from brain.zora import Zora
    from developer.self_development import ZoraSelfDevelopment
    from developer.development_planner import ZoraDevelopmentPlanner
    from developer.skill_discovery import ZoraSkillDiscovery

    zora = Zora()

    try:

        developer = ZoraSelfDevelopment(zora)
        planner = ZoraDevelopmentPlanner(developer)
        discovery = ZoraSkillDiscovery(planner)

        prioritization = ZoraSkillPrioritization(discovery)
        prioritization.report()

    finally:

        zora.memory.close()


if __name__ == "__main__":
    main()
