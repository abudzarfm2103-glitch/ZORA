import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ZoraCapabilityRegistry:

    def __init__(self):
        self.sandbox_file = ROOT / "developer" / "sandbox_runner.py"
        self.state_file = ROOT / "data" / "zora_capabilities.json"

    def uses_ast_type(self, method, type_name):
        return any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "ast"
            and node.attr == type_name
            for node in ast.walk(method)
        )

    def inspect_sandbox(self):
        source = self.sandbox_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        methods = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

        validate_method = methods.get("validate_code")
        process_method = methods.get("process_statements")

        if validate_method is None or process_method is None:
            raise ValueError("Metode Sandbox tidak lengkap.")

        operators = {}

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue

            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "OPERATORS", "COMPARISONS"
                ):
                    if isinstance(node.value, ast.Dict):
                        operators[target.id] = [
                            key.attr for key in node.value.keys
                            if isinstance(key, ast.Attribute)
                        ]

        return {
            "variables": self.uses_ast_type(validate_method, "Assign"),

            "arithmetic": operators.get("OPERATORS", []),

            "comparisons": operators.get("COMPARISONS", []),

            "conditions": (
                self.uses_ast_type(validate_method, "If")
                and self.uses_ast_type(process_method, "If")
            ),

            "output": (
                self.uses_ast_type(validate_method, "Expr")
                and self.uses_ast_type(validate_method, "Call")
                and self.uses_ast_type(process_method, "Expr")
            ),

            "loops": all(
                self.uses_ast_type(validate_method, name)
                and self.uses_ast_type(process_method, name)
                for name in ("For", "While")
            ),

            "functions": any(
                self.uses_ast_type(validate_method, name)
                for name in ("FunctionDef", "AsyncFunctionDef")
            ),

            "imports": any(
                self.uses_ast_type(validate_method, name)
                for name in ("Import", "ImportFrom")
            ),

            "collections": any(
                self.uses_ast_type(validate_method, name)
                for name in ("List", "Dict", "Set", "Tuple")
            )
        }

    def report(self):
        detected = self.inspect_sandbox()

        try:
            verified = json.loads(
                self.state_file.read_text(encoding="utf-8")
            ) if self.state_file.exists() else {}
        except (OSError, ValueError):
            verified = {}

        inventory = {}

        for name, value in detected.items():
            available = bool(value)

            inventory[name] = {
                "available_in_sandbox": available,
                "verified": (
                    available
                    and verified.get(name, {}).get("verified", False)
                )
            }

        return {
            "success": True,
            "capabilities": inventory,
            "total_detected": sum(
                1 for item in inventory.values()
                if item["available_in_sandbox"]
            ),
            "total_verified": sum(
                1 for item in inventory.values()
                if item["verified"]
            )
        }


if __name__ == "__main__":
    registry = ZoraCapabilityRegistry()
    print(json.dumps(
        registry.report(),
        indent=4,
        ensure_ascii=False
    ))
