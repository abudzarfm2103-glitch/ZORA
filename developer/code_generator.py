
import ast
import re


class ZoraCodeGenerator:

    def __init__(self, brain, execution):
        self.brain = brain
        self.execution = execution

    def extract_source_values(self, instruction):
        pattern_a = (
            r"nilai_sumber_a\s+bernilai\s+(-?\d+(?:\.\d+)?)"
        )
        pattern_b = (
            r"nilai_sumber_b\s+bernilai\s+(-?\d+(?:\.\d+)?)"
        )

        match_a = re.search(pattern_a, instruction)
        match_b = re.search(pattern_b, instruction)

        if not match_a or not match_b:
            return None

        def convert(value):
            number = float(value)
            if number.is_integer():
                return int(number)
            return number

        return {
            "a": convert(match_a.group(1)),
            "b": convert(match_b.group(1))
        }

    def validate_source_code(self, code, values):
        tree = ast.parse(code)

        errors = []

        assignments = {}

        for node in tree.body:
            if isinstance(node, ast.Assign):
                if (
                    len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, (int, float))
                    and not isinstance(node.value.value, bool)
                ):
                    assignments[node.targets[0].id] = (
                        node.value.value
                    )

        if assignments.get("nilai_sumber_a") != values["a"]:
            errors.append("Nilai variabel nilai_sumber_a salah.")

        if assignments.get("nilai_sumber_b") != values["b"]:
            errors.append("Nilai variabel nilai_sumber_b salah.")

        if "nilai_sumber_a" not in assignments:
            errors.append("Variabel nilai_sumber_a tidak tersedia.")

        if "nilai_sumber_b" not in assignments:
            errors.append("Variabel nilai_sumber_b tidak tersedia.")

        expected = (
            "sumber_a"
            if values["a"] > values["b"]
            else "sumber_b"
        )

        if len(tree.body) != 3:
            errors.append(
                "Struktur kode harus berisi dua variabel dan satu IF."
            )
            return errors

        condition = tree.body[2]

        if not isinstance(condition, ast.If):
            errors.append("Struktur IF tidak ditemukan.")
            return errors

        test = condition.test

        valid_condition = (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "nilai_sumber_a"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Gt)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Name)
            and test.comparators[0].id == "nilai_sumber_b"
        )

        if not valid_condition:
            errors.append(
                "Perbandingan harus nilai_sumber_a > nilai_sumber_b."
            )

        def get_print_value(statements):
            if len(statements) != 1:
                return None

            statement = statements[0]

            if not isinstance(statement, ast.Expr):
                return None

            call = statement.value

            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "print"
                and len(call.args) == 1
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
            ):
                return None

            return call.args[0].value

        if get_print_value(condition.body) != "sumber_a":
            errors.append("Cabang IF harus mencetak sumber_a.")

        if get_print_value(condition.orelse) != "sumber_b":
            errors.append("Cabang ELSE harus mencetak sumber_b.")

        if expected not in ("sumber_a", "sumber_b"):
            errors.append("Target hasil tidak valid.")

        return errors

    def generate(self, instruction):

        feedback = ""

        values = self.extract_source_values(instruction)

        for attempt in range(3):

            prompt = f"""
Kamu adalah pembuat kode Python milik ZORA.

INSTRUKSI ASLI:
{instruction}

ATURAN:
1. Ikuti instruksi secara persis.
2. Jangan mengubah nama variabel.
3. Jangan mengubah angka.
4. Jangan menggunakan angka dari contoh sebelumnya.
5. Gunakan if dan else jika diminta.
6. Gunakan print sesuai target instruksi.
7. Jangan menambahkan fitur atau output lain.
8. Jangan menggunakan def, class, import.
9. Jangan menggunakan input, for, while.
10. Jangan menggunakan akses file atau sistem operasi.
11. Jangan menggunakan atribut atau indeks.
12. Gunakan sintaks yang didukung Sandbox.

{feedback}

Keluarkan hanya kode Python tanpa Markdown.
"""

            result = self.brain.think([
                {
                    "role": "user",
                    "content": prompt
                }
            ])

            if not isinstance(result, str):
                result = str(result)

            code = re.sub(
                r"```(?:python)?|```",
                "",
                result,
                flags=re.IGNORECASE
            ).strip()

            if not code:
                feedback = "Hasil kosong. Buat ulang kode lengkap."
                continue

            try:
                tree = ast.parse(code)

                self.execution.sandbox.validate_code(tree)

                if values is not None:
                    errors = self.validate_source_code(
                        code,
                        values
                    )

                    if errors:
                        feedback = (
                            "KODE DITOLAK KARENA TIDAK SESUAI "
                            "INSTRUKSI:\n"
                            + "\n".join(errors)
                            + "\nBuat ulang kode dan perbaiki "
                            "semua kesalahan tersebut."
                        )
                        continue

                return {
                    "success": True,
                    "code": code
                }

            except (
                SyntaxError,
                ValueError,
                PermissionError,
                TypeError
            ) as error:

                feedback = f"""
KODE DITOLAK.
Kesalahan: {error}

Buat ulang kode dari awal.
Patuhi instruksi dan batasan Sandbox.
"""

        return {
            "success": False,
            "message": (
                "ZORA gagal menghasilkan kode yang valid "
                "setelah 3 percobaan."
            )
        }
