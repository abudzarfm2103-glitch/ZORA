import tempfile
import unittest
from pathlib import Path

from memory.memory import ZoraMemory
from memory.memory_filter import MemoryFilter
from memory.memory_update import MemoryUpdate


class TestMemoryFilter(unittest.TestCase):

    def setUp(self):
        self.filter = MemoryFilter()

    def test_question_is_not_saved(self):
        self.assertIsNone(
            self.filter.analyze("Apakah ZORA akan berjalan di server?")
        )

    def test_hypothetical_is_not_saved(self):
        self.assertIsNone(
            self.filter.analyze("Kalau ZORA berjalan di server, apakah aman?")
        )

    def test_negative_plan_is_not_saved(self):
        self.assertIsNone(
            self.filter.analyze("Saya tidak ingin mengembangkan proyek baru")
        )

    def test_explicit_project_plan(self):
        result = self.filter.analyze(
            "ZORA nantinya akan berjalan di server"
        )
        self.assertEqual(result["status"], "rencana")

    def test_current_work_is_fact(self):
        result = self.filter.analyze(
            "Saya bekerja sebagai Supervisor di DC Senen"
        )
        self.assertEqual(result["status"], "fakta")


class TestMemoryUpdate(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.memory = ZoraMemory(Path(self.folder.name) / "test.db")
        self.updater = MemoryUpdate(self.memory)

    def tearDown(self):
        self.memory.close()
        self.folder.cleanup()

    def test_same_job_same_location_is_duplicate(self):
        self.memory.save(
            "Saya bekerja sebagai Supervisor di DC Senen",
            "pekerjaan",
            "fakta"
        )

        result = self.updater.check(
            "Saya menjabat sebagai Supervisor di DC Senen",
            "pekerjaan"
        )

        self.assertEqual(result["status"], "same")
        self.assertIsNone(self.updater.pending_update)

    def test_same_job_different_location_requires_confirmation(self):
        self.memory.save(
            "Saya bekerja sebagai Supervisor di DC Senen",
            "pekerjaan",
            "fakta"
        )

        result = self.updater.check(
            "Saya bekerja sebagai Supervisor di DC Cakung",
            "pekerjaan"
        )

        self.assertEqual(result["status"], "confirm")
        self.assertIsNotNone(self.updater.pending_update)

    def test_different_job_requires_confirmation(self):
        self.memory.save(
            "Saya bekerja sebagai Supervisor di DC Senen",
            "pekerjaan",
            "fakta"
        )

        result = self.updater.check(
            "Saya bekerja sebagai Manager di DC Senen",
            "pekerjaan"
        )

        self.assertEqual(result["status"], "confirm")

    def test_rejection_preserves_old_memory(self):
        old = "Saya bekerja sebagai Supervisor di DC Senen"
        self.memory.save(old, "pekerjaan", "fakta")

        self.updater.check(
            "Saya bekerja sebagai Supervisor di DC Cakung",
            "pekerjaan"
        )
        self.updater.confirm("tidak")

        self.assertEqual(
            self.memory.recall("pekerjaan")[0][0],
            old
        )

    def test_approval_replaces_old_memory(self):
        self.memory.save(
            "Saya bekerja sebagai Supervisor di DC Senen",
            "pekerjaan",
            "fakta"
        )

        self.updater.check(
            "Saya bekerja sebagai Supervisor di DC Cakung",
            "pekerjaan"
        )
        self.updater.confirm("ya")

        self.assertEqual(
            self.memory.recall("pekerjaan")[0][0],
            "Saya bekerja sebagai Supervisor di DC Cakung"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
