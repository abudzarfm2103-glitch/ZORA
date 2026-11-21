
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain.zora import Zora
from developer.development_history import ZoraDevelopmentHistory
from developer.decision_task_generator import ZoraDecisionTaskGenerator
from developer.autonomous_task_executor import ZoraAutonomousTaskExecutor


MAX_CYCLES = 3


def main():

    zora = Zora()

    try:

        history = ZoraDevelopmentHistory()
        generator = ZoraDecisionTaskGenerator()

        executor = ZoraAutonomousTaskExecutor(
            zora,
            generator
        )

        successful_cycles = 0
        failed_cycles = 0

        print("\nZORA AUTONOMOUS LEARNING SYSTEM")
        print("================================")
        print("Maksimum siklus:", MAX_CYCLES)

        for cycle in range(1, MAX_CYCLES + 1):

            print("\n")
            print("=" * 45)
            print("SIKLUS PENGEMBANGAN KE-", cycle)
            print("=" * 45)

            print("\nTAHAP 1: EVALUASI KEMAMPUAN")

            task_result = generator.generate()

            if not task_result.get("success"):

                print(
                    "ZORA tidak dapat membuat tugas:",
                    task_result.get("message")
                )

                failed_cycles += 1
                break

            task = task_result["task"]

            print("Kemampuan:", task["skill_name"])
            print("Jenis:", task["development_type"])
            print("Prioritas:", task["priority_score"])

            print("\nTAHAP 2: PERENCANAAN PENGEMBANGAN")
            print("Tujuan:", task["objective"])
            print("Tugas berhasil disiapkan.")

            print("\nTAHAP 3: PENGEMBANGAN DAN PENGUJIAN")

            result = executor.execute(
                selected_task=task
            )

            if result and result.get("success"):

                successful_cycles += 1
                print("\nSIKLUS BERHASIL.")

            else:

                failed_cycles += 1
                print("\nSIKLUS GAGAL.")
                print("ZORA menghentikan pengembangan otomatis.")
                break

        report = history.report()

        print("\n")
        print("=" * 45)
        print("LAPORAN PENGEMBANGAN ZORA")
        print("=" * 45)

        print("Siklus dijalankan:", successful_cycles + failed_cycles)
        print("Siklus berhasil:", successful_cycles)
        print("Siklus gagal:", failed_cycles)

        print("\nRIWAYAT KESELURUHAN")
        print("Total percobaan:", report["total"])
        print("Berhasil:", report["successful"])
        print("Gagal:", report["failed"])

        print("\nZORA menyelesaikan sesi pengembangan.")

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
