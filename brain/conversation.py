from datetime import datetime
import threading


class ZoraConversation:

    MAX_HISTORY_LIMIT = 100
    MAX_MESSAGE_LENGTH = 10000

    def __init__(self, max_history=10):
        try:
            max_history = int(max_history)
        except (TypeError, ValueError):
            max_history = 10

        self.max_history = max(
            1,
            min(max_history, self.MAX_HISTORY_LIMIT)
        )

        self.history = []
        self.started_at = datetime.now().astimezone().isoformat()
        self.lock = threading.RLock()

    def add_message(self, role, content):
        if role not in ("user", "zora"):
            raise ValueError("Role percakapan tidak valid.")

        if not isinstance(content, str):
            raise TypeError("Isi pesan harus berupa teks.")

        if len(content) > self.MAX_MESSAGE_LENGTH:
            raise ValueError("Isi pesan melebihi batas 10.000 karakter.")

        message = {
            "role": role,
            "content": content,
            "time": datetime.now().astimezone().isoformat()
        }

        with self.lock:
            self.history.append(message)

            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

    def remember_user(self, message):
        self.add_message("user", message)

    def remember_zora(self, message):
        self.add_message("zora", message)

    def get_history(self):
        with self.lock:
            return [message.copy() for message in self.history]

    def get_context(self):
        with self.lock:
            return "\n".join(
                f"{message['role'].upper()}: {message['content']}"
                for message in self.history
            )

    def clear(self):
        with self.lock:
            self.history.clear()
