
class ZoraContextManager:

    def __init__(self, conversation, memory):
        self.conversation = conversation
        self.memory = memory

    def understand(self, message):
        text = message.lower().strip()

        # Mengenali pertanyaan tentang lokasi ZORA
        pertanyaan_lokasi = (
            "di mana" in text
            and any(kata in text for kata in [
                "zora",
                "proyek ini",
                "proyek tersebut"
            ])
        )

        if not pertanyaan_lokasi:
            return None

        # Periksa percakapan sebelumnya
        history = self.conversation.get_history()

        # Abaikan pesan yang sedang ditanyakan
        previous_messages = history[:-1]

        for item in reversed(previous_messages):
            if item["role"] != "user":
                continue

            kalimat = item["content"].strip()
            lower = kalimat.lower()

            pola = [
                "akan berjalan di",
                "nantinya berjalan di",
                "berjalan di",
                "beroperasi di"
            ]

            for kata in pola:
                if kata in lower:
                    lokasi = kalimat[
                        lower.find(kata) + len(kata):
                    ].strip(" .,!?:;")

                    if lokasi:
                        return (
                            "Berdasarkan percakapan sebelumnya, "
                            "ZORA nantinya akan berjalan di "
                            + lokasi
                            + "."
                        )

        return None
