
from memory.memory_relationship import MemoryRelationship


class ZoraUnderstanding:

    def __init__(self, memory):
        self.memory = memory
        self.relationship = MemoryRelationship(memory)

    def extract_answer(self, content, prefix):
        text = content.strip()

        if text.lower().startswith(prefix):
            return text[len(prefix):].strip()

        return text

    def get_relationships(self, relation=None):
        relationships = self.relationship.build_relationships()

        if relation:
            relationships = [
                item for item in relationships
                if item["relation"] == relation
            ]

        return relationships

    def understand(self, message):

        text = message.lower().strip()

        # Pertanyaan khusus tentang jabatan
        if any(word in text for word in [
            "apa jabatan saya",
            "jabatan saya apa",
            "jabatan saya sekarang"
        ]):

            relationships = self.get_relationships(
                "bekerja_sebagai"
            )

            facts = [
                item for item in relationships
                if item["status"] == "fakta"
            ]

            if facts:
                return f"Jabatan Anda adalah {facts[0]['object']}."

            return "Saya belum mengetahui jabatan Anda."

        # Pertanyaan tentang tempat kerja
        if any(word in text for word in [
            "di mana saya bekerja",
            "dimana saya bekerja",
            "saya bekerja di mana",
            "tempat kerja saya",
            "pekerjaan saya",
            "apa pekerjaan saya"
        ]):

            relationships = self.get_relationships(
                "bekerja_sebagai"
            )

            facts = [
                item for item in relationships
                if item["status"] == "fakta"
            ]

            if facts:
                item = facts[0]

                answer = f"Anda bekerja sebagai {item['object']}."

                if item.get("location"):
                    answer += f" Tempat kerja Anda adalah {item['location']}."

                return answer

            return "Saya belum memiliki informasi pekerjaan yang jelas."

        # Mengenali nama
        if any(word in text for word in [
            "nama saya",
            "siapa nama saya",
            "siapa nama pengguna"
        ]):

            data = self.memory.recall()

            for item in data:
                content = item[0]

                if content.lower().startswith("nama saya"):
                    answer = self.extract_answer(
                        content,
                        "nama saya"
                    )
                    return f"Nama Anda {answer.rstrip('.')}."

            return "Saya belum mengetahui nama Anda."

        # Mengenali lokasi operasional ZORA
        if "zora" in text and any(word in text for word in [
            "di mana",
            "dimana",
            "lokasi",
            "berjalan",
            "beroperasi"
        ]):

            relationships = self.get_relationships(
                "direncanakan_berjalan_di"
            )

            if any(word in text for word in [
                "sudah",
                "sekarang",
                "saat ini"
            ]):

                if relationships:
                    return (
                        "ZORA belum memiliki status berjalan yang "
                        "terkonfirmasi dalam memori saya. "
                        f"Lokasi yang direncanakan adalah "
                        f"{relationships[0]['object']}."
                    )

                return "Saya belum mengetahui lokasi operasional ZORA."

            if relationships:
                return (
                    "Berdasarkan rencana yang tersimpan, "
                    f"ZORA nantinya akan berjalan di "
                    f"{relationships[0]['object']}. "
                    "Statusnya masih rencana."
                )

            return "Saya belum mengetahui rencana lokasi operasional ZORA."

        # Mengenali proyek yang sedang dikembangkan
        if any(word in text for word in [
            "apa yang sedang saya kembangkan",
            "proyek saya",
            "apa proyek saya",
            "apa yang sedang saya buat"
        ]):

            data = self.memory.recall("proyek")

            for item in data:
                content = item[0]

                if "saya sedang mengembangkan" in content.lower():
                    answer = self.extract_answer(
                        content,
                        "saya sedang mengembangkan"
                    )

                    return (
                        f"Anda sedang mengembangkan {answer.rstrip('.')}."
                    )

            return "Saya belum mengetahui proyek yang sedang Anda kembangkan."

        return None
