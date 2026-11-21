
from pathlib import Path

from developer.sandbox_runner import ZoraSandboxRunner


class ZoraExecutionEngine:

    ALLOWED_ACTIONS = [
        "buat_folder",
        "daftar_file",
        "buat_file",
        "baca_file",
        "tulis_file",
        "uji_kode"
    ]

    def __init__(self):

        self.project_root = Path(__file__).resolve().parent.parent

        self.workspace = (
            self.project_root / "data" / "zora_workspace"
        )

        self.workspace.mkdir(parents=True, exist_ok=True)

        self.sandbox = ZoraSandboxRunner()

    def validate_path(self, name):

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Nama file atau folder tidak valid.")

        target = (self.workspace / name).resolve()

        if not target.is_relative_to(self.workspace.resolve()):
            raise PermissionError(
                "Akses ditolak. Lokasi berada di luar ruang kerja ZORA."
            )

        return target

    def create_folder(self, name):

        target = self.validate_path(name)

        if target.exists():
            return {
                "success": False,
                "message": "Folder tersebut sudah tersedia."
            }

        target.mkdir(parents=True)

        return {
            "success": True,
            "message": f"Folder berhasil dibuat: {target.name}"
        }

    def list_files(self, name="."):

        target = self.validate_path(name)

        if not target.exists():
            return {
                "success": False,
                "message": "Folder tidak ditemukan."
            }

        if not target.is_dir():
            return {
                "success": False,
                "message": "Lokasi tersebut bukan folder."
            }

        items = []

        for item in sorted(target.iterdir()):

            jenis = "Folder" if item.is_dir() else "File"

            items.append({
                "nama": item.name,
                "jenis": jenis
            })

        return {
            "success": True,
            "lokasi": str(target.relative_to(self.workspace)),
            "items": items
        }

    def create_file(self, name):

        target = self.validate_path(name)

        if target.exists():
            return {
                "success": False,
                "message": "File tersebut sudah tersedia."
            }

        if not target.parent.exists():
            return {
                "success": False,
                "message": "Folder tujuan belum tersedia."
            }

        if not target.parent.is_dir():
            return {
                "success": False,
                "message": "Lokasi tujuan bukan folder."
            }

        target.touch()

        return {
            "success": True,
            "message": f"File berhasil dibuat: {target.name}"
        }

    def read_file(self, name):

        target = self.validate_path(name)

        if not target.exists():
            return {
                "success": False,
                "message": "File tidak ditemukan."
            }

        if not target.is_file():
            return {
                "success": False,
                "message": "Lokasi tersebut bukan file."
            }

        content = target.read_text(encoding="utf-8")

        return {
            "success": True,
            "nama": target.name,
            "content": content
        }

    def write_file(self, name, content):

        target = self.validate_path(name)

        if not isinstance(content, str):
            return {
                "success": False,
                "message": "Isi file harus berupa teks."
            }

        if target.exists() and not target.is_file():
            return {
                "success": False,
                "message": "Lokasi tersebut bukan file."
            }

        if not target.parent.exists():
            return {
                "success": False,
                "message": "Folder tujuan belum tersedia."
            }

        target.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "message": f"Isi file berhasil disimpan: {target.name}"
        }

    def test_code(self, name):

        if not isinstance(name, str) or not name.strip():
            return {
                "success": False,
                "message": "Nama file pengujian tidak valid."
            }

        return self.sandbox.run_file(name)

    def execute(self, action, parameters=None):

        parameters = parameters or {}

        if action not in self.ALLOWED_ACTIONS:
            return {
                "success": False,
                "message": "Tindakan tidak diizinkan."
            }

        try:

            if action == "buat_folder":
                return self.create_folder(parameters.get("nama"))

            if action == "daftar_file":
                return self.list_files(parameters.get("lokasi", "."))

            if action == "buat_file":
                return self.create_file(parameters.get("nama"))

            if action == "baca_file":
                return self.read_file(parameters.get("nama"))

            if action == "tulis_file":
                return self.write_file(
                    parameters.get("nama"),
                    parameters.get("isi")
                )

            if action == "uji_kode":
                return self.test_code(parameters.get("nama"))

        except (ValueError, PermissionError, OSError, TypeError) as error:

            return {
                "success": False,
                "message": str(error)
            }

        return {
            "success": False,
            "message": "Perintah tidak dikenali."
        }
