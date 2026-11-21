import ast
import operator
from pathlib import Path


class ZoraSandboxRunner:

    MAX_FILE_SIZE = 65536
    MAX_NODES = 500
    MAX_OUTPUT = 10000
    MAX_LOOP_ITERATIONS = 100
    MAX_STEPS = 1000

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
        self.steps = 0

    def validate_file(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Nama file tidak valid.")

        target = (self.workspace / name).resolve()

        if not target.is_relative_to(self.workspace):
            raise PermissionError("Akses ditolak. File berada di luar Sandbox.")

        if not target.is_file():
            raise FileNotFoundError("File pengujian tidak ditemukan.")

        if target.suffix.lower() != ".py":
            raise ValueError("Hanya file Python yang boleh diuji.")

        if target.stat().st_size > self.MAX_FILE_SIZE:
            raise ValueError("Ukuran file melebihi batas pengujian.")

        return target

    def validate_code(self, tree):
        nodes = list(ast.walk(tree))

        if len(nodes) > self.MAX_NODES:
            raise ValueError("Kode terlalu kompleks untuk pengujian.")

        parents = {
            child: parent
            for parent in nodes
            for child in ast.iter_child_nodes(parent)
        }

        for node in nodes:

            if isinstance(node, ast.Assign):
                if len(node.targets) != 1:
                    raise PermissionError("Penugasan variabel tidak diizinkan.")
                if not isinstance(node.targets[0], ast.Name):
                    raise PermissionError("Target variabel tidak diizinkan.")

            elif isinstance(node, ast.Expr):
                if not isinstance(node.value, ast.Call):
                    raise PermissionError("Hanya perintah print() yang diizinkan.")
                if not isinstance(node.value.func, ast.Name):
                    raise PermissionError("Pemanggilan fungsi tidak diizinkan.")
                if node.value.func.id != "print":
                    raise PermissionError("Hanya fungsi print() yang diizinkan.")
                if node.value.keywords:
                    raise PermissionError("Parameter tambahan belum diizinkan.")

            elif isinstance(node, ast.For):
                if not isinstance(node.target, ast.Name):
                    raise PermissionError("Variabel perulangan tidak diizinkan.")
                if not isinstance(node.iter, ast.Call):
                    raise PermissionError("Perulangan for harus menggunakan range().")
                if not isinstance(node.iter.func, ast.Name):
                    raise PermissionError("Fungsi perulangan tidak diizinkan.")
                if node.iter.func.id != "range":
                    raise PermissionError("Hanya range() yang diizinkan untuk for.")
                if node.iter.keywords or not 1 <= len(node.iter.args) <= 3:
                    raise PermissionError("Parameter range() tidak valid.")

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
                    raise PermissionError("Pemanggilan fungsi tidak diizinkan.")

            elif isinstance(node, (
                ast.Module, ast.Load, ast.Store, ast.If,
                ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
                ast.Compare, ast.Add, ast.Sub, ast.Mult, ast.Div,
                ast.FloorDiv, ast.Mod, ast.UAdd, ast.USub,
                ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE
            )):
                continue

            else:
                raise PermissionError(
                    f"Struktur kode tidak diizinkan: {type(node).__name__}"
                )

        return True

    def evaluate(self, node, variables):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool, type(None))):
                return node.value
            raise ValueError("Jenis data tidak diizinkan.")

        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ValueError(f"Variabel '{node.id}' belum didefinisikan.")
            return variables[node.id]

        if isinstance(node, ast.BinOp):
            left = self.evaluate(node.left, variables)
            right = self.evaluate(node.right, variables)
            operation = self.OPERATORS.get(type(node.op))

            if operation is None:
                raise PermissionError("Operator tidak diizinkan.")

            if isinstance(node.op, ast.Mult):
                if isinstance(left, (str, list)) and isinstance(right, int) and abs(right) > 1000:
                    raise ValueError("Operasi terlalu besar.")
                if isinstance(right, (str, list)) and isinstance(left, int) and abs(left) > 1000:
                    raise ValueError("Operasi terlalu besar.")

            result = operation(left, right)

            if isinstance(result, int) and result.bit_length() > 1024:
                raise ValueError("Hasil angka terlalu besar.")
            if isinstance(result, float) and abs(result) > 1e100:
                raise ValueError("Hasil angka terlalu besar.")

            return result

        if isinstance(node, ast.UnaryOp):
            value = self.evaluate(node.operand, variables)
            if isinstance(node.op, ast.UAdd):
                return +value
            if isinstance(node.op, ast.USub):
                return -value
            raise PermissionError("Operator tidak diizinkan.")

        if isinstance(node, ast.Compare):
            left = self.evaluate(node.left, variables)

            for operation, comparator in zip(node.ops, node.comparators):
                right = self.evaluate(comparator, variables)
                function = self.COMPARISONS.get(type(operation))

                if function is None:
                    raise PermissionError("Perbandingan tidak diizinkan.")
                if not function(left, right):
                    return False

                left = right

            return True

        raise PermissionError("Ekspresi kode tidak diizinkan.")

    def consume_step(self):
        self.steps += 1
        if self.steps > self.MAX_STEPS:
            raise ValueError("Batas langkah eksekusi Sandbox terlampaui.")

    def check_output(self, output):
        if len("\n".join(output)) > self.MAX_OUTPUT:
            raise ValueError("Hasil pengujian terlalu panjang.")

    def process_statements(self, statements, variables, output):
        for node in statements:
            self.consume_step()

            if isinstance(node, ast.Assign):
                value = self.evaluate(node.value, variables)
                variables[node.targets[0].id] = value

            elif isinstance(node, ast.Expr):
                values = [
                    self.evaluate(argument, variables)
                    for argument in node.value.args
                ]
                output.append(" ".join(str(value) for value in values))

            elif isinstance(node, ast.If):
                branch = (
                    node.body
                    if self.evaluate(node.test, variables)
                    else node.orelse
                )
                self.process_statements(branch, variables, output)

            elif isinstance(node, ast.For):
                arguments = [
                    self.evaluate(argument, variables)
                    for argument in node.iter.args
                ]

                if any(type(value) is not int for value in arguments):
                    raise ValueError("Parameter range() harus berupa bilangan bulat.")

                values = range(*arguments)

                if len(values) > self.MAX_LOOP_ITERATIONS:
                    raise ValueError("Jumlah iterasi for melebihi batas.")

                for value in values:
                    self.consume_step()
                    variables[node.target.id] = value
                    self.process_statements(node.body, variables, output)
                    self.check_output(output)

                self.process_statements(node.orelse, variables, output)

            elif isinstance(node, ast.While):
                iterations = 0

                while self.evaluate(node.test, variables):
                    if iterations >= self.MAX_LOOP_ITERATIONS:
                        raise ValueError("Batas iterasi while terlampaui.")

                    self.consume_step()
                    iterations += 1
                    self.process_statements(node.body, variables, output)
                    self.check_output(output)

                self.process_statements(node.orelse, variables, output)

            self.check_output(output)

    def run_file(self, name):
        try:
            target = self.validate_file(name)
            source = target.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=target.name)

            self.validate_code(tree)

            variables = {}
            output = []
            self.steps = 0

            self.process_statements(tree.body, variables, output)

            return {
                "success": True,
                "message": "Pengujian berhasil.",
                "output": "\n".join(output)
            }

        except SyntaxError as error:
            return {
                "success": False,
                "message": f"Kesalahan sintaks pada baris {error.lineno}."
            }

        except (
            ValueError, PermissionError, FileNotFoundError,
            OSError, TypeError, ArithmeticError
        ) as error:
            return {
                "success": False,
                "message": str(error)
            }
