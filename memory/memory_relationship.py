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
        text = content.lower().strip()

        prefixes = [
            "saya bekerja sebagai",
            "saya menjabat sebagai"
        ]

        for prefix in prefixes:
            if text.startswith(prefix):
                detail = content[len(prefix):].strip()

                if " di " in detail.lower():
                    parts = detail.split(" di ", 1)

                    return {
                        "subject": "Pengguna",
                        "relation": "bekerja_sebagai",
                        "object": parts[0].strip(),
                        "location": parts[1].strip(),
                        "status": status
                    }

                return {
                    "subject": "Pengguna",
                    "relation": "bekerja_sebagai",
                    "object": detail,
                    "location": None,
                    "status": status
                }

        return None

    def extract_project_relationship(self, content, status):
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
            location = content[location_start:].strip(
                " .,!?:;"
            )

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

            key = (
                relationship["subject"],
                relationship["relation"],
                relationship["object"].lower()
            )

            priority = self.STATUS_PRIORITY.get(status, 0)

            if key not in selected:
                selected[key] = relationship
                continue

            old_status = selected[key]["status"]
            old_priority = self.STATUS_PRIORITY.get(
                old_status,
                0
            )

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
