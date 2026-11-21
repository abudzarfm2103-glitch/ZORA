
import sys
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain.zora import Zora


class ZoraSelfRepair:

    def __init__(self, zora, max_attempts=3):
        self.zora = zora
        self.max_attempts = max_attempts

    def run(self, instruction, filename, initial_code=None):

        target = self.zora.execution.validate_path(filename)

        if target.exists():
            return {
                "success": False,
                "message": "File sudah tersedia. Tidak akan ditimpa."
            }

        if initial_code is None:

            generated = self.zora.generate_code(instruction)

            if not generated.get("success"):
                return generated

            code = generated["code"]

        else:
            code = initial_code

        try:
            tree = ast.parse(code)
            self.zora.execution.sandbox.validate_code(tree)

        except (SyntaxError, ValueError, PermissionError, TypeError) as error:
            return {
                "success": False,
                "message": f"Kode awal ditolak: {error}"
            }

        created = self.zora.execution.create_file(filename)

        if not created.get("success"):
            return created

        saved = self.zora.execution.write_file(filename, code)

        if not saved.get("success"):
            return saved

        for attempt in range(self.max_attempts + 1):

            print(f"\nPengujian ke-{attempt + 1}...")

            result = self.zora.execution.test_code(filename)

            if result.get("success"):

                return {
                    "success": True,
                    "message": "Kode berhasil diperbaiki dan diuji.",
                    "attempts": attempt,
                    "code": code,
                    "output": result.get("output", "")
                }

            if attempt == self.max_attempts:
                break

            error_message = result.get("message", str(result))

            print("Kesalahan ditemukan:", error_message)
            print("ZORA sedang memperbaiki kode...")

            repair_instruction = f"""
Perbaiki kode Python berikut berdasarkan tujuan dan kesalahan pengujian.

Tujuan program:
{instruction}

Kode yang gagal:
{code}

Pesan kesalahan:
{error_message}

Buat kode pengganti yang memperbaiki kesalahan tersebut.
Pertahankan tujuan program.
Ikuti seluruh batasan Sandbox.
Hasilkan hanya kode Python.
"""

            repaired = self.zora.generate_code(repair_instruction)

            if not repaired.get("success"):
                return {
                    "success": False,
                    "message": repaired.get("message"),
                    "attempts": attempt + 1
                }

            code = repaired["code"]

            saved = self.zora.execution.write_file(
                filename,
                code
            )

            if not saved.get("success"):
                return saved

        return {
            "success": False,
            "message": "ZORA belum berhasil memperbaiki kode setelah batas percobaan.",
            "attempts": self.max_attempts
        }


def main():

    zora = Zora()

    try:

        repair = ZoraSelfRepair(zora)

        hasil = repair.run(
            instruction="Buat program untuk menghitung 10 dibagi 2 dan tampilkan hasilnya.",
            filename="developer_sandbox/pengujian/hasil_perbaikan_01.py",
            initial_code="hasil = 10 / 0\nprint(hasil)"
        )

        print("\nHASIL AKHIR:")
        print(hasil)

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
