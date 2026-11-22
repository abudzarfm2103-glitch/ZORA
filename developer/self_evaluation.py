import ast


class ZoraSelfEvaluation:

    @staticmethod
    def _parse(code):
        if not isinstance(code, str) or len(code) > 65536:
            return None
        try:
            return ast.parse(code)
        except (SyntaxError, ValueError, TypeError, RecursionError):
            return None

    @staticmethod
    def _assignments(tree):
        result = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        result[target.id] = node.value
        return result

    def _static_value(self, node, assignments):
        if isinstance(node, ast.Constant):
            if type(node.value) in (int, float):
                return node.value

        if isinstance(node, ast.Name):
            value = assignments.get(node.id)
            if isinstance(value, ast.Constant):
                if type(value.value) in (int, float):
                    return value.value

        return None

    def _has_comparison_values(self, tree, assignments, expected):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue

            if len(node.ops) != 1:
                continue

            left = self._static_value(node.left, assignments)
            right = self._static_value(node.comparators[0], assignments)

            if {left, right} == set(expected):
                return True

        return False

    @staticmethod
    def _has_operator(node, operator):
        return any(
            isinstance(item, ast.BinOp)
            and isinstance(item.op, operator)
            for item in ast.walk(node)
        )

    @staticmethod
    def _uses_names(node, names):
        used = {
            item.id for item in ast.walk(node)
            if isinstance(item, ast.Name)
        }
        return set(names).issubset(used)

    @staticmethod
    def _has_if(tree):
        return any(isinstance(node, ast.If) for node in ast.walk(tree))

    @staticmethod
    def _result(success, message):
        return {"success": success, "message": message}

    def evaluate(self, task_id, code, output):

        tree = self._parse(code)

        if tree is None:
            return self._result(
                False,
                "Kode memiliki kesalahan sintaks atau ukuran tidak valid."
            )

        if not isinstance(output, str):
            output = str(output)

        actual_output = output.strip()
        assignments = self._assignments(tree)

        if task_id == "logical_reasoning":

            valid_values = (
                assignments.get("a") is not None
                and assignments.get("b") is not None
                and self._static_value(
                    assignments["a"], assignments
                ) == 10
                and self._static_value(
                    assignments["b"], assignments
                ) == 20
            )

            if not valid_values:
                valid_values = self._has_comparison_values(
                    tree, assignments, (10, 20)
                )

            valid = (
                valid_values
                and self._has_comparison_values(
                    tree, assignments, (10, 20)
                )
                and self._has_if(tree)
                and actual_output == "20"
            )

            return self._result(
                valid,
                "Penalaran logis berhasil diverifikasi."
                if valid else
                "Gunakan perbandingan angka 10 dan 20 dengan if. "
                "Output harus tepat 20."
            )

        if task_id == "calculation":

            valid_values = (
                self._static_value(
                    assignments.get("a"), assignments
                ) == 10
                and self._static_value(
                    assignments.get("b"), assignments
                ) == 20
            )

            operators = (
                ast.Add, ast.Sub, ast.Mult, ast.Div
            )

            valid_operations = all(
                self._has_operator(tree, op)
                for op in operators
            )

            expected = ["30", "-10", "200", "0.5"]
            actual = [
                line.strip()
                for line in actual_output.splitlines()
                if line.strip()
            ]

            valid = (
                valid_values
                and valid_operations
                and actual == expected
            )

            return self._result(
                valid,
                "Operasi matematika berhasil diverifikasi."
                if valid else
                "Pastikan a=10, b=20 dan empat hasil operasi benar."
            )

        if task_id == "condition_analysis":

            valid_number = (
                self._static_value(
                    assignments.get("angka"), assignments
                ) == 10
            )

            valid_comparison = self._has_comparison_values(
                tree, assignments, (0, 10)
            )

            valid = (
                valid_number
                and valid_comparison
                and self._has_if(tree)
                and actual_output == "positif"
            )

            return self._result(
                valid,
                "Analisis kondisi berhasil diverifikasi."
                if valid else
                "Gunakan angka=10, bandingkan dengan 0 menggunakan "
                "if, dan tampilkan positif."
            )

        if task_id == "data_analysis":

            expected_values = {
                "pagi": 10,
                "siang": 20,
                "sore": 30
            }

            valid_values = all(
                self._static_value(
                    assignments.get(name), assignments
                ) == value
                for name, value in expected_values.items()
            )

            total_node = assignments.get("total")
            average_node = assignments.get("rata_rata")

            valid_total = (
                total_node is not None
                and self._uses_names(
                    total_node, ("pagi", "siang", "sore")
                )
                and self._has_operator(total_node, ast.Add)
            )

            valid_average = (
                average_node is not None
                and self._uses_names(average_node, ("total",))
                and self._has_operator(average_node, ast.Div)
                and any(
                    isinstance(item, ast.Constant)
                    and item.value == 3
                    for item in ast.walk(average_node)
                )
            )

            valid_condition = False

            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue

                if self._uses_names(node.test, ("rata_rata",)):
                    if self._has_comparison_values(
                        ast.Expression(node.test),
                        assignments,
                        (20, 20)
                    ):
                        valid_condition = True
                        break

            # Perbandingan rata-rata minimal 20.
            if not valid_condition:
                for node in ast.walk(tree):
                    if not isinstance(node, ast.If):
                        continue
                    for comparison in ast.walk(node.test):
                        if not isinstance(comparison, ast.Compare):
                            continue
                        if (
                            self._uses_names(
                                comparison, ("rata_rata",)
                            )
                            and any(
                                isinstance(item, ast.Constant)
                                and item.value == 20
                                for item in ast.walk(comparison)
                            )
                        ):
                            valid_condition = True
                            break

            valid = (
                valid_values
                and valid_total
                and valid_average
                and valid_condition
                and self._has_if(tree)
                and actual_output == "target tercapai"
            )

            return self._result(
                valid,
                "Analisis data berhasil diverifikasi."
                if valid else
                "Periksa nilai data, total, rata-rata, dan kondisi minimal 20."
            )

        return self._result(
            False,
            "Jenis tugas belum memiliki aturan evaluasi."
        )


def main():
    evaluator = ZoraSelfEvaluation()
    print(evaluator.evaluate(
        "condition_analysis",
        'angka = 10\nif angka > 0:\n    print("positif")',
        "positif"
    ))


if __name__ == "__main__":
    main()
