
import ast
import re


class ZoraCodeQualityEvaluator:

    def evaluate(self, code, output, task_id, task=None):
        try:
            tree = ast.parse(code)
        except (SyntaxError, TypeError):
            return {
                "success": False,
                "message": "Kode memiliki kesalahan sintaks.",
                "checks": {}
            }

        nodes = list(ast.walk(tree))

        if task is not None:
            return self.evaluate_task(nodes, output, task)

        return self.evaluate_legacy(nodes, output, task_id)

    def get_assignments(self, nodes):
        assignments = {}

        for node in nodes:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                assignments[node.targets[0].id] = node.value

        return assignments

    def constant_value(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        return None

    def get_printed_value(self, nodes):
        values = []

        for node in nodes:
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "print"
                and node.value.args
            ):
                value = node.value.args[0]

                if isinstance(value, ast.Constant):
                    values.append(str(value.value))

        return values

    def get_source_values(self, task, criteria):
        """
        Mengambil nilai sumber dari kriteria atau instruksi tugas.
        Tidak mengunci angka tertentu.
        """

        parameters = criteria.get("semantic_parameters", {})

        if (
            "nilai_sumber_a" in parameters
            and "nilai_sumber_b" in parameters
        ):
            return (
                parameters["nilai_sumber_a"],
                parameters["nilai_sumber_b"]
            )

        instruction = str(task.get("instruction", ""))

        pattern_a = (
            r"nilai_sumber_a\s+bernilai\s+"
            r"(-?\d+(?:\.\d+)?)"
        )

        pattern_b = (
            r"nilai_sumber_b\s+bernilai\s+"
            r"(-?\d+(?:\.\d+)?)"
        )

        match_a = re.search(
            pattern_a, instruction, re.IGNORECASE
        )

        match_b = re.search(
            pattern_b, instruction, re.IGNORECASE
        )

        if not match_a or not match_b:
            return None, None

        def convert_number(value):
            number = float(value)

            if number.is_integer():
                return int(number)

            return number

        return (
            convert_number(match_a.group(1)),
            convert_number(match_b.group(1))
        )

    def evaluate_task(self, nodes, output, task):

        criteria = task.get("evaluation_criteria", {})

        if not criteria:
            return {
                "success": False,
                "message": "Kriteria evaluasi tidak tersedia.",
                "checks": {}
            }

        assignments = self.get_assignments(nodes)

        required_variables = criteria.get(
            "required_variables", []
        )

        variable_check = all(
            name in assignments
            for name in required_variables
        )

        actual_operations = set()

        for node in nodes:
            if isinstance(node, ast.BinOp):
                actual_operations.add(type(node.op).__name__)

            elif isinstance(node, ast.Compare):
                for operator in node.ops:
                    actual_operations.add(type(operator).__name__)

        required_operations = criteria.get(
            "required_operations", []
        )

        operation_check = all(
            operation in actual_operations
            for operation in required_operations
        )

        actual_control_flow = {
            type(node).__name__
            for node in nodes
            if isinstance(node, (ast.If, ast.For, ast.While))
        }

        required_control_flow = criteria.get(
            "required_control_flow", []
        )

        control_check = all(
            item in actual_control_flow
            for item in required_control_flow
        )

        require_print = criteria.get("require_print", False)

        print_check = (
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
                for node in nodes
            )
            if require_print
            else True
        )

        expected_output = str(
            criteria.get("expected_output", "")
        ).strip()

        output_check = (
            bool(expected_output)
            and str(output).strip() == expected_output
        )

        checks = {
            "Variabel wajib tersedia": variable_check,
            "Operasi wajib digunakan": operation_check,
            "Struktur kontrol wajib digunakan": control_check,
            "Penggunaan print": print_check,
            "Output sesuai target": output_check
        }

        if task.get("skill_id") == "source_evaluation":

            expected_a, expected_b = self.get_source_values(
                task, criteria
            )

            actual_a = (
                self.constant_value(
                    assignments["nilai_sumber_a"]
                )
                if "nilai_sumber_a" in assignments
                else None
            )

            actual_b = (
                self.constant_value(
                    assignments["nilai_sumber_b"]
                )
                if "nilai_sumber_b" in assignments
                else None
            )

            values_available = (
                expected_a is not None
                and expected_b is not None
            )

            checks["Nilai sumber tersedia dalam instruksi"] = (
                values_available
            )

            checks["Nilai sumber A benar"] = (
                values_available and actual_a == expected_a
            )

            checks["Nilai sumber B benar"] = (
                values_available and actual_b == expected_b
            )

            valid_condition = False
            valid_true_branch = False
            valid_false_branch = False

            for node in nodes:
                if not isinstance(node, ast.If):
                    continue

                condition = node.test

                if (
                    isinstance(condition, ast.Compare)
                    and isinstance(condition.left, ast.Name)
                    and condition.left.id == "nilai_sumber_a"
                    and len(condition.ops) == 1
                    and isinstance(condition.ops[0], ast.Gt)
                    and len(condition.comparators) == 1
                    and isinstance(condition.comparators[0], ast.Name)
                    and condition.comparators[0].id == "nilai_sumber_b"
                ):
                    valid_condition = True

                    true_values = self.get_printed_value(
                        node.body
                    )

                    false_values = self.get_printed_value(
                        node.orelse
                    )

                    valid_true_branch = (
                        "sumber_a" in true_values
                    )

                    valid_false_branch = (
                        "sumber_b" in false_values
                    )

            checks["Perbandingan sumber benar"] = valid_condition
            checks["Cabang IF memilih sumber A"] = valid_true_branch
            checks["Cabang ELSE memilih sumber B"] = valid_false_branch

            if values_available:
                correct_target = (
                    "sumber_a"
                    if expected_a > expected_b
                    else "sumber_b"
                )

                checks["Target sesuai perbandingan nilai"] = (
                    expected_output == correct_target
                )

        success = all(checks.values())

        return {
            "success": success,
            "checks": checks,
            "message": (
                "Tugas berhasil diverifikasi berdasarkan kriteria."
                if success
                else "Tugas belum memenuhi seluruh kriteria evaluasi."
            )
        }

    def evaluate_legacy(self, nodes, output, task_id):

        assignments = {}

        for node in nodes:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
            ):
                assignments[node.targets[0].id] = node.value.value

        operators = {
            type(node.op)
            for node in nodes
            if isinstance(node, ast.BinOp)
        }

        output_text = str(output).strip()

        output_lines = [
            line.strip()
            for line in output_text.splitlines()
            if line.strip()
        ]

        try:
            numeric_output = float(output_text)
        except (ValueError, TypeError):
            numeric_output = None

        valid_print = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
            for node in nodes
        )

        checks = {}

        if task_id == "problem_solving":

            valid_division = any(
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Div)
                and isinstance(node.left, ast.Name)
                and node.left.id == "total"
                and isinstance(node.right, ast.Name)
                and node.right.id == "kelompok"
                for node in nodes
            )

            checks = {
                "Total bernilai 20": assignments.get("total") == 20,
                "Kelompok bernilai 4": assignments.get("kelompok") == 4,
                "Pembagian menggunakan kedua variabel": valid_division,
                "Menggunakan print": valid_print,
                "Hasil benar": numeric_output == 5
            }

        elif task_id == "data_analysis":

            values = {
                value for value in assignments.values()
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
            }

            checks = {
                "Menggunakan angka 10, 20, 30":
                    {10, 20, 30}.issubset(values),
                "Minimal tiga variabel": len(assignments) >= 3,
                "Menggunakan penjumlahan": ast.Add in operators,
                "Menggunakan pembagian": ast.Div in operators,
                "Menggunakan print": valid_print,
                "Hasil rata-rata benar": numeric_output == 20
            }

        elif task_id == "pattern_recognition":

            values = {
                value for value in assignments.values()
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
            }

            valid_increment = any(
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Add)
                and isinstance(node.right, ast.Constant)
                and node.right.value == 2
                for node in nodes
            )

            checks = {
                "Menggunakan pola 2, 4, 6, 8":
                    {2, 4, 6, 8}.issubset(values),
                "Minimal empat variabel": len(assignments) >= 4,
                "Menggunakan penambahan 2": valid_increment,
                "Menggunakan print": valid_print,
                "Hasil pola benar": numeric_output == 10
            }

        elif task_id == "language_understanding":

            checks = {
                "Memiliki variabel pesan": "pesan" in assignments,
                "Memiliki variabel tujuan": "tujuan" in assignments,
                "Isi tujuan sesuai permintaan":
                    "membuat folder laporan"
                    in str(assignments.get("tujuan", "")).lower(),
                "Menggunakan print": valid_print,
                "Hasil pemahaman benar":
                    "membuat folder laporan" in output_text.lower()
            }

        elif task_id == "planning":

            checks = {
                "Memiliki tiga tahapan":
                    output_lines == [
                        "analisis",
                        "rencana",
                        "pengujian"
                    ],
                "Menggunakan print": valid_print
            }

        elif task_id == "code_debugging":

            valid_division = any(
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Div)
                and isinstance(node.left, ast.Constant)
                and node.left.value == 10
                and isinstance(node.right, ast.Constant)
                and node.right.value == 2
                for node in nodes
            )

            checks = {
                "Pembagian 10 dibagi 2": valid_division,
                "Menggunakan print": valid_print,
                "Hasil perbaikan benar": numeric_output == 5
            }

        elif task_id == "source_evaluation":

            valid_condition = any(
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == "nilai_sumber_a"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Gt)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Name)
                and node.comparators[0].id == "nilai_sumber_b"
                for node in nodes
            )

            checks = {
                "Nilai sumber A adalah 1":
                    assignments.get("nilai_sumber_a") == 1,
                "Nilai sumber B adalah 0":
                    assignments.get("nilai_sumber_b") == 0,
                "Membandingkan kedua sumber": valid_condition,
                "Menggunakan percabangan":
                    any(isinstance(node, ast.If) for node in nodes),
                "Menggunakan print": valid_print,
                "Hasil evaluasi benar": output_text == "sumber_a"
            }

        elif task_id == "decision_making":

            valid_condition = any(
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Constant)
                and node.left.value == 20
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Gt)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == 10
                for node in nodes
            )

            checks = {
                "Kondisi 20 lebih besar dari 10": valid_condition,
                "Menggunakan percabangan":
                    any(isinstance(node, ast.If) for node in nodes),
                "Menggunakan print": valid_print,
                "Keputusan benar": output_text == "pilih_b"
            }

        else:
            return {
                "success": False,
                "message": "Jenis tugas belum memiliki aturan evaluasi.",
                "checks": {}
            }

        success = all(checks.values())

        return {
            "success": success,
            "checks": checks,
            "message": (
                "Kualitas kode berhasil diverifikasi."
                if success
                else "Kode belum memenuhi semua persyaratan."
            )
        }


def main():

    evaluator = ZoraCodeQualityEvaluator()

    task = {
        "skill_id": "source_evaluation",
        "instruction": (
            "Buat nilai_sumber_a bernilai 8 dan "
            "nilai_sumber_b bernilai 5. "
            "Bandingkan kedua nilai menggunakan if/else."
        ),
        "evaluation_criteria": {
            "required_variables": [
                "nilai_sumber_a",
                "nilai_sumber_b"
            ],
            "required_operations": ["Gt"],
            "required_control_flow": ["If"],
            "expected_output": "sumber_a",
            "require_print": True
        }
    }

    tests = [
        (
            "Variasi nilai 8 dan 5",
            "nilai_sumber_a = 8\n"
            "nilai_sumber_b = 5\n"
            "if nilai_sumber_a > nilai_sumber_b:\n"
            "    print('sumber_a')\n"
            "else:\n"
            "    print('sumber_b')",
            "sumber_a",
            True
        ),
        (
            "Nilai sumber salah",
            "nilai_sumber_a = 1\n"
            "nilai_sumber_b = 0\n"
            "if nilai_sumber_a > nilai_sumber_b:\n"
            "    print('sumber_a')\n"
            "else:\n"
            "    print('sumber_b')",
            "sumber_a",
            False
        ),
        (
            "Percabangan salah",
            "nilai_sumber_a = 8\n"
            "nilai_sumber_b = 5\n"
            "if nilai_sumber_a > nilai_sumber_b:\n"
            "    print('sumber_b')\n"
            "else:\n"
            "    print('sumber_a')",
            "sumber_a",
            False
        ),
        (
            "Nilai terbalik",
            "nilai_sumber_a = 3\n"
            "nilai_sumber_b = 9\n"
            "if nilai_sumber_a > nilai_sumber_b:\n"
            "    print('sumber_a')\n"
            "else:\n"
            "    print('sumber_b')",
            "sumber_b",
            False
        )
    ]

    print("\nZORA SEMANTIC EVALUATOR TEST")
    print("============================")

    for name, code, output, expected in tests:
        test_task = dict(task)

        if name == "Nilai terbalik":
            test_task["instruction"] = (
                "Buat nilai_sumber_a bernilai 3 dan "
                "nilai_sumber_b bernilai 9."
            )
            test_task["evaluation_criteria"] = dict(
                task["evaluation_criteria"]
            )
            test_task["evaluation_criteria"]["expected_output"] = (
                "sumber_b"
            )

        result = evaluator.evaluate(
            code,
            output,
            "source_evaluation",
            task=test_task
        )

        passed = result["success"] == expected

        print(
            name, ":",
            "LULUS" if passed else "GAGAL"
        )

        for check, status in result["checks"].items():
            print(
                " -", check, ":",
                "LULUS" if status else "GAGAL"
            )

    print("\nSELESAI")


if __name__ == "__main__":
    main()
