import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.zora import Zora


class ZoraSelfRepair:

    MAX_ATTEMPTS = 3

    def __init__(self, zora, max_attempts=3):
        self.zora = zora

        try:
            requested = int(max_attempts)
        except (TypeError, ValueError):
            requested = self.MAX_ATTEMPTS

        self.max_attempts = max(
            0,
            min(requested, self.MAX_ATTEMPTS)
        )

    def validate_code(self, code):
        if not isinstance(code, str):
            raise ValueError("Kode harus berupa teks.")

        maximum = self.zora.execution.MAX_WRITE_SIZE

        if len(code.encode("utf-8")) > maximum:
            raise ValueError("Ukuran kode melebihi batas penyimpanan.")

        tree = ast.parse(code)
        self.zora.execution.sandbox.validate_code(tree)

        return True

    def cleanup_created_file(self, target):
        try:
            if not isinstance(target, Path):
                return False

            workspace = Path(
                self.zora.execution.workspace
            ).resolve()

            try:
                relative = target.relative_to(workspace)
            except ValueError:
                print("Peringatan: penghapusan di luar workspace ditolak.")
                return False

            if not relative.parts:
                return False

            safe_target = self.zora.execution.validate_path(
                relative.as_posix()
            )

            if safe_target != target:
                print("Peringatan: lokasi file tidak cocok.")
                return False

            if safe_target.is_symlink():
                print("Peringatan: penghapusan symlink ditolak.")
                return False

            if not safe_target.is_file():
                return False

            safe_target.unlink()
            print("File percobaan yang gagal telah dibersihkan.")
            return True

        except (OSError, ValueError, PermissionError, TypeError) as error:
            print(
                "Peringatan: file gagal dibersihkan:",
                str(error)
            )
            return False

    def run(self, instruction, filename, initial_code=None):
        if not isinstance(instruction, str) or not instruction.strip():
            return {
                "success": False,
                "message": "Instruksi perbaikan tidak valid."
            }

        try:
            target = self.zora.execution.validate_path(filename)
        except (ValueError, PermissionError, OSError) as error:
            return {
                "success": False,
                "message": str(error)
            }

        if target.exists():
            return {
                "success": False,
                "message": "File sudah tersedia. Tidak akan ditimpa."
            }

        if initial_code is None:
            generated = self.zora.generate_code(instruction)

            if not isinstance(generated, dict):
                return {
                    "success": False,
                    "message": "Respons generator kode tidak valid."
                }

            if not generated.get("success"):
                return generated

            code = generated.get("code")
        else:
            code = initial_code

        try:
            self.validate_code(code)
        except (
            SyntaxError,
            ValueError,
            PermissionError,
            TypeError,
            UnicodeError
        ) as error:
            return {
                "success": False,
                "message": f"Kode awal ditolak: {error}"
            }

        created = self.zora.execution.create_file(filename)

        if not created.get("success"):
            return created

        saved = self.zora.execution.write_file(filename, code)

        if not saved.get("success"):
            self.cleanup_created_file(target)
            return saved

        for attempt in range(self.max_attempts + 1):
            print(f"\nPengujian ke-{attempt + 1}...")

            result = self.zora.execution.test_code(filename)

            if not isinstance(result, dict):
                self.cleanup_created_file(target)
                return {
                    "success": False,
                    "message": "Hasil pengujian Sandbox tidak valid.",
                    "attempts": attempt + 1
                }

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

            error_message = str(
                result.get("message", "Kesalahan tidak diketahui.")
            )[:2000]

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

            if not isinstance(repaired, dict) or not repaired.get("success"):
                self.cleanup_created_file(target)
                return {
                    "success": False,
                    "message": (
                        repaired.get("message", "Generator gagal.")
                        if isinstance(repaired, dict)
                        else "Respons generator tidak valid."
                    ),
                    "attempts": attempt + 1
                }

            new_code = repaired.get("code")

            try:
                self.validate_code(new_code)
            except (
                SyntaxError,
                ValueError,
                PermissionError,
                TypeError,
                UnicodeError
            ) as error:
                print("Kode perbaikan ditolak:", str(error))
                continue

            saved = self.zora.execution.write_file(filename, new_code)

            if not saved.get("success"):
                self.cleanup_created_file(target)
                return saved

            code = new_code

        self.cleanup_created_file(target)

        return {
            "success": False,
            "message": (
                "ZORA belum berhasil memperbaiki kode "
                "setelah batas percobaan."
            ),
            "attempts": self.max_attempts
        }


def main():
    zora = Zora()

    try:
        repair = ZoraSelfRepair(zora)

        result = repair.run(
            instruction=(
                "Buat program untuk menghitung 10 dibagi 2 "
                "dan tampilkan hasilnya."
            ),
            filename="developer_sandbox/pengujian/hasil_perbaikan_01.py",
            initial_code="hasil = 10 / 0\nprint(hasil)"
        )

        print("\nHASIL AKHIR:")
        print(result)

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
