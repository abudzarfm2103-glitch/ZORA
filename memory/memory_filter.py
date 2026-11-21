
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
            "zora nantinya akan berjalan",
            "zora akan berjalan",
            "server zora",
            "zora berjalan di",
            "zora beroperasi di"
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
        "saya tidak suka"
    ]

    def determine_status(self, text):

        lower_text = text.lower()

        for word in self.PLAN_WORDS:
            if word in lower_text:
                return "rencana"

        for pattern in self.FACT_PATTERNS:
            if pattern in lower_text:
                return "fakta"

        return "belum_diklasifikasikan"

    def analyze(self, message):

        text = " ".join(message.strip().split())
        lower_text = text.lower()

        if not text or len(text) < 5:
            return None

        if lower_text in self.IGNORE_WORDS:
            return None

        for category, keywords in self.KEYWORDS.items():

            for keyword in keywords:

                if keyword in lower_text:
                    return {
                        "content": text,
                        "category": category,
                        "status": self.determine_status(text)
                    }

        return None
