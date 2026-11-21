import ast


class ZoraSelfEvaluation:

    def evaluate(self, task_id, code, output):

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "success": False,
                "message": "Kode memiliki kesalahan sintaks."
            }

        nodes = list(ast.walk(tree))

        operators = {
            type(node.op)
            for node in nodes
            if isinstance(node, ast.BinOp)
        }

        has_if = any(
            isinstance(node, ast.If)
            for node in nodes
        )

        has_comparison = any(
            isinstance(node, ast.Compare)
            for node in nodes
        )

        actual_output = str(output).strip()

        if task_id == "logical_reasoning":

            valid_structure = has_if and has_comparison
            valid_output = actual_output == "20"

            if valid_structure and valid_output:
                return {
                    "success": True,
                    "message": "Penalaran logis berhasil diverifikasi."
                }

            return {
                "success": False,
                "message": "Gunakan if dan perbandingan. Output harus tepat 20."
            }

        if task_id == "calculation":

            required = {
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div
            }

            expected = ["30", "-10", "200", "0.5"]

            actual = [
                line.strip()
                for line in actual_output.splitlines()
                if line.strip()
            ]

            if required.issubset(operators) and actual == expected:
                return {
                    "success": True,
                    "message": "Operasi matematika berhasil diverifikasi."
                }

            return {
                "success": False,
                "message": "Operasi dan empat output perhitungan belum sesuai."
            }

        if task_id == "condition_analysis":

            has_ten = any(
                isinstance(node, ast.Constant)
                and node.value == 10
                for node in nodes
            )

            if (
                has_if
                and has_comparison
                and has_ten
                and actual_output == "positif"
            ):
                return {
                    "success": True,
                    "message": "Analisis kondisi berhasil diverifikasi."
                }

            return {
                "success": False,
                "message": "Periksa angka 10 dengan if. Output harus tepat positif."
            }

        if task_id == "data_analysis":

            assigned_names = {
                node.id
                for item in nodes
                if isinstance(item, ast.Assign)
                for target in item.targets
                for node in ast.walk(target)
                if isinstance(node, ast.Name)
            }

            required_names = {
                "pagi",
                "siang",
                "sore",
                "total",
                "rata_rata"
            }

            required_operators = {
                ast.Add,
                ast.Div
            }

            valid_structure = (
                required_names.issubset(assigned_names)
                and required_operators.issubset(operators)
                and has_if
                and has_comparison
            )

            valid_output = actual_output == "target tercapai"

            if valid_structure and valid_output:
                return {
                    "success": True,
                    "message": "Analisis data berhasil diverifikasi."
                }

            return {
                "success": False,
                "message": (
                    "Gunakan variabel pagi, siang, sore, total, "
                    "dan rata_rata. Hitung total dan rata-rata "
                    "dengan penjumlahan serta pembagian. "
                    "Gunakan if dan perbandingan. "
                    "Output harus tepat: target tercapai."
                )
            }

        return {
            "success": False,
            "message": "Jenis tugas belum memiliki aturan evaluasi."
        }


def main():

    evaluator = ZoraSelfEvaluation()

    print("PENGUJIAN SELF-EVALUATION ENGINE")

    kode_salah = """
angka = 10

if angka > 0:
    print("Teks positif")
"""

    hasil = evaluator.evaluate(
        "condition_analysis",
        kode_salah,
        "Teks positif"
    )

    print(hasil)

    if hasil["success"]:
        print("PENGUJIAN GAGAL")
    else:
        print("PENGUJIAN BERHASIL: output yang salah ditolak.")


if __name__ == "__main__":
    main()
