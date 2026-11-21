
from datetime import datetime


class ZoraConversation:

    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history
        self.started_at = datetime.now().isoformat()

    def add_message(self, role, content):
        message = {
            "role": role,
            "content": content,
            "time": datetime.now().isoformat()
        }

        self.history.append(message)

        if len(self.history) > self.max_history:
            self.history.pop(0)

    def remember_user(self, message):
        self.add_message("user", message)

    def remember_zora(self, message):
        self.add_message("zora", message)

    def get_history(self):
        return self.history.copy()

    def get_context(self):
        context = []

        for message in self.history:
            context.append(
                f"{message['role'].upper()}: {message['content']}"
            )

        return "\n".join(context)

    def clear(self):
        self.history.clear()
