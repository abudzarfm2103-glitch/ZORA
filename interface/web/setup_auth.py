import hashlib
import json
import os
import secrets
import tempfile
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
TARGET = DATA / "web_auth.json"
ITERATIONS = 600000

def main():
    DATA.mkdir(parents=True, exist_ok=True)

    if TARGET.exists() or TARGET.is_symlink():
        print("Konfigurasi login sudah ada. Tidak diubah.")
        return

    password = getpass("Buat password ZORA (minimal 12 karakter): ")

    if len(password) < 12:
        print("Password minimal 12 karakter.")
        return

    confirm = getpass("Ulangi password: ")

    if password != confirm:
        print("Password tidak cocok.")
        return

    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, ITERATIONS
    )

    config = {
        "password_hash": (
            f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"
        ),
        "secret_key": secrets.token_hex(32)
    }

    fd, temp_name = tempfile.mkstemp(dir=DATA, prefix=".web_auth_")

    try:
        os.fchmod(fd, 0o600)

        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f)
            f.flush()
            os.fsync(f.fileno())

        try:
            os.link(temp_name, TARGET)
        except FileExistsError:
            print("Konfigurasi sudah dibuat sebelumnya.")
            return

        os.chmod(TARGET, 0o600)
        print("Konfigurasi login berhasil dibuat.")
        print("Password tersimpan dalam bentuk hash.")

    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

if __name__ == "__main__":
    main()
