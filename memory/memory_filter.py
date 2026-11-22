import re


class MemoryFilter:

    KEYWORDS = {
        "pribadi": [
            "nama saya",
            "umur saya",
            "saya tinggal"
        ],
        "pekerjaan": [
            "saya bekerja",
            "pekerjaan saya",
            "kantor saya",
            "saya menjabat",
            "jabatan saya",
            "saat ini saya bekerja",
            "sekarang saya bekerja"
        ],
        "proyek": [
            "proyek saya",
            "saya sedang mengembangkan",
            "saya sedang membuat",
            "saya ingin mengembangkan",
            "saya ingin membuat",
            "ingin mengembangkan",
            "ingin membuat",
            "zora nantinya akan berjalan",
            "zora akan berjalan",
            "zora berjalan di",
            "zora beroperasi di",
            "zora sekarang berjalan di",
            "zora sudah berjalan di",
            "zora saat ini berjalan di",
            "zora sekarang beroperasi di",
            "zora sudah beroperasi di",
            "zora saat ini beroperasi di",
            "server zora"
        ],
        "preferensi": [
            "saya suka",
            "saya lebih suka",
            "saya tidak suka"
        ]
    }

    IGNORE_WORDS = [
        "halo", "hai", "selamat pagi", "selamat malam",
        "terima kasih", "oke", "baik", "sudah", "iya"
    ]

    QUESTION_STARTS = [
        "apakah", "apa", "siapa", "dimana", "di mana",
        "kapan", "mengapa", "kenapa", "bagaimana",
        "bisakah", "bolehkah", "adakah"
    ]

    HYPOTHETICAL_STARTS = [
        "kalau", "jika", "seandainya", "andaikan",
        "misalnya", "bagaimana jika"
    ]

    NEGATIVE_PLAN_PATTERNS = [
        r"\btidak\s+ingin\b",
        r"\bbelum\s+ingin\b",
        r"\btidak\s+akan\b",
        r"\btidak\s+berencana\b",
        r"\btidak\s+berniat\b",
        r"\bbukan\s+rencana\b"
    ]

    PLAN_PATTERNS = [
        r"\bsaya\s+akan\b",
        r"\bsaya\s+ingin\b",
        r"\bsaya\s+berencana\b",
        r"\bsaya\s+berniat\b",
        r"\brencana\s+saya\b",
        r"\btarget\s+saya\b",
        r"\bzora\s+nantinya\s+akan\b",
        r"\bzora\s+akan\b",
        r"\bzora\s+direncanakan\b",
        r"\bdirencanakan\s+berjalan\b"
    ]

    FACT_PATTERNS = [
        "nama saya",
        "saya bekerja sebagai",
        "saya bekerja di",
        "pekerjaan saya sekarang",
        "saat ini saya bekerja",
        "sekarang saya bekerja",
        "saya menjabat",
        "jabatan saya",
        "saya tinggal",
        "saya adalah",
        "saya memiliki",
        "saya sedang mengembangkan",
        "saya sedang membuat",
        "saya suka",
        "saya lebih suka",
        "saya tidak suka",
        "zora sekarang berjalan",
        "zora sudah berjalan",
        "zora saat ini berjalan",
        "zora sekarang beroperasi",
        "zora sudah beroperasi",
        "zora saat ini beroperasi"
    ]

    def contains_phrase(self, text, phrase):
        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
        return re.search(pattern, text) is not None

    def is_question_or_hypothetical(self, text):
        lower = text.casefold().strip()

        if "?" in lower:
            return True

        if any(
            lower.startswith(word + " ")
            or lower == word
            for word in self.QUESTION_STARTS
        ):
            return True

        if any(
            lower.startswith(word + " ")
            or lower == word
            for word in self.HYPOTHETICAL_STARTS
        ):
            return True

        return False

    def determine_status(self, text):
        if not isinstance(text, str):
            return "belum_diklasifikasikan"

        lower = " ".join(text.casefold().split())

        if self.is_question_or_hypothetical(lower):
            return "belum_diklasifikasikan"

        if any(
            re.search(pattern, lower)
            for pattern in self.NEGATIVE_PLAN_PATTERNS
        ):
            return "belum_diklasifikasikan"

        if any(
            re.search(pattern, lower)
            for pattern in self.PLAN_PATTERNS
        ):
            return "rencana"

        for pattern in self.FACT_PATTERNS:
            if self.contains_phrase(lower, pattern):
                return "fakta"

        return "belum_diklasifikasikan"

    def analyze(self, message):
        if not isinstance(message, str):
            return None

        text = " ".join(message.strip().split())
        lower = text.casefold()

        if not text or len(text) < 5:
            return None

        if lower in self.IGNORE_WORDS:
            return None

        if self.is_question_or_hypothetical(text):
            return None

        if any(
            re.search(pattern, lower)
            for pattern in self.NEGATIVE_PLAN_PATTERNS
        ):
            return None

        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if self.contains_phrase(lower, keyword):
                    return {
                        "content": text,
                        "category": category,
                        "status": self.determine_status(text)
                    }

        return None
