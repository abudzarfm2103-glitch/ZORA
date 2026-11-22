import unittest

from developer.code_quality_evaluator import ZoraCodeQualityEvaluator


class TestCodeQualityEvaluator(unittest.TestCase):

    def setUp(self):
        self.evaluator = ZoraCodeQualityEvaluator()
        self.task = {
            "skill_id": "validation_test",
            "instruction": "Uji validasi kriteria",
            "evaluation_criteria": {
                "required_variables": ["angka"],
                "expected_variables": {"angka": 10},
                "required_operations": [],
                "required_control_flow": [],
                "require_print": True,
                "expected_output": "10"
            }
        }
        self.code = "angka = 10\nprint(angka)"

    def evaluate(self, criteria):
        task = dict(self.task)
        task["evaluation_criteria"] = criteria
        return self.evaluator.evaluate(
            self.code, "10", "validation_test", task=task
        )

    def source_criteria(self, value_a=80, value_b=40):
        return {
            "required_variables": [
                "nilai_sumber_a",
                "nilai_sumber_b"
            ],
            "required_operations": ["Gt"],
            "required_control_flow": ["If"],
            "require_print": True,
            "expected_output": "sumber_a",
            "semantic_type": "source_evaluation",
            "semantic_parameters": {
                "nilai_sumber_a": value_a,
                "nilai_sumber_b": value_b
            }
        }

    # Pengujian lama

    def test_valid_criteria_pass(self):
        result = self.evaluate(self.task["evaluation_criteria"])
        self.assertTrue(result["success"])

    def test_operations_string_rejected(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["required_operations"] = "OPERASI_TIDAK_VALID"
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_unknown_operation_rejected(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["required_operations"] = ["OPERASI_TIDAK_VALID"]
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_control_flow_string_rejected(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["required_control_flow"] = "STRUKTUR_TIDAK_VALID"
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_unknown_control_flow_rejected(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["required_control_flow"] = ["FunctionDefinition"]
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_required_variables_string_rejected(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["required_variables"] = "angka"
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_invalid_expected_variables_rejected(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["expected_variables"] = ["angka", 10]
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_require_print_must_be_boolean(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["require_print"] = "yes"
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_expected_output_must_be_nonempty_text(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["expected_output"] = 10
        self.assertFalse(self.evaluate(criteria)["success"])

    def test_unknown_criteria_rejected(self):
        criteria = dict(self.task["evaluation_criteria"])
        criteria["skip_security"] = True
        self.assertFalse(self.evaluate(criteria)["success"])

    # Pengujian keamanan parameter sumber

    def test_valid_source_parameters_accepted(self):
        criteria = self.source_criteria()
        self.assertIsNone(
            self.evaluator.validate_criteria(criteria)
        )
        self.assertEqual(
            self.evaluator.get_source_values({}, criteria),
            (80, 40)
        )

    def test_boolean_source_values_rejected(self):
        for value_a, value_b in [
            (True, 40),
            (80, False),
            (True, False)
        ]:
            with self.subTest(value_a=value_a, value_b=value_b):
                criteria = self.source_criteria(value_a, value_b)
                self.assertIsNotNone(
                    self.evaluator.validate_criteria(criteria)
                )
                self.assertEqual(
                    self.evaluator.get_source_values({}, criteria),
                    (None, None)
                )

    def test_float_source_values_rejected(self):
        criteria = self.source_criteria(80.0, 40)
        self.assertIsNotNone(
            self.evaluator.validate_criteria(criteria)
        )
        self.assertEqual(
            self.evaluator.get_source_values({}, criteria),
            (None, None)
        )

    def test_source_values_below_range_rejected(self):
        criteria = self.source_criteria(0, 40)
        self.assertIsNotNone(
            self.evaluator.validate_criteria(criteria)
        )

    def test_source_values_above_range_rejected(self):
        criteria = self.source_criteria(101, 40)
        self.assertIsNotNone(
            self.evaluator.validate_criteria(criteria)
        )

    def test_equal_source_values_rejected(self):
        criteria = self.source_criteria(50, 50)
        self.assertIsNotNone(
            self.evaluator.validate_criteria(criteria)
        )

    def test_missing_source_parameter_rejected(self):
        criteria = self.source_criteria()
        del criteria["semantic_parameters"]["nilai_sumber_b"]
        self.assertIsNotNone(
            self.evaluator.validate_criteria(criteria)
        )

    def test_extra_source_parameter_rejected(self):
        criteria = self.source_criteria()
        criteria["semantic_parameters"]["nilai_tambahan"] = 20
        self.assertIsNotNone(
            self.evaluator.validate_criteria(criteria)
        )

    def test_source_parameters_require_correct_semantic_type(self):
        criteria = self.source_criteria()
        criteria["semantic_type"] = "unknown"
        self.assertIsNotNone(
            self.evaluator.validate_criteria(criteria)
        )

    # Pengujian nilai yang diambil dari instruksi

    def test_instruction_source_values_valid(self):
        task = {
            "instruction": (
                "nilai_sumber_a bernilai 80 dan "
                "nilai_sumber_b bernilai 40"
            )
        }
        self.assertEqual(
            self.evaluator.get_source_values(task, {}),
            (80, 40)
        )

    def test_instruction_equal_values_rejected(self):
        task = {
            "instruction": (
                "nilai_sumber_a bernilai 50 dan "
                "nilai_sumber_b bernilai 50"
            )
        }
        self.assertEqual(
            self.evaluator.get_source_values(task, {}),
            (None, None)
        )

    def test_instruction_out_of_range_rejected(self):
        task = {
            "instruction": (
                "nilai_sumber_a bernilai 101 dan "
                "nilai_sumber_b bernilai 40"
            )
        }
        self.assertEqual(
            self.evaluator.get_source_values(task, {}),
            (None, None)
        )

    def test_instruction_decimal_values_rejected(self):
        task = {
            "instruction": (
                "nilai_sumber_a bernilai 80.5 dan "
                "nilai_sumber_b bernilai 40"
            )
        }
        self.assertEqual(
            self.evaluator.get_source_values(task, {}),
            (None, None)
        )


if __name__ == "__main__":
    unittest.main()
