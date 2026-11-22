import ast
import math
import operator
from pathlib import Path


class ZoraSandboxRunner:

    MAX_FILE_SIZE = 65536
    MAX_NODES = 500
    MAX_OUTPUT = 10000
    MAX_LINE_OUTPUT = 5000
    MAX_STRING_SIZE = 10000
    MAX_TOTAL_STRING_SIZE = 50000
    MAX_VARIABLES = 100
    MAX_LOOP_ITERATIONS = 100
    MAX_STEPS = 1000
    MAX_INTEGER_BITS = 1024
    MAX_FLOAT_VALUE = 1e100
    MAX_PRINT_ARGUMENTS = 20

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod
    }

    COMPARISONS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge
    }

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.workspace = (
            self.project_root / "data" / "zora_workspace"
        ).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.steps = 0

    def validate_file(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Nama file tidak valid.")

        target = (self.workspace / name).resolve()

        if not target.is_relative_to(self.workspace):
            raise PermissionError(
                "Akses ditolak. File berada di luar Sandbox."
            )

        if not target.is_file():
            raise FileNotFoundError(
                "File pengujian tidak ditemukan."
            )

        if target.suffix.lower() != ".py":
            raise ValueError(
                "Hanya file Python yang boleh diuji."
            )

        if target.stat().st_size > self.MAX_FILE_SIZE:
            raise ValueError(
                "Ukuran file melebihi batas pengujian."
            )

        return target

    def validate_value(self, value):
        if type(value) is str:
            if len(value) > self.MAX_STRING_SIZE:
                raise ValueError(
                    "Ukuran teks melebihi batas Sandbox."
                )

        elif type(value) is int:
            if value.bit_length() > self.MAX_INTEGER_BITS:
                raise ValueError("Ukuran angka terlalu besar.")

        elif type(value) is float:
            if not math.isfinite(value):
                raise ValueError("Nilai angka tidak valid.")

            if abs(value) > self.MAX_FLOAT_VALUE:
                raise ValueError("Ukuran angka terlalu besar.")

        elif type(value) not in (bool, type(None)):
            raise ValueError("Jenis data tidak diizinkan.")

        return value

    def validate_code(self, tree):
        nodes = list(ast.walk(tree))

        if len(nodes) > self.MAX_NODES:
            raise ValueError(
                "Kode terlalu kompleks untuk pengujian."
            )

        parents = {
            child: parent
            for parent in nodes
            for child in ast.iter_child_nodes(parent)
        }

        for node in nodes:
            if isinstance(node, ast.Assign):
                if len(node.targets) != 1:
                    raise PermissionError(
                        "Penugasan variabel tidak diizinkan."
                    )

                if not isinstance(node.targets[0], ast.Name):
                    raise PermissionError(
                        "Target variabel tidak diizinkan."
                    )

            elif isinstance(node, ast.Expr):
                if not isinstance(node.value, ast.Call):
                    raise PermissionError(
                        "Hanya perintah print() yang diizinkan."
                    )

                if not isinstance(node.value.func, ast.Name):
                    raise PermissionError(
                        "Pemanggilan fungsi tidak diizinkan."
                    )

                if node.value.func.id != "print":
                    raise PermissionError(
                        "Hanya fungsi print() yang diizinkan."
                    )

                if node.value.keywords:
                    raise PermissionError(
                        "Parameter tambahan belum diizinkan."
                    )

                if len(node.value.args) > self.MAX_PRINT_ARGUMENTS:
                    raise ValueError(
                        "Jumlah parameter print() terlalu banyak."
                    )

            elif isinstance(node, ast.For):
                if not isinstance(node.target, ast.Name):
                    raise PermissionError(
                        "Variabel perulangan tidak diizinkan."
                    )

                if not isinstance(node.iter, ast.Call):
                    raise PermissionError(
                        "Perulangan for harus menggunakan range()."
                    )

                if not isinstance(node.iter.func, ast.Name):
                    raise PermissionError(
                        "Fungsi perulangan tidak diizinkan."
                    )

                if node.iter.func.id != "range":
                    raise PermissionError(
                        "Hanya range() yang diizinkan untuk for."
                    )

                if (
                    node.iter.keywords
                    or not 1 <= len(node.iter.args) <= 3
                ):
                    raise PermissionError(
                        "Parameter range() tidak valid."
                    )

            elif isinstance(node, ast.While):
                continue

            elif isinstance(node, ast.Call):
                parent = parents.get(node)

                is_print = (
                    isinstance(parent, ast.Expr)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                )

                is_range = (
                    isinstance(parent, ast.For)
                    and parent.iter is node
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "range"
                )

                if not (is_print or is_range):
                    raise PermissionError(
                        "Pemanggilan fungsi tidak diizinkan."
                    )

            elif isinstance(node, (
                ast.Module, ast.Load, ast.Store, ast.If,
                ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
                ast.Compare, ast.Add, ast.Sub, ast.Mult,
                ast.Div, ast.FloorDiv, ast.Mod, ast.UAdd,
                ast.USub, ast.Eq, ast.NotEq, ast.Lt,
                ast.LtE, ast.Gt, ast.GtE
            )):
                continue

            else:
                raise PermissionError(
                    "Struktur kode tidak diizinkan: "
                    f"{type(node).__name__}"
                )

        return True

    def evaluate(self, node, variables):
        if isinstance(node, ast.Constant):
            return self.validate_value(node.value)

        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ValueError(
                    f"Variabel '{node.id}' belum didefinisikan."
                )
            return variables[node.id]

        if isinstance(node, ast.BinOp):
            left = self.evaluate(node.left, variables)
            right = self.evaluate(node.right, variables)

            operation = self.OPERATORS.get(type(node.op))

            if operation is None:
                raise PermissionError("Operator tidak diizinkan.")

            if isinstance(node.op, ast.Add):
                if type(left) is str and type(right) is str:
                    if len(left) + len(right) > self.MAX_STRING_SIZE:
                        raise ValueError(
                            "Hasil penggabungan teks terlalu besar."
                        )
                elif not (
                    type(left) in (int, float)
                    and type(right) in (int, float)
                ):
                    raise ValueError(
                        "Jenis data tidak sesuai untuk penjumlahan."
                    )

            elif isinstance(node.op, ast.Mult):
                if type(left) is str and type(right) is int:
                    if len(left) * abs(right) > self.MAX_STRING_SIZE:
                        raise ValueError(
                            "Hasil perkalian teks terlalu besar."
                        )

                elif type(right) is str and type(left) is int:
                    if len(right) * abs(left) > self.MAX_STRING_SIZE:
                        raise ValueError(
                            "Hasil perkalian teks terlalu besar."
                        )

                elif not (
                    type(left) in (int, float)
                    and type(right) in (int, float)
                ):
                    raise ValueError(
                        "Jenis data tidak sesuai untuk perkalian."
                    )

            elif not (
                type(left) in (int, float)
                and type(right) in (int, float)
            ):
                raise ValueError(
                    "Operasi matematika hanya menerima angka."
                )

            return self.validate_value(operation(left, right))

        if isinstance(node, ast.UnaryOp):
            value = self.evaluate(node.operand, variables)

            if type(value) not in (int, float):
                raise ValueError(
                    "Operator tanda hanya menerima angka."
                )

            if isinstance(node.op, ast.UAdd):
                result = +value
            elif isinstance(node.op, ast.USub):
                result = -value
            else:
                raise PermissionError("Operator tidak diizinkan.")

            return self.validate_value(result)

        if isinstance(node, ast.Compare):
            left = self.evaluate(node.left, variables)

            for operation, comparator in zip(
                node.ops, node.comparators
            ):
                right = self.evaluate(comparator, variables)
                function = self.COMPARISONS.get(type(operation))

                if function is None:
                    raise PermissionError(
                        "Perbandingan tidak diizinkan."
                    )

                if type(left) is not type(right):
                    raise ValueError(
                        "Perbandingan harus menggunakan jenis data yang sama."
                    )

                if type(left) is type(None):
                    if not isinstance(operation, (ast.Eq, ast.NotEq)):
                        raise ValueError(
                            "Nilai None hanya boleh dibandingkan dengan == atau !=."
                        )

                if not function(left, right):
                    return False

                left = right

            return True

        raise PermissionError(
            "Ekspresi kode tidak diizinkan."
        )

    def consume_step(self):
        self.steps += 1

        if self.steps > self.MAX_STEPS:
            raise ValueError(
                "Batas langkah eksekusi Sandbox terlampaui."
            )

    def check_variables(self, variables):
        if len(variables) > self.MAX_VARIABLES:
            raise ValueError(
                "Jumlah variabel melebihi batas Sandbox."
            )

        total_size = sum(
            len(value)
            for value in variables.values()
            if type(value) is str
        )

        if total_size > self.MAX_TOTAL_STRING_SIZE:
            raise ValueError(
                "Total penyimpanan teks melebihi batas Sandbox."
            )

    def check_output(self, output):
        total = sum(len(item) + 1 for item in output)

        if total > self.MAX_OUTPUT:
            raise ValueError(
                "Hasil pengujian terlalu panjang."
            )

    def process_statements(self, statements, variables, output):
        for node in statements:
            self.consume_step()

            if isinstance(node, ast.Assign):
                value = self.evaluate(node.value, variables)
                variables[node.targets[0].id] = value
                self.check_variables(variables)

            elif isinstance(node, ast.Expr):
                values = [
                    self.evaluate(argument, variables)
                    for argument in node.value.args
                ]

                line = " ".join(str(value) for value in values)

                if len(line) > self.MAX_LINE_OUTPUT:
                    raise ValueError(
                        "Satu baris output terlalu panjang."
                    )

                output.append(line)
                self.check_output(output)

            elif isinstance(node, ast.If):
                branch = (
                    node.body
                    if self.evaluate(node.test, variables)
                    else node.orelse
                )

                self.process_statements(
                    branch, variables, output
                )

            elif isinstance(node, ast.For):
                arguments = [
                    self.evaluate(argument, variables)
                    for argument in node.iter.args
                ]

                if any(type(value) is not int for value in arguments):
                    raise ValueError(
                        "Parameter range() harus berupa bilangan bulat."
                    )

                values = range(*arguments)

                if len(values) > self.MAX_LOOP_ITERATIONS:
                    raise ValueError(
                        "Jumlah iterasi for melebihi batas."
                    )

                for value in values:
                    self.consume_step()
                    variables[node.target.id] = value
                    self.check_variables(variables)

                    self.process_statements(
                        node.body, variables, output
                    )

                self.process_statements(
                    node.orelse, variables, output
                )

            elif isinstance(node, ast.While):
                iterations = 0

                while self.evaluate(node.test, variables):
                    if iterations >= self.MAX_LOOP_ITERATIONS:
                        raise ValueError(
                            "Batas iterasi while terlampaui."
                        )

                    self.consume_step()
                    iterations += 1

                    self.process_statements(
                        node.body, variables, output
                    )

                self.process_statements(
                    node.orelse, variables, output
                )

            self.check_variables(variables)
            self.check_output(output)

    def run_file(self, name):
        try:
            target = self.validate_file(name)

            with target.open("rb") as file:
                source_bytes = file.read(
                    self.MAX_FILE_SIZE + 1
                )

            if len(source_bytes) > self.MAX_FILE_SIZE:
                raise ValueError(
                    "Ukuran file melebihi batas pengujian."
                )

            source = source_bytes.decode("utf-8")

            tree = ast.parse(
                source,
                filename=target.name
            )

            self.validate_code(tree)

            variables = {}
            output = []
            self.steps = 0

            self.process_statements(
                tree.body, variables, output
            )

            return {
                "success": True,
                "message": "Pengujian berhasil.",
                "output": "\n".join(output)
            }

        except SyntaxError as error:
            return {
                "success": False,
                "message": (
                    f"Kesalahan sintaks pada baris {error.lineno}."
                )
            }

        except (
            ValueError,
            PermissionError,
            FileNotFoundError,
            OSError,
            TypeError,
            ArithmeticError,
            RecursionError,
            MemoryError,
            UnicodeError
        ) as error:
            return {
                "success": False,
                "message": str(error) or "Pengujian gagal."
            }
