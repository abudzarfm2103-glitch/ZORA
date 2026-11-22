import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.zora import Zora


class ZoraSelfRepair:

    MAX_ATTEMPTS = 3
    MAX_ERROR_MESSAGE = 2000

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

        except Exception as error:
            print(
                "Peringatan: file gagal dibersihkan:",
                str(error)[:self.MAX_ERROR_MESSAGE]
            )
            return False

    def _failure(self, message, attempts=0):
        return {
            "success": False,
            "message": str(message)[:self.MAX_ERROR_MESSAGE],
            "attempts": attempts
        }

    def _safe_generate(self, instruction):
        try:
            result = self.zora.generate_code(instruction)

            if not isinstance(result, dict):
                return self._failure(
                    "Respons generator kode tidak valid."
                )

            return result

        except Exception as error:
            return self._failure(
                f"Generator mengalami kesalahan: {error}"
            )

    def _safe_write(self, filename, code):
        try:
            result = self.zora.execution.write_file(
                filename,
                code
            )

            if not isinstance(result, dict):
                return self._failure(
                    "Respons penyimpanan file tidak valid."
                )

            return result

        except Exception as error:
            return self._failure(
                f"Penyimpanan file gagal: {error}"
            )

    def _safe_test(self, filename):
        try:
            result = self.zora.execution.test_code(filename)

            if not isinstance(result, dict):
                return self._failure(
                    "Hasil pengujian Sandbox tidak valid."
                )

            return result

        except Exception as error:
            return self._failure(
                f"Pengujian Sandbox mengalami kesalahan: {error}"
            )

    def run(self, instruction, filename, initial_code=None):
        if not isinstance(instruction, str) or not instruction.strip():
            return self._failure(
                "Instruksi perbaikan tidak valid."
            )

        try:
            target = self.zora.execution.validate_path(filename)
        except Exception as error:
            return self._failure(error)

        if target.exists() or target.is_symlink():
            return self._failure(
                "File sudah tersedia. Tidak akan ditimpa."
            )

        if initial_code is None:
            generated = self._safe_generate(instruction)

            if not generated.get("success"):
                return generated

            code = generated.get("code")
        else:
            code = initial_code

        try:
            self.validate_code(code)
        except Exception as error:
            return self._failure(
                f"Kode awal ditolak: {error}"
            )

        created = False
        success = False
        attempts = 0

        try:
            # Buat file secara eksklusif.
            # Status kepemilikan langsung dicatat setelah os.open berhasil.
            try:
                descriptor = os.open(
                    target,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600
                )
                created = True
            except FileExistsError:
                return self._failure(
                    "File sudah tersedia. Tidak akan ditimpa."
                )
            except Exception as error:
                return self._failure(
                    f"Pembuatan file gagal: {error}"
                )

            try:
                os.close(descriptor)
            except Exception as error:
                return self._failure(
                    f"Penutupan file gagal: {error}"
                )

            saved = self._safe_write(filename, code)

            if not saved.get("success"):
                return self._failure(
                    saved.get("message", "Penyimpanan file gagal.")
                )

            for test_number in range(1, self.max_attempts + 2):
                attempts = test_number

                print(f"\nPengujian ke-{test_number}...")

                result = self._safe_test(filename)

                if result.get("success"):
                    success = True

                    print("LULUS: File berhasil dipertahankan")

                    return {
                        "success": True,
                        "message": "Kode berhasil diperbaiki dan diuji.",
                        "attempts": test_number,
                        "code": code,
                        "output": result.get("output", "")
                    }

                error_message = str(
                    result.get(
                        "message",
                        "Kesalahan tidak diketahui."
                    )
                )[:self.MAX_ERROR_MESSAGE]

                print("Kesalahan ditemukan:", error_message)

                if test_number > self.max_attempts:
                    break

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

                repaired = self._safe_generate(repair_instruction)

                if not repaired.get("success"):
                    return self._failure(
                        repaired.get(
                            "message",
                            "Generator gagal memperbaiki kode."
                        ),
                        attempts
                    )

                new_code = repaired.get("code")

                try:
                    self.validate_code(new_code)
                except Exception as error:
                    print(
                        "Kode perbaikan ditolak:",
                        str(error)[:self.MAX_ERROR_MESSAGE]
                    )
                    continue

                saved = self._safe_write(filename, new_code)

                if not saved.get("success"):
                    return self._failure(
                        saved.get("message", "Penyimpanan file gagal."),
                        attempts
                    )

                code = new_code

            return self._failure(
                "ZORA belum berhasil memperbaiki kode setelah batas percobaan.",
                attempts
            )

        except Exception as error:
            return self._failure(
                f"Proses perbaikan mengalami kesalahan: {error}",
                attempts
            )

        finally:
            if created and not success:
                self.cleanup_created_file(target)


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
