
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.development_history import ZoraDevelopmentHistory


class ZoraLearningAnalyzer:

    def __init__(self, history):
        self.history = history

    def analyze(self):

        report = self.history.report()
        records = report["history"]

        skills = {}

        for item in records:

            skill_id = item.get("skill_id")

            if not skill_id:
                continue

            if skill_id not in skills:
                skills[skill_id] = {
                    "name": item.get("skill_name", skill_id),
                    "successful": 0,
                    "failed": 0
                }

            if item.get("success"):
                skills[skill_id]["successful"] += 1
            else:
                skills[skill_id]["failed"] += 1

        verified = []
        needs_improvement = []

        for data in skills.values():

            if data["successful"] > 0 and data["failed"] == 0:
                verified.append(data["name"])
            else:
                needs_improvement.append(data["name"])

        if needs_improvement:
            recommendation = (
                "Perbaiki kemampuan yang masih memiliki kegagalan."
            )
        elif verified:
            recommendation = (
                "Kembangkan kemampuan baru dan tingkatkan "
                "kompleksitas pengujian."
            )
        else:
            recommendation = (
                "Mulai pengembangan kemampuan dasar."
            )

        return {
            "total_pengembangan": report["total"],
            "total_berhasil": report["successful"],
            "total_gagal": report["failed"],
            "kemampuan_terverifikasi": verified,
            "perlu_perbaikan": needs_improvement,
            "rekomendasi": recommendation
        }

    def report(self):

        result = self.analyze()

        print("\nZORA AUTONOMOUS LEARNING ANALYZER")
        print("--------------------------------")

        print("Total pengembangan:", result["total_pengembangan"])
        print("Berhasil:", result["total_berhasil"])
        print("Gagal:", result["total_gagal"])

        print("\nKemampuan terverifikasi:")

        for item in result["kemampuan_terverifikasi"]:
            print("-", item)

        print("\nKemampuan perlu perbaikan:")

        if result["perlu_perbaikan"]:
            for item in result["perlu_perbaikan"]:
                print("-", item)
        else:
            print("- Tidak ada.")

        print("\nRekomendasi ZORA:")
        print(result["rekomendasi"])

        return result


def main():

    history = ZoraDevelopmentHistory()
    analyzer = ZoraLearningAnalyzer(history)

    analyzer.report()


if __name__ == "__main__":
    main()
