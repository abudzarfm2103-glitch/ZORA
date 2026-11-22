import unittest

from brain.context_manager import ZoraContextManager


class FakeConversation:

    def __init__(self, messages):
        self.messages = messages

    def get_history(self):
        return self.messages


class FakeMemory:
    pass


class TestZoraContextManager(unittest.TestCase):

    def create_manager(self, messages):
        return ZoraContextManager(
            FakeConversation(messages),
            FakeMemory()
        )

    def test_explicit_future_plan(self):
        manager = self.create_manager([
            {
                "role": "user",
                "content": "ZORA nantinya akan berjalan di server."
            },
            {
                "role": "user",
                "content": "ZORA akan berjalan di mana?"
            }
        ])

        result = manager.understand(
            "ZORA akan berjalan di mana?"
        )

        self.assertIn("server", result)

    def test_hypothetical_statement_is_not_a_plan(self):
        manager = self.create_manager([
            {
                "role": "user",
                "content": "Kalau ZORA berjalan di server, apakah aman?"
            },
            {
                "role": "user",
                "content": "ZORA berjalan di mana?"
            }
        ])

        result = manager.understand(
            "ZORA berjalan di mana?"
        )

        self.assertIsNone(result)

    def test_question_is_not_a_plan(self):
        manager = self.create_manager([
            {
                "role": "user",
                "content": "Apakah ZORA akan berjalan di server?"
            },
            {
                "role": "user",
                "content": "ZORA akan berjalan di mana?"
            }
        ])

        result = manager.understand(
            "ZORA akan berjalan di mana?"
        )

        self.assertIsNone(result)

    def test_no_location_in_history(self):
        manager = self.create_manager([
            {
                "role": "user",
                "content": "Saya sedang mengembangkan ZORA."
            },
            {
                "role": "user",
                "content": "ZORA berjalan di mana?"
            }
        ])

        result = manager.understand(
            "ZORA berjalan di mana?"
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
