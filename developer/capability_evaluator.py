
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ZoraCapabilityEvaluator:

    MIN_SUCCESS_STREAK = 2
    MIN_TESTS_FOR_REINFORCEMENT = 3
    MIN_SUCCESS_RATE = 0.70

    def __init__(self):

        self.history_file = (
            ROOT / "data" / "zora_autonomous_development_history.json"
        )

        self.state_file = (
            ROOT / "data" / "zora_self_development.json"
        )

        self.report_file = (
            ROOT / "data" / "zora_capability_report.json"
        )

        self.capabilities = {
            "problem_solving": "Pemecahan masalah",
            "data_analysis": "Analisis data",
            "logical_reasoning": "Penalaran logis",
            "calculation": "Kemampuan perhitungan",
            "condition_analysis": "Analisis kondisi",
            "pattern_recognition": "Pengenalan pola",
            "language_understanding": "Pemahaman bahasa alami",
            "planning": "Perencanaan",
            "code_debugging": "Perbaikan kesalahan kode",
            "source_evaluation": "Evaluasi sumber informasi",
            "decision_making": "Pengambilan keputusan"
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

    def calculate_streak(self, records):

        streak = 0

        for record in reversed(records):

            if record.get("success") is True:
                streak += 1
            else:
                break

        return streak

    def evaluate_skill(
        self,
        skill_id,
        skill_name,
        records,
        verified_old=False
    ):

        successful = sum(
            1 for item in records
            if item.get("success") is True
        )

        failed = sum(
            1 for item in records
            if item.get("success") is False
        )

        total = successful + failed

        success_rate = (
            successful / total
            if total > 0 else 0
        )

        streak = self.calculate_streak(records)

        latest_success = (
            records[-1].get("success")
            if records else None
        )

        if records:

            if latest_success is False:
                status = "perlu_perbaikan"
                recommendation = (
                    "Analisis kegagalan terakhir dan perbaiki kemampuan."
                )

            elif (
                total >= self.MIN_TESTS_FOR_REINFORCEMENT
                and success_rate < self.MIN_SUCCESS_RATE
            ):
                status = "perlu_penguatan"
                recommendation = (
                    "Pelajari penyebab kegagalan dan tingkatkan "
                    "konsistensi kemampuan."
                )

            elif (
                streak >= self.MIN_SUCCESS_STREAK
                and success_rate >= self.MIN_SUCCESS_RATE
            ):
                status = "terverifikasi"
                recommendation = (
                    "Pertahankan kemampuan dan lakukan pengujian "
                    "berkala."
                )

            else:
                status = "perlu_pengujian"
                recommendation = (
                    "Lakukan pengujian tambahan untuk memastikan "
                    "konsistensi kemampuan."
                )

        elif verified_old:

            status = "terverifikasi"
            recommendation = (
                "Kemampuan memiliki verifikasi dari prototype lama. "
                "Perlu pengujian ulang secara berkala."
            )

        else:

            status = "belum_diuji"
            recommendation = (
                "Buat tugas pengembangan dan pengujian kemampuan."
            )

        return {
            "name": skill_name,
            "successful": successful,
            "failed": failed,
            "total_tests": total,
            "success_rate": round(success_rate, 2),
            "success_streak": streak,
            "latest_success": latest_success,
            "status": status,
            "recommendation": recommendation
        }

    def evaluate(self):

        autonomous_history = self.read_json(
            self.history_file, []
        )

        development_state = self.read_json(
            self.state_file, {}
        )

        if not isinstance(autonomous_history, list):
            autonomous_history = []

        if not isinstance(development_state, dict):
            development_state = {}

        old_history = development_state.get("history", [])

        if not isinstance(old_history, list):
            old_history = []

        completed = development_state.get(
            "completed_prototypes", []
        )

        if not isinstance(completed, list):
            completed = []

        report = {}

        for skill_id, skill_name in self.capabilities.items():

            records = [
                item for item in autonomous_history
                if isinstance(item, dict)
                and item.get("skill_id") == skill_id
                and isinstance(item.get("success"), bool)
            ]

            old_records = [
                item for item in old_history
                if isinstance(item, dict)
                and (
                    skill_id in str(item.get("filename", ""))
                    or item.get("task") == skill_name
                )
            ]

            old_success = any(
                item.get("success") is True
                for item in old_records
            )

            verified_old = (
                skill_id in completed and old_success
            )

            report[skill_id] = self.evaluate_skill(
                skill_id,
                skill_name,
                records,
                verified_old
            )

        self.report_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.report_file.write_text(
            json.dumps(
                report,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        return report

    def show_report(self):

        report = self.evaluate()

        print("\nZORA CAPABILITY EVALUATION")
        print("==========================")

        for skill_id, item in report.items():

            print("\nKemampuan:", item["name"])
            print("ID:", skill_id)
            print("Berhasil:", item["successful"])
            print("Gagal:", item["failed"])
            print("Total pengujian:", item["total_tests"])
            print(
                "Tingkat keberhasilan:",
                str(round(item["success_rate"] * 100, 1)) + "%"
            )
            print("Berhasil berturut-turut:", item["success_streak"])
            print("Status:", item["status"])
            print("Rekomendasi:", item["recommendation"])

        verified = sum(
            1 for item in report.values()
            if item["status"] == "terverifikasi"
        )

        needs_development = len(report) - verified

        print("\nRINGKASAN")
        print("Terverifikasi:", verified)
        print("Masih membutuhkan pengembangan:", needs_development)

        return report


def main():

    evaluator = ZoraCapabilityEvaluator()
    evaluator.show_report()


if __name__ == "__main__":
    main()
