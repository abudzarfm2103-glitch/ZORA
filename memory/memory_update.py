
from datetime import datetime
import re

from memory.memory_filter import MemoryFilter


class MemoryUpdate:

    def __init__(self, memory):
        self.memory = memory
        self.pending_update = None
        self.filter = MemoryFilter()

    def normalize_text(self, content):
        text = content.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    def get_conflict_key(self, content, category):

        text = self.normalize_text(content)

        if category == "pekerjaan":
            patterns = [
                "saya bekerja sebagai",
                "saya bekerja di",
                "pekerjaan saya adalah",
                "pekerjaan saya sekarang",
                "saat ini saya bekerja sebagai",
                "sekarang saya bekerja sebagai",
                "saya menjabat sebagai",
                "jabatan saya"
            ]

            if any(pattern in text for pattern in patterns):
                return "pekerjaan"

        elif category in ["pribadi", "lainnya"]:

            if text.startswith("nama saya"):
                return "nama"

            if text.startswith("umur saya"):
                return "umur"

            if text.startswith("saya tinggal"):
                return "tempat_tinggal"

        elif category == "proyek":

            if "zora" in text and any(
                phrase in text
                for phrase in [
                    "berjalan di",
                    "beroperasi di",
                    "dijalankan di"
                ]
            ):
                return "lokasi_operasional_zora"

        return None

    def get_job_role(self, content):

        text = self.normalize_text(content)

        prefixes = [
            "saat ini saya bekerja sebagai",
            "sekarang saya bekerja sebagai",
            "pekerjaan saya sekarang",
            "pekerjaan saya adalah",
            "saya bekerja sebagai",
            "saya bekerja di",
            "saya menjabat sebagai",
            "jabatan saya"
        ]

        for prefix in sorted(prefixes, key=len, reverse=True):

            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        for separator in [" di ", " pada ", " untuk ", " bagian "]:

            if separator in text:
                text = text.split(separator, 1)[0].strip()

        return text

    def get_job_location(self, content):

        text = self.normalize_text(content)

        if " di " in text:
            return text.split(" di ", 1)[1].strip()

        return ""

    def same_job_role(self, old_text, new_text):

        old_role = self.get_job_role(old_text)
        new_role = self.get_job_role(new_text)

        if old_role == new_role:
            return True

        old_location = self.get_job_location(old_text)

        if old_location:
            if new_role == old_role + " " + old_location:
                return True

        return False

    def check(self, content, category):

        content = content.strip()

        if not content:
            return None

        new_text = self.normalize_text(content)
        new_status = self.filter.determine_status(content)

        old_memories = self.memory.recall_details(category)

        for old_text, old_category, old_status, created_at in old_memories:

            if self.normalize_text(old_text) == new_text:

                if (
                    old_status == "belum_diklasifikasikan"
                    and new_status != "belum_diklasifikasikan"
                ):
                    self.memory.conn.execute(
                        """
                        UPDATE memories
                        SET status = ?
                        WHERE content = ? AND category = ?
                        """,
                        (new_status, old_text, category)
                    )
                    self.memory.conn.commit()

                return {
                    "status": "same",
                    "message": "Informasi tersebut sudah saya ingat."
                }

        new_key = self.get_conflict_key(content, category)

        if not new_key:
            return None

        for old_text, old_category, old_status, created_at in old_memories:

            old_key = self.get_conflict_key(old_text, old_category)

            if old_key != new_key:
                continue

            if category == "pekerjaan":

                if self.same_job_role(old_text, content):
                    return {
                        "status": "same",
                        "message": (
                            "Informasi pekerjaan tersebut sudah saya ingat. "
                            "Tidak perlu menyimpan ulang."
                        )
                    }

            self.pending_update = {
                "old": old_text,
                "new": content,
                "category": category,
                "status": new_status
            }

            return {
                "status": "confirm",
                "message": (
                    "Saya menemukan kemungkinan perubahan informasi.\n\n"
                    f"Informasi sebelumnya: {old_text}\n"
                    f"Informasi baru: {content}\n\n"
                    "Apakah informasi baru ini benar dan menggantikan "
                    "informasi sebelumnya? Jawab ya atau tidak."
                )
            }

        return None

    def confirm(self, answer):

        if not self.pending_update:
            return None

        answer = answer.strip().lower()

        if answer in ["ya", "iya", "benar", "setuju"]:

            data = self.pending_update

            cursor = self.memory.conn.execute(
                """
                UPDATE memories
                SET content = ?, status = ?, created_at = ?
                WHERE id = (
                    SELECT id FROM memories
                    WHERE content = ? AND category = ?
                    ORDER BY id DESC
                    LIMIT 1
                )
                """,
                (
                    data["new"],
                    data["status"],
                    datetime.now().isoformat(),
                    data["old"],
                    data["category"]
                )
            )

            self.memory.conn.commit()
            self.pending_update = None

            if cursor.rowcount == 0:
                return (
                    "Informasi lama tidak ditemukan. "
                    "Tidak ada perubahan yang dilakukan."
                )

            return "Informasi berhasil diperbarui setelah konfirmasi Anda."

        if answer in ["tidak", "bukan", "tidak setuju"]:
            self.pending_update = None
            return "Baik, informasi lama tetap saya pertahankan."

        return "Silakan jawab ya atau tidak."
