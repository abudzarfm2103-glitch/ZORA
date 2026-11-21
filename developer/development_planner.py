
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain.zora import Zora
from developer.self_development import ZoraSelfDevelopment


class ZoraDevelopmentPlanner:

    def __init__(self, developer):
        self.developer = developer

    def inspect_capabilities(self):

        state = self.developer.verify_previous_progress()
        completed = state["completed_prototypes"]

        capabilities = []

        for task in self.developer.roadmap:

            status = (
                "terverifikasi"
                if task["id"] in completed
                else "belum dikuasai"
            )

            capabilities.append({
                "id": task["id"],
                "name": task["name"],
                "status": status
            })

        return capabilities

    def identify_gaps(self, capabilities):

        return [
            item for item in capabilities
            if item["status"] != "terverifikasi"
        ]

    def create_plan(self):

        capabilities = self.inspect_capabilities()
        gaps = self.identify_gaps(capabilities)

        progress = self.developer.evaluate_progress()

        next_task = progress["next_task"]

        if next_task:
            priority = next_task["name"]
        else:
            priority = "Kemampuan analisis data"

        return {
            "kemampuan": capabilities,
            "kekurangan": gaps,
            "prioritas_berikutnya": priority
        }

    def report(self):

        plan = self.create_plan()

        print("\nZORA AUTONOMOUS DEVELOPMENT PLANNER")
        print("------------------------------------")

        print("\nKemampuan berdasarkan hasil pengujian:")

        for item in plan["kemampuan"]:
            print("-", item["name"], ":", item["status"])

        print("\nKekurangan kemampuan:")

        if plan["kekurangan"]:
            for item in plan["kekurangan"]:
                print("-", item["name"])
        else:
            print("- Belum ditemukan.")

        print("\nPrioritas pengembangan berikutnya:")
        print(plan["prioritas_berikutnya"])

        return plan


def main():

    zora = Zora()

    try:
        developer = ZoraSelfDevelopment(zora)
        planner = ZoraDevelopmentPlanner(developer)

        planner.report()

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
