import sys
import json
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

    def __init__(self, zora):
        self.zora = zora
        self.registry = ZoraCapabilityRegistry()

    def run(self):
        results = {}
        folder = "developer_sandbox/pengujian"

        for name, (code, expected) in self.TESTS.items():
            filename = f"{folder}/capability_test_{name}.py"

            try:
                target = self.zora.execution.validate_path(filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(code, encoding="utf-8")

                result = self.zora.execution.test_code(filename)
                actual = result.get("output", "").strip()

                success = (
                    result.get("success") is True
                    and actual == expected
                )

                results[name] = {
                    "verified": success,
                    "expected": expected,
                    "actual": actual,
                    "message": result.get("message")
                }

            except Exception as error:
                results[name] = {
                    "verified": False,
                    "message": str(error)
                }

        safety_filename = f"{folder}/capability_test_loop_safety.py"

        try:
            target = self.zora.execution.validate_path(safety_filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "angka = 1\nwhile angka > 0:\n    angka = angka + 1",
                encoding="utf-8"
            )

            safety_result = self.zora.execution.test_code(safety_filename)

            safety_verified = (
                safety_result.get("success") is False
                and "Batas iterasi while terlampaui."
                in safety_result.get("message", "")
            )

            results["loop_safety"] = {
                "verified": safety_verified,
                "message": safety_result.get("message")
            }

        except Exception as error:
            results["loop_safety"] = {
                "verified": False,
                "message": str(error)
            }

        state_file = self.registry.state_file

        try:
            if state_file.exists():
                state = json.loads(
                    state_file.read_text(encoding="utf-8")
                )
            else:
                state = {}

            for name in self.TESTS:
                state[name] = {
                    "verified": results[name]["verified"]
                }

            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(
                json.dumps(state, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )

        except (OSError, ValueError) as error:
            print("Peringatan: hasil belum tersimpan:", error)

        return results


if __name__ == "__main__":
    from brain.zora import Zora

    zora = Zora()

    try:
        tester = ZoraCapabilityTester(zora)
        print("=== HASIL PENGUJIAN KEMAMPUAN ===")
        print(json.dumps(
            tester.run(),
            indent=4,
            ensure_ascii=False
        ))

        print("\n=== INVENTARIS KEMAMPUAN ===")
        print(json.dumps(
            tester.registry.report(),
            indent=4,
            ensure_ascii=False
        ))

    finally:
        zora.memory.close()
