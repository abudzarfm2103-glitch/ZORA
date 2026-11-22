import re


class MemoryRelationship:

    STATUS_PRIORITY = {
        "fakta": 3,
        "rencana": 2,
        "dugaan": 1,
        "belum_diklasifikasikan": 0
    }

    def __init__(self, memory):
        self.memory = memory

    def extract_work_relationship(self, content, status):
        if not isinstance(content, str):
            return None

        text = content.strip()

        prefixes = [
            "saya bekerja sebagai",
            "saya menjabat sebagai"
        ]

        prefix = next(
            (
                item for item in prefixes
                if text.lower().startswith(item)
            ),
            None
        )

        if not prefix:
            return None

        detail = text[len(prefix):].strip()

        if not detail:
            return None

        parts = re.split(r"\s+di\s+", detail, maxsplit=1, flags=re.I)

        role = parts[0].strip()
        location = parts[1].strip() if len(parts) > 1 else None

        if not role:
            return None

        if location == "":
            location = None

        return {
            "subject": "Pengguna",
            "relation": "bekerja_sebagai",
            "object": role,
            "location": location,
            "status": status
        }

    def extract_project_relationship(self, content, status):
        if not isinstance(content, str):
            return None

        text = content.lower()

        patterns = [
            "zora nantinya akan berjalan di",
            "zora sekarang beroperasi di",
            "zora sudah beroperasi di",
            "zora saat ini beroperasi di",
            "zora sekarang berjalan di",
            "zora sudah berjalan di",
            "zora saat ini berjalan di",
            "zora akan berjalan di",
            "zora beroperasi di",
            "zora berjalan di"
        ]

        for pattern in patterns:
            position = text.find(pattern)

            if position == -1:
                continue

            location_start = position + len(pattern)
            location = content[location_start:].strip(" .,!?:;")

            if not location:
                continue

            relation = "direncanakan_berjalan_di"

            if status == "fakta":
                relation = "berjalan_di"

            return {
                "subject": "ZORA",
                "relation": relation,
                "object": location,
                "status": status
            }

        return None

    def build_relationships(self):
        memories = self.memory.recall_details()
        selected = {}

        for content, category, status, created_at in memories:
            relationship = None

            if category == "pekerjaan":
                relationship = self.extract_work_relationship(
                    content,
                    status
                )

            elif category == "proyek":
                relationship = self.extract_project_relationship(
                    content,
                    status
                )

            if not relationship:
                continue

            location = relationship.get("location") or ""

            key = (
                relationship["subject"].casefold(),
                relationship["relation"].casefold(),
                relationship["object"].strip().casefold(),
                location.strip().casefold()
            )

            priority = self.STATUS_PRIORITY.get(status, 0)

            if key not in selected:
                selected[key] = relationship
                continue

            old_status = selected[key]["status"]
            old_priority = self.STATUS_PRIORITY.get(old_status, 0)

            if priority > old_priority:
                selected[key] = relationship

        return list(selected.values())

    def show_relationships(self):
        relationships = self.build_relationships()

        if not relationships:
            return (
                "Belum ada hubungan informasi "
                "yang dapat dikenali."
            )

        results = [
            "Hubungan informasi yang saya pahami:"
        ]

        for item in relationships:
            if item["relation"] == "bekerja_sebagai":
                results.append(
                    f"- {item['subject']} bekerja sebagai "
                    f"{item['object']}"
                )

                if item.get("location"):
                    results.append(
                        f"  Tempat kerja: {item['location']}"
                    )
            else:
                results.append(
                    f"- {item['subject']} "
                    f"{item['relation']} "
                    f"{item['object']}"
                )

            results.append(
                f"  Status: {item['status']}"
            )

        return "\n".join(results)


def main():
    import tempfile
    from pathlib import Path
    from memory.memory import ZoraMemory

    with tempfile.TemporaryDirectory() as folder:
        memory = ZoraMemory(Path(folder) / "test.db")

        try:
            memory.save(
                "Saya bekerja sebagai Supervisor di DC Senen",
                "pekerjaan",
                "fakta"
            )

            memory.save(
                "Saya bekerja sebagai Supervisor di DC Cakung",
                "pekerjaan",
                "fakta"
            )

            relationship = MemoryRelationship(memory)
            results = relationship.build_relationships()

            locations = {
                item.get("location")
                for item in results
                if item["relation"] == "bekerja_sebagai"
            }

            assert "DC Senen" in locations
            assert "DC Cakung" in locations
            assert len(results) == 2
            print("LULUS: jabatan sama dengan lokasi berbeda tetap dipisahkan")

            memory.save(
                "Saya bekerja sebagai Admin di DC Senen",
                "pekerjaan",
                "rencana"
            )

            memory.save(
                "Saya menjabat sebagai Admin di DC Senen",
                "pekerjaan",
                "fakta"
            )

            results = relationship.build_relationships()

            admin = [
                item for item in results
                if item["object"] == "Admin"
            ]

            assert len(admin) == 1
            assert admin[0]["status"] == "fakta"
            print("LULUS: fakta diprioritaskan dari rencana yang sama")

            print("\nHASIL: 2/2 pengujian hubungan memori lulus")

        finally:
            memory.close()


if __name__ == "__main__":
    main()
