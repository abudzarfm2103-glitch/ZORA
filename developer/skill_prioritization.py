import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class ZoraSkillPrioritization:

    def __init__(self, discovery):

        self.discovery = discovery

        self.result_file = ROOT / "data" / "zora_skill_priorities.json"
        self.history_file = ROOT / "data" / "zora_autonomous_development_history.json"
        self.capability_file = ROOT / "data" / "zora_capability_report.json"

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
                data = json.loads(path.read_text(encoding="utf-8"))
                return data
        except (OSError, json.JSONDecodeError):
            pass

        return default

    def evaluate_skill(self, skill):

        if not isinstance(skill, dict):
            raise ValueError("Data kemampuan tidak valid.")

        proposal_id = skill.get("id")
        skill_id = skill.get("skill_id", proposal_id)
        skill_name = skill.get("name", skill_id)

        if not isinstance(skill_id, str) or not skill_id:
            raise ValueError("ID kemampuan tidak valid.")

        history = self.read_json(self.history_file, [])
        capability_report = self.read_json(self.capability_file, {})

        if not isinstance(history, list):
            history = []

        if not isinstance(capability_report, dict):
            capability_report = {}

        records = [
            item for item in history
            if isinstance(item, dict)
            and item.get("skill_id") == skill_id
            and isinstance(item.get("success"), bool)
        ]

        capability = capability_report.get(skill_id, {})

        if not isinstance(capability, dict):
            capability = {}

        status = capability.get("status", skill.get("status", "belum_diuji"))

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

        if latest_failed or status == "perlu_perbaikan":
            importance = 10
        elif status == "belum_diuji":
            importance = 9
        elif status == "terverifikasi":
            importance = 3
        else:
            importance = 7

        dependencies = self.dependency_map.get(skill_id, [])

        verified_dependencies = sum(
            1 for dependency in dependencies
            if isinstance(capability_report.get(dependency), dict)
            and capability_report[dependency].get("status") == "terverifikasi"
        )

        dependency_score = (
            5 + verified_dependencies * 2
            if dependencies else 5
        )

        dependency_score = min(10, dependency_score)
        failure_score = min(10, failed * 2)

        total = (
            usefulness * 0.30
            + importance * 0.35
            + dependency_score * 0.20
            + failure_score * 0.15
        )

        return {
            "id": proposal_id,
            "skill_id": skill_id,
            "name": skill_name,
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

    def save_result(self, result):

        self.result_file.parent.mkdir(parents=True, exist_ok=True)

        temporary_file = self.result_file.with_name(
            f".{self.result_file.name}.{uuid.uuid4().hex}.tmp"
        )

        try:
            temporary_file.write_text(
                json.dumps(result, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )
            os.replace(temporary_file, self.result_file)

        finally:
            try:
                temporary_file.unlink(missing_ok=True)
            except OSError:
                pass

    def prioritize(self):

        discovery_result = self.discovery.discover()

        if (
            isinstance(discovery_result, tuple)
            and len(discovery_result) == 2
        ):
            proposals, new_candidates = discovery_result
        elif isinstance(discovery_result, list):
            proposals = discovery_result
            new_candidates = []
        else:
            raise ValueError(
                "Hasil discovery tidak memiliki format yang dikenali."
            )

        if not isinstance(proposals, list):
            proposals = []

        if not isinstance(new_candidates, list):
            new_candidates = []

        evaluated = []

        for skill in proposals:
            try:
                evaluated.append(self.evaluate_skill(skill))
            except (ValueError, TypeError, KeyError) as error:
                print("Peringatan: kandidat dilewati:", error)

        evaluated.sort(
            key=lambda item: (
                item["status"] == "terverifikasi",
                -item["total"]
            )
        )

        for index, item in enumerate(evaluated, start=1):
            item["rank"] = index

        result = {
            "selected_skill": evaluated[0] if evaluated else None,
            "all_priorities": evaluated,
            "unreviewed_candidates": new_candidates
        }

        self.save_result(result)

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

            print("ID usulan:", item["id"])
            print("ID kemampuan:", item["skill_id"])
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
            print("\nTidak ada kebutuhan pengembangan yang ditemukan.")

        print(
            "\nKandidat kemampuan baru yang belum ditinjau:",
            len(result["unreviewed_candidates"])
        )

        return result


def main():

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
