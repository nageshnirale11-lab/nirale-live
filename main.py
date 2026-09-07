import os
import re
import json
import time
import base64
import hashlib
import secrets
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import google.generativeai as genai


# =========================================================
# CONFIG
# =========================================================

APP_NAME = "Nirale AI"
DB_FILE = "nirale.db"

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "").strip().lower()

if API_KEY:
    genai.configure(api_key=API_KEY)


app = FastAPI(title=APP_NAME)


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            plan TEXT DEFAULT 'Free',
            created_at TEXT NOT NULL,
            last_active TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'New Chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER,
            message TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# PASSWORD SECURITY
# =========================================================

def hash_password(password: str, salt: Optional[str] = None):
    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt),
        n=16384,
        r=8,
        p=1,
        dklen=64
    )

    return hashed.hex(), salt


def verify_password(password: str, password_hash: str, salt: str):
    hashed, _ = hash_password(password, salt)
    return secrets.compare_digest(hashed, password_hash)


# =========================================================
# SESSION
# =========================================================

def current_user(request: Request):
    token = request.cookies.get("nirale_session")

    if not token:
        return None

    conn = db()

    row = conn.execute("""
        SELECT users.*
        FROM users
        JOIN sessions ON sessions.user_id = users.id
        WHERE sessions.token = ?
    """, (token,)).fetchone()

    conn.close()

    return row


def update_last_active(user_id: int):
    conn = db()
    conn.execute(
        "UPDATE users SET last_active=? WHERE id=?",
        (datetime.now().isoformat(), user_id)
    )
    conn.commit()
    conn.close()


# =========================================================
# MODELS
# =========================================================

class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[int] = None
    image_data: Optional[str] = None


class UpgradeRequest(BaseModel):
    plan: str


# =========================================================
# CREATOR
# =========================================================

def is_creator_question(text: str):
    t = text.lower().strip()

    words = [
        "who created you",
        "who made you",
        "who is your creator",
        "who developed you",
        "who built you",
        "who owns you",
        "who is owner",
        "ಯಾರು ನಿನ್ನನ್ನು ರಚಿಸಿದ್ದಾರೆ",
        "ನಿನ್ನನ್ನು ಯಾರು ರಚಿಸಿದ್ದಾರೆ",
        "ನಿನ್ನ creator ಯಾರು",
        "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
        "ನಿಮ್ಮ creator ಯಾರು"
    ]

    return any(x in t for x in words)


CREATOR_REPLY = "ನನ್ನನ್ನು Nagesh Nirale ಅವರು ರಚಿಸಿದ್ದಾರೆ."


# =========================================================
# GEMINI
# =========================================================

SYSTEM_PROMPT = """
You are Nirale AI.

You are a helpful multilingual AI assistant.

Answer naturally in the language used by the user.
You can understand and answer in:
Kannada, English, Hindi, Telugu, Tamil, Malayalam,
Marathi, Bengali, Gujarati, Punjabi, Urdu and other
commonly supported languages.

Important:
- Give accurate and useful answers.
- If the user asks for code, provide working code.
- Explain code clearly when useful.
- Preserve the user's requested programming language.
- Use Markdown.
- Use fenced code blocks for code.
- Do not claim that an action was completed when it was not.
- Never reveal passwords, API keys, session tokens or secrets.
"""


def generate_ai_reply(message: str, image_data: Optional[str] = None):

    if is_creator_question(message):
        return CREATOR_REPLY

    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY or GEMINI_API_KEY is not configured."
        )

    model = genai.GenerativeModel(
        MODEL_NAME,
        system_instruction=SYSTEM_PROMPT
    )

    contents = [message]

    if image_data:
        try:
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]

            raw = base64.b64decode(image_data)

            contents.append({
                "mime_type": "image/jpeg",
                "data": raw
            })

        except Exception:
            pass

    response = model.generate_content(contents)

    if not response or not getattr(response, "text", None):
        return "Sorry, nanage answer generate madakke agalilla."

    return response.text


# =========================================================
# AUTH API
# =========================================================

@app.post("/api/signup")
async def signup(data: SignupRequest):

    email = data.email.strip().lower()
    password = data.password

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(400, "Valid email address enter madi.")

    if len(password) < 6:
        raise HTTPException(
            400,
            "Password ಕನಿಷ್ಠ 6 characters ಇರಬೇಕು."
        )

    password_hash, salt = hash_password(password)

    conn = db()

    try:
        cur = conn.execute("""
            INSERT INTO users
            (email, password_hash, salt, plan, created_at, last_active)
            VALUES (?, ?, ?, 'Free', ?, ?)
        """, (
            email,
            password_hash,
            salt,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        user_id = cur.lastrowid
        token = secrets.token_urlsafe(48)

        conn.execute("""
            INSERT INTO sessions(token, user_id, created_at)
            VALUES (?, ?, ?)
        """, (
            token,
            user_id,
            datetime.now().isoformat()
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            400,
            "ಈ email ಈಗಾಗಲೇ registered ಆಗಿದೆ."
        )

    conn.close()

    response = {
        "ok": True,
        "message": "Account created successfully.",
        "email": email
    }

    from fastapi.responses import JSONResponse

    r = JSONResponse(response)

    r.set_cookie(
        "nirale_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30
    )

    return r


@app.post("/api/login")
async def login(data: LoginRequest):

    email = data.email.strip().lower()

    conn = db()

    user = conn.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(
            401,
            "Email ಅಥವಾ password ತಪ್ಪಾಗಿದೆ."
        )

    if not verify_password(
        data.password,
        user["password_hash"],
        user["salt"]
    ):
        raise HTTPException(
            401,
            "Email ಅಥವಾ password ತಪ್ಪಾಗಿದೆ."
        )

    token = secrets.token_urlsafe(48)

    conn = db()

    conn.execute("""
        INSERT INTO sessions(token, user_id, created_at)
        VALUES (?, ?, ?)
    """, (
        token,
        user["id"],
        datetime.now().isoformat()
    ))

    conn.execute(
        "UPDATE users SET last_active=? WHERE id=?",
        (datetime.now().isoformat(), user["id"])
    )

    conn.commit()
    conn.close()

    from fastapi.responses import JSONResponse

    r = JSONResponse({
        "ok": True,
        "email": email,
        "plan": user["plan"]
    })

    r.set_cookie(
        "nirale_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30
    )

    return r


@app.post("/api/logout")
async def logout(request: Request):

    token = request.cookies.get("nirale_session")

    if token:
        conn = db()
        conn.execute(
            "DELETE FROM sessions WHERE token=?",
            (token,)
        )
        conn.commit()
        conn.close()

    from fastapi.responses import JSONResponse

    r = JSONResponse({"ok": True})
    r.delete_cookie("nirale_session")

    return r


@app.get("/api/me")
async def me(request: Request):

    user = current_user(request)

    if not user:
        return {
            "logged_in": False
        }

    update_last_active(user["id"])

    return {
        "logged_in": True,
        "id": user["id"],
        "email": user["email"],
        "plan": user["plan"],
        "created_at": user["created_at"],
        "last_active": user["last_active"]
    }


# =========================================================
# CHAT API
# =========================================================

@app.post("/api/chat")
async def chat(request: Request, data: ChatRequest):

    user = current_user(request)

    if not user:
        raise HTTPException(
            401,
            "Login madi."
        )

    message = data.message.strip()

    if not message:
        raise HTTPException(
            400,
            "Message empty ide."
        )

    update_last_active(user["id"])

    conn = db()

    chat_id = data.chat_id

    if chat_id:

        chat = conn.execute("""
            SELECT *
            FROM chats
            WHERE id=? AND user_id=?
        """, (
            chat_id,
            user["id"]
        )).fetchone()

        if not chat:
            conn.close()
            raise HTTPException(
                404,
                "Chat not found."
            )

    else:

        title = message[:60]

        cur = conn.execute("""
            INSERT INTO chats
            (user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (
            user["id"],
            title,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        chat_id = cur.lastrowid

    conn.execute("""
        INSERT INTO messages
        (chat_id, role, content, created_at)
        VALUES (?, 'user', ?, ?)
    """, (
        chat_id,
        message,
        datetime.now().isoformat()
    ))

    conn.execute("""
        INSERT INTO usage
        (user_id, chat_id, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        user["id"],
        chat_id,
        message,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    try:
        reply = generate_ai_reply(
            message,
            data.image_data
        )

    except Exception as e:
        raise HTTPException(
            500,
            f"Gemini error: {str(e)}"
        )

    conn = db()

    conn.execute("""
        INSERT INTO messages
        (chat_id, role, content, created_at)
        VALUES (?, 'assistant', ?, ?)
    """, (
        chat_id,
        reply,
        datetime.now().isoformat()
    ))

    conn.execute("""
        UPDATE chats
        SET updated_at=?
        WHERE id=?
    """, (
        datetime.now().isoformat(),
        chat_id
    ))

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "chat_id": chat_id,
        "reply": reply
    }


# =========================================================
# CHAT HISTORY
# =========================================================

@app.get("/api/chats")
async def get_chats(request: Request):

    user = current_user(request)

    if not user:
        raise HTTPException(401, "Login madi.")

    conn = db()

    rows = conn.execute("""
        SELECT id, title, created_at, updated_at
        FROM chats
        WHERE user_id=?
        ORDER BY updated_at DESC
    """, (
        user["id"],
    )).fetchall()

    conn.close()

    return {
        "chats": [dict(x) for x in rows]
    }


@app.get("/api/chats/{chat_id}")
async def get_chat(
    chat_id: int,
    request: Request
):

    user = current_user(request)

    if not user:
        raise HTTPException(401, "Login madi.")

    conn = db()

    chat = conn.execute("""
        SELECT *
        FROM chats
        WHERE id=? AND user_id=?
    """, (
        chat_id,
        user["id"]
    )).fetchone()

    if not chat:
        conn.close()
        raise HTTPException(404, "Chat not found.")

    messages = conn.execute("""
        SELECT role, content, created_at
        FROM messages
        WHERE chat_id=?
        ORDER BY id ASC
    """, (
        chat_id,
    )).fetchall()

    conn.close()

    return {
        "chat": dict(chat),
        "messages": [dict(x) for x in messages]
    }


@app.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: int,
    request: Request
):

    user = current_user(request)

    if not user:
        raise HTTPException(401, "Login madi.")

    conn = db()

    conn.execute("""
        DELETE FROM messages
        WHERE chat_id=?
    """, (chat_id,))

    conn.execute("""
        DELETE FROM chats
        WHERE id=? AND user_id=?
    """, (
        chat_id,
        user["id"]
    ))

    conn.commit()
    conn.close()

    return {
        "ok": True
    }


# =========================================================
# ACCOUNT / PLANS
# =========================================================

@app.get("/api/plans")
async def plans():

    return {
        "plans": [
            {
                "name": "Free",
                "price": 0,
                "description": "Basic AI access"
            },
            {
                "name": "Plus",
                "price": 499,
                "description": "More AI usage"
            },
            {
                "name": "Pro",
                "price": 999,
                "description": "Higher usage and advanced access"
            }
        ]
    }


@app.post("/api/upgrade")
async def upgrade(
    request: Request,
    data: UpgradeRequest
):

    user = current_user(request)

    if not user:
        raise HTTPException(401, "Login madi.")

    allowed = ["Free", "Plus", "Pro"]

    if data.plan not in allowed:
        raise HTTPException(
            400,
            "Invalid plan."
        )

    if data.plan == "Free":

        conn = db()

        conn.execute("""
            UPDATE users
            SET plan='Free'
            WHERE id=?
        """, (
            user["id"],
        ))

        conn.commit()
        conn.close()

        return {
            "ok": True,
            "plan": "Free"
        }

    return {
        "ok": False,
        "payment_required": True,
        "message": "Payment gateway connect madida mele paid plan activate agutte.",
        "plan": data.plan
    }


# =========================================================
# ADMIN
# =========================================================

def require_admin(request: Request):

    user = current_user(request)

    if not user:
        raise HTTPException(401, "Login madi.")

    if not OWNER_EMAIL:
        raise HTTPException(
            403,
            "OWNER_EMAIL Render environment variable configure madi."
        )

    if user["email"].lower() != OWNER_EMAIL:
        raise HTTPException(
            403,
            "Admin access denied."
        )

    return user


@app.get("/api/admin/users")
async def admin_users(request: Request):

    require_admin(request)

    conn = db()

    users = conn.execute("""
        SELECT
            id,
            email,
            plan,
            created_at,
            last_active
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return {
        "users": [dict(x) for x in users]
    }


@app.get("/api/admin/activity")
async def admin_activity(request: Request):

    require_admin(request)

    conn = db()

    rows = conn.execute("""
        SELECT
            usage.id,
            users.email,
            usage.message,
            usage.created_at
        FROM usage
        JOIN users
        ON users.id = usage.user_id
        ORDER BY usage.id DESC
        LIMIT 200
    """).fetchall()

    conn.close()

    return {
        "activity": [dict(x) for x in rows]
    }


@app.get("/api/admin/stats")
async def admin_stats(request: Request):

    require_admin(request)

    conn = db()

    users = conn.execute(
        "SELECT COUNT(*) AS c FROM users"
    ).fetchone()["c"]

    messages = conn.execute(
        "SELECT COUNT(*) AS c FROM usage"
    ).fetchone()["c"]

    chats = conn.execute(
        "SELECT COUNT(*) AS c FROM chats"
    ).fetchone()["c"]

    conn.close()

    return {
        "users": users,
        "messages": messages,
        "chats": chats
    }


# =========================================================
# FRONTEND
# =========================================================

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width,initial-scale=1.0"
>

<title>Nirale AI</title>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<link
rel="stylesheet"
href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css"
>

<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family:
        Arial,
        Helvetica,
        sans-serif;
    background: #ffffff;
    color: #202124;
}

button,
input {
    font: inherit;
}

.hidden {
    display: none !important;
}


/* =====================================================
   AUTH
===================================================== */

#authScreen {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
        linear-gradient(
            135deg,
            #f8f9fa,
            #ffffff
        );
    padding: 20px;
}

.auth-card {
    width: 100%;
    max-width: 420px;
    padding: 34px;
    border: 1px solid #e5e7eb;
    border-radius: 22px;
    background: white;
    box-shadow:
        0 15px 45px rgba(0,0,0,.08);
}

.logo {
    font-size: 27px;
    font-weight: 700;
    margin-bottom: 8px;
}

.auth-subtitle {
    color: #6b7280;
    margin-bottom: 28px;
}

.auth-card input {
    width: 100%;
    padding: 14px;
    border: 1px solid #d1d5db;
    border-radius: 12px;
    margin-bottom: 12px;
    outline: none;
}

.auth-card input:focus {
    border-color: #777;
}

.primary-btn {
    width: 100%;
    border: 0;
    border-radius: 12px;
    padding: 14px;
    cursor: pointer;
    background: #111827;
    color: white;
    font-weight: 600;
}

.auth-switch {
    margin-top: 18px;
    text-align: center;
    color: #666;
}

.auth-switch button {
    border: 0;
    background: none;
    cursor: pointer;
    font-weight: 600;
}


/* =====================================================
   APP
===================================================== */

#app {
    height: 100vh;
    display: flex;
    overflow: hidden;
}

.sidebar {
    width: 270px;
    border-right: 1px solid #e5e7eb;
    background: #fafafa;
    display: flex;
    flex-direction: column;
    transition: .25s;
}

.sidebar-top {
    padding: 15px;
}

.new-chat {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 12px;
    background: white;
    cursor: pointer;
    text-align: left;
}

.side-item {
    margin-top: 8px;
    padding: 12px;
    border-radius: 10px;
    cursor: pointer;
}

.side-item:hover {
    background: #eeeeee;
}

.recents-title {
    padding: 18px 15px 8px;
    font-size: 12px;
    color: #777;
    text-transform: uppercase;
}

.recents {
    flex: 1;
    overflow-y: auto;
    padding: 0 10px;
}

.recent {
    padding: 10px;
    border-radius: 9px;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.recent:hover {
    background: #eeeeee;
}

.account-box {
    padding: 14px;
    border-top: 1px solid #ddd;
}

.account-email {
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
}

.account-plan {
    font-size: 12px;
    color: #777;
    margin-top: 3px;
}


/* =====================================================
   MAIN
===================================================== */

.main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.header {
    height: 60px;
    border-bottom: 1px solid #eee;
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 12px;
}

.menu-btn {
    display: none;
    border: 0;
    background: none;
    font-size: 23px;
    cursor: pointer;
}

.header-logo {
    font-size: 19px;
    font-weight: 700;
}

.header-spacer {
    flex: 1;
}

.upgrade-btn {
    border: 0;
    border-radius: 10px;
    padding: 9px 14px;
    cursor: pointer;
    background: #111827;
    color: white;
}


/* =====================================================
   CHAT
===================================================== */

.chatbox {
    flex: 1;
    overflow-y: auto;
    padding: 25px;
}

.welcome {
    max-width: 800px;
    margin: 100px auto 0;
    text-align: center;
}

.welcome h1 {
    font-size: 34px;
}

.welcome p {
    color: #777;
}

.message {
    max-width: 850px;
    margin: 0 auto 22px;
    line-height: 1.65;
}

.message.user {
    background: #f3f4f6;
    border-radius: 16px;
    padding: 13px 17px;
}

.message.assistant {
    padding: 5px 0;
}

.message pre {
    position: relative;
    overflow-x: auto;
    background: #f6f8fa;
    border-radius: 12px;
    padding: 45px 15px 15px;
}

.message code {
    font-family: Consolas, monospace;
}

.code-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    gap: 6px;
}

.code-actions button {
    border: 1px solid #ddd;
    border-radius: 7px;
    background: white;
    padding: 5px 8px;
    cursor: pointer;
}

.thinking {
    max-width: 850px;
    margin: 0 auto 20px;
    color: #777;
}


/* =====================================================
   INPUT
===================================================== */

.footer {
    padding: 12px 18px 18px;
}

.input-wrap {
    max-width: 850px;
    margin: auto;
    border: 1px solid #d9d9d9;
    border-radius: 18px;
    display: flex;
    align-items: flex-end;
    padding: 8px;
    box-shadow: 0 3px 15px rgba(0,0,0,.05);
}

.input-wrap textarea {
    flex: 1;
    resize: none;
    border: 0;
    outline: 0;
    padding: 10px;
    min-height: 42px;
    max-height: 150px;
}

.icon-btn {
    width: 40px;
    height: 40px;
    border: 0;
    background: transparent;
    border-radius: 10px;
    cursor: pointer;
    font-size: 19px;
}

.icon-btn:hover {
    background: #eee;
}

.send-btn {
    background: #111827;
    color: white;
}

.listening {
    background: #ef4444 !important;
    color: white;
}


/* =====================================================
   PLUS MENU
===================================================== */

.plus-menu {
    position: absolute;
    bottom: 80px;
    left: 18px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 14px;
    padding: 8px;
    box-shadow: 0 12px 35px rgba(0,0,0,.15);
    width: 220px;
    z-index: 50;
}

.plus-menu button {
    width: 100%;
    text-align: left;
    border: 0;
    background: white;
    padding: 11px;
    border-radius: 9px;
    cursor: pointer;
}

.plus-menu button:hover {
    background: #f1f1f1;
}


/* =====================================================
   MODAL
===================================================== */

.modal {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    padding: 20px;
}

.modal-card {
    width: 100%;
    max-width: 500px;
    background: white;
    border-radius: 18px;
    padding: 25px;
}

.modal-close {
    float: right;
    border: 0;
    background: none;
    font-size: 22px;
    cursor: pointer;
}

.plan {
    border: 1px solid #ddd;
    border-radius: 14px;
    padding: 16px;
    margin-top: 10px;
}

.plan button {
    float: right;
    border: 0;
    background: #111827;
    color: white;
    padding: 8px 12px;
    border-radius: 8px;
}


/* =====================================================
   MOBILE
===================================================== */

@media (max-width: 700px) {

    .sidebar {
        position: fixed;
        z-index: 90;
        left: -280px;
        top: 0;
        bottom: 0;
    }

    .sidebar.open {
        left: 0;
    }

    .menu-btn {
        display: block;
    }

    .chatbox {
        padding: 15px;
    }

    .welcome {
        margin-top: 70px;
    }

    .welcome h1 {
        font-size: 27px;
    }

    .header {
        padding: 0 10px;
    }

    .upgrade-btn {
        padding: 8px 10px;
    }

    .footer {
        padding: 8px;
        padding-bottom: calc(8px + env(safe-area-inset-bottom));
    }

    .message {
        max-width: 100%;
    }
}

</style>

</head>

<body>


<!-- =====================================================
     AUTH SCREEN
===================================================== -->

<div id="authScreen">

    <div class="auth-card">

        <div class="logo">
            ✨ Nirale AI
        </div>

        <div class="auth-subtitle">
            Your intelligent AI assistant
        </div>

        <div id="loginForm">

            <input
                id="loginEmail"
                type="email"
                placeholder="Email"
            >

            <input
                id="loginPassword"
                type="password"
                placeholder="Password"
            >

            <button
                class="primary-btn"
                onclick="login()"
            >
                Login
            </button>

            <div class="auth-switch">
                Don't have an account?
                <button onclick="showSignup()">
                    Create account
                </button>
            </div>

        </div>


        <div id="signupForm" class="hidden">

            <input
                id="signupEmail"
                type="email"
                placeholder="Email"
            >

            <input
                id="signupPassword"
                type="password"
                placeholder="Password"
            >

            <button
                class="primary-btn"
                onclick="signup()"
            >
                Create account
            </button>

            <div class="auth-switch">
                Already have an account?
                <button onclick="showLogin()">
                    Login
                </button>
            </div>

        </div>

    </div>

</div>


<!-- =====================================================
     APP
===================================================== -->

<div id="app" class="hidden">


    <aside id="sidebar" class="sidebar">

        <div class="sidebar-top">

            <button
                class="new-chat"
                onclick="newChat()"
            >
                ＋ New Chat
            </button>

            <div
                class="side-item"
                onclick="openUpgrade()"
            >
                ⭐ Upgrade
            </div>

            <div
                class="side-item"
                onclick="openAccount()"
            >
                👤 Account
            </div>

            <div
                id="adminItem"
                class="side-item hidden"
                onclick="openAdmin()"
            >
                👑 Admin Dashboard
            </div>

        </div>


        <div class="recents-title">
            Recents
        </div>

        <div
            id="recents"
            class="recents"
        ></div>


        <div class="account-box">

            <div
                id="sideEmail"
                class="account-email"
            >
            </div>

            <div
                id="sidePlan"
                class="account-plan"
            >
            </div>

            <div
                class="side-item"
                onclick="logout()"
            >
                ↪ Logout
            </div>

        </div>

    </aside>


    <main class="main">


        <header class="header">

            <button
                class="menu-btn"
                onclick="toggleSidebar()"
            >
                ☰
            </button>

            <div class="header-logo">
                ✨ Nirale AI
            </div>

            <div class="header-spacer"></div>

            <button
                class="upgrade-btn"
                onclick="openUpgrade()"
            >
                ⭐ Upgrade
            </button>

        </header>


        <div
            id="chatbox"
            class="chatbox"
        >

            <div
                id="welcome"
                class="welcome"
            >

                <h1>
                    How can I help you?
                </h1>

                <p>
                    Ask Nirale AI anything.
                </p>

            </div>

        </div>


        <div class="footer">

            <div
                id="plusMenu"
                class="plus-menu hidden"
            >

                <button onclick="attachFile()">
                    📎 Attach files
                </button>

                <button onclick="openCamera()">
                    📷 Camera
                </button>

                <button onclick="openGallery()">
                    🖼️ Photos / Gallery
                </button>

                <button onclick="webSearch()">
                    🔎 Web search
                </button>

                <button onclick="createImage()">
                    🎨 Create image
                </button>

                <button onclick="openMap()">
                    🗺️ Map
                </button>

            </div>


            <div class="input-wrap">

                <button
                    class="icon-btn"
                    onclick="togglePlusMenu()"
                >
                    ＋
                </button>

                <textarea
                    id="messageInput"
                    placeholder="Message Nirale AI..."
                    rows="1"
                    onkeydown="handleKey(event)"
                ></textarea>

                <button
                    id="micBtn"
                    class="icon-btn"
                    onclick="startVoice()"
                >
                    🎤
                </button>

                <button
                    class="icon-btn send-btn"
                    onclick="sendMessage()"
                >
                    ➤
                </button>

            </div>

        </div>

    </main>

</div>


<input
    id="fileInput"
    type="file"
    hidden
    onchange="fileSelected(event)"
>

<input
    id="cameraInput"
    type="file"
    accept="image/*"
    capture="environment"
    hidden
    onchange="imageSelected(event)"
>

<input
    id="galleryInput"
    type="file"
    accept="image/*"
    hidden
    onchange="imageSelected(event)"
>


<!-- =====================================================
     ACCOUNT MODAL
===================================================== -->

<div
    id="accountModal"
    class="modal hidden"
>

    <div class="modal-card">

        <button
            class="modal-close"
            onclick="closeModals()"
        >
            ×
        </button>

        <h2>Account</h2>

        <p id="accountEmail"></p>
        <p id="accountPlan"></p>

    </div>

</div>


<!-- =====================================================
     UPGRADE MODAL
===================================================== -->

<div
    id="upgradeModal"
    class="modal hidden"
>

    <div class="modal-card">

        <button
            class="modal-close"
            onclick="closeModals()"
        >
            ×
        </button>

        <h2>Upgrade Nirale AI</h2>

        <div class="plan">

            <b>Free</b>

            <p>₹0</p>

            <button onclick="selectPlan('Free')">
                Select
            </button>

        </div>

        <div class="plan">

            <b>Plus</b>

            <p>₹499 / month</p>

            <button onclick="selectPlan('Plus')">
                Upgrade
            </button>

        </div>

        <div class="plan">

            <b>Pro</b>

            <p>₹999 / month</p>

            <button onclick="selectPlan('Pro')">
                Upgrade
            </button>

        </div>

    </div>

</div>


<!-- =====================================================
     ADMIN MODAL
===================================================== -->

<div
    id="adminModal"
    class="modal hidden"
>

    <div class="modal-card">

        <button
            class="modal-close"
            onclick="closeModals()"
        >
            ×
        </button>

        <h2>👑 Admin Dashboard</h2>

        <div id="adminStats"></div>

        <h3>Users</h3>

        <div
            id="adminUsers"
            style="max-height:250px;overflow:auto;"
        ></div>

        <h3>Recent Activity</h3>

        <div
            id="adminActivity"
            style="max-height:250px;overflow:auto;"
        ></div>

    </div>

</div>


<script>

/* =====================================================
   GLOBAL
===================================================== */

let currentChatId = null;
let selectedImage = null;


/* =====================================================
   AUTH UI
===================================================== */

function showSignup() {

    document
        .getElementById("loginForm")
        .classList
        .add("hidden");

    document
        .getElementById("signupForm")
        .classList
        .remove("hidden");
}


function showLogin() {

    document
        .getElementById("signupForm")
        .classList
        .add("hidden");

    document
        .getElementById("loginForm")
        .classList
        .remove("hidden");
}


/* =====================================================
   SIGNUP
===================================================== */

async function signup() {

    const email =
        document.getElementById("signupEmail").value.trim();

    const password =
        document.getElementById("signupPassword").value;

    if (!email || !password) {
        alert("Email ಮತ್ತು password enter madi.");
        return;
    }

    const res = await fetch(
        "/api/signup",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email,
                password
            })
        }
    );

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Signup failed.");
        return;
    }

    await loadApp();

}


/* =====================================================
   LOGIN
===================================================== */

async function login() {

    const email =
        document.getElementById("loginEmail").value.trim();

    const password =
        document.getElementById("loginPassword").value;

    if (!email || !password) {
        alert("Email ಮತ್ತು password enter madi.");
        return;
    }

    const res = await fetch(
        "/api/login",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email,
                password
            })
        }
    );

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Login failed.");
        return;
    }

    await loadApp();

}


/* =====================================================
   LOAD APP
===================================================== */

async function loadApp() {

    const res = await fetch("/api/me");

    const user = await res.json();

    if (!user.logged_in) {

        document
            .getElementById("authScreen")
            .classList
            .remove("hidden");

        document
            .getElementById("app")
            .classList
            .add("hidden");

        return;
    }

    document
        .getElementById("authScreen")
        .classList
        .add("hidden");

    document
        .getElementById("app")
        .classList
        .remove("hidden");

    document.getElementById("sideEmail").textContent =
        user.email;

    document.getElementById("sidePlan").textContent =
        user.plan + " plan";

    document.getElementById("accountEmail").textContent =
        "Email: " + user.email;

    document.getElementById("accountPlan").textContent =
        "Plan: " + user.plan;

    if (
        window.location.hostname &&
        user.email
    ) {

        /*
         Admin item is displayed only when
         server-side admin endpoint confirms access.
        */

        const test = await fetch(
            "/api/admin/stats"
        );

        if (test.ok) {

            document
                .getElementById("adminItem")
                .classList
                .remove("hidden");

        }

    }

    loadRecents();

}


/* =====================================================
   LOGOUT
===================================================== */

async function logout() {

    await fetch(
        "/api/logout",
        {
            method: "POST"
        }
    );

    location.reload();
}


/* =====================================================
   SIDEBAR
===================================================== */

function toggleSidebar() {

    document
        .getElementById("sidebar")
        .classList
        .toggle("open");
}


/* =====================================================
   PLUS MENU
===================================================== */

function togglePlusMenu() {

    document
        .getElementById("plusMenu")
        .classList
        .toggle("hidden");
}


function attachFile() {

    document
        .getElementById("fileInput")
        .click();

    togglePlusMenu();
}


function openCamera() {

    document
        .getElementById("cameraInput")
        .click();

    togglePlusMenu();
}


function openGallery() {

    document
        .getElementById("galleryInput")
        .click();

    togglePlusMenu();
}


function fileSelected(event) {

    const file =
        event.target.files[0];

    if (!file) return;

    addUserMessage(
        "📎 Attached file: " + file.name
    );

    document
        .getElementById("messageInput")
        .focus();
}


function imageSelected(event) {

    const file =
        event.target.files[0];

    if (!file) return;

    const reader =
        new FileReader();

    reader.onload = function(e) {

        selectedImage =
            e.target.result;

        const chat =
            document.getElementById("chatbox");

        const div =
            document.createElement("div");

        div.className =
            "message user";

        div.innerHTML =
            `<img
                src="${selectedImage}"
                style="
                    max-width:280px;
                    max-height:280px;
                    border-radius:14px;
                "
            >`;

        chat.appendChild(div);

        chat.scrollTop =
            chat.scrollHeight;
    };

    reader.readAsDataURL(file);
}


/* =====================================================
   WEB / MAP / IMAGE
===================================================== */

function webSearch() {

    togglePlusMenu();

    const q =
        document
            .getElementById("messageInput")
            .value
            .trim();

    if (q) {

        window.open(
            "https://www.google.com/search?q=" +
            encodeURIComponent(q),
            "_blank"
        );

    } else {

        window.open(
            "https://www.google.com",
            "_blank"
        );

    }
}


function openMap() {

    togglePlusMenu();

    const q =
        document
            .getElementById("messageInput")
            .value
            .trim();

    window.open(
        "https://www.google.com/maps/search/" +
        encodeURIComponent(q || "India"),
        "_blank"
    );
}


function createImage() {

    togglePlusMenu();

    addAssistantMessage(
        "🎨 Create Image option selected. " +
        "Image generation API connect madidaga " +
        "illi actual image generation enable madabahudu."
    );
}


/* =====================================================
   CHAT
===================================================== */

function newChat() {

    currentChatId = null;
    selectedImage = null;

    document
        .getElementById("chatbox")
        .innerHTML = `
            <div
                id="welcome"
                class="welcome"
            >
                <h1>How can I help you?</h1>
                <p>Ask Nirale AI anything.</p>
            </div>
        `;

    document
        .getElementById("messageInput")
        .focus();
}


function addUserMessage(text) {

    const welcome =
        document.getElementById("welcome");

    if (welcome) {
        welcome.remove();
    }

    const chat =
        document.getElementById("chatbox");

    const div =
        document.createElement("div");

    div.className =
        "message user";

    div.textContent =
        text;

    chat.appendChild(div);

    chat.scrollTop =
        chat.scrollHeight;
}


function addAssistantMessage(text) {

    const chat =
        document.getElementById("chatbox");

    const div =
        document.createElement("div");

    div.className =
        "message assistant";

    div.innerHTML =
        marked.parse(text);

    chat.appendChild(div);

    formatCode(div);

    chat.scrollTop =
        chat.scrollHeight;
}


/* =====================================================
   CODE ACTIONS
===================================================== */

function formatCode(container) {

    container
        .querySelectorAll("pre")
        .forEach(pre => {

            const code =
                pre.querySelector("code");

            if (!code) return;

            hljs.highlightElement(code);

            const actions =
                document.createElement("div");

            actions.className =
                "code-actions";

            const copy =
                document.createElement("button");

            copy.textContent =
                "Copy";

            copy.onclick =
                () => {

                    navigator
                        .clipboard
                        .writeText(code.innerText);

                    copy.textContent =
                        "Copied";

                    setTimeout(
                        () => copy.textContent = "Copy",
                        1200
                    );
                };


            const download =
                document.createElement("button");

            download.textContent =
                "Download";

            download.onclick =
                () => {

                    const blob =
                        new Blob(
                            [code.innerText],
                            {type:"text/plain"}
                        );

                    const url =
                        URL.createObjectURL(blob);

                    const a =
                        document.createElement("a");

                    a.href = url;

                    a.download =
                        "nirale-code.txt";

                    a.click();

                    URL.revokeObjectURL(url);
                };

            actions.appendChild(copy);
            actions.appendChild(download);

            pre.appendChild(actions);
        });
}


/* =====================================================
   SEND
===================================================== */

async function sendMessage() {

    const input =
        document.getElementById("messageInput");

    const message =
        input.value.trim();

    if (!message && !selectedImage) {
        return;
    }

    if (message) {
        addUserMessage(message);
    }

    input.value = "";

    const chat =
        document.getElementById("chatbox");

    const thinking =
        document.createElement("div");

    thinking.className =
        "thinking";

    thinking.textContent =
        "ಯೋಚಿಸುತ್ತಿದೆ...";

    chat.appendChild(thinking);

    chat.scrollTop =
        chat.scrollHeight;

    try {

        const res =
            await fetch(
                "/api/chat",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        message:
                            message || "ಈ image ನೋಡಿ.",
                        chat_id:
                            currentChatId,
                        image_data:
                            selectedImage
                    })
                }
            );

        const data =
            await res.json();

        thinking.remove();

        if (!res.ok) {

            addAssistantMessage(
                "❌ " +
                (data.detail ||
                "Something went wrong.")
            );

            return;
        }

        currentChatId =
            data.chat_id;

        selectedImage = null;

        addAssistantMessage(
            data.reply
        );

        loadRecents();

    } catch (error) {

        thinking.remove();

        addAssistantMessage(
            "❌ Server connection problem."
        );
    }
}


/* =====================================================
   ENTER KEY
===================================================== */

function handleKey(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        sendMessage();
    }
}


/* =====================================================
   VOICE
===================================================== */

let recognition = null;

function startVoice() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        alert(
            "Voice input ಈ browserನಲ್ಲಿ support ಆಗುತ್ತಿಲ್ಲ."
        );

        return;
    }

    if (recognition) {

        recognition.stop();
        recognition = null;

        document
            .getElementById("micBtn")
            .classList
            .remove("listening");

        return;
    }

    recognition =
        new SpeechRecognition();

    recognition.lang =
        "kn-IN";

    recognition.continuous =
        false;

    recognition.interimResults =
        true;

    const mic =
        document.getElementById("micBtn");

    mic.classList.add(
        "listening"
    );

    recognition.onresult =
        function(event) {

            let text = "";

            for (
                let i = event.resultIndex;
                i < event.results.length;
                i++
            ) {

                text +=
                    event.results[i][0].transcript;
            }

            document
                .getElementById("messageInput")
                .value = text;
        };


    recognition.onerror =
        function() {

            mic.classList.remove(
                "listening"
            );

            recognition = null;
        };


    recognition.onend =
        function() {

            mic.classList.remove(
                "listening"
            );

            recognition = null;
        };

    recognition.start();
}


/* =====================================================
   RECENTS
===================================================== */

async function loadRecents() {

    const res =
        await fetch("/api/chats");

    if (!res.ok) return;

    const data =
        await res.json();

    const recents =
        document.getElementById("recents");

    recents.innerHTML = "";

    data.chats.forEach(chat => {

        const div =
            document.createElement("div");

        div.className =
            "recent";

        div.textContent =
            chat.title || "New Chat";

        div.onclick =
            () => openChat(chat.id);

        recents.appendChild(div);
    });
}


async function openChat(id) {

    const res =
        await fetch(
            "/api/chats/" + id
        );

    if (!res.ok) return;

    const data =
        await res.json();

    currentChatId =
        id;

    const chatbox =
        document.getElementById("chatbox");

    chatbox.innerHTML = "";

    data.messages.forEach(msg => {

        const div =
            document.createElement("div");

        div.className =
            "message " +
            (
                msg.role === "user"
                ? "user"
                : "assistant"
            );

        if (msg.role === "user") {

            div.textContent =
                msg.content;

        } else {

            div.innerHTML =
                marked.parse(msg.content);

            formatCode(div);
        }

        chatbox.appendChild(div);
    });

    chatbox.scrollTop =
        chatbox.scrollHeight;
}


/* =====================================================
   ACCOUNT / UPGRADE
===================================================== */

function openAccount() {

    document
        .getElementById("accountModal")
        .classList
        .remove("hidden");
}


function openUpgrade() {

    document
        .getElementById("upgradeModal")
        .classList
        .remove("hidden");
}


function closeModals() {

    document
        .querySelectorAll(".modal")
        .forEach(x =>
            x.classList.add("hidden")
        );
}


async function selectPlan(plan) {

    const res =
        await fetch(
            "/api/upgrade",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    plan
                })
            }
        );

    const data =
        await res.json();

    if (data.payment_required) {

        alert(
            "Paid plan activate madoke payment gateway connect madbeku."
        );

        return;
    }

    if (!res.ok) {

        alert(
            data.detail ||
            "Plan change failed."
        );

        return;
    }

    closeModals();

    loadApp();
}


/* =====================================================
   ADMIN
===================================================== */

async function openAdmin() {

    const statsRes =
        await fetch(
            "/api/admin/stats"
        );

    if (!statsRes.ok) {

        alert("Admin access denied.");
        return;
    }

    const stats =
        await statsRes.json();

    document
        .getElementById("adminStats")
        .innerHTML = `
            <p>Users: ${stats.users}</p>
            <p>Messages: ${stats.messages}</p>
            <p>Chats: ${stats.chats}</p>
        `;


    const usersRes =
        await fetch(
            "/api/admin/users"
        );

    const users =
        await usersRes.json();

    document
        .getElementById("adminUsers")
        .innerHTML =
        users.users.map(
            u => `
                <div style="
                    padding:8px;
                    border-bottom:1px solid #eee;
                ">
                    <b>${escapeHtml(u.email)}</b><br>
                    Plan: ${escapeHtml(u.plan)}<br>
                    Created: ${escapeHtml(u.created_at)}
                </div>
            `
        ).join("");


    const activityRes =
        await fetch(
            "/api/admin/activity"
        );

    const activity =
        await activityRes.json();

    document
        .getElementById("adminActivity")
        .innerHTML =
        activity.activity.map(
            a => `
                <div style="
                    padding:8px;
                    border-bottom:1px solid #eee;
                ">
                    <b>${escapeHtml(a.email)}</b><br>
                    ${escapeHtml(a.message)}<br>
                    <small>
                        ${escapeHtml(a.created_at)}
                    </small>
                </div>
            `
        ).join("");


    document
        .getElementById("adminModal")
        .classList
        .remove("hidden");
}


/* =====================================================
   ESCAPE HTML
===================================================== */

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text || "";

    return div.innerHTML;
}


/* =====================================================
   START
===================================================== */

loadApp();

</script>

</body>
</html>
"""


# =========================================================
# ROOT
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def root():

    return HTMLResponse(HTML)
