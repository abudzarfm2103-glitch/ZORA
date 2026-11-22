import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain.zora import Zora
from developer.development_history import ZoraDevelopmentHistory
from developer.decision_task_generator import ZoraDecisionTaskGenerator
from developer.autonomous_task_executor import ZoraAutonomousTaskExecutor


MAX_CYCLES = 3


def normalize_max_cycles(value):

    if not isinstance(value, int) or isinstance(value, bool):
        return MAX_CYCLES

    return max(1, min(value, MAX_CYCLES))


def validate_task(task):

    if not isinstance(task, dict):
        return False

    required_strings = (
        "skill_id",
        "skill_name",
        "instruction",
        "expected_output"
    )

    for key in required_strings:
        value = task.get(key)

        if not isinstance(value, str) or not value.strip():
            return False

    criteria = task.get("evaluation_criteria")

    if not isinstance(criteria, dict) or not criteria:
        return False

    return True


def run_learning_cycles(
    generator,
    executor,
    history,
    max_cycles=MAX_CYCLES
):

    cycle_limit = normalize_max_cycles(max_cycles)

    successful_cycles = 0
    failed_cycles = 0
    stopped_reason = "Batas siklus tercapai."

    print("\nZORA AUTONOMOUS LEARNING SYSTEM")
    print("================================")
    print("Maksimum siklus:", cycle_limit)

    for cycle in range(1, cycle_limit + 1):

        print("\n" + "=" * 45)
        print("SIKLUS PENGEMBANGAN KE-", cycle)
        print("=" * 45)

        try:

            print("\nTAHAP 1: EVALUASI DAN PEMBUATAN TUGAS")

            task_result = generator.generate()

            if not isinstance(task_result, dict):
                stopped_reason = "Hasil generator tidak valid."
                failed_cycles += 1
                print(stopped_reason)
                break

            if task_result.get("success") is not True:
                stopped_reason = task_result.get(
                    "message",
                    "Generator gagal membuat tugas."
                )
                failed_cycles += 1
                print(stopped_reason)
                break

            task = task_result.get("task")

            if not validate_task(task):
                stopped_reason = "Struktur tugas tidak memenuhi persyaratan."
                failed_cycles += 1
                print(stopped_reason)
                break

            print("Kemampuan:", task["skill_name"])
            print("Jenis:", task.get("development_type", "tidak diketahui"))
            print("Tujuan:", task.get("objective", "tidak tersedia"))

            print("\nTAHAP 2: PENGEMBANGAN DAN PENGUJIAN")

            result = executor.execute(selected_task=task)

            if not isinstance(result, dict):
                stopped_reason = "Executor memberikan hasil yang tidak valid."
                failed_cycles += 1
                print(stopped_reason)
                break

            if result.get("success") is True:
                successful_cycles += 1
                print("\nSIKLUS BERHASIL.")
            else:
                failed_cycles += 1
                stopped_reason = result.get(
                    "message",
                    "Pengembangan atau evaluasi gagal."
                )
                print("\nSIKLUS GAGAL.")
                print("ZORA menghentikan pengembangan otomatis.")
                break

        except Exception as error:
            failed_cycles += 1
            stopped_reason = (
                "Kesalahan saat menjalankan siklus: "
                + type(error).__name__
            )
            print(stopped_reason)
            break

    try:
        report = history.report()

        if not isinstance(report, dict):
            raise ValueError("Format laporan riwayat tidak valid.")

        history_report = {
            "total": report.get("total", 0),
            "successful": report.get("successful", 0),
            "failed": report.get("failed", 0)
        }

    except Exception as error:
        history_report = {
            "error": type(error).__name__
        }

    result = {
        "cycles_run": successful_cycles + failed_cycles,
        "successful_cycles": successful_cycles,
        "failed_cycles": failed_cycles,
        "max_cycles": cycle_limit,
        "stopped_reason": stopped_reason,
        "history": history_report
    }

    print("\n" + "=" * 45)
    print("LAPORAN PENGEMBANGAN ZORA")
    print("=" * 45)

    print("Siklus dijalankan:", result["cycles_run"])
    print("Siklus berhasil:", successful_cycles)
    print("Siklus gagal:", failed_cycles)
    print("Alasan berhenti:", stopped_reason)

    print("\nRIWAYAT KESELURUHAN")

    if "error" in history_report:
        print("Laporan riwayat gagal dibaca:", history_report["error"])
    else:
        print("Total percobaan:", history_report["total"])
        print("Berhasil:", history_report["successful"])
        print("Gagal:", history_report["failed"])

    print("\nZORA menyelesaikan sesi pengembangan.")

    return result


def main():

    zora = Zora()

    try:

        history = ZoraDevelopmentHistory()
        generator = ZoraDecisionTaskGenerator()

        executor = ZoraAutonomousTaskExecutor(
            zora,
            generator,
            max_attempts=3
        )

        return run_learning_cycles(
            generator,
            executor,
            history,
            MAX_CYCLES
        )

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
