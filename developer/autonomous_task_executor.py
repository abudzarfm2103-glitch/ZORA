import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.self_repair import ZoraSelfRepair
from developer.code_quality_evaluator import ZoraCodeQualityEvaluator
from developer.development_history import ZoraDevelopmentHistory


class ZoraAutonomousTaskExecutor:

    MAX_ATTEMPTS = 3
    MAX_FILENAME_ATTEMPTS = 10000

    def __init__(self, zora, task_generator, max_attempts=3):
        self.zora = zora
        self.task_generator = task_generator

        try:
            requested_attempts = int(max_attempts)
        except (TypeError, ValueError):
            requested_attempts = 3

        self.max_attempts = max(
            1,
            min(requested_attempts, self.MAX_ATTEMPTS)
        )

        self.repair = ZoraSelfRepair(
            zora,
            max_attempts=self.MAX_ATTEMPTS
        )

        self.evaluator = ZoraCodeQualityEvaluator()
        self.history = ZoraDevelopmentHistory()

    def create_filename(self, skill_id):
        if not isinstance(skill_id, str):
            raise ValueError("ID kemampuan tidak valid.")

        safe_skill_id = re.sub(
            r"[^a-zA-Z0-9_-]",
            "_",
            skill_id
        ).strip("_")

        if not safe_skill_id:
            raise ValueError("ID kemampuan tidak boleh kosong.")

        folder = "developer_sandbox/pengujian"

        for nomor in range(1, self.MAX_FILENAME_ATTEMPTS + 1):
            filename = (
                f"{folder}/autonomous_"
                f"{safe_skill_id}_{nomor}.py"
            )

            target = self.zora.execution.validate_path(filename)

            if not target.exists():
                return filename

        raise RuntimeError(
            "Tidak dapat menemukan nama file prototype yang tersedia."
        )

    def validate_task(self, task):
        if not isinstance(task, dict):
            return False, "Format tugas tidak valid."

        required_fields = (
            "skill_id",
            "skill_name",
            "instruction",
            "expected_output"
        )

        for field in required_fields:
            value = task.get(field)

            if not isinstance(value, str) or not value.strip():
                return False, f"Data tugas {field} tidak valid."

        criteria = task.get("evaluation_criteria")

        if not isinstance(criteria, dict) or not criteria:
            return False, "Tugas tidak memiliki kriteria evaluasi resmi."

        return True, ""

    def execute(self, selected_task=None):
        if selected_task is None:
            generated = self.task_generator.generate()

            if not isinstance(generated, dict):
                return {
                    "success": False,
                    "message": "Generator menghasilkan format yang tidak valid."
                }

            if not generated.get("success"):
                return generated

            task = generated.get("task")
        else:
            task = selected_task

        valid, message = self.validate_task(task)

        if not valid:
            return {
                "success": False,
                "message": message
            }

        print("\nZORA AUTONOMOUS TASK EXECUTOR")
        print("-----------------------------")
        print("Tugas:", task["skill_name"])
        print("Sumber:", task.get("task_source", "tidak diketahui"))

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
                    "\n\nPERBAIKI KEGAGALAN SEBELUMNYA:\n"
                    + feedback
                    + "\nBuat ulang kode yang memenuhi semua kriteria."
                )

            try:
                filename = self.create_filename(task["skill_id"])
            except Exception as error:
                return {
                    "success": False,
                    "message": (
                        "Gagal menyiapkan file prototype: "
                        + str(error)
                    )
                }

            print("ZORA sedang membuat prototype...")

            try:
                result = self.repair.run(
                    instruction=instruction,
                    filename=filename
                )
            except Exception as error:
                result = {
                    "success": False,
                    "message": "Proses perbaikan gagal: " + str(error)
                }

            if not isinstance(result, dict):
                result = {
                    "success": False,
                    "message": "Hasil prototype tidak valid."
                }

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
                output = result.get("output", "")

                if not isinstance(code, str) or not isinstance(output, str):
                    evaluation = {
                        "success": False,
                        "message": "Kode atau output prototype tidak valid.",
                        "checks": {}
                    }
                    code = ""
                    output = ""
                else:
                    output = output.strip()

                    print("Pemeriksaan Sandbox: LULUS")

                    try:
                        evaluation = self.evaluator.evaluate(
                            code,
                            output,
                            task["skill_id"],
                            task=task
                        )
                    except Exception as error:
                        evaluation = {
                            "success": False,
                            "message": (
                                "Evaluasi kode gagal: " + str(error)
                            ),
                            "checks": {}
                        }

            if not isinstance(evaluation, dict):
                evaluation = {
                    "success": False,
                    "message": "Evaluator menghasilkan format tidak valid.",
                    "checks": {}
                }

            checks = evaluation.get("checks", {})
            if not isinstance(checks, dict):
                checks = {}

            for name, status in checks.items():
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

            try:
                self.history.record(current_result)
            except Exception as error:
                return {
                    "success": False,
                    "message": (
                        "Hasil pengembangan tidak dapat dicatat: "
                        + str(error)
                    ),
                    "result": current_result
                }

            last_result = current_result

            if current_result["success"]:
                print("\nStatus:", evaluation.get("message", "Berhasil."))
                print("Pengembangan berhasil diverifikasi.")
                break

            feedback = evaluation.get(
                "message",
                "Hasil kode belum memenuhi kriteria."
            )

            failed_checks = [
                name
                for name, passed in checks.items()
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

        try:
            report = self.history.report()
        except Exception:
            report = {}

        print("\nRIWAYAT PENGEMBANGAN")
        print("Total:", report.get("total", "tidak tersedia"))
        print("Berhasil:", report.get("successful", "tidak tersedia"))
        print("Gagal:", report.get("failed", "tidak tersedia"))

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
