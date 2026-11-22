import os
import tempfile
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

    MAX_READ_SIZE = 1_000_000
    MAX_WRITE_SIZE = 1_000_000
    MAX_LIST_ITEMS = 500

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent

        self.workspace = (
            self.project_root / "data" / "zora_workspace"
        ).resolve()

        self.workspace.mkdir(parents=True, exist_ok=True)

        self.sandbox = ZoraSandboxRunner()

    def validate_path(self, name):

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Nama file atau folder tidak valid."
            )

        try:
            relative = Path(name)

            if relative.is_absolute():
                raise PermissionError(
                    "Akses ke lokasi absolut tidak diizinkan."
                )

            if ".." in relative.parts:
                raise PermissionError(
                    "Akses ke folder di luar ruang kerja ditolak."
                )

            candidate = self.workspace / relative

            current = self.workspace

            for part in relative.parts:
                if part in ("", "."):
                    continue

                current = current / part

                if current.is_symlink():
                    raise PermissionError(
                        "Akses melalui symbolic link tidak diizinkan."
                    )

            target = candidate.resolve()

            if not target.is_relative_to(self.workspace):
                raise PermissionError(
                    "Akses ditolak. Lokasi berada di luar ruang kerja ZORA."
                )

            return target

        except (OSError, ValueError) as error:
            if isinstance(error, PermissionError):
                raise

            raise ValueError(
                "Lokasi file atau folder tidak valid."
            ) from error

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

        entries = []

        with os.scandir(target) as scanner:
            for entry in scanner:
                entries.append(entry)

                if len(entries) > self.MAX_LIST_ITEMS:
                    break

        truncated = len(entries) > self.MAX_LIST_ITEMS
        entries = entries[:self.MAX_LIST_ITEMS]
        entries.sort(key=lambda item: item.name.lower())

        items = []

        for entry in entries:
            if entry.is_symlink():
                jenis = "Link"
            elif entry.is_dir(follow_symlinks=False):
                jenis = "Folder"
            else:
                jenis = "File"

            items.append({
                "nama": entry.name,
                "jenis": jenis
            })

        return {
            "success": True,
            "lokasi": str(target.relative_to(self.workspace)),
            "items": items,
            "terbatas": truncated
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

        with target.open("x", encoding="utf-8"):
            pass

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

        if target.stat().st_size > self.MAX_READ_SIZE:
            return {
                "success": False,
                "message": "Ukuran file terlalu besar untuk dibaca."
            }

        with target.open("rb") as file:
            content_bytes = file.read(
                self.MAX_READ_SIZE + 1
            )

        if len(content_bytes) > self.MAX_READ_SIZE:
            return {
                "success": False,
                "message": "Ukuran file terlalu besar untuk dibaca."
            }

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "success": False,
                "message": "File bukan teks UTF-8 yang valid."
            }

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

        try:
            content_bytes = content.encode("utf-8")
        except UnicodeEncodeError:
            return {
                "success": False,
                "message": "Isi file tidak dapat dikodekan sebagai UTF-8."
            }

        if len(content_bytes) > self.MAX_WRITE_SIZE:
            return {
                "success": False,
                "message": "Ukuran isi file melebihi batas 1 MB."
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

        if not target.parent.is_dir():
            return {
                "success": False,
                "message": "Lokasi tujuan bukan folder."
            }

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=".zora-temp-",
                delete=False
            ) as temporary_file:

                temporary_path = Path(temporary_file.name)
                temporary_file.write(content_bytes)

            os.replace(temporary_path, target)

        except OSError:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

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

        if not isinstance(parameters, dict):
            parameters = {}

        if action not in self.ALLOWED_ACTIONS:
            return {
                "success": False,
                "message": "Tindakan tidak diizinkan."
            }

        try:
            if action == "buat_folder":
                return self.create_folder(
                    parameters.get("nama")
                )

            if action == "daftar_file":
                return self.list_files(
                    parameters.get("lokasi", ".")
                )

            if action == "buat_file":
                return self.create_file(
                    parameters.get("nama")
                )

            if action == "baca_file":
                return self.read_file(
                    parameters.get("nama")
                )

            if action == "tulis_file":
                return self.write_file(
                    parameters.get("nama"),
                    parameters.get("isi")
                )

            if action == "uji_kode":
                return self.test_code(
                    parameters.get("nama")
                )

        except (
            ValueError,
            PermissionError,
            OSError,
            TypeError,
            UnicodeError,
            RecursionError
        ) as error:

            return {
                "success": False,
                "message": str(error) or "Operasi gagal."
            }

        return {
            "success": False,
            "message": "Perintah tidak dikenali."
        }
