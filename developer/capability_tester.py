import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.capability_registry import ZoraCapabilityRegistry


class ZoraCapabilityTester:

    TESTS = {
        "variables": (
            "angka = 25\nprint(angka)",
            "25"
        ),
        "arithmetic": (
            "a = 10\nb = 5\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)",
            "15\n5\n50\n2.0"
        ),
        "comparisons": (
            "a = 10\nb = 20\nprint(a < b)\nprint(a == b)",
            "True\nFalse"
        ),
        "conditions": (
            "angka = 10\nif angka > 0:\n    print('positif')\nelse:\n    print('negatif')",
            "positif"
        ),
        "output": (
            "print('ZORA')",
            "ZORA"
        ),
        "loops": (
            "total = 0\nfor angka in range(1, 6):\n    total = total + angka\nprint(total)\n\nangka = 1\ntotal = 0\nwhile angka <= 5:\n    total = total + angka\n    angka = angka + 1\nprint(total)",
            "15\n15"
        )
    }

    SECURITY_TESTS = {
        "large_integer": (
            "angka = " + ("9" * 500) + "\nprint(angka)"
        ),
        "large_string": (
            "teks = 'A' * 20000\nprint(teks)"
        ),
        "import_denied": (
            "import os\nprint('tidak boleh berjalan')"
        ),
        "file_access_denied": (
            "isi = open('/etc/passwd')\nprint(isi)"
        ),
        "infinite_loop": (
            "angka = 1\nwhile angka > 0:\n    angka = angka + 1"
        )
    }

    def __init__(self, zora):
        self.zora = zora
        self.registry = ZoraCapabilityRegistry()

    def run_one_test(self, code):
        folder = "developer_sandbox/pengujian"
        filename = (
            f"{folder}/capability_test_{uuid.uuid4().hex}.py"
        )

        target = None

        try:
            target = self.zora.execution.validate_path(filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code, encoding="utf-8")

            return self.zora.execution.test_code(filename)

        finally:
            if target is not None:
                try:
                    target.unlink(missing_ok=True)
                except OSError as error:
                    print(
                        "Peringatan: file pengujian sementara "
                        "tidak dapat dihapus:",
                        error
                    )

    def save_results(self, results):
        state_file = self.registry.state_file
        temporary_file = state_file.with_name(
            f".{state_file.name}.{uuid.uuid4().hex}.tmp"
        )

        try:
            if state_file.exists():
                state = json.loads(
                    state_file.read_text(encoding="utf-8")
                )
                if not isinstance(state, dict):
                    raise ValueError(
                        "Format data kemampuan tidak valid."
                    )
            else:
                state = {}

            for name in self.TESTS:
                state[name] = {
                    "verified": results.get(name, {}).get(
                        "verified", False
                    )
                }

            state_file.parent.mkdir(parents=True, exist_ok=True)
            temporary_file.write_text(
                json.dumps(
                    state,
                    indent=4,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )
            os.replace(temporary_file, state_file)

            return True

        except (OSError, ValueError, TypeError) as error:
            print("Peringatan: hasil belum tersimpan:", error)
            return False

        finally:
            try:
                temporary_file.unlink(missing_ok=True)
            except OSError:
                pass

    def run(self):
        results = {}

        for name, (code, expected) in self.TESTS.items():
            try:
                result = self.run_one_test(code)
                actual = result.get("output", "").strip()

                verified = (
                    result.get("success") is True
                    and actual == expected
                )

                results[name] = {
                    "verified": verified,
                    "expected": expected,
                    "actual": actual,
                    "message": result.get("message")
                }

            except Exception as error:
                results[name] = {
                    "verified": False,
                    "message": str(error)
                }

        for name, code in self.SECURITY_TESTS.items():
            try:
                result = self.run_one_test(code)

                verified = result.get("success") is False

                results[name] = {
                    "verified": verified,
                    "message": result.get("message"),
                    "rejected": verified
                }

            except Exception as error:
                results[name] = {
                    "verified": False,
                    "message": str(error),
                    "rejected": False
                }

        self.save_results(results)
        return results


if __name__ == "__main__":
    from brain.zora import Zora

    zora = Zora()

    try:
        tester = ZoraCapabilityTester(zora)

        print("=== HASIL PENGUJIAN KEMAMPUAN DAN KEAMANAN ===")
        results = tester.run()

        print(json.dumps(
            results,
            indent=4,
            ensure_ascii=False
        ))

        total = len(results)
        passed = sum(
            1 for item in results.values()
            if item.get("verified") is True
        )

        print(f"\nHASIL: {passed}/{total} pengujian lulus")

        print("\n=== INVENTARIS KEMAMPUAN ===")
        print(json.dumps(
            tester.registry.report(),
            indent=4,
            ensure_ascii=False
        ))

    finally:
        zora.memory.close()
