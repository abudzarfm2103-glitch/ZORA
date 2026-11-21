
import re


class ZoraCommandUnderstanding:

    def understand(self, message):

        text = " ".join(message.lower().strip().split())

        if not text:
            return None

        # Menguji kode di Sandbox
        test_phrases = [
            "tolong uji kode",
            "uji kode",
            "tes kode",
            "jalankan pengujian kode"
        ]

        for phrase in test_phrases:

            if text.startswith(phrase):

                position = text.find(phrase)
                name = message[position + len(phrase):].strip(" .,!?:;")

                if not name:
                    return {
                        "action": "uji_kode",
                        "parameters": {},
                        "needs_clarification": True,
                        "message": "File Python mana yang ingin saya uji?"
                    }

                return {
                    "action": "uji_kode",
                    "parameters": {"nama": name},
                    "needs_clarification": False
                }

        # Membuat folder
        create_phrases = [
            "tolong siapkan folder",
            "saya butuh folder",
            "buat tempat untuk menyimpan",
            "tolong buat folder",
            "buatkan folder",
            "siapkan folder",
            "buat folder"
        ]

        for phrase in create_phrases:

            if phrase in text:

                position = text.find(phrase)
                name = message[position + len(phrase):].strip(" .,!?:;")

                prefixes = [
                    "baru bernama ",
                    "untuk menyimpan ",
                    "baru ",
                    "bernama ",
                    "untuk "
                ]

                changed = True

                while changed:
                    changed = False

                    for prefix in prefixes:
                        if name.lower().startswith(prefix):
                            name = name[len(prefix):].strip()
                            changed = True
                            break

                if not name:
                    return {
                        "action": "buat_folder",
                        "parameters": {},
                        "needs_clarification": True,
                        "message": "Folder tersebut ingin diberi nama apa?"
                    }

                return {
                    "action": "buat_folder",
                    "parameters": {"nama": name},
                    "needs_clarification": False
                }

        # Melihat isi folder tertentu atau folder utama
        list_phrases = [
            "tampilkan isi folder",
            "lihat isi folder",
            "apa isi folder",
            "tampilkan file",
            "lihat file",
            "daftar file"
        ]

        for phrase in list_phrases:

            if phrase in text:

                position = text.find(phrase)
                lokasi = message[position + len(phrase):].strip(" .,!?:;")

                return {
                    "action": "daftar_file",
                    "parameters": {
                        "lokasi": lokasi if lokasi else "."
                    },
                    "needs_clarification": False
                }

        # Membuat file
        create_file_phrases = [
            "tolong buatkan file",
            "tolong buat file",
            "buatkan file",
            "buat file",
            "siapkan file"
        ]

        for phrase in create_file_phrases:

            if phrase in text:

                position = text.find(phrase)
                name = message[position + len(phrase):].strip(" .,!?:;")

                if not name:
                    return {
                        "action": "buat_file",
                        "parameters": {},
                        "needs_clarification": True,
                        "message": "File tersebut ingin diberi nama apa?"
                    }

                return {
                    "action": "buat_file",
                    "parameters": {"nama": name},
                    "needs_clarification": False
                }

        # Membaca file
        read_phrases = [
            "tolong baca file",
            "bacakan file",
            "baca file",
            "lihat isi file"
        ]

        for phrase in read_phrases:

            if phrase in text:

                position = text.find(phrase)
                name = message[position + len(phrase):].strip(" .,!?:;")

                if not name:
                    return {
                        "action": "baca_file",
                        "parameters": {},
                        "needs_clarification": True,
                        "message": "File mana yang ingin saya baca?"
                    }

                return {
                    "action": "baca_file",
                    "parameters": {"nama": name},
                    "needs_clarification": False
                }

        # Menulis file
        write_phrases = [
            "tulis ke file",
            "tuliskan ke file",
            "simpan ke file",
            "isi file"
        ]

        for phrase in write_phrases:

            if phrase in text:

                position = text.find(phrase)
                remainder = message[position + len(phrase):].strip()

                match = re.search(
                    r"\s+dengan isi\s+",
                    remainder,
                    flags=re.IGNORECASE
                )

                if match:
                    name = remainder[:match.start()].strip(" .,!?:;")
                    content = remainder[match.end():].strip()
                else:
                    name = remainder.strip(" .,!?:;")
                    content = ""

                if not name:
                    return {
                        "action": "tulis_file",
                        "parameters": {},
                        "needs_clarification": True,
                        "message": "File mana yang ingin saya isi?"
                    }

                if not content:
                    return {
                        "action": "tulis_file",
                        "parameters": {"nama": name},
                        "needs_clarification": True,
                        "message": "Apa isi tulisan yang ingin disimpan?"
                    }

                return {
                    "action": "tulis_file",
                    "parameters": {
                        "nama": name,
                        "isi": content
                    },
                    "needs_clarification": False
                }

        return None
