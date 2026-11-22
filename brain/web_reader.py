import ipaddress
import socket
import urllib.request
import urllib.error

from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.title_parts = []
        self.in_title = False
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag == "title":
            self.in_title = True

        if tag in ("script", "style", "noscript", "svg", "nav", "footer"):
            self.skip_depth += 1

        if tag in ("p", "div", "br", "h1", "h2", "h3", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "title":
            self.in_title = False

        if tag in ("script", "style", "noscript", "svg", "nav", "footer"):
            self.skip_depth = max(0, self.skip_depth - 1)

        if tag in ("p", "div", "br", "h1", "h2", "h3", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()

        if not text:
            return

        if self.in_title:
            self.title_parts.append(text)

        if self.skip_depth == 0:
            self.parts.append(text)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WebReader:
    MAX_BYTES = 1_000_000
    MAX_TEXT = 20_000
    MAX_REDIRECTS = 3

    def __init__(self, timeout=15):
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise ValueError("Timeout harus antara 1 sampai 60 detik.")

        self.timeout = timeout
        self.opener = urllib.request.build_opener(NoRedirectHandler())

    def _validate_url(self, url):
        if not isinstance(url, str) or len(url) > 2048:
            raise ValueError("Alamat URL tidak valid.")

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError("Hanya alamat HTTP dan HTTPS yang diizinkan.")

        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Hostname atau kredensial URL tidak valid.")

        host = parsed.hostname.rstrip(".").lower()

        if host in ("localhost",) or host.endswith((".localhost", ".local")):
            raise ValueError("Alamat lokal tidak diizinkan.")

        try:
            port = parsed.port
        except ValueError:
            raise ValueError("Port URL tidak valid.")

        expected_port = 443 if parsed.scheme == "https" else 80

        if port is not None and port != expected_port:
            raise ValueError("Port selain 80 dan 443 tidak diizinkan.")

        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            try:
                records = socket.getaddrinfo(
                    host, port or expected_port,
                    type=socket.SOCK_STREAM
                )
                addresses = [
                    ipaddress.ip_address(record[4][0])
                    for record in records
                ]
            except OSError:
                raise ValueError("Hostname tidak dapat ditemukan.")

        if not addresses:
            raise ValueError("Hostname tidak memiliki alamat IP.")

        for address in addresses:
            if not address.is_global:
                raise ValueError("Alamat IP privat atau khusus ditolak.")

        return url

    def _fetch_once(self, url):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ZORA-WebReader/1.0",
                "Accept": "text/html,application/xhtml+xml"
            },
            method="GET"
        )
        return self.opener.open(request, timeout=self.timeout)

    def read(self, url):
        try:
            current_url = url
            response = None

            for redirect_count in range(self.MAX_REDIRECTS + 1):
                current_url = self._validate_url(current_url)

                try:
                    response = self._fetch_once(current_url)
                    break
                except urllib.error.HTTPError as error:
                    if error.code not in (301, 302, 303, 307, 308):
                        raise

                    location = error.headers.get("Location")
                    error.close()

                    if not location:
                        raise ValueError("Redirect tidak memiliki alamat tujuan.")

                    if redirect_count >= self.MAX_REDIRECTS:
                        raise ValueError("Batas redirect terlampaui.")

                    current_url = urljoin(current_url, location)

            if response is None:
                raise ValueError("Halaman tidak dapat dibuka.")

            with response:
                content_type = response.headers.get("Content-Type", "").lower()

                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    raise ValueError("Alamat tersebut bukan halaman HTML.")

                length = response.headers.get("Content-Length")

                if length:
                    try:
                        if int(length) > self.MAX_BYTES:
                            raise ValueError("Ukuran halaman terlalu besar.")
                    except ValueError as error:
                        if "terlalu besar" in str(error):
                            raise

                raw = response.read(self.MAX_BYTES + 1)

                if len(raw) > self.MAX_BYTES:
                    raise ValueError("Ukuran halaman melebihi batas 1 MB.")

                charset = response.headers.get_content_charset() or "utf-8"
                html = raw.decode(charset, errors="replace")

            parser = TextExtractor()
            parser.feed(html)

            title = " ".join(parser.title_parts).strip()
            content = " ".join(" ".join(parser.parts).split())

            return {
                "success": True,
                "url": current_url,
                "title": title[:500],
                "content": content[:self.MAX_TEXT],
                "truncated": len(content) > self.MAX_TEXT
            }

        except Exception as error:
            return {
                "success": False,
                "url": url if isinstance(url, str) else "",
                "error": f"{type(error).__name__}: {str(error)[:300]}"
            }


if __name__ == "__main__":
    import json

    reader = WebReader()
    result = reader.read("https://ollama.com/")

    print(json.dumps(result, indent=2, ensure_ascii=False))
