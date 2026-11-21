
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain.zora import Zora
from developer.self_development import ZoraSelfDevelopment
from developer.development_planner import ZoraDevelopmentPlanner
from developer.skill_discovery import ZoraSkillDiscovery
from developer.skill_prioritization import ZoraSkillPrioritization
from developer.development_history import ZoraDevelopmentHistory
from developer.learning_analyzer import ZoraLearningAnalyzer


class ZoraAutonomousDecision:

    def __init__(self, planner, discovery, prioritization, history):

        self.planner = planner
        self.discovery = discovery
        self.prioritization = prioritization
        self.history = history

        self.decision_file = (
            ROOT / "data" / "zora_autonomous_decision.json"
        )

    def decide(self):

        learning = ZoraLearningAnalyzer(
            self.history
        ).analyze()

        records = self.history.report()["history"]

        latest_status = {}

        for item in records:

            skill_id = item.get("skill_id")

            if not skill_id:
                continue

            latest_status[skill_id] = {
                "name": item.get("skill_name", skill_id),
                "success": item.get("success") is True
            }

        failed_skills = [
            skill_id
            for skill_id, status in latest_status.items()
            if not status["success"]
        ]

        selected = None
        reason = ""

        # Perbaiki kemampuan jika pengujian terakhir gagal.
        if failed_skills:

            selected_id = failed_skills[0]

            selected = {
                "id": selected_id,
                "name": latest_status[selected_id]["name"]
            }

            reason = (
                "Pengujian terakhir kemampuan ini gagal. "
                "Perlu dilakukan perbaikan."
            )

        else:

            priorities = self.prioritization.prioritize()

            completed_ids = {
                skill_id
                for skill_id, status in latest_status.items()
                if status["success"]
            }

            for candidate in priorities["all_priorities"]:

                if candidate["id"] not in completed_ids:

                    selected = {
                        "id": candidate["id"],
                        "name": candidate["name"],
                        "priority_score": candidate["total"],
                        "rank": candidate["rank"]
                    }

                    reason = (
                        "Memilih kemampuan yang belum memiliki "
                        "hasil pengembangan berhasil."
                    )

                    break

        if selected:

            decision = {
                "success": True,
                "selected_skill": selected,
                "reason": reason,
                "learning_analysis": learning
            }

        else:

            decision = {
                "success": True,
                "selected_skill": None,
                "reason": (
                    "Seluruh kemampuan yang tercatat telah berhasil "
                    "pada pengujian terakhir. Diperlukan penemuan "
                    "kemampuan baru."
                ),
                "learning_analysis": learning
            }

        self.decision_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.decision_file.write_text(
            json.dumps(
                decision,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        return decision

    def report(self):

        self.planner.create_plan()
        self.discovery.discover()

        decision = self.decide()

        print("\nZORA AUTONOMOUS DEVELOPMENT DECISION")
        print("------------------------------------")

        if decision["selected_skill"]:

            print(
                "Kemampuan pilihan:",
                decision["selected_skill"]["name"]
            )

        else:

            print("Belum ada kemampuan baru untuk dikembangkan.")

        print("\nAlasan keputusan:")
        print(decision["reason"])

        print("\nAnalisis riwayat:")
        print(
            "Berhasil:",
            decision["learning_analysis"]["total_berhasil"]
        )
        print(
            "Gagal:",
            decision["learning_analysis"]["total_gagal"]
        )

        print("\nKeputusan tersimpan:")
        print(self.decision_file)

        return decision


def main():

    zora = Zora()

    try:

        developer = ZoraSelfDevelopment(zora)
        planner = ZoraDevelopmentPlanner(developer)
        discovery = ZoraSkillDiscovery(planner)
        prioritization = ZoraSkillPrioritization(discovery)
        history = ZoraDevelopmentHistory()

        decision_engine = ZoraAutonomousDecision(
            planner,
            discovery,
            prioritization,
            history
        )

        decision_engine.report()

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
