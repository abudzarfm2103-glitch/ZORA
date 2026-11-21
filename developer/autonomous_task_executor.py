
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.self_repair import ZoraSelfRepair
from developer.code_quality_evaluator import ZoraCodeQualityEvaluator
from developer.development_history import ZoraDevelopmentHistory


class ZoraAutonomousTaskExecutor:

    def __init__(self, zora, task_generator, max_attempts=3):

        self.zora = zora
        self.task_generator = task_generator
        self.max_attempts = max_attempts

        self.repair = ZoraSelfRepair(
            zora,
            max_attempts=3
        )

        self.evaluator = ZoraCodeQualityEvaluator()
        self.history = ZoraDevelopmentHistory()

    def create_filename(self, skill_id):

        folder = "developer_sandbox/pengujian"
        nomor = 1

        while True:

            filename = (
                f"{folder}/autonomous_"
                f"{skill_id}_{nomor}.py"
            )

            target = self.zora.execution.validate_path(filename)

            if not target.exists():
                return filename

            nomor += 1

    def execute(self, selected_task=None):

        if selected_task is None:

            generated = self.task_generator.generate()

            if not generated.get("success"):
                return generated

            task = generated["task"]

        else:
            task = selected_task

        print("\nZORA AUTONOMOUS TASK EXECUTOR")
        print("-----------------------------")
        print("Tugas:", task["skill_name"])
        print("Sumber:", task.get("task_source", "tidak diketahui"))

        criteria = task.get("evaluation_criteria")

        if not isinstance(criteria, dict) or not criteria:

            return {
                "success": False,
                "message": "Tugas tidak memiliki kriteria evaluasi resmi."
            }

        base_instruction = (
            task["instruction"]
            + "\nTarget output wajib: "
            + task["expected_output"]
        )

        feedback = ""
        last_result = None

        for attempt in range(1, self.max_attempts + 1):

            print(f"\nPENGEMBANGAN KE-{attempt}")

            instruction = base_instruction

            if feedback:

                instruction += (
                    "\n\nPERBAIKI KEGAGALAN SEBELUMNYA:"
                    "\n"
                    + feedback
                    + "\nBuat ulang kode yang memenuhi semua kriteria."
                )

            filename = self.create_filename(task["skill_id"])

            print("ZORA sedang membuat prototype...")

            result = self.repair.run(
                instruction=instruction,
                filename=filename
            )

            if not result.get("success"):

                evaluation = {
                    "success": False,
                    "message": result.get(
                        "message",
                        "Pembuatan atau pengujian kode gagal."
                    ),
                    "checks": {}
                }

                code = result.get("code", "")
                output = result.get("output", "")

            else:

                code = result.get("code", "")
                output = result.get("output", "").strip()

                print("Pemeriksaan Sandbox: LULUS")

                evaluation = self.evaluator.evaluate(
                    code,
                    output,
                    task["skill_id"],
                    task=task
                )

            for name, status in evaluation.get("checks", {}).items():

                print(
                    "-",
                    name,
                    ":",
                    "LULUS" if status else "GAGAL"
                )

            current_result = {
                "success": bool(evaluation.get("success")),
                "task": task,
                "filename": filename,
                "code": code,
                "output": output,
                "evaluation": evaluation,
                "attempt": attempt
            }

            self.history.record(current_result)
            last_result = current_result

            if current_result["success"]:

                print("\nStatus:", evaluation["message"])
                print("Pengembangan berhasil diverifikasi.")
                break

            feedback = evaluation.get(
                "message",
                "Hasil kode belum memenuhi kriteria."
            )

            failed_checks = [
                name
                for name, passed in evaluation.get("checks", {}).items()
                if not passed
            ]

            if failed_checks:

                feedback += (
                    "\nKriteria yang gagal: "
                    + ", ".join(failed_checks)
                )

            print("\nEvaluasi belum berhasil.")
            print("Alasan:", feedback)

            if attempt < self.max_attempts:
                print("ZORA akan mencoba memperbaiki kode.")

        report = self.history.report()

        print("\nRIWAYAT PENGEMBANGAN")
        print("Total:", report["total"])
        print("Berhasil:", report["successful"])
        print("Gagal:", report["failed"])

        if last_result and last_result["success"]:
            print("\nHASIL AKHIR: BERHASIL")
        else:
            print("\nHASIL AKHIR: BELUM BERHASIL")

        return last_result


def main():

    from brain.zora import Zora
    from developer.decision_task_generator import ZoraDecisionTaskGenerator

    zora = Zora()

    try:

        generator = ZoraDecisionTaskGenerator()

        executor = ZoraAutonomousTaskExecutor(
            zora,
            generator
        )

        print(executor.execute())

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
