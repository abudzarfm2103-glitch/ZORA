import json
import os
import sys
import tempfile
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
        path = Path(path)

        if path.is_symlink():
            raise ValueError(f"File JSON tidak boleh berupa symlink: {path}")

        if not path.exists():
            return default

        if not path.is_file():
            raise ValueError(f"Lokasi JSON bukan file biasa: {path}")

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(
                f"JSON rusak. File asli dipertahankan: {path} "
                f"(baris {error.lineno}, kolom {error.colno})"
            ) from error
        except OSError as error:
            raise OSError(
                f"Gagal membaca JSON: {path}: {error}"
            ) from error

    def validate_history(self, history):
        if not isinstance(history, list):
            raise ValueError("Riwayat pengembangan harus berupa daftar.")

        for item in history:
            if not isinstance(item, dict):
                raise ValueError("Riwayat mengandung data yang tidak valid.")

            if "success" in item and not isinstance(item["success"], bool):
                raise ValueError("Status keberhasilan riwayat tidak valid.")

        return history

    def validate_capability_report(self, report):
        if not isinstance(report, dict):
            raise ValueError("Laporan kemampuan harus berupa objek.")

        for skill_id, item in report.items():
            if not isinstance(skill_id, str) or not isinstance(item, dict):
                raise ValueError("Struktur laporan kemampuan tidak valid.")

        return report

    def evaluate_skill(self, skill):
        if not isinstance(skill, dict):
            raise ValueError("Data kemampuan tidak valid.")

        proposal_id = skill.get("id")
        skill_id = skill.get("skill_id", proposal_id)
        skill_name = skill.get("name", skill_id)

        if not isinstance(skill_id, str) or not skill_id:
            raise ValueError("ID kemampuan tidak valid.")

        history = self.validate_history(
            self.read_json(self.history_file, [])
        )

        capability_report = self.validate_capability_report(
            self.read_json(self.capability_file, {})
        )

        records = [
            item for item in history
            if item.get("skill_id") == skill_id
            and isinstance(item.get("success"), bool)
        ]

        capability = capability_report.get(skill_id, {})
        status = capability.get("status", skill.get("status", "belum_diuji"))

        successful = sum(
            1 for item in records if item["success"] is True
        )

        failed = sum(
            1 for item in records if item["success"] is False
        )

        latest_failed = (
            bool(records)
            and records[-1]["success"] is False
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

        if self.result_file.is_symlink():
            raise ValueError(
                f"Menolak menimpa symlink: {self.result_file}"
            )

        if self.result_file.exists():
            if not self.result_file.is_file():
                raise ValueError("Target hasil prioritas bukan file biasa.")
            # Jangan pernah menimpa hasil lama yang JSON-nya rusak.
            self.read_json(self.result_file, None)

        serialized = json.dumps(
            result,
            indent=4,
            ensure_ascii=False,
            allow_nan=False
        )

        temporary_path = None

        try:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{self.result_file.name}.",
                suffix=".tmp",
                dir=str(self.result_file.parent)
            )
            temporary_path = Path(temporary_name)

            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(serialized)
                file.flush()
                os.fsync(file.fileno())

            if self.result_file.is_symlink():
                raise ValueError("Target hasil berubah menjadi symlink.")

            os.replace(temporary_path, self.result_file)
            temporary_path = None

            try:
                directory_fd = os.open(self.result_file.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
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
            raise ValueError("Daftar proposal discovery tidak valid.")

        if not isinstance(new_candidates, list):
            raise ValueError("Daftar kandidat baru tidak valid.")

        evaluated = []

        for skill in proposals:
            evaluated.append(self.evaluate_skill(skill))

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
            print(f"\nPeringkat {item['rank']}: {item['name']}")
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
