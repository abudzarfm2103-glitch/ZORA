class ZoraLearningAnalyzer:

    MIN_SUCCESS_FOR_VERIFICATION = 2

    def __init__(self, history):
        self.history = history

    def analyze(self):

        report = self.history.report()

        if not isinstance(report, dict):
            raise ValueError("Laporan riwayat tidak valid.")

        records = report.get("history", [])

        if not isinstance(records, list):
            raise ValueError("Data riwayat tidak valid.")

        skills = {}

        for item in records:

            if not isinstance(item, dict):
                continue

            skill_id = item.get("skill_id")

            if not isinstance(skill_id, str) or not skill_id.strip():
                continue

            skill_name = item.get("skill_name")

            if not isinstance(skill_name, str) or not skill_name.strip():
                skill_name = skill_id

            if skill_id not in skills:
                skills[skill_id] = {
                    "id": skill_id,
                    "name": skill_name,
                    "successful": 0,
                    "failed": 0
                }

            if item.get("success") is True:
                skills[skill_id]["successful"] += 1
            else:
                skills[skill_id]["failed"] += 1

        verified = []
        needs_improvement = []
        needs_testing = []
        skill_details = []

        for data in skills.values():

            total = data["successful"] + data["failed"]

            if data["failed"] > 0:
                status = "perlu_perbaikan"
                needs_improvement.append(data["name"])

            elif (
                data["successful"]
                >= self.MIN_SUCCESS_FOR_VERIFICATION
            ):
                status = "terverifikasi"
                verified.append(data["name"])

            else:
                status = "perlu_pengujian"
                needs_testing.append(data["name"])

            skill_details.append({
                "id": data["id"],
                "name": data["name"],
                "successful": data["successful"],
                "failed": data["failed"],
                "total": total,
                "status": status
            })

        if needs_improvement:
            recommendation = (
                "Perbaiki kemampuan yang masih memiliki kegagalan."
            )

        elif needs_testing:
            recommendation = (
                "Lakukan pengujian tambahan sebelum menyatakan "
                "kemampuan telah terverifikasi."
            )

        elif verified:
            recommendation = (
                "Kemampuan dasar telah terverifikasi. "
                "Kembangkan kemampuan baru dan tingkatkan "
                "kompleksitas pengujian."
            )

        else:
            recommendation = (
                "Belum ada riwayat pengembangan. "
                "Mulai pengembangan kemampuan dasar."
            )

        return {
            "total_pengembangan": report.get("total", len(records)),
            "total_berhasil": report.get(
                "successful",
                sum(1 for item in records
                    if isinstance(item, dict)
                    and item.get("success") is True)
            ),
            "total_gagal": report.get(
                "failed",
                sum(1 for item in records
                    if isinstance(item, dict)
                    and item.get("success") is not True)
            ),
            "kemampuan_terverifikasi": verified,
            "perlu_perbaikan": needs_improvement,
            "perlu_pengujian": needs_testing,
            "detail_kemampuan": skill_details,
            "rekomendasi": recommendation
        }

    def report(self):

        result = self.analyze()

        print("\nZORA AUTONOMOUS LEARNING ANALYZER")
        print("--------------------------------")

        print("Total pengembangan:", result["total_pengembangan"])
        print("Berhasil:", result["total_berhasil"])
        print("Gagal:", result["total_gagal"])

        print("\nKemampuan terverifikasi:")

        if result["kemampuan_terverifikasi"]:
            for item in result["kemampuan_terverifikasi"]:
                print("-", item)
        else:
            print("- Belum ada.")

        print("\nKemampuan perlu pengujian:")

        if result["perlu_pengujian"]:
            for item in result["perlu_pengujian"]:
                print("-", item)
        else:
            print("- Tidak ada.")

        print("\nKemampuan perlu perbaikan:")

        if result["perlu_perbaikan"]:
            for item in result["perlu_perbaikan"]:
                print("-", item)
        else:
            print("- Tidak ada.")

        print("\nRekomendasi ZORA:")
        print(result["rekomendasi"])

        return result


def main():

    from developer.development_history import ZoraDevelopmentHistory

    history = ZoraDevelopmentHistory()
    analyzer = ZoraLearningAnalyzer(history)

    analyzer.report()


if __name__ == "__main__":
    main()
