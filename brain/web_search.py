import json
import urllib.request
from urllib.parse import urlparse

from ddgs import DDGS


class WebSearch:
    BACKENDS = ("yahoo", "startpage", "brave")
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    TRANSLATION_MODEL = "zora"

    INDONESIAN_MARKERS = {
        "apa", "bagaimana", "mengapa", "siapa", "kapan", "dimana",
        "terbaru", "teknologi", "berita", "tahun", "tentang",
        "perkembangan", "penjelasan", "pencarian", "contoh",
        "terbaik", "terkini", "harga", "cara", "dampak",
        "kecerdasan", "buatan", "penelitian", "di", "dan",
        "untuk", "dengan", "yang", "dari", "pada"
    }

    def __init__(self, timeout=12):
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise ValueError("Timeout harus berupa angka 1 sampai 60.")
        self.timeout = timeout

    def _is_indonesian_query(self, query):
        words = set(query.lower().split())
        return bool(words.intersection(self.INDONESIAN_MARKERS))

    def _translate_query(self, query):
        """Menerjemahkan kata pencarian melalui Ollama lokal."""
        if not self._is_indonesian_query(query):
            return None

        prompt = (
            "Translate this search query into natural English. "
            "Return ONLY the translated search query. "
            "Do not answer the question and do not add explanations.\n"
            "Search query: " + json.dumps(query, ensure_ascii=False)
        )

        payload = {
            "model": self.TRANSLATION_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 80
            }
        }

        try:
            request = urllib.request.Request(
                self.OLLAMA_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))

            translated = str(data.get("response", "")).strip()
            translated = translated.strip("\"'` ").strip()

            if not translated or len(translated) > 500:
                return None

            if translated.lower() == query.lower():
                return None

            return translated

        except Exception:
            return None

    def _search_with_backends(self, query, max_results):
        errors = []

        for backend in self.BACKENDS:
            try:
                engine = DDGS(timeout=self.timeout)
                raw_results = engine.text(
                    query,
                    max_results=max_results,
                    safesearch="moderate",
                    backend=backend
                )

                results = []

                for item in raw_results or []:
                    if not isinstance(item, dict):
                        continue

                    title = str(item.get("title", "")).strip()
                    body = str(item.get("body", "")).strip()
                    href = str(item.get("href", "")).strip()

                    parsed = urlparse(href)

                    if parsed.scheme not in ("http", "https"):
                        continue

                    if not parsed.netloc or not title and not body:
                        continue

                    results.append({
                        "title": title[:500],
                        "summary": body[:2000],
                        "url": href[:2000]
                    })

                    if len(results) >= max_results:
                        break

                if results:
                    return {
                        "results": results,
                        "backend": backend,
                        "errors": errors
                    }

                errors.append(f"{backend}: tidak ada hasil")

            except Exception as error:
                errors.append(
                    f"{backend}: {type(error).__name__}: {str(error)[:200]}"
                )

        return {
            "results": [],
            "backend": None,
            "errors": errors
        }

    def search(self, query, max_results=5):
        if not isinstance(query, str):
            raise ValueError("Kata pencarian harus berupa teks.")

        query = query.strip()

        if not query:
            raise ValueError("Kata pencarian tidak boleh kosong.")

        if len(query) > 500:
            raise ValueError("Kata pencarian maksimal 500 karakter.")

        if type(max_results) is not int or not 1 <= max_results <= 5:
            raise ValueError("Jumlah hasil harus antara 1 sampai 5.")

        # Tahap pertama: gunakan kata pencarian asli.
        result = self._search_with_backends(query, max_results)

        if result["results"]:
            return {
                "success": True,
                "query": query,
                "search_query": query,
                "total": len(result["results"]),
                "results": result["results"],
                "backend": result["backend"]
            }

        errors = list(result["errors"])

        # Tahap kedua: jika perlu, terjemahkan menggunakan Ollama lokal.
        translated = self._translate_query(query)

        if translated:
            translated_result = self._search_with_backends(
                translated,
                max_results
            )

            if translated_result["results"]:
                return {
                    "success": True,
                    "query": query,
                    "search_query": translated,
                    "total": len(translated_result["results"]),
                    "results": translated_result["results"],
                    "backend": translated_result["backend"]
                }

            errors.extend(
                "pencarian terjemahan - " + error
                for error in translated_result["errors"]
            )

        return {
            "success": False,
            "query": query,
            "total": 0,
            "results": [],
            "error": "Semua mesin pencarian gagal. " + " | ".join(errors)
        }


if __name__ == "__main__":
    import json

    searcher = WebSearch()
    result = searcher.search("Ollama official website")
    print(json.dumps(result, indent=2, ensure_ascii=False))
