
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain.zora import Zora


def main():

    zora = Zora()

    nama_file = "developer_sandbox/pengujian/hasil_generator_01.py"

    try:
        print("ZORA sedang membuat kode...")

        hasil = zora.generate_code(
            "Buat program untuk menghitung 10 + 20 dan tampilkan hasilnya."
        )

        if not hasil.get("success"):
            print("Pembuatan kode gagal:")
            print(hasil.get("message"))
            return

        kode = hasil["code"]

        print("\nKode berhasil dibuat:")
        print(kode)

        target = zora.execution.validate_path(nama_file)

        if target.exists():
            print("\nFile sudah tersedia. Tidak akan ditimpa.")
            return

        dibuat = zora.execution.create_file(nama_file)

        if not dibuat.get("success"):
            print(dibuat.get("message"))
            return

        disimpan = zora.execution.write_file(nama_file, kode)

        if not disimpan.get("success"):
            print(disimpan.get("message"))
            return

        print("\nKode berhasil disimpan.")
        print("ZORA sedang menguji kode...")

        pengujian = zora.execution.test_code(nama_file)

        print("\nHasil pengujian:")
        print(pengujian)

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
