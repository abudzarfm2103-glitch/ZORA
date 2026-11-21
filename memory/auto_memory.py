
from memory.memory_filter import MemoryFilter


class AutoMemory:

    def __init__(self, memory):
        self.memory = memory
        self.filter = MemoryFilter()

    def analyze(self, message):

        result = self.filter.analyze(message)

        if not result:
            return False

        berhasil = self.memory.save(
            result["content"],
            result["category"],
            result["status"]
        )

        if berhasil:
            return {
                "category": result["category"],
                "status": result["status"],
                "content": result["content"]
            }

        return False
