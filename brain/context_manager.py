import re


class ZoraContextManager:

    PLAN_PATTERNS = [
        "zora nantinya akan berjalan di",
        "zora akan berjalan di",
        "zora berencana berjalan di",
        "zora nantinya akan beroperasi di",
        "zora akan beroperasi di",
        "zora berencana beroperasi di"
    ]

    HYPOTHETICAL_STARTS = (
        "kalau ",
        "jika ",
        "seandainya ",
        "andaikan ",
        "misalnya "
    )

    QUESTION_STARTS = (
        "apakah ",
        "bagaimana jika ",
        "bagaimana kalau ",
        "menurut kamu ",
        "menurutmu "
    )

    def __init__(self, conversation, memory):
        self.conversation = conversation
        self.memory = memory

    def extract_plan_location(self, content):
        if not isinstance(content, str):
            return None

        sentence = " ".join(content.strip().split())
        lower = sentence.lower()

        if not sentence or sentence.endswith("?"):
            return None

        if lower.startswith(self.HYPOTHETICAL_STARTS):
            return None

        if lower.startswith(self.QUESTION_STARTS):
            return None

        for pattern in self.PLAN_PATTERNS:
            position = lower.find(pattern)

            if position == -1:
                continue

            # Pola harus dimulai dari awal kalimat.
            if position != 0:
                continue

            location = sentence[
                position + len(pattern):
            ].strip(" .,!?:;")

            if not location:
                continue

            # Hindari kalimat yang berisi pertanyaan lanjutan.
            if "?" in location:
                continue

            return location

        return None

    def understand(self, message):
        if not isinstance(message, str):
            return None

        text = message.lower().strip()

        pertanyaan_lokasi = (
            any(kata in text for kata in [
                "di mana",
                "dimana"
            ])
            and any(kata in text for kata in [
                "zora",
                "proyek ini",
                "proyek tersebut"
            ])
        )

        if not pertanyaan_lokasi:
            return None

        history = self.conversation.get_history()
        previous_messages = history[:-1]

        for item in reversed(previous_messages):
            if item.get("role") != "user":
                continue

            lokasi = self.extract_plan_location(
                item.get("content")
            )

            if lokasi:
                return (
                    "Berdasarkan percakapan sebelumnya, "
                    "ZORA nantinya akan berjalan di "
                    f"{lokasi}. Statusnya masih rencana."
                )

        return None
