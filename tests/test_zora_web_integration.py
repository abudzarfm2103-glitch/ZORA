import unittest

from brain.zora import Zora


class FakeConversation:
    def __init__(self):
        self.saved = []

    def remember_user(self, message):
        self.saved.append(("user", message))

    def remember_zora(self, message):
        self.saved.append(("zora", message))


class FakeBrain:
    def __init__(self):
        self.calls = []

    def summarize_external_data(self, question, external_data):
        self.calls.append((question, external_data))
        return "Ringkasan simulasi: " + external_data


class FakeMemoryUpdate:
    pending_update = False


class FakeWebSearch:
    def __init__(self, result=None):
        self.result = result
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return self.result


class FakeWebReader:
    def __init__(self, result=None):
        self.result = result
        self.urls = []

    def read(self, url):
        self.urls.append(url)
        return self.result


class TestZoraWebIntegration(unittest.TestCase):

    def make_zora(self):
        zora = Zora.__new__(Zora)
        zora.conversation = FakeConversation()
        zora.brain = FakeBrain()
        zora.memory_update = FakeMemoryUpdate()
        zora.pending_command = None
        zora.pending_parameters = {}
        zora.web_search = FakeWebSearch({
            "success": True,
            "query": "contoh",
            "total": 1,
            "results": [{
                "title": "Contoh hasil",
                "summary": "Ringkasan contoh",
                "url": "https://example.com"
            }]
        })
        zora.web_reader = FakeWebReader({
            "success": True,
            "url": "https://example.com",
            "title": "Halaman Contoh",
            "content": "Isi halaman contoh",
            "truncated": False
        })
        return zora

    def test_search_command(self):
        zora = self.make_zora()
        result = zora.process_message(
            "cari di internet tentang contoh"
        )

        self.assertIn("Contoh hasil", result)
        self.assertEqual(zora.web_search.queries, ["contoh"])

    def test_search_without_query(self):
        zora = self.make_zora()
        result = zora.process_message("cari di internet")

        self.assertIn("Apa yang ingin saya cari", result)
        self.assertEqual(zora.web_search.queries, [])

    def test_read_page_command(self):
        zora = self.make_zora()
        result = zora.process_message(
            "baca halaman https://example.com"
        )

        self.assertIn("Isi halaman contoh", result)
        self.assertEqual(zora.web_reader.urls, ["https://example.com"])

    def test_read_page_without_url(self):
        zora = self.make_zora()
        result = zora.process_message("baca halaman")

        self.assertIn("berikan alamat", result)
        self.assertEqual(zora.web_reader.urls, [])

    def test_web_result_saved_to_conversation(self):
        zora = self.make_zora()
        result = zora.process_message("cari di internet contoh")

        self.assertIn(("zora", result), zora.conversation.saved)

    def test_failed_search_handled(self):
        zora = self.make_zora()
        zora.web_search.result = {
            "success": False,
            "error": "Koneksi gagal",
            "results": []
        }

        result = zora.process_message("cari di internet contoh")

        self.assertIn("Koneksi gagal", result)


if __name__ == "__main__":
    unittest.main()
