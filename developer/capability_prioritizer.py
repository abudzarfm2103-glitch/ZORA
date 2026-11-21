
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.capability_evaluator import ZoraCapabilityEvaluator


class ZoraCapabilityPrioritizer:

    def __init__(self):

        self.evaluator = ZoraCapabilityEvaluator()

        self.priority_order = [
            "belum_berhasil",
            "perlu_perbaikan",
            "belum_diuji"
        ]

    def select_next(self):

        report = self.evaluator.evaluate()

        candidates = []

        for skill_id, item in report.items():

            if item["status"] in self.priority_order:

                priority = self.priority_order.index(
                    item["status"]
                )

                candidates.append({
                    "id": skill_id,
                    "name": item["name"],
                    "status": item["status"],
                    "priority": priority
                })

        candidates.sort(
            key=lambda item: item["priority"]
        )

        if not candidates:

            return {
                "success": True,
                "selected": None,
                "message": "Semua kemampuan sudah terverifikasi."
            }

        selected = candidates[0]

        return {
            "success": True,
            "selected": selected,
            "message": (
                "Dipilih berdasarkan status evaluasi: "
                + selected["status"]
            )
        }

    def show_report(self):

        result = self.select_next()

        print("\nZORA CAPABILITY PRIORITIZER")
        print("===========================")

        if result["selected"] is None:
            print(result["message"])
            return result

        selected = result["selected"]

        print("Kemampuan berikutnya:", selected["name"])
        print("Status:", selected["status"])
        print("Alasan:", result["message"])

        return result


def main():

    prioritizer = ZoraCapabilityPrioritizer()
    prioritizer.show_report()


if __name__ == "__main__":
    main()
