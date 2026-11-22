import unittest
from unittest.mock import patch

from brain.web_reader import WebReader, TextExtractor


class TestWebReader(unittest.TestCase):

    def setUp(self):
        self.reader = WebReader()

    def test_https_url_accepted(self):
        with patch("brain.web_reader.socket.getaddrinfo") as dns:
            dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 443))
            ]
            self.assertEqual(
                self.reader._validate_url("https://example.com"),
                "https://example.com"
            )

    def test_local_ip_rejected(self):
        for url in (
            "http://127.0.0.1",
            "http://192.168.1.1",
            "http://10.0.0.1",
            "http://169.254.1.1"
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.reader._validate_url(url)

    def test_local_hostname_rejected(self):
        for url in ("http://localhost", "http://server.local"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.reader._validate_url(url)

    def test_unsafe_scheme_rejected(self):
        with self.assertRaises(ValueError):
            self.reader._validate_url("file:///etc/passwd")

    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):
            self.reader._validate_url("https://user:pass@example.com")

    def test_nonstandard_port_rejected(self):
        with self.assertRaises(ValueError):
            self.reader._validate_url("http://example.com:8080")

    def test_script_content_removed(self):
        parser = TextExtractor()
        parser.feed(
            "<html><title>Judul</title>"
            "<p>Konten aman</p>"
            "<script>kode berbahaya</script>"
            "<style>CSS</style></html>"
        )

        content = " ".join(" ".join(parser.parts).split())

        self.assertEqual(" ".join(parser.title_parts), "Judul")
        self.assertIn("Konten aman", content)
        self.assertNotIn("kode berbahaya", content)
        self.assertNotIn("CSS", content)

    def test_invalid_url_returns_error(self):
        result = self.reader.read("file:///etc/passwd")

        self.assertFalse(result["success"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
