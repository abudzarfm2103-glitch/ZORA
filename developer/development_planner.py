from developer.self_development import ZoraSelfDevelopment


class ZoraDevelopmentPlanner:

    def __init__(self, developer):
        self.developer = developer

    def inspect_capabilities(self):

        state = self.developer.verify_previous_progress()

        completed = set(state["completed_prototypes"])
        capabilities = []

        for task in self.developer.roadmap:

            verified = task["id"] in completed

            capabilities.append({
                "id": task["id"],
                "name": task["name"],
                "status": (
                    "terverifikasi"
                    if verified
                    else "belum dikuasai"
                )
            })

        return capabilities

    def identify_gaps(self, capabilities):

        return [
            item.copy()
            for item in capabilities
            if item["status"] != "terverifikasi"
        ]

    def create_plan(self):

        capabilities = self.inspect_capabilities()
        gaps = self.identify_gaps(capabilities)

        next_task = next(
            (
                task for task in self.developer.roadmap
                if any(
                    gap["id"] == task["id"]
                    for gap in gaps
                )
            ),
            None
        )

        return {
            "kemampuan": capabilities,
            "kekurangan": gaps,
            "prioritas_berikutnya": (
                next_task["name"]
                if next_task
                else None
            ),
            "seluruh_roadmap_selesai": not bool(gaps)
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
            print("- Tidak ada.")

        print("\nPrioritas pengembangan berikutnya:")

        if plan["prioritas_berikutnya"]:
            print(plan["prioritas_berikutnya"])
        else:
            print("Seluruh roadmap telah selesai.")

        return plan


def main():

    from brain.zora import Zora

    zora = Zora()

    try:
        developer = ZoraSelfDevelopment(zora)
        planner = ZoraDevelopmentPlanner(developer)

        planner.report()

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
