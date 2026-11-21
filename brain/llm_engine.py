import json
import urllib.request
import urllib.error

from memory.memory_relationship import MemoryRelationship


class ZoraBrain:

    def __init__(self, identity, memory=None, model="zora"):

        self.identity = identity
        self.memory = memory
        self.model = model
        self.api_url = "http://localhost:11434/api/chat"

        self.relationship = None

        if self.memory:
            self.relationship = MemoryRelationship(self.memory)

    def get_long_term_memory(self):

        if not self.memory:
            return "Belum ada memori yang tersedia."

        memories = self.memory.recall_details()

        if not memories:
            return "Belum ada memori yang tersimpan."

        result = []

        for content, category, status, created_at in memories[:30]:
            result.append(
                f"- Informasi: {content}\n"
                f"  Kategori: {category}\n"
                f"  Status: {status}"
            )

        return "\n".join(result)

    def get_relationship_context(self):

        if not self.relationship:
            return "Belum ada hubungan informasi."

        relationships = self.relationship.build_relationships()

        if not relationships:
            return "Belum ada hubungan informasi yang dikenali."

        result = []

        for item in relationships:
            line = (
                f"- {item['subject']} "
                f"{item['relation']} "
                f"{item['object']}"
            )

            if item.get("location"):
                line += f" | Lokasi: {item['location']}"

            line += f" | Status: {item['status']}"
            result.append(line)

        return "\n".join(result)

    def build_system_prompt(self):

        name = self.identity.get("name", "ZORA")

        character = ", ".join(
            self.identity.get("character", [])
        )

        principles = "\n".join(
            "- " + item
            for item in self.identity.get("principles", [])
        )

        memories = self.get_long_term_memory()
        relationships = self.get_relationship_context()

        return f"""
KAMU ADALAH {name}.

Kamu adalah asisten AI pribadi dengan identitas,
kepribadian, penalaran, dan sistem memori sendiri.

IDENTITAS:
{self.identity.get("identity", "")}

KARAKTER:
{character}

PRINSIP:
{principles}

================================
DATABASE MEMORI JANGKA PANJANG
================================

{memories}

================================
HUBUNGAN ANTAR-MEMORI
================================

{relationships}

Hubungan di atas merupakan hasil pengolahan
dari informasi yang tersimpan.

Jangan menganggap hubungan hasil pengolahan
sebagai fakta baru yang tidak pernah diberikan pengguna.

================================
ATURAN MEMAHAMI MEMORI
================================

STATUS MEMORI:

1. fakta:
   Informasi yang dinyatakan secara jelas oleh pengguna.

2. rencana:
   Sesuatu yang ingin dilakukan atau direncanakan.
   Jangan menganggapnya sudah terlaksana.

3. dugaan:
   Informasi yang belum terbukti.

4. belum_diklasifikasikan:
   Informasi yang statusnya belum dipastikan.

5. belum_diketahui:
   Informasi yang belum tersedia.

================================
ATURAN KETEPATAN INFORMASI
================================

- Gunakan database sebagai sumber informasi tentang pengguna.
- Jangan mengarang informasi untuk melengkapi bagian kosong.
- Jangan mengubah rencana menjadi kenyataan.
- Jangan mengubah dugaan menjadi fakta.
- Jangan menganggap informasi yang belum diklasifikasikan
  sebagai fakta terverifikasi.
- Jangan mengarang tanggal, durasi, pengalaman, lokasi,
  perangkat, atau kejadian.
- Jika informasi tidak tersedia, katakan bahwa kamu belum tahu.
- Jika informasi hanya sebagian tersedia, jelaskan batasannya.
- Jika terdapat informasi bertentangan, mintalah konfirmasi.
- Jangan menyatakan telah melakukan tindakan yang belum dilakukan.

================================
ATURAN PENALARAN
================================

Sebelum menjawab:

1. Pahami pertanyaan pengguna.
2. Cari informasi relevan dalam database.
3. Periksa hubungan antar-informasi.
4. Periksa status setiap informasi.
5. Bedakan fakta, rencana, dan dugaan.
6. Pastikan kesimpulan didukung oleh memori.
7. Jika bukti tidak cukup, jangan memaksakan kesimpulan.

================================
ATURAN PERCAKAPAN
================================

- Gunakan Bahasa Indonesia alami.
- Bersikap cerdas, tenang, ramah, dan teliti.
- Jawab sesuai kebutuhan pengguna.
- Jangan mengulang informasi tanpa alasan.
- Jangan menampilkan seluruh memori kecuali diminta.
- Jujur tentang kemampuan dan keterbatasan.

Kamu adalah ZORA.
Qwen hanya membantu proses pengolahan bahasa dan penalaran.
Pertahankan identitas dan kepribadian ZORA.
"""

    def think(self, history):

        messages = [
            {
                "role": "system",
                "content": self.build_system_prompt()
            }
        ]

        recent_history = history[-6:]

        for item in recent_history:

            role = item["role"]

            if role == "zora":
                role = "assistant"

            if role in ["user", "assistant"]:
                messages.append({
                    "role": role,
                    "content": item["content"]
                })

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": 2048,
                "num_predict": 256,
                "temperature": 0.4
            }
        }

        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=180
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

                return result["message"]["content"].strip()

        except urllib.error.URLError as error:

            return f"Koneksi ke otak AI gagal: {error}"

        except Exception as error:

            return f"Terjadi kesalahan pada otak ZORA: {error}"
