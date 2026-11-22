import unittest

from brain.understanding import ZoraUnderstanding


class FakeMemory:

    def __init__(self, memories):
        self.memories = memories

    def recall_details(self, category=None):
        if category:
            return [
                item for item in self.memories
                if item[1] == category
            ]
        return self.memories

    def recall(self, category=None):
        data = self.recall_details(category)
        return [(item[0],) for item in data]


class TestZoraUnderstanding(unittest.TestCase):

    def create_understanding(self, memories):
        return ZoraUnderstanding(FakeMemory(memories))

    def test_single_job_fact(self):
        zora = self.create_understanding([
            (
                "Saya bekerja sebagai Supervisor di DC Senen",
                "pekerjaan", "fakta", ""
            )
        ])

        result = zora.understand("Apa jabatan saya sekarang?")

        self.assertIn("Supervisor", result)

    def test_conflicting_job_facts(self):
        zora = self.create_understanding([
            (
                "Saya bekerja sebagai Supervisor",
                "pekerjaan", "fakta", "2026-11-22"
            ),
            (
                "Saya bekerja sebagai Kurir",
                "pekerjaan", "fakta", "2026-10-01"
            )
        ])

        result = zora.understand("Apa jabatan saya sekarang?")

        self.assertNotIn("Supervisor", result)
        self.assertNotIn("Kurir", result)
        self.assertTrue(
            "berbeda" in result.lower()
            or "memastikan" in result.lower()
        )

    def test_conflicting_zora_locations(self):
        zora = self.create_understanding([
            (
                "ZORA sekarang berjalan di server",
                "proyek", "fakta", "2026-11-22"
            ),
            (
                "ZORA sudah berjalan di laptop",
                "proyek", "fakta", "2026-10-01"
            )
        ])

        result = zora.understand("ZORA sekarang berjalan di mana?")

        self.assertNotIn("server.", result)
        self.assertNotIn("laptop.", result)
        self.assertTrue(
            "berbeda" in result.lower()
            or "memastikan" in result.lower()
        )

    def test_plan_is_not_current_fact(self):
        zora = self.create_understanding([
            (
                "ZORA nantinya akan berjalan di server",
                "proyek", "rencana", ""
            )
        ])

        result = zora.understand("ZORA sekarang berjalan di mana?")

        self.assertIn("belum", result.lower())
        self.assertIn("server", result.lower())

    def test_plan_question(self):
        zora = self.create_understanding([
            (
                "ZORA nantinya akan berjalan di server",
                "proyek", "rencana", ""
            )
        ])

        result = zora.understand("ZORA akan berjalan di mana?")

        self.assertIn("server", result)
        self.assertIn("rencana", result.lower())

    def test_single_project_fact(self):
        zora = self.create_understanding([
            (
                "ZORA sekarang berjalan di Lenovo",
                "proyek", "fakta", ""
            )
        ])

        result = zora.understand("ZORA berjalan di mana?")

        self.assertIn("Lenovo", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
