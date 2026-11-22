import ast
import re


class ZoraCodeQualityEvaluator:

    def evaluate(self, code, output, task_id, task=None):
        try:
            tree = ast.parse(code)
        except (SyntaxError, TypeError, ValueError):
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
        parameters = criteria.get("semantic_parameters")

        if parameters is not None:
            if (
                not isinstance(parameters, dict)
                or set(parameters) != {
                    "nilai_sumber_a",
                    "nilai_sumber_b"
                }
            ):
                return None, None

            value_a = parameters["nilai_sumber_a"]
            value_b = parameters["nilai_sumber_b"]

            if (
                type(value_a) is not int
                or type(value_b) is not int
                or not 1 <= value_a <= 100
                or not 1 <= value_b <= 100
                or value_a == value_b
            ):
                return None, None

            return value_a, value_b

        instruction = str(task.get("instruction", ""))

        match_a = re.search(
            r"nilai_sumber_a\s+bernilai\s+(-?\d+(?:\.\d+)?)",
            instruction,
            re.IGNORECASE
        )

        match_b = re.search(
            r"nilai_sumber_b\s+bernilai\s+(-?\d+(?:\.\d+)?)",
            instruction,
            re.IGNORECASE
        )

        if not match_a or not match_b:
            return None, None

        try:
            number_a = float(match_a.group(1))
            number_b = float(match_b.group(1))
        except (ValueError, OverflowError):
            return None, None

        if not number_a.is_integer() or not number_b.is_integer():
            return None, None

        value_a = int(number_a)
        value_b = int(number_b)

        if (
            not 1 <= value_a <= 100
            or not 1 <= value_b <= 100
            or value_a == value_b
        ):
            return None, None

        return value_a, value_b

    def validate_criteria(self, criteria):
        if not isinstance(criteria, dict) or not criteria:
            return "Kriteria evaluasi tidak tersedia."

        allowed_keys = {
            "required_variables",
            "expected_variables",
            "required_operations",
            "required_control_flow",
            "require_print",
            "expected_output",
            "semantic_type",
            "semantic_parameters"
        }

        unknown = set(criteria) - allowed_keys
        if unknown:
            return "Ditemukan kriteria yang tidak dikenal."

        def valid_names(values):
            return (
                isinstance(values, list)
                and all(
                    isinstance(item, str)
                    and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item)
                    for item in values
                )
                and len(values) == len(set(values))
            )

        required_variables = criteria.get("required_variables")
        if not valid_names(required_variables):
            return "Format variabel wajib tidak valid."

        if "expected_variables" in criteria:
            expected = criteria["expected_variables"]
            if (
                not isinstance(expected, dict)
                or not expected
                or any(
                    not isinstance(name, str)
                    or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
                    or type(value) not in (str, int, float, bool, type(None))
                    for name, value in expected.items()
                )
            ):
                return "Format nilai variabel target tidak valid."

        allowed_operations = {
            "Add", "Sub", "Mult", "Div", "FloorDiv", "Mod",
            "Eq", "NotEq", "Lt", "LtE", "Gt", "GtE"
        }

        operations = criteria.get("required_operations", [])
        if (
            not isinstance(operations, list)
            or any(
                not isinstance(item, str) or item not in allowed_operations
                for item in operations
            )
            or len(operations) != len(set(operations))
        ):
            return "Format operasi wajib tidak valid."

        allowed_control_flow = {"If", "For", "While"}
        control_flow = criteria.get("required_control_flow", [])
        if (
            not isinstance(control_flow, list)
            or any(
                not isinstance(item, str) or item not in allowed_control_flow
                for item in control_flow
            )
            or len(control_flow) != len(set(control_flow))
        ):
            return "Format struktur kontrol tidak valid."

        if type(criteria.get("require_print", False)) is not bool:
            return "Format ketentuan print tidak valid."

        expected_output = criteria.get("expected_output")
        if (
            not isinstance(expected_output, str)
            or not expected_output.strip()
        ):
            return "Target output wajib berupa teks yang tidak kosong."

        semantic_type = criteria.get("semantic_type")
        if "semantic_type" in criteria and not isinstance(semantic_type, str):
            return "Jenis evaluasi semantik tidak valid."

        if "semantic_parameters" in criteria:
            parameters = criteria["semantic_parameters"]

            if (
                semantic_type != "source_evaluation"
                or not isinstance(parameters, dict)
                or set(parameters) != {
                    "nilai_sumber_a",
                    "nilai_sumber_b"
                }
            ):
                return "Parameter evaluasi semantik tidak valid."

        if semantic_type == "source_evaluation":
            parameters = criteria.get("semantic_parameters")

            if not isinstance(parameters, dict):
                return "Parameter evaluasi sumber tidak tersedia."

            value_a = parameters.get("nilai_sumber_a")
            value_b = parameters.get("nilai_sumber_b")

            if type(value_a) is not int or type(value_b) is not int:
                return "Nilai sumber harus berupa bilangan bulat."

            if (
                not 1 <= value_a <= 100
                or not 1 <= value_b <= 100
            ):
                return "Nilai sumber harus berada pada rentang 1 sampai 100."

            if value_a == value_b:
                return "Kedua nilai sumber tidak boleh sama."

        return None

    def evaluate_task(self, nodes, output, task):

        criteria = task.get("evaluation_criteria", {})
        validation_error = self.validate_criteria(criteria)

        if validation_error:
            return {
                "success": False,
                "message": validation_error,
                "checks": {}
            }

        if not isinstance(criteria, dict) or not criteria:
            return {
                "success": False,
                "message": "Kriteria evaluasi tidak tersedia.",
                "checks": {}
            }

        assignments = self.get_assignments(nodes)

        required_variables = criteria.get(
            "required_variables", []
        )

        if not isinstance(required_variables, list):
            return {
                "success": False,
                "message": "Format variabel wajib tidak valid.",
                "checks": {}
            }

        variable_check = all(
            isinstance(name, str) and name in assignments
            for name in required_variables
        )

        expected_variables = criteria.get(
            "expected_variables"
        )

        value_check = True

        if expected_variables is not None:

            if not isinstance(expected_variables, dict) or not expected_variables:
                value_check = False

            else:
                for name, expected_value in expected_variables.items():

                    if name not in assignments:
                        value_check = False
                        break

                    actual_value = self.constant_value(
                        assignments[name]
                    )

                    if (
                        type(actual_value) is not type(expected_value)
                        or actual_value != expected_value
                    ):
                        value_check = False
                        break

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

        if not isinstance(required_operations, list):
            required_operations = []

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

        if not isinstance(required_control_flow, list):
            required_control_flow = []

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
            "Nilai variabel sesuai target": value_check,
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
                self.constant_value(assignments["nilai_sumber_a"])
                if "nilai_sumber_a" in assignments else None
            )

            actual_b = (
                self.constant_value(assignments["nilai_sumber_b"])
                if "nilai_sumber_b" in assignments else None
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

                    valid_true_branch = (
                        "sumber_a" in self.get_printed_value(node.body)
                    )

                    valid_false_branch = (
                        "sumber_b" in self.get_printed_value(node.orelse)
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
        "skill_id": "problem_solving",
        "instruction": "Hitung total dibagi kelompok.",
        "expected_output": "5.0",
        "evaluation_criteria": {
            "required_variables": ["total", "kelompok"],
            "expected_variables": {
                "total": 20,
                "kelompok": 4
            },
            "required_operations": ["Div"],
            "required_control_flow": [],
            "expected_output": "5.0",
            "require_print": True
        }
    }

    tests = [
        (
            "Nilai dan hasil benar",
            "total = 20\nkelompok = 4\nhasil = total / kelompok\nprint(hasil)",
            "5.0",
            True
        ),
        (
            "Nilai variabel salah",
            "total = 10\nkelompok = 2\nhasil = total / kelompok\nprint(hasil)",
            "5.0",
            False
        ),
        (
            "Output salah",
            "total = 20\nkelompok = 4\nhasil = total / kelompok\nprint(hasil)",
            "10",
            False
        ),
        (
            "Variabel wajib hilang",
            "total = 20\nhasil = total / 4\nprint(hasil)",
            "5.0",
            False
        )
    ]

    print("\nZORA CODE QUALITY EVALUATOR TEST")
    print("--------------------------------")

    for name, code, output, expected in tests:

        result = evaluator.evaluate(
            code,
            output,
            "problem_solving",
            task=task
        )

        passed = result["success"] == expected

        print(
            f"{'LULUS' if passed else 'GAGAL'}: {name}"
        )

    print("\nSELESAI")


if __name__ == "__main__":
    main()
