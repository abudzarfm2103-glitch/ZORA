from collections import OrderedDict
import secrets
import threading

from flask import (
    Flask,
    render_template_string,
    request,
    jsonify,
    session
)

from brain.zora import Zora


app = Flask(__name__)

# Kunci acak berlaku selama proses server berjalan.
# Sesi browser akan dibuat ulang setelah server dimulai ulang.
app.secret_key = secrets.token_hex(32)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    MAX_CONTENT_LENGTH=64 * 1024
)

MAX_SESSIONS = 50
MAX_MESSAGE_LENGTH = 10000

_sessions = OrderedDict()
_sessions_lock = threading.RLock()


HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZORA Assistant</title>

    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #eef2f7;
        }

        header {
            background: #142d4e;
            color: white;
            padding: 18px;
            text-align: center;
            font-size: 22px;
            font-weight: bold;
        }

        #chat {
            height: calc(100vh - 160px);
            overflow-y: auto;
            padding: 15px;
        }

        .message {
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 12px;
            max-width: 85%;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }

        .user {
            background: #d4e7ff;
            margin-left: auto;
        }

        .zora {
            background: white;
            margin-right: auto;
        }

        footer {
            display: flex;
            padding: 12px;
            background: white;
            gap: 8px;
        }

        input {
            flex: 1;
            padding: 13px;
            border: 1px solid #ccc;
            border-radius: 10px;
            font-size: 16px;
            min-width: 0;
        }

        button {
            background: #142d4e;
            color: white;
            border: none;
            padding: 12px 18px;
            border-radius: 10px;
            font-size: 16px;
        }

        button:disabled {
            opacity: 0.5;
        }
    </style>
</head>

<body>

<header>ZORA</header>

<div id="chat">
    <div class="message zora">
        Halo, saya ZORA. Ada yang bisa saya bantu?
    </div>
</div>

<footer>
    <input id="message" placeholder="Tulis pesan..." autocomplete="off">
    <button id="send" onclick="sendMessage()">Kirim</button>
</footer>

<script>
async function sendMessage() {

    const input = document.getElementById("message");
    const button = document.getElementById("send");
    const message = input.value.trim();

    if (!message) return;

    addMessage(message, "user");
    input.value = "";
    button.disabled = true;

    try {

        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({message: message})
        });

        const data = await response.json();

        addMessage(
            data.reply || data.error || "Tidak ada jawaban.",
            "zora"
        );

    } catch (error) {

        addMessage(
            "Koneksi ke server ZORA terputus.",
            "zora"
        );

    } finally {

        button.disabled = false;
        input.focus();
    }
}

function addMessage(text, sender) {

    const chat = document.getElementById("chat");
    const div = document.createElement("div");

    div.className = "message " + sender;
    div.textContent = text;

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

document.getElementById("message").addEventListener(
    "keydown",
    function(event) {
        if (event.key === "Enter") sendMessage();
    }
);
</script>

</body>
</html>
"""


def _close_zora(zora):
    try:
        zora.memory.close()
    except Exception:
        app.logger.exception("Gagal menutup memori sesi ZORA")


def get_zora_for_session():
    session_id = session.get("zora_session_id")

    if not session_id:
        session_id = secrets.token_urlsafe(32)
        session["zora_session_id"] = session_id

    with _sessions_lock:

        record = _sessions.get(session_id)

        if record is not None:
            _sessions.move_to_end(session_id)
            return record

        zora = Zora()

        record = {
            "zora": zora,
            "lock": threading.RLock()
        }

        _sessions[session_id] = record

        while len(_sessions) > MAX_SESSIONS:
            old_id, old_record = _sessions.popitem(last=False)

            if old_id != session_id:
                with old_record["lock"]:
                    _close_zora(old_record["zora"])

        return record


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    if not isinstance(message, str) or not message.strip():
        return jsonify({
            "error": "Pesan tidak boleh kosong."
        }), 400

    message = message.strip()

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "error": "Pesan terlalu panjang. Maksimal 10.000 karakter."
        }), 413

    try:
        record = get_zora_for_session()

        # Satu sesi hanya memproses satu pesan pada satu waktu.
        with record["lock"]:
            jawaban = record["zora"].process_message(message)

        return jsonify({
            "reply": jawaban
        })

    except Exception:
        app.logger.exception(
            "Terjadi kesalahan saat memproses pesan ZORA"
        )

        return jsonify({
            "error": "Maaf, ZORA mengalami kesalahan saat memproses pesan."
        }), 500


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )
