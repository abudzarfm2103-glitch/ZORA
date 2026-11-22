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
        "halo",
        "hai",
        "selamat pagi",
        "selamat malam",
        "terima kasih",
        "oke",
        "baik",
        "sudah",
        "iya"
    ]

    PLAN_WORDS = [
        "akan",
        "nantinya",
        "berencana",
        "rencana",
        "ingin",
        "berniat",
        "direncanakan",
        "target saya"
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
        pattern = (
            r"(?<!\w)"
            + re.escape(phrase)
            + r"(?!\w)"
        )
        return re.search(pattern, text) is not None

    def determine_status(self, text):
        lower_text = text.lower()

        for word in self.PLAN_WORDS:
            if self.contains_phrase(lower_text, word):
                return "rencana"

        for pattern in self.FACT_PATTERNS:
            if self.contains_phrase(lower_text, pattern):
                return "fakta"

        return "belum_diklasifikasikan"

    def analyze(self, message):
        if not isinstance(message, str):
            return None

        text = " ".join(message.strip().split())
        lower_text = text.lower()

        if not text or len(text) < 5:
            return None

        if lower_text in self.IGNORE_WORDS:
            return None

        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if self.contains_phrase(lower_text, keyword):
                    return {
                        "content": text,
                        "category": category,
                        "status": self.determine_status(text)
                    }

        return None
