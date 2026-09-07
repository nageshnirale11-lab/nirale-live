import os
import re
import base64
import hashlib
import secrets
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import google.generativeai as genai


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "Nirale AI"
DB_FILE = "nirale.db"

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "").strip().lower()

if API_KEY:
    genai.configure(api_key=API_KEY)

app = FastAPI(title=APP_NAME)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

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


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str, salt: Optional[str] = None):

    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt),
        n=16384,
        r=8,
        p=1,
        dklen=64
    )

    return hashed.hex(), salt


def verify_password(password: str, password_hash: str, salt: str):

    new_hash, _ = hash_password(password, salt)

    return secrets.compare_digest(
        new_hash,
        password_hash
    )


# ============================================================
# SESSION
# ============================================================

def get_current_user(request: Request):

    token = request.cookies.get("nirale_session")

    if not token:
        return None

    conn = get_db()

    user = conn.execute("""
        SELECT users.*
        FROM users
        INNER JOIN sessions
        ON sessions.user_id = users.id
        WHERE sessions.token = ?
    """, (token,)).fetchone()

    conn.close()

    return user


def update_last_active(user_id):

    conn = get_db()

    conn.execute("""
        UPDATE users
        SET last_active = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        user_id
    ))

    conn.commit()
    conn.close()


# ============================================================
# REQUEST MODELS
# ============================================================

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


# ============================================================
# CREATOR
# ============================================================

def is_creator_question(message: str):

    text = message.lower().strip()

    keywords = [
        "who created you",
        "who made you",
        "who is your creator",
        "who developed you",
        "who built you",
        "who owns you",
        "creator yaaru",
        "creator yaru",
        "ninna creator yaaru",
        "ninna creator yaru",
        "ninnannu yaaru madidaru",
        "ninnannu yaaru madidru",
        "ninnannu yaaru rachisidaru",
        "ನಿನ್ನ creator ಯಾರು",
        "ನಿನ್ನನ್ನು ಯಾರು ರಚಿಸಿದ್ದಾರೆ",
        "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
        "ನಿನ್ನನ್ನು ಯಾರು ಅಭಿವೃದ್ಧಿಪಡಿಸಿದರು",
        "ನಿಮ್ಮ creator ಯಾರು"
    ]

    return any(word in text for word in keywords)


CREATOR_REPLY = "ನನ್ನನ್ನು Nagesh Nirale ಅವರು ರಚಿಸಿದ್ದಾರೆ."


# ============================================================
# GEMINI
# ============================================================

SYSTEM_PROMPT = """
You are Nirale AI.

You are a helpful, intelligent and friendly multilingual AI assistant.

Support the user's language naturally.

You can answer in:
Kannada,
English,
Hindi,
Telugu,
Tamil,
Malayalam,
Marathi,
Bengali,
Gujarati,
Punjabi,
Urdu,
and other languages supported by the AI model.

Rules:

1. Answer the user's actual question.
2. Do not unnecessarily ask the user to login.
3. Give useful and clear answers.
4. If the user asks for programming code, provide working code.
5. Use Markdown when useful.
6. Put programming code inside fenced code blocks.
7. Do not expose API keys, passwords or secret tokens.
8. Do not pretend that an action was completed when it was not.
"""


def generate_ai_reply(
    message: str,
    image_data: Optional[str] = None
):

    if is_creator_question(message):
        return CREATOR_REPLY

    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY or GEMINI_API_KEY is not configured in the server."
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

            image_bytes = base64.b64decode(image_data)

            contents.append({
                "mime_type": "image/jpeg",
                "data": image_bytes
            })

        except Exception:
            pass

    response = model.generate_content(contents)

    text = getattr(response, "text", None)

    if not text:
        return "ಕ್ಷಮಿಸಿ, ಈಗ answer generate ಆಗಲಿಲ್ಲ."

    return text


# ============================================================
# GUEST QUESTION COUNTER
# ============================================================

def get_guest_count(request: Request):

    value = request.cookies.get(
        "nirale_guest_count",
        "0"
    )

    try:
        return int(value)
    except Exception:
        return 0


# ============================================================
# SIGNUP
# ============================================================

@app.post("/api/signup")
async def signup(data: SignupRequest):

    email = data.email.strip().lower()
    password = data.password

    if not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email
    ):
        raise HTTPException(
            400,
            "Valid email address enter madi."
        )

    if len(password) < 6:
        raise HTTPException(
            400,
            "Password ಕನಿಷ್ಠ 6 characters ಇರಬೇಕು."
        )

    password_hash, salt = hash_password(password)

    conn = get_db()

    try:

        cur = conn.execute("""
            INSERT INTO users
            (
                email,
                password_hash,
                salt,
                plan,
                created_at,
                last_active
            )
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
            INSERT INTO sessions
            (
                token,
                user_id,
                created_at
            )
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

    response = JSONResponse({
        "ok": True,
        "email": email
    })

    response.set_cookie(
        key="nirale_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30
    )

    response.delete_cookie(
        "nirale_guest_count"
    )

    return response


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/login")
async def login(data: LoginRequest):

    email = data.email.strip().lower()

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

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

    conn = get_db()

    conn.execute("""
        INSERT INTO sessions
        (
            token,
            user_id,
            created_at
        )
        VALUES (?, ?, ?)
    """, (
        token,
        user["id"],
        datetime.now().isoformat()
    ))

    conn.execute("""
        UPDATE users
        SET last_active = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        user["id"]
    ))

    conn.commit()
    conn.close()

    response = JSONResponse({
        "ok": True,
        "email": email,
        "plan": user["plan"]
    })

    response.set_cookie(
        key="nirale_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30
    )

    response.delete_cookie(
        "nirale_guest_count"
    )

    return response


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/logout")
async def logout(request: Request):

    token = request.cookies.get(
        "nirale_session"
    )

    if token:

        conn = get_db()

        conn.execute(
            "DELETE FROM sessions WHERE token = ?",
            (token,)
        )

        conn.commit()
        conn.close()

    response = JSONResponse({
        "ok": True
    })

    response.delete_cookie(
        "nirale_session"
    )

    return response


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/me")
async def me(request: Request):

    user = get_current_user(request)

    if not user:

        return {
            "logged_in": False
        }

    update_last_active(
        user["id"]
    )

    return {
        "logged_in": True,
        "id": user["id"],
        "email": user["email"],
        "plan": user["plan"],
        "created_at": user["created_at"],
        "last_active": user["last_active"]
    }


# ============================================================
# CHAT
# ============================================================

@app.post("/api/chat")
async def chat(
    request: Request,
    data: ChatRequest
):

    message = data.message.strip()

    if not message and not data.image_data:

        raise HTTPException(
            400,
            "Message empty ide."
        )

    user = get_current_user(request)

    # ========================================================
    # GUEST MODE
    # First 4 questions are allowed without login.
    # ========================================================

    if not user:

        guest_count = get_guest_count(
            request
        )

        if guest_count >= 4:

            raise HTTPException(
                status_code=401,
                detail="FREE_LOGIN_REQUIRED"
            )

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

        new_count = guest_count + 1

        response = JSONResponse({
            "ok": True,
            "guest": True,
            "guest_count": new_count,
            "remaining": max(
                0,
                4 - new_count
            ),
            "login_required_after": (
                new_count >= 4
            ),
            "reply": reply
        })

        response.set_cookie(
            key="nirale_guest_count",
            value=str(new_count),
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24
        )

        return response

    # ========================================================
    # LOGGED IN MODE
    # ========================================================

    update_last_active(
        user["id"]
    )

    conn = get_db()

    chat_id = data.chat_id

    if chat_id:

        existing_chat = conn.execute("""
            SELECT *
            FROM chats
            WHERE id = ?
            AND user_id = ?
        """, (
            chat_id,
            user["id"]
        )).fetchone()

        if not existing_chat:

            conn.close()

            raise HTTPException(
                404,
                "Chat not found."
            )

    else:

        title = (
            message[:60]
            if message
            else "Image Chat"
        )

        cur = conn.execute("""
            INSERT INTO chats
            (
                user_id,
                title,
                created_at,
                updated_at
            )
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
        (
            chat_id,
            role,
            content,
            created_at
        )
        VALUES (?, 'user', ?, ?)
    """, (
        chat_id,
        message or "[Image]",
        datetime.now().isoformat()
    ))

    conn.execute("""
        INSERT INTO usage
        (
            user_id,
            chat_id,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        user["id"],
        chat_id,
        message or "[Image]",
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

    conn = get_db()

    conn.execute("""
        INSERT INTO messages
        (
            chat_id,
            role,
            content,
            created_at
        )
        VALUES (?, 'assistant', ?, ?)
    """, (
        chat_id,
        reply,
        datetime.now().isoformat()
    ))

    conn.execute("""
        UPDATE chats
        SET updated_at = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        chat_id
    ))

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "guest": False,
        "chat_id": chat_id,
        "reply": reply
    }


# ============================================================
# CHAT HISTORY
# ============================================================

@app.get("/api/chats")
async def get_chats(request: Request):

    user = get_current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            title,
            created_at,
            updated_at
        FROM chats
        WHERE user_id = ?
        ORDER BY updated_at DESC
    """, (
        user["id"],
    )).fetchall()

    conn.close()

    return {
        "chats": [
            dict(row)
            for row in rows
        ]
    }


@app.get("/api/chats/{chat_id}")
async def get_chat(
    chat_id: int,
    request: Request
):

    user = get_current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    conn = get_db()

    chat = conn.execute("""
        SELECT *
        FROM chats
        WHERE id = ?
        AND user_id = ?
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

    messages = conn.execute("""
        SELECT
            role,
            content,
            created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
    """, (
        chat_id,
    )).fetchall()

    conn.close()

    return {
        "chat": dict(chat),
        "messages": [
            dict(row)
            for row in messages
        ]
    }


@app.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: int,
    request: Request
):

    user = get_current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    conn = get_db()

    conn.execute(
        "DELETE FROM messages WHERE chat_id = ?",
        (chat_id,)
    )

    conn.execute("""
        DELETE FROM chats
        WHERE id = ?
        AND user_id = ?
    """, (
        chat_id,
        user["id"]
    ))

    conn.commit()
    conn.close()

    return {
        "ok": True
    }


# ============================================================
# PLANS
# ============================================================

@app.get("/api/plans")
async def plans():

    return {
        "plans": [
            {
                "name": "Free",
                "price": 0
            },
            {
                "name": "Plus",
                "price": 499
            },
            {
                "name": "Pro",
                "price": 999
            }
        ]
    }


@app.post("/api/upgrade")
async def upgrade(
    request: Request,
    data: UpgradeRequest
):

    user = get_current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    if data.plan not in [
        "Free",
        "Plus",
        "Pro"
    ]:

        raise HTTPException(
            400,
            "Invalid plan."
        )

    if data.plan == "Free":

        conn = get_db()

        conn.execute("""
            UPDATE users
            SET plan = 'Free'
            WHERE id = ?
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
        "plan": data.plan,
        "message":
            "Payment gateway connect madida mele paid plan activate agutte."
    }


# ============================================================
# ADMIN
# ============================================================

def require_admin(request: Request):

    user = get_current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    if not OWNER_EMAIL:

        raise HTTPException(
            403,
            "OWNER_EMAIL configure madi."
        )

    if user["email"].lower() != OWNER_EMAIL:

        raise HTTPException(
            403,
            "Admin access denied."
        )

    return user


@app.get("/api/admin/stats")
async def admin_stats(request: Request):

    require_admin(request)

    conn = get_db()

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


@app.get("/api/admin/users")
async def admin_users(request: Request):

    require_admin(request)

    conn = get_db()

    rows = conn.execute("""
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
        "users": [
            dict(row)
            for row in rows
        ]
    }


@app.get("/api/admin/activity")
async def admin_activity(request: Request):

    require_admin(request)

    conn = get_db()

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
        "activity": [
            dict(row)
            for row in rows
        ]
    }


# ============================================================
# FRONTEND
# ============================================================

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1.0"
>

<title>✨ Nirale AI</title>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<link
rel="stylesheet"
href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css"
>

<script
src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js">
</script>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    color: #202124;
    background: #fff;
}

button,
input,
textarea {
    font: inherit;
}

.hidden {
    display: none !important;
}


/* =========================================================
   AUTH
========================================================= */

#authScreen {
    position: fixed;
    inset: 0;
    z-index: 200;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #fff;
    padding: 20px;
}

.auth-card {
    width: 100%;
    max-width: 420px;
    padding: 32px;
    border: 1px solid #e5e7eb;
    border-radius: 22px;
    box-shadow: 0 15px 45px rgba(0,0,0,.08);
}

.auth-logo {
    text-align: center;
    font-size: 30px;
    font-weight: 700;
    margin-bottom: 8px;
}

.auth-description {
    text-align: center;
    color: #777;
    margin-bottom: 25px;
}

.auth-card input {
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    outline: none;
}

.auth-card input:focus {
    border-color: #555;
}

.primary-button {
    width: 100%;
    border: none;
    border-radius: 12px;
    padding: 14px;
    color: white;
    background: #111827;
    cursor: pointer;
    font-weight: 600;
}

.auth-switch {
    text-align: center;
    margin-top: 18px;
    color: #666;
}

.auth-switch button {
    border: none;
    background: transparent;
    cursor: pointer;
    font-weight: 600;
}


/* =========================================================
   APP
========================================================= */

#app {
    height: 100vh;
    display: flex;
    overflow: hidden;
}

.sidebar {
    width: 270px;
    flex-shrink: 0;
    background: #fafafa;
    border-right: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
}

.sidebar-top {
    padding: 14px;
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

.side-button {
    margin-top: 8px;
    padding: 12px;
    border-radius: 10px;
    cursor: pointer;
}

.side-button:hover {
    background: #ededed;
}

.recents-title {
    padding: 15px;
    color: #777;
    font-size: 12px;
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
    background: #eee;
}

.account-area {
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


/* =========================================================
   MAIN
========================================================= */

.main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.header {
    height: 60px;
    flex-shrink: 0;
    border-bottom: 1px solid #eee;
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 12px;
}

.menu-button {
    display: none;
    border: none;
    background: transparent;
    font-size: 23px;
    cursor: pointer;
}

.header-logo {
    font-size: 20px;
    font-weight: 700;
}

.header-space {
    flex: 1;
}

.upgrade-button {
    border: none;
    border-radius: 10px;
    padding: 9px 14px;
    background: #111827;
    color: white;
    cursor: pointer;
}


/* =========================================================
   CHAT
========================================================= */

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

.user-message {
    padding: 13px 17px;
    border-radius: 16px;
    background: #f3f4f6;
}

.assistant-message {
    padding: 5px 0;
}

.assistant-message pre {
    position: relative;
    padding: 45px 15px 15px;
    border-radius: 12px;
    overflow-x: auto;
    background: #f6f8fa;
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
    padding: 5px 8px;
    background: white;
    cursor: pointer;
}

.thinking {
    max-width: 850px;
    margin: 0 auto 20px;
    color: #777;
}


/* =========================================================
   FOOTER
========================================================= */

.footer {
    padding: 12px 18px 18px;
    position: relative;
}

.input-container {
    max-width: 850px;
    margin: auto;
    display: flex;
    align-items: flex-end;
    padding: 8px;
    border: 1px solid #d9d9d9;
    border-radius: 18px;
    box-shadow: 0 3px 15px rgba(0,0,0,.05);
}

.message-input {
    flex: 1;
    resize: none;
    border: none;
    outline: none;
    padding: 10px;
    min-height: 42px;
    max-height: 150px;
}

.icon-button {
    width: 40px;
    height: 40px;
    border: none;
    background: transparent;
    border-radius: 10px;
    cursor: pointer;
    font-size: 18px;
}

.icon-button:hover {
    background: #eee;
}

.send-button {
    color: white;
    background: #111827;
}

.listening {
    background: #ef4444 !important;
    color: white;
}


/* =========================================================
   PLUS MENU
========================================================= */

.plus-menu {
    position: absolute;
    left: 18px;
    bottom: 82px;
    width: 230px;
    padding: 8px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 14px;
    box-shadow: 0 12px 35px rgba(0,0,0,.15);
    z-index: 50;
}

.plus-menu button {
    width: 100%;
    border: none;
    background: white;
    padding: 11px;
    text-align: left;
    border-radius: 9px;
    cursor: pointer;
}

.plus-menu button:hover {
    background: #f1f1f1;
}


/* =========================================================
   MODALS
========================================================= */

.modal {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
    background: rgba(0,0,0,.45);
}

.modal-card {
    width: 100%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
    padding: 25px;
    border-radius: 18px;
    background: white;
}

.modal-close {
    float: right;
    border: none;
    background: transparent;
    font-size: 24px;
    cursor: pointer;
}

.plan-card {
    border: 1px solid #ddd;
    border-radius: 14px;
    padding: 16px;
    margin-top: 10px;
}

.plan-card button {
    float: right;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    background: #111827;
    color: white;
    cursor: pointer;
}


/* =========================================================
   MOBILE
========================================================= */

@media (max-width: 700px) {

    .sidebar {
        position: fixed;
        top: 0;
        bottom: 0;
        left: -280px;
        z-index: 90;
        transition: left .25s;
    }

    .sidebar.open {
        left: 0;
    }

    .menu-button {
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

    .upgrade-button {
        padding: 8px 10px;
    }

    .footer {
        padding: 8px;
        padding-bottom: calc(
            8px + env(safe-area-inset-bottom)
        );
    }

    .message {
        max-width: 100%;
    }

    .auth-card {
        padding: 25px;
    }
}

</style>

</head>

<body>


<!-- =========================================================
     AUTH SCREEN
     Hidden when user first opens Nirale AI.
========================================================= -->

<div
    id="authScreen"
    class="hidden"
>

    <div class="auth-card">

        <div class="auth-logo">
            ✨ Nirale AI
        </div>

        <div class="auth-description">
            Login to continue using Nirale AI
        </div>


        <!-- LOGIN -->

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
                class="primary-button"
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


        <!-- SIGNUP -->

        <div
            id="signupForm"
            class="hidden"
        >

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
                class="primary-button"
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


<!-- =========================================================
     APP
========================================================= -->

<div id="app">


    <!-- SIDEBAR -->

    <aside
        id="sidebar"
        class="sidebar"
    >

        <div class="sidebar-top">

            <button
                class="new-chat"
                onclick="newChat()"
            >
                ＋ New Chat
            </button>

            <div
                class="side-button"
                onclick="openUpgrade()"
            >
                ⭐ Upgrade
            </div>

            <div
                class="side-button"
                onclick="openAccount()"
            >
                👤 Account
            </div>

            <div
                id="adminItem"
                class="side-button hidden"
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
        >
        </div>


        <div class="account-area">

            <div
                id="sideEmail"
                class="account-email"
            >
                Guest
            </div>

            <div
                id="sidePlan"
                class="account-plan"
            >
                4 free questions
            </div>

            <div
                id="logoutButton"
                class="side-button hidden"
                onclick="logout()"
            >
                ↪ Logout
            </div>

        </div>

    </aside>


    <!-- MAIN -->

    <main class="main">


        <header class="header">

            <button
                class="menu-button"
                onclick="toggleSidebar()"
            >
                ☰
            </button>

            <div class="header-logo">
                ✨ Nirale AI
            </div>

            <div class="header-space"></div>

            <button
                class="upgrade-button"
                onclick="openUpgrade()"
            >
                ⭐ Upgrade
            </button>

        </header>


        <!-- CHATBOX -->

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


        <!-- FOOTER -->

        <div class="footer">


            <!-- PLUS MENU -->

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


            <!-- INPUT -->

            <div class="input-container">

                <button
                    class="icon-button"
                    onclick="togglePlusMenu()"
                >
                    ＋
                </button>

                <textarea
                    id="messageInput"
                    class="message-input"
                    rows="1"
                    placeholder="Message Nirale AI..."
                    onkeydown="handleKey(event)"
                ></textarea>

                <button
                    id="micBtn"
                    class="icon-button"
                    onclick="startVoice()"
                >
                    🎤
                </button>

                <button
                    class="icon-button send-button"
                    onclick="sendMessage()"
                >
                    ➤
                </button>

            </div>

        </div>

    </main>

</div>


<!-- FILE INPUTS -->

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


<!-- ACCOUNT MODAL -->

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

        <h2>👤 Account</h2>

        <p id="accountEmail"></p>

        <p id="accountPlan"></p>

    </div>

</div>


<!-- UPGRADE MODAL -->

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

        <h2>⭐ Upgrade Nirale AI</h2>


        <div class="plan-card">

            <b>Free</b>

            <p>₹0</p>

            <button
                onclick="selectPlan('Free')"
            >
                Select
            </button>

        </div>


        <div class="plan-card">

            <b>Plus</b>

            <p>₹499 / month</p>

            <button
                onclick="selectPlan('Plus')"
            >
                Upgrade
            </button>

        </div>


        <div class="plan-card">

            <b>Pro</b>

            <p>₹999 / month</p>

            <button
                onclick="selectPlan('Pro')"
            >
                Upgrade
            </button>

        </div>

    </div>

</div>


<!-- ADMIN MODAL -->

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
            style="
                max-height:250px;
                overflow:auto;
            "
        >
        </div>

        <h3>Recent Activity</h3>

        <div
            id="adminActivity"
            style="
                max-height:250px;
                overflow:auto;
            "
        >
        </div>

    </div>

</div>


<script>

/* ============================================================
   GLOBAL
============================================================ */

let currentChatId = null;
let selectedImage = null;
let recognition = null;


/* ============================================================
   AUTH UI
============================================================ */

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


/* ============================================================
   LOGIN
============================================================ */

async function login() {

    const email =
        document
            .getElementById("loginEmail")
            .value
            .trim();

    const password =
        document
            .getElementById("loginPassword")
            .value;

    if (!email || !password) {

        alert(
            "Email ಮತ್ತು password enter madi."
        );

        return;
    }

    const res =
        await fetch(
            "/api/login",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    email,
                    password
                })
            }
        );

    const data =
        await res.json();

    if (!res.ok) {

        alert(
            data.detail ||
            "Login failed."
        );

        return;
    }

    await loadApp();

}


/* ============================================================
   SIGNUP
============================================================ */

async function signup() {

    const email =
        document
            .getElementById("signupEmail")
            .value
            .trim();

    const password =
        document
            .getElementById("signupPassword")
            .value;

    if (!email || !password) {

        alert(
            "Email ಮತ್ತು password enter madi."
        );

        return;
    }

    const res =
        await fetch(
            "/api/signup",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    email,
                    password
                })
            }
        );

    const data =
        await res.json();

    if (!res.ok) {

        alert(
            data.detail ||
            "Signup failed."
        );

        return;
    }

    await loadApp();

}


/* ============================================================
   LOAD APP
============================================================ */

async function loadApp() {

    const res =
        await fetch("/api/me");

    const user =
        await res.json();


    /* -----------------------------------------
       GUEST
    ----------------------------------------- */

    if (!user.logged_in) {

        document
            .getElementById("authScreen")
            .classList
            .add("hidden");

        document
            .getElementById("app")
            .classList
            .remove("hidden");

        document
            .getElementById("sideEmail")
            .textContent =
            "Guest";

        document
            .getElementById("sidePlan")
            .textContent =
            "4 free questions";

        document
            .getElementById("logoutButton")
            .classList
            .add("hidden");

        return;
    }


    /* -----------------------------------------
       LOGGED IN
    ----------------------------------------- */

    document
        .getElementById("authScreen")
        .classList
        .add("hidden");

    document
        .getElementById("app")
        .classList
        .remove("hidden");


    document
        .getElementById("sideEmail")
        .textContent =
        user.email;

    document
        .getElementById("sidePlan")
        .textContent =
        user.plan + " plan";


    document
        .getElementById("logoutButton")
        .classList
        .remove("hidden");


    document
        .getElementById("accountEmail")
        .textContent =
        "Email: " + user.email;


    document
        .getElementById("accountPlan")
        .textContent =
        "Plan: " + user.plan;


    loadRecents();


    const adminCheck =
        await fetch(
            "/api/admin/stats"
        );

    if (adminCheck.ok) {

        document
            .getElementById("adminItem")
            .classList
            .remove("hidden");

    }

}


/* ============================================================
   LOGOUT
============================================================ */

async function logout() {

    await fetch(
        "/api/logout",
        {
            method: "POST"
        }
    );

    location.reload();
}


/* ============================================================
   SIDEBAR
============================================================ */

function toggleSidebar() {

    document
        .getElementById("sidebar")
        .classList
        .toggle("open");
}


/* ============================================================
   NEW CHAT
============================================================ */

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


/* ============================================================
   PLUS MENU
============================================================ */

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
        "📎 Attached file: " +
        file.name
    );
}


function imageSelected(event) {

    const file =
        event.target.files[0];

    if (!file) return;

    const reader =
        new FileReader();

    reader.onload =
        function(e) {

            selectedImage =
                e.target.result;

            const chat =
                document
                    .getElementById("chatbox");

            const div =
                document
                    .createElement("div");

            div.className =
                "message user-message";

            const img =
                document
                    .createElement("img");

            img.src =
                selectedImage;

            img.style.maxWidth =
                "280px";

            img.style.maxHeight =
                "280px";

            img.style.borderRadius =
                "14px";

            div.appendChild(img);

            chat.appendChild(div);

            chat.scrollTop =
                chat.scrollHeight;
        };

    reader.readAsDataURL(file);
}


/* ============================================================
   WEB SEARCH
============================================================ */

function webSearch() {

    togglePlusMenu();

    const q =
        document
            .getElementById("messageInput")
            .value
            .trim();

    window.open(
        "https://www.google.com/search?q=" +
        encodeURIComponent(
            q || "Nirale AI"
        ),
        "_blank"
    );
}


/* ============================================================
   MAP
============================================================ */

function openMap() {

    togglePlusMenu();

    const q =
        document
            .getElementById("messageInput")
            .value
            .trim();

    window.open(
        "https://www.google.com/maps/search/" +
        encodeURIComponent(
            q || "India"
        ),
        "_blank"
    );
}


/* ============================================================
   CREATE IMAGE
============================================================ */

function createImage() {

    togglePlusMenu();

    addAssistantMessage(
        "🎨 Create Image selected. " +
        "Actual image generation API connect " +
        "madida mele image generate madabahudu."
    );
}


/* ============================================================
   ADD USER MESSAGE
============================================================ */

function addUserMessage(text) {

    const welcome =
        document
            .getElementById("welcome");

    if (welcome) {
        welcome.remove();
    }

    const chat =
        document
            .getElementById("chatbox");

    const div =
        document
            .createElement("div");

    div.className =
        "message user-message";

    div.textContent =
        text;

    chat.appendChild(div);

    chat.scrollTop =
        chat.scrollHeight;
}


/* ============================================================
   ADD ASSISTANT MESSAGE
============================================================ */

function addAssistantMessage(text) {

    const welcome =
        document
            .getElementById("welcome");

    if (welcome) {
        welcome.remove();
    }

    const chat =
        document
            .getElementById("chatbox");

    const div =
        document
            .createElement("div");

    div.className =
        "message assistant-message";

    div.innerHTML =
        marked.parse(text);

    chat.appendChild(div);

    formatCode(div);

    chat.scrollTop =
        chat.scrollHeight;
}


/* ============================================================
   CODE FORMAT
============================================================ */

function formatCode(container) {

    container
        .querySelectorAll("pre")
        .forEach(pre => {

            const code =
                pre.querySelector("code");

            if (!code) return;

            try {
                hljs.highlightElement(code);
            } catch(e) {}


            const actions =
                document
                    .createElement("div");

            actions.className =
                "code-actions";


            const copy =
                document
                    .createElement("button");

            copy.textContent =
                "Copy";

            copy.onclick =
                async function() {

                    try {

                        await navigator
                            .clipboard
                            .writeText(
                                code.innerText
                            );

                        copy.textContent =
                            "Copied";

                        setTimeout(
                            () => {
                                copy.textContent =
                                    "Copy";
                            },
                            1200
                        );

                    } catch(e) {}
                };


            const download =
                document
                    .createElement("button");

            download.textContent =
                "Download";

            download.onclick =
                function() {

                    const blob =
                        new Blob(
                            [code.innerText],
                            {
                                type:
                                    "text/plain"
                            }
                        );

                    const url =
                        URL.createObjectURL(
                            blob
                        );

                    const a =
                        document
                            .createElement("a");

                    a.href =
                        url;

                    a.download =
                        "nirale-code.txt";

                    a.click();

                    URL.revokeObjectURL(
                        url
                    );
                };


            actions.appendChild(copy);
            actions.appendChild(download);

            pre.appendChild(actions);

        });
}


/* ============================================================
   SEND MESSAGE
============================================================ */

async function sendMessage() {

    const input =
        document
            .getElementById("messageInput");

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
        document
            .getElementById("chatbox");


    const thinking =
        document
            .createElement("div");

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
                            message ||
                            "ಈ image ನೋಡಿ.",
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


        /* ------------------------------------
           4 QUESTIONS COMPLETE
        ------------------------------------ */

        if (
            data.detail ===
            "FREE_LOGIN_REQUIRED"
        ) {

            showLoginRequired();

            return;
        }


        if (!res.ok) {

            addAssistantMessage(
                "❌ " +
                (
                    data.detail ||
                    "Something went wrong."
                )
            );

            return;
        }


        if (data.chat_id) {

            currentChatId =
                data.chat_id;
        }


        selectedImage = null;


        addAssistantMessage(
            data.reply
        );


        /* ------------------------------------
           AFTER 4TH ANSWER
        ------------------------------------ */

        if (
            data.guest === true &&
            data.guest_count >= 4
        ) {

            setTimeout(
                () => {
                    showLoginRequired();
                },
                1000
            );

        }


        loadRecents();

    } catch(error) {

        thinking.remove();

        addAssistantMessage(
            "❌ Server connection problem."
        );
    }
}


/* ============================================================
   LOGIN REQUIRED
============================================================ */

function showLoginRequired() {

    document
        .getElementById("authScreen")
        .classList
        .remove("hidden");

    document
        .getElementById("app")
        .classList
        .add("hidden");

    showLogin();
}


/* ============================================================
   ENTER KEY
============================================================ */

function handleKey(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        sendMessage();
    }
}


/* ============================================================
   VOICE
============================================================ */

function startVoice() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;


    if (!SpeechRecognition) {

        alert(
            "ಈ browserನಲ್ಲಿ voice input support ಇಲ್ಲ."
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
        document
            .getElementById("micBtn");

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
                    event.results[i][0]
                        .transcript;
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


/* ============================================================
   RECENTS
============================================================ */

async function loadRecents() {

    const res =
        await fetch(
            "/api/chats"
        );

    if (!res.ok) return;

    const data =
        await res.json();

    const recents =
        document
            .getElementById("recents");

    recents.innerHTML = "";


    data.chats.forEach(chat => {

        const div =
            document
                .createElement("div");

        div.className =
            "recent";

        div.textContent =
            chat.title ||
            "New Chat";

        div.onclick =
            function() {

                openChat(chat.id);
            };

        recents.appendChild(div);

    });
}


/* ============================================================
   OPEN CHAT
============================================================ */

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
        document
            .getElementById("chatbox");

    chatbox.innerHTML = "";


    data.messages.forEach(
        msg => {

            const div =
                document
                    .createElement("div");

            if (
                msg.role === "user"
            ) {

                div.className =
                    "message user-message";

                div.textContent =
                    msg.content;

            } else {

                div.className =
                    "message assistant-message";

                div.innerHTML =
                    marked.parse(
                        msg.content
                    );

                formatCode(div);
            }

            chatbox.appendChild(div);

        }
    );


    chatbox.scrollTop =
        chatbox.scrollHeight;
}


/* ============================================================
   ACCOUNT
============================================================ */

function openAccount() {

    document
        .getElementById("accountModal")
        .classList
        .remove("hidden");
}


/* ============================================================
   UPGRADE
============================================================ */

function openUpgrade() {

    document
        .getElementById("upgradeModal")
        .classList
        .remove("hidden");
}


/* ============================================================
   CLOSE MODALS
============================================================ */

function closeModals() {

    document
        .querySelectorAll(".modal")
        .forEach(
            modal =>
                modal.classList.add(
                    "hidden"
                )
        );
}


/* ============================================================
   PLAN
============================================================ */

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


    if (
        data.payment_required
    ) {

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


/* ============================================================
   ADMIN
============================================================ */

async function openAdmin() {

    const statsRes =
        await fetch(
            "/api/admin/stats"
        );


    if (!statsRes.ok) {

        alert(
            "Admin access denied."
        );

        return;
    }


    const stats =
        await statsRes.json();


    document
        .getElementById("adminStats")
        .innerHTML = `
            <p>
                Users: ${stats.users}
            </p>

            <p>
                Messages: ${stats.messages}
            </p>

            <p>
                Chats: ${stats.chats}
            </p>
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
        users.users
            .map(
                user => `
                    <div
                        style="
                            padding:8px;
                            border-bottom:
                                1px solid #eee;
                        "
                    >
                        <b>
                            ${escapeHtml(
                                user.email
                            )}
                        </b>

                        <br>

                        Plan:
                        ${escapeHtml(
                            user.plan
                        )}

                        <br>

                        Created:
                        ${escapeHtml(
                            user.created_at
                        )}
                    </div>
                `
            )
            .join("");


    const activityRes =
        await fetch(
            "/api/admin/activity"
        );


    const activity =
        await activityRes.json();


    document
        .getElementById("adminActivity")
        .innerHTML =
        activity.activity
            .map(
                item => `
                    <div
                        style="
                            padding:8px;
                            border-bottom:
                                1px solid #eee;
                        "
                    >
                        <b>
                            ${escapeHtml(
                                item.email
                            )}
                        </b>

                        <br>

                        ${escapeHtml(
                            item.message
                        )}

                        <br>

                        <small>
                            ${escapeHtml(
                                item.created_at
                            )}
                        </small>
                    </div>
                `
            )
            .join("");


    document
        .getElementById("adminModal")
        .classList
        .remove("hidden");
}


/* ============================================================
   ESCAPE HTML
============================================================ */

function escapeHtml(text) {

    const div =
        document
            .createElement("div");

    div.textContent =
        text || "";

    return div.innerHTML;
}


/* ============================================================
   START
============================================================ */

loadApp();

</script>

</body>
</html>
"""


# ============================================================
# ROOT
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root():

    return HTMLResponse(HTML)

