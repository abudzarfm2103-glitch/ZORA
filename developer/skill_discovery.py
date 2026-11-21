
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from developer.capability_evaluator import ZoraCapabilityEvaluator


class ZoraSkillDiscovery:

    def __init__(self, planner):

        self.planner = planner

        self.proposal_file = ROOT / "data" / "zora_skill_proposals.json"
        self.candidate_file = ROOT / "data" / "zora_new_skill_candidates.json"

        self.capability_evaluator = ZoraCapabilityEvaluator()

        self.priorities = {
            "perlu_perbaikan": 1,
            "perlu_penguatan": 2,
            "perlu_pengujian": 3,
            "belum_diuji": 4
        }

    def read_json(self, path, default):

        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

        return default

    def save_json(self, path, data):

        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

    def get_brain(self):

        developer = getattr(self.planner, "developer", None)
        zora = getattr(developer, "zora", None)
        brain = getattr(zora, "brain", None)

        if brain is not None and hasattr(brain, "think"):
            return brain

        return None

    def extract_field(self, response, label):

        pattern = (
            r"(?im)^\s*" + re.escape(label)
            + r"\s*:\s*(.*?)\s*$"
        )

        match = re.search(pattern, response)

        if match:
            return match.group(1).strip()

        return ""

    def analyze_new_capabilities(self, report, plan):

        brain = self.get_brain()

        if brain is None:
            print("Otak AI tidak tersedia.")
            return []

        existing_ids = list(report.keys())

        previous = self.read_json(
            self.candidate_file,
            []
        )

        known_ids = set(existing_ids)

        if isinstance(previous, list):
            for item in previous:
                if isinstance(item, dict):
                    known_ids.add(item.get("id"))

        evidence = {
            skill_id: {
                "name": result.get("name", skill_id),
                "status": result.get("status"),
                "successful": result.get("successful", 0),
                "failed": result.get("failed", 0)
            }
            for skill_id, result in report.items()
            if isinstance(result, dict)
        }

        prompt = f"""
Kamu adalah analis kemampuan AI bernama ZORA.

Analisis kemampuan yang belum dimiliki atau belum
tercakup dalam daftar kemampuan saat ini.

DATA KEMAMPUAN:
{json.dumps(evidence, ensure_ascii=False)}

ID YANG SUDAH ADA:
{", ".join(sorted(str(x) for x in known_ids))}

RENCANA SAAT INI:
{str(plan)[:1500]}

Cari SATU kemampuan baru yang berguna untuk
membuat ZORA lebih mandiri.

Jangan mengusulkan ID yang sudah ada.
Jangan mengarang hasil pengujian.
Jangan mengusulkan kemampuan yang sama dengan
kemampuan dalam daftar.

Jika tidak ada kemampuan baru yang masuk akal,
tulis saja: TIDAK_ADA.

Jika menemukan kemampuan baru, jawab tepat
dengan lima baris berikut:

ID: nama_kemampuan
NAMA: Nama kemampuan
ALASAN: Alasan kemampuan dibutuhkan
BUKTI: Keterbatasan yang terlihat dari data
UJI: Cara menguji kemampuan tersebut

Jangan gunakan JSON.
Jangan gunakan Markdown.
Jangan menambahkan teks di luar lima baris.
"""

        try:

            response = brain.think([
                {
                    "role": "user",
                    "content": prompt
                }
            ])

            if not isinstance(response, str):
                response = str(response)

            if "TIDAK_ADA" in response.upper():
                return []

            candidate = {
                "id": self.extract_field(response, "ID").lower(),
                "name": self.extract_field(response, "NAMA"),
                "reason": self.extract_field(response, "ALASAN"),
                "evidence": self.extract_field(response, "BUKTI"),
                "test_idea": self.extract_field(response, "UJI")
            }

            if not all(candidate.values()):
                print("Usulan AI tidak lengkap.")
                return []

            if not re.fullmatch(
                r"[a-z][a-z0-9_]{2,49}",
                candidate["id"]
            ):
                print("ID kemampuan baru tidak valid.")
                return []

            if candidate["id"] in known_ids:
                print("AI mengusulkan kemampuan yang sudah ada.")
                return []

            if candidate["id"] in (
                "tidak_ada",
                "none",
                "null"
            ):
                return []

            candidate.update({
                "source": "analisis_ai",
                "status": "calon_kemampuan",
                "priority": 5,
                "requires_review": True
            })

            return [candidate]

        except Exception as error:

            print("Analisis kemampuan AI gagal:", str(error))
            return []

    def discover(self):

        print("\nZORA sedang menganalisis kebutuhan pengembangan...")

        report = self.capability_evaluator.evaluate()
        plan = self.planner.create_plan()

        discovered = []

        for skill_id, result in report.items():

            if not isinstance(result, dict):
                continue

            status = result.get("status")

            if status not in self.priorities:
                continue

            actions = {
                "perlu_perbaikan": (
                    "Perbaikan",
                    "Pengujian terakhir gagal. "
                    "ZORA perlu menganalisis penyebab kegagalan."
                ),
                "perlu_penguatan": (
                    "Penguatan",
                    "Tingkat keberhasilan masih rendah."
                ),
                "perlu_pengujian": (
                    "Pengujian",
                    "Bukti pengujian belum cukup."
                ),
                "belum_diuji": (
                    "Pengembangan",
                    "Kemampuan belum pernah diuji."
                )
            }

            action, reason = actions[status]

            discovered.append({
                "id": "improve_" + skill_id,
                "skill_id": skill_id,
                "name": action + " " + result.get("name", skill_id),
                "reason": reason,
                "source": "evaluasi_kemampuan",
                "status": status,
                "priority": self.priorities[status],
                "history": {
                    "success": result.get("successful", 0),
                    "failed": result.get("failed", 0),
                    "success_rate": result.get("success_rate", 0),
                    "success_streak": result.get("success_streak", 0)
                }
            })

        discovered.sort(
            key=lambda item: (item["priority"], item["name"])
        )

        self.save_json(self.proposal_file, discovered)

        candidates = self.analyze_new_capabilities(
            report,
            plan
        )

        previous = self.read_json(self.candidate_file, [])

        if not isinstance(previous, list):
            previous = []

        known_ids = {
            item.get("id")
            for item in previous
            if isinstance(item, dict)
        }

        for candidate in candidates:

            if candidate["id"] not in known_ids:
                previous.append(candidate)
                known_ids.add(candidate["id"])

        self.save_json(self.candidate_file, previous)

        return discovered, candidates

    def report(self):

        proposals, candidates = self.discover()

        print("\nZORA AUTONOMOUS SKILL DISCOVERY")
        print("--------------------------------")

        print("\nKEBUTUHAN KEMAMPUAN SAAT INI")

        for item in proposals:

            print("\nKemampuan:", item["name"])
            print("ID:", item["skill_id"])
            print("Status:", item["status"])
            print("Alasan:", item["reason"])
            print("Prioritas:", item["priority"])
            print("Riwayat:", item["history"])

        print("\nPENEMUAN KEMAMPUAN BARU")

        if not candidates:
            print("Belum ada usulan baru yang lolos validasi AI.")

        for item in candidates:

            print("\nCalon kemampuan:", item["name"])
            print("ID:", item["id"])
            print("Alasan:", item["reason"])
            print("Bukti:", item["evidence"])
            print("Ide pengujian:", item["test_idea"])
            print("Status:", item["status"])

        print("\nTotal kebutuhan pengembangan:", len(proposals))
        print("Total usulan baru pada analisis ini:", len(candidates))
        print("File kandidat:", self.candidate_file)

        return proposals, candidates


def main():

    from brain.zora import Zora
    from developer.self_development import ZoraSelfDevelopment
    from developer.development_planner import ZoraDevelopmentPlanner

    zora = Zora()

    try:

        developer = ZoraSelfDevelopment(zora)
        planner = ZoraDevelopmentPlanner(developer)

        discovery = ZoraSkillDiscovery(planner)
        discovery.report()

    finally:
        zora.memory.close()


if __name__ == "__main__":
    main()
