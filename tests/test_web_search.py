import unittest
from unittest.mock import patch

from brain.web_search import WebSearch


class TestWebSearch(unittest.TestCase):

    def setUp(self):
        self.searcher = WebSearch()

    def test_search_success(self):
        fake_results = [{
            "title": "Situs resmi",
            "body": "Ringkasan hasil",
            "href": "https://example.com"
        }]

        with patch("brain.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.return_value = fake_results
            result = self.searcher.search("contoh pencarian")

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["results"][0]["url"], "https://example.com")
        self.assertEqual(result["backend"], "yahoo")
        self.assertEqual(result["search_query"], "contoh pencarian")

    def test_fallback_to_next_backend(self):
        fake_results = [{
            "title": "Hasil Startpage",
            "body": "Ringkasan",
            "href": "https://example.com"
        }]

        with patch("brain.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.side_effect = [
                TimeoutError("Yahoo timeout"),
                fake_results
            ]
            result = self.searcher.search("tes")

        self.assertTrue(result["success"])
        self.assertEqual(result["backend"], "startpage")
        self.assertEqual(mock_ddgs.return_value.text.call_count, 2)

    def test_all_backends_fail(self):
        with patch(
            "brain.web_search.DDGS",
            side_effect=RuntimeError("Koneksi gagal")
        ):
            result = self.searcher.search("tes")

        self.assertFalse(result["success"])
        self.assertIn("Semua mesin pencarian gagal", result["error"])

    def test_indonesian_query_translation_fallback(self):
        fake_results = [{
            "title": "AI Technology 2026",
            "body": "Latest AI technology",
            "href": "https://example.com/ai"
        }]

        with patch.object(
            self.searcher,
            "_translate_query",
            return_value="latest artificial intelligence technology 2026"
        ), patch("brain.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.side_effect = [
                RuntimeError("No results"),
                RuntimeError("No results"),
                RuntimeError("No results"),
                fake_results
            ]

            result = self.searcher.search(
                "teknologi AI terbaru tahun 2026"
            )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["search_query"],
            "latest artificial intelligence technology 2026"
        )
        self.assertEqual(result["backend"], "yahoo")

    def test_translation_not_needed_for_english_query(self):
        with patch.object(
            self.searcher,
            "_translate_query"
        ) as mock_translate:
            self.assertIsNone(
                self.searcher._translate_query(
                    "latest artificial intelligence technology"
                )
            )
            mock_translate.assert_not_called()

    def test_translation_failure_does_not_crash_search(self):
        with patch.object(
            self.searcher,
            "_translate_query",
            return_value=None
        ), patch(
            "brain.web_search.DDGS",
            side_effect=RuntimeError("Koneksi gagal")
        ):
            result = self.searcher.search(
                "teknologi AI terbaru tahun 2026"
            )

        self.assertFalse(result["success"])
        self.assertIn("Semua mesin pencarian gagal", result["error"])

    def test_empty_query_rejected(self):
        with self.assertRaises(ValueError):
            self.searcher.search(" ")

    def test_non_string_query_rejected(self):
        with self.assertRaises(ValueError):
            self.searcher.search(123)

    def test_long_query_rejected(self):
        with self.assertRaises(ValueError):
            self.searcher.search("a" * 501)

    def test_invalid_max_results_rejected(self):
        for value in [0, 6, True, 1.5]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.searcher.search("tes", value)

    def test_unsafe_urls_filtered(self):
        fake_results = [
            {
                "title": "Invalid",
                "body": "Tes",
                "href": "javascript:alert(1)"
            },
            {
                "title": "Valid",
                "body": "Tes",
                "href": "https://example.com"
            }
        ]

        with patch("brain.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.return_value = fake_results
            result = self.searcher.search("tes")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["results"][0]["title"], "Valid")

    def test_result_limit_enforced(self):
        fake_results = [
            {
                "title": f"Hasil {i}",
                "body": "Ringkasan",
                "href": f"https://example{i}.com"
            }
            for i in range(10)
        ]

        with patch("brain.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.return_value = fake_results
            result = self.searcher.search("tes", 3)

        self.assertEqual(result["total"], 3)

    def test_timeout_validation(self):
        for value in [0, 61, True, 1.5]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    WebSearch(timeout=value)


if __name__ == "__main__":
    unittest.main()
