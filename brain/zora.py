
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory.memory import ZoraMemory
from memory.auto_memory import AutoMemory
from memory.memory_update import MemoryUpdate

from brain.understanding import ZoraUnderstanding
from brain.conversation import ZoraConversation
from brain.context_manager import ZoraContextManager
from brain.llm_engine import ZoraBrain

from developer.execution_engine import ZoraExecutionEngine
from developer.command_understanding import ZoraCommandUnderstanding
from developer.code_generator import ZoraCodeGenerator

from brain.web_search import WebSearch
from brain.web_reader import WebReader


class Zora:

    def __init__(self):

        self.root = Path(__file__).resolve().parent.parent

        identity_file = self.root / "personality" / "identity.json"

        with open(identity_file, "r", encoding="utf-8") as file:
            self.identity = json.load(file)

        self.memory = ZoraMemory()
        self.auto_memory = AutoMemory(self.memory)
        self.memory_update = MemoryUpdate(self.memory)

        self.understanding = ZoraUnderstanding(self.memory)
        self.conversation = ZoraConversation()

        self.context_manager = ZoraContextManager(
            self.conversation,
            self.memory
        )

        self.brain = ZoraBrain(
            self.identity,
            self.memory
        )

        self.execution = ZoraExecutionEngine()
        self.command_understanding = ZoraCommandUnderstanding()
        self.web_search = WebSearch()
        self.web_reader = WebReader()

        self.code_generator = ZoraCodeGenerator(
            self.brain,
            self.execution
        )

        self.pending_command = None
        self.pending_parameters = {}

    def generate_code(self, instruction):

        result = self.code_generator.generate(instruction)

        if not result.get("success"):
            return result

        code = result.get("code", "")

        try:

            tree = ast.parse(code)

            self.execution.sandbox.validate_code(tree)

            return {
                "success": True,
                "message": "Kode berhasil dibuat dan lolos validasi Sandbox.",
                "code": code
            }

        except SyntaxError as error:

            return {
                "success": False,
                "message": f"Kode memiliki kesalahan sintaks pada baris {error.lineno}."
            }

        except (ValueError, PermissionError, TypeError) as error:

            return {
                "success": False,
                "message": f"Kode ditolak oleh Sandbox: {error}"
            }

    def reply(self, message):

        print("ZORA:", message)
        self.conversation.remember_zora(message)

    def process_message(self, message):

        message = message.strip()

        if not message:
            return "Silakan tulis pesan terlebih dahulu."

        self.conversation.remember_user(message)
        perintah = message.lower().strip()

        if self.memory_update.pending_update:

            jawaban = self.memory_update.confirm(message)
            self.conversation.remember_zora(jawaban)
            return jawaban

        if self.pending_command:

            if perintah in ["batal", "batalkan"]:

                self.pending_command = None
                self.pending_parameters = {}
                jawaban = "Baik, perintah dibatalkan."

            else:

                action = self.pending_command

                if action == "buat_folder":
                    self.pending_parameters["nama"] = message

                elif action == "buat_file":
                    self.pending_parameters["nama"] = message

                elif action == "baca_file":
                    self.pending_parameters["nama"] = message

                elif action == "uji_kode":
                    self.pending_parameters["nama"] = message

                elif action == "tulis_file":

                    if not self.pending_parameters.get("nama"):
                        self.pending_parameters["nama"] = message
                    else:
                        self.pending_parameters["isi"] = message

                result = None

                if (
                    action != "tulis_file"
                    or self.pending_parameters.get("isi")
                ):

                    result = self.execution.execute(
                        action,
                        self.pending_parameters
                    )

                    self.pending_command = None
                    self.pending_parameters = {}

                    jawaban = self.format_execution_result(
                        action,
                        result
                    )

                else:
                    jawaban = "Apa isi tulisan yang ingin disimpan?"

            self.conversation.remember_zora(jawaban)
            return jawaban

        if perintah == "keluar":
            return "Untuk mengakhiri sesi web, cukup tutup halaman chat."

        if perintah == "ingatanku":

            data = self.memory.recall_details()

            if not data:
                jawaban = "Belum ada informasi yang tersimpan."

            else:

                hasil = ["Berikut informasi yang saya ingat:"]

                for content, kategori, status, created_at in data:
                    hasil.append(f"- {content} [Status: {status}]")

                jawaban = "\n".join(hasil)

            self.conversation.remember_zora(jawaban)
            return jawaban

        if perintah in [
            "ingat pribadi",
            "ingat pekerjaan",
            "ingat proyek",
            "ingat preferensi",
            "ingat keluarga"
        ]:

            kategori = perintah.replace("ingat ", "")
            data = self.memory.recall_details(kategori)

            if not data:
                jawaban = "Belum ada informasi dalam kategori tersebut."

            else:

                hasil = ["Berikut informasi yang saya ingat:"]

                for content, kategori, status, created_at in data:
                    hasil.append(f"- {content} [Status: {status}]")

                jawaban = "\n".join(hasil)

            self.conversation.remember_zora(jawaban)
            return jawaban


        # Internet hanya diakses jika pengguna meminta secara eksplisit.
        search_prefixes = (
            "cari di internet tentang ",
            "telusuri internet tentang ",
            "cari di internet ",
            "telusuri internet ",
            "cari di internet",
            "telusuri internet",
        )

        read_prefixes = (
            "baca halaman ",
            "buka halaman web ",
            "baca url ",
            "baca halaman",
            "buka halaman web",
            "baca url",
        )

        web_response = None

        for prefix in search_prefixes:
            if perintah.startswith(prefix):
                query = message[len(prefix):].strip()

                if not query:
                    web_response = "Apa yang ingin saya cari di internet?"
                else:
                    result = self.web_search.search(query)

                    if not result.get("success"):
                        web_response = (
                            "Pencarian internet gagal: "
                            + str(result.get("error", "Kesalahan tidak diketahui."))
                        )
                    elif not result.get("results"):
                        web_response = "Saya tidak menemukan hasil pencarian."
                    else:
                        sources = result["results"]
                        external_data = json.dumps(
                            sources, ensure_ascii=False
                        )
                        summary = self.brain.summarize_external_data(
                            query, external_data
                        )

                        lines = [
                            "HASIL ANALISIS ZORA",
                            summary,
                            "",
                            "SUMBER INFORMASI:"
                        ]

                        for index, item in enumerate(sources, 1):
                            lines.extend([
                                f"{index}. {item.get('title') or 'Tanpa judul'}",
                                item.get("url", "")
                            ])

                        web_response = "\n".join(lines)
                break

        if web_response is None:
            for prefix in read_prefixes:
                if perintah.startswith(prefix):
                    url = message[len(prefix):].strip()

                    if not url:
                        web_response = (
                            "Silakan berikan alamat halaman web yang ingin dibaca."
                        )
                    else:
                        result = self.web_reader.read(url)

                        if not result.get("success"):
                            web_response = (
                                "Halaman web gagal dibaca: "
                                + str(result.get("error", "Kesalahan tidak diketahui."))
                            )
                        else:
                            title = result.get("title", "Tanpa judul")
                            source = result.get("url", url)
                            external_data = json.dumps({
                                "judul": title,
                                "alamat_sumber": source,
                                "isi_halaman": result.get("content", ""),
                                "terpotong": result.get("truncated", False)
                            }, ensure_ascii=False)

                            summary = self.brain.summarize_external_data(
                                "Rangkum dan jelaskan isi halaman ini.",
                                external_data
                            )

                            web_response = (
                                "HASIL ANALISIS ZORA\n"
                                + summary
                                + "\n\nSumber: " + source
                            )
                    break

        if web_response is not None:
            self.conversation.remember_zora(web_response)
            return web_response

        command = self.command_understanding.understand(message)

        if command:

            action = command["action"]

            if command["needs_clarification"]:

                self.pending_command = action
                self.pending_parameters = command.get("parameters", {})

                jawaban = command["message"]

            else:

                result = self.execution.execute(
                    action,
                    command["parameters"]
                )

                if (
                    not result["success"]
                    and action in [
                        "buat_folder",
                        "buat_file",
                        "baca_file",
                        "tulis_file",
                        "uji_kode"
                    ]
                    and not command["parameters"].get("nama")
                ):

                    self.pending_command = action
                    self.pending_parameters = command["parameters"]

                    jawaban = (
                        "Informasi perintah belum lengkap. "
                        "Silakan lengkapi terlebih dahulu."
                    )

                else:

                    jawaban = self.format_execution_result(
                        action,
                        result
                    )

            self.conversation.remember_zora(jawaban)
            return jawaban

        jawaban = self.understanding.understand(message)

        if not jawaban:
            jawaban = self.context_manager.understand(message)

        if jawaban:
            self.conversation.remember_zora(jawaban)
            return jawaban

        hasil_filter = self.auto_memory.filter.analyze(message)

        if hasil_filter:

            kategori = hasil_filter["category"]

            perubahan = self.memory_update.check(
                hasil_filter["content"],
                kategori
            )

            if perubahan:

                jawaban = perubahan["message"]
                self.conversation.remember_zora(jawaban)
                return jawaban

            tersimpan = self.auto_memory.analyze(message)

            if tersimpan:

                jawaban = (
                    "Informasi berhasil disimpan dalam kategori "
                    f"{tersimpan['category']} dengan status "
                    f"{tersimpan['status']}."
                )

                self.conversation.remember_zora(jawaban)
                return jawaban

        riwayat = self.conversation.get_history()
        jawaban = self.brain.think(riwayat)

        self.conversation.remember_zora(jawaban)
        return jawaban

    def format_execution_result(self, action, result):

        if not result.get("success"):

            return result.get(
                "message",
                "Perintah gagal dijalankan."
            )

        if action == "daftar_file":

            items = result.get("items", [])

            if not items:
                return "Ruang kerja ZORA masih kosong."

            hasil = ["Berikut isi ruang kerja ZORA:"]

            for item in items:
                hasil.append(
                    f"- {item['jenis']}: {item['nama']}"
                )

            return "\n".join(hasil)

        if action == "baca_file":

            content = result.get("content", "")

            if not content:
                return f"File {result.get('nama')} masih kosong."

            return (
                f"Isi file {result.get('nama')}:\n"
                f"{content}"
            )

        if action == "buat_folder":
            return result.get("message", "Folder berhasil dibuat.")

        if action == "buat_file":
            return result.get("message", "File berhasil dibuat.")

        if action == "tulis_file":
            return result.get("message", "Isi file berhasil disimpan.")

        if action == "uji_kode":

            output = result.get("output", "")

            if output:
                return (
                    "Pengujian kode berhasil.\n"
                    "Hasil:\n"
                    f"{output}"
                )

            return result.get(
                "message",
                "Pengujian kode selesai tanpa output."
            )

        return result.get("message", "Perintah berhasil dijalankan.")

    def show_memories(self, category=None):

        data = self.memory.recall_details(category)

        if not data:
            self.reply("Belum ada informasi dalam kategori tersebut.")
            return

        hasil = ["Berikut informasi yang saya ingat:"]

        for content, kategori, status, created_at in data:
            hasil.append(f"- {content} [Status: {status}]")

        self.reply("\n".join(hasil))

    def handle_pending_command(self, message):

        if not self.pending_command:
            return False

        jawaban = self.process_message(message)
        self.reply(jawaban)

        return True

    def handle_execution(self, message):

        command = self.command_understanding.understand(message)

        if not command:
            return False

        if command["needs_clarification"]:

            self.pending_command = command["action"]
            self.pending_parameters = command.get("parameters", {})

            self.reply(command["message"])
            return True

        result = self.execution.execute(
            command["action"],
            command["parameters"]
        )

        self.reply(
            self.format_execution_result(
                command["action"],
                result
            )
        )

        return True

    def start(self):

        print("=" * 40)
        print(f"{self.identity['name']} SYSTEM ONLINE")
        print("=" * 40)

        print("Otak AI: Qwen 2.5 1.5B")
        print("Memori jangka panjang: AKTIF")
        print("Klasifikasi memori: AKTIF")
        print("Execution Engine: AKTIF")
        print("Pemahaman perintah: AKTIF")
        print("Code Generator: AKTIF")
        print("Ketik 'ingatanku' untuk melihat memori.")
        print("Ketik 'keluar' untuk berhenti.\n")

        while True:

            pesan = input("Anda: ").strip()

            if not pesan:
                continue

            if pesan.lower() == "keluar":
                self.reply("Sampai jumpa.")
                self.memory.close()
                break

            jawaban = self.process_message(pesan)
            self.reply(jawaban)


if __name__ == "__main__":

    zora = Zora()
    zora.start()
