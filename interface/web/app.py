from collections import OrderedDict
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
import hashlib
import hmac
import json
import secrets
import threading
import time

import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import (
    Flask, render_template_string, request,
    jsonify, session, redirect, url_for
)

from brain.zora import Zora


# =========================================================
# KONFIGURASI KEAMANAN
# =========================================================

ROOT_DIR = Path(__file__).resolve().parents[2]
AUTH_FILE = ROOT_DIR / "data" / "web_auth.json"

try:
    AUTH_CONFIG = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    SECRET_KEY = AUTH_CONFIG["secret_key"]
    PASSWORD_HASH = AUTH_CONFIG["password_hash"]
except Exception as exc:
    raise RuntimeError(
        "Konfigurasi login ZORA tidak tersedia atau tidak valid."
    ) from exc

if not isinstance(SECRET_KEY, str) or len(SECRET_KEY) < 32:
    raise RuntimeError("Secret key ZORA tidak valid.")

if not isinstance(PASSWORD_HASH, str):
    raise RuntimeError("Password hash ZORA tidak valid.")


app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # Aktifkan True setelah HTTPS tersedia.
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=64 * 1024
)

MAX_SESSIONS = 50
MAX_MESSAGE_LENGTH = 10000

MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 900

_sessions = OrderedDict()
_sessions_lock = threading.RLock()

_login_attempts = {}
_login_lock = threading.RLock()


# =========================================================
# AUTENTIKASI PASSWORD
# =========================================================

def verify_password(password):
    try:
        algorithm, iterations, salt_hex, expected = PASSWORD_HASH.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations)

        if not 100000 <= iterations <= 2000000:
            return False

        salt = bytes.fromhex(salt_hex)

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations
        ).hex()

        return hmac.compare_digest(actual, expected)

    except (ValueError, TypeError, AttributeError):
        return False


def is_authenticated():
    return session.get("authenticated") is True


def get_csrf_token():
    token = session.get("csrf_token")

    if not isinstance(token, str):
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token

    return token


def valid_csrf_token(token):
    expected = session.get("csrf_token")

    return (
        isinstance(token, str)
        and isinstance(expected, str)
        and hmac.compare_digest(token, expected)
    )


def login_attempt_status():
    address = request.remote_addr or "unknown"
    now = time.time()

    with _login_lock:
        attempts = [
            timestamp
            for timestamp in _login_attempts.get(address, [])
            if now - timestamp < LOGIN_WINDOW_SECONDS
        ]

        _login_attempts[address] = attempts

        if len(attempts) >= MAX_LOGIN_ATTEMPTS:
            remaining = int(
                LOGIN_WINDOW_SECONDS - (now - attempts[0])
            )
            return False, max(1, remaining)

        return True, 0


def record_failed_login():
    address = request.remote_addr or "unknown"
    now = time.time()

    with _login_lock:
        attempts = _login_attempts.get(address, [])
        attempts = [
            timestamp
            for timestamp in attempts
            if now - timestamp < LOGIN_WINDOW_SECONDS
        ]
        attempts.append(now)
        _login_attempts[address] = attempts


def clear_login_attempts():
    address = request.remote_addr or "unknown"

    with _login_lock:
        _login_attempts.pop(address, None)


# =========================================================
# HALAMAN LOGIN
# =========================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login ZORA</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #eef2f7;
            font-family: Arial, sans-serif;
        }
        .login-box {
            width: calc(100% - 40px);
            max-width: 360px;
            padding: 28px;
            background: white;
            border-radius: 16px;
            box-sizing: border-box;
            box-shadow: 0 5px 25px rgba(0,0,0,.08);
        }
        h2 {
            text-align: center;
            color: #142d4e;
        }
        input {
            width: 100%;
            padding: 14px;
            margin: 12px 0;
            box-sizing: border-box;
            border: 1px solid #ccc;
            border-radius: 9px;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 14px;
            border: 0;
            border-radius: 9px;
            background: #142d4e;
            color: white;
            font-size: 16px;
        }
        .error {
            color: #b42318;
            text-align: center;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>LOGIN ZORA</h2>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST" action="/login">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <input
                type="password"
                name="password"
                placeholder="Masukkan password"
                autocomplete="current-password"
                required
                autofocus
            >
            <button type="submit">Masuk</button>
        </form>
    </div>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():

    if is_authenticated():
        return redirect(url_for("home"))

    error = None
    csrf_token = get_csrf_token()

    if request.method == "POST":

        if not valid_csrf_token(request.form.get("csrf_token")):
            return "Permintaan tidak valid.", 400

        allowed, remaining = login_attempt_status()

        if not allowed:
            response = app.make_response(
                "Terlalu banyak percobaan login. Silakan coba lagi nanti."
            )
            response.status_code = 429
            response.headers["Retry-After"] = str(remaining)
            return response

        password = request.form.get("password", "")

        if not isinstance(password, str) or len(password) > 1024:
            record_failed_login()
            error = "Password salah."

        elif verify_password(password):
            clear_login_attempts()

            session.clear()
            session.permanent = True
            session["authenticated"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)

            return redirect(url_for("home"))

        else:
            record_failed_login()
            error = "Password salah."

    return render_template_string(
        LOGIN_HTML,
        error=error,
        csrf_token=csrf_token
    )


@app.route("/logout", methods=["POST"])
def logout():

    if not is_authenticated():
        return redirect(url_for("login"))

    if not valid_csrf_token(request.form.get("csrf_token")):
        return "Permintaan tidak valid.", 400

    session.clear()
    return redirect(url_for("login"))


# =========================================================
# HALAMAN CHAT
# =========================================================

HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token }}">
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
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        #chat {
            height: calc(100vh - 170px);
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
        .logout {
            background: #b42318;
            padding: 8px 12px;
            font-size: 13px;
        }
    </style>
</head>
<body>

<header>
    <span>ZORA</span>
    <form method="POST" action="/logout">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <button class="logout" type="submit">Keluar</button>
    </form>
</header>

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
                "Content-Type": "application/json",
                "X-CSRF-Token":
                    document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({message: message})
        });

        const data = await response.json();

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        addMessage(
            data.reply || data.error || "Tidak ada jawaban.",
            "zora"
        );

    } catch (error) {
        addMessage("Koneksi ke server ZORA terputus.", "zora");

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


# =========================================================
# MANAJEMEN SESI ZORA
# =========================================================

def _close_zora(zora):
    try:
        zora.memory.close()
    except Exception:
        app.logger.exception("Gagal menutup memori sesi ZORA")


@contextmanager
def get_zora_for_session():

    session_id = session.get("zora_session_id")

    if not session_id:
        session_id = secrets.token_urlsafe(32)
        session["zora_session_id"] = session_id

    record = None
    acquired = False

    try:
        with _sessions_lock:

            record = _sessions.get(session_id)

            if record is None:
                record = {
                    "zora": Zora(),
                    "lock": threading.RLock()
                }
                _sessions[session_id] = record
            else:
                _sessions.move_to_end(session_id)

            record["lock"].acquire()
            acquired = True

            while len(_sessions) > max(1, MAX_SESSIONS):

                old_id, old_record = _sessions.popitem(last=False)

                if old_id != session_id:
                    with old_record["lock"]:
                        _close_zora(old_record["zora"])

        yield record

    finally:
        if acquired:
            record["lock"].release()


# =========================================================
# ROUTE UTAMA
# =========================================================

@app.route("/")
def home():

    if not is_authenticated():
        return redirect(url_for("login"))

    return render_template_string(
        HTML,
        csrf_token=get_csrf_token()
    )


@app.route("/chat", methods=["POST"])
def chat():

    if not is_authenticated():
        return jsonify({"error": "Silakan login terlebih dahulu."}), 401

    if not valid_csrf_token(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Token keamanan tidak valid."}), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Format pesan tidak valid."}), 400

    message = data.get("message", "")

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Pesan tidak boleh kosong."}), 400

    message = message.strip()

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "error": "Pesan terlalu panjang. Maksimal 10.000 karakter."
        }), 413

    try:
        with get_zora_for_session() as record:
            jawaban = record["zora"].process_message(message)

        return jsonify({"reply": jawaban})

    except Exception:
        app.logger.exception(
            "Terjadi kesalahan saat memproses pesan ZORA"
        )

        return jsonify({
            "error": "Maaf, ZORA mengalami kesalahan saat memproses pesan."
        }), 500


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


if __name__ == "__main__":
    app.run(
        host="100.122.21.116",
        port=5000,
        debug=False,
        threaded=True
    )
