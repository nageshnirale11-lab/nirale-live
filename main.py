import os
import re
import json
import base64
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import google.generativeai as genai


# =========================================================
# NIRALE AI
# Single-file FastAPI application
# =========================================================

app = FastAPI(title="Nirale AI")

DB_FILE = os.getenv("NIRALE_DB", "nirale.db")

GOOGLE_API_KEY = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

OWNER_EMAIL = os.getenv(
    "OWNER_EMAIL",
    ""
).strip().lower()


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
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'New Chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(chat_id) REFERENCES chats(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER,
            question TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# HELPERS
# =========================================================

def now():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str, salt: Optional[str] = None):
    if salt is None:
        salt = secrets.token_hex(16)

    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt),
        n=16384,
        r=8,
        p=1,
        dklen=64
    )

    return derived.hex(), salt


def verify_password(password, stored_hash, salt):
    new_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(new_hash, stored_hash)


def create_session(user_id):
    token = secrets.token_urlsafe(48)

    conn = db()
    conn.execute(
        "INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)",
        (token, user_id, now())
    )
    conn.commit()
    conn.close()

    return token


def get_current_user(request: Request):
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

    if row:
        conn.execute(
            "UPDATE users SET last_active=? WHERE id=?",
            (now(), row["id"])
        )
        conn.commit()

    conn.close()

    return row


def require_user(request: Request):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Login required"
        )

    return user


def is_creator_question(message):
    text = message.lower().strip()

    phrases = [
        "who created you",
        "who made you",
        "who is your creator",
        "who developed you",
        "who built you",
        "nimmannu yaru create madidru",
        "nimmannu yaru madidru",
        "nimmanna yaru create madidare",
        "ninna creator yaru",
        "ninna create madidavaru yaru",
        "ನಿನ್ನನ್ನು ಯಾರು ರಚಿಸಿದ್ದಾರೆ",
        "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
        "ನಿನ್ನ ಕ್ರಿಯೇಟರ್ ಯಾರು",
        "ನಿನ್ನನ್ನು ಯಾರು create ಮಾಡಿದರು",
    ]

    return any(x in text for x in phrases)


def creator_answer():
    return "ನನ್ನನ್ನು Nagesh Nirale ಅವರು ರಚಿಸಿದ್ದಾರೆ."


# =========================================================
# MODELS
# =========================================================

class AuthRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[int] = None
    image_data: Optional[str] = None


class PlanRequest(BaseModel):
    plan: str


# =========================================================
# AUTH
# =========================================================

@app.post("/api/signup")
async def signup(data: AuthRequest):

    email = data.email.strip().lower()
    password = data.password

    if not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email
    ):
        raise HTTPException(
            status_code=400,
            detail="Valid email required"
        )

    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )

    password_hash, salt = hash_password(password)

    conn = db()

    try:
        cursor = conn.execute("""
            INSERT INTO users(
                email,
                password_hash,
                salt,
                plan,
                created_at,
                last_active
            )
            VALUES(?,?,?,?,?,?)
        """, (
            email,
            password_hash,
            salt,
            "Free",
            now(),
            now()
        ))

        conn.commit()
        user_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        conn.close()

        raise HTTPException(
            status_code=409,
            detail="Account already exists"
        )

    conn.close()

    token = create_session(user_id)

    response = JSONResponse({
        "ok": True,
        "email": email
    })

    response.set_cookie(
        "nirale_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30
    )

    return response


@app.post("/api/login")
async def login(data: AuthRequest):

    email = data.email.strip().lower()

    conn = db()

    user = conn.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        data.password,
        user["password_hash"],
        user["salt"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_session(user["id"])

    response = JSONResponse({
        "ok": True,
        "email": user["email"],
        "plan": user["plan"]
    })

    response.set_cookie(
        "nirale_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30
    )

    return response


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

    response = JSONResponse({"ok": True})

    response.delete_cookie("nirale_session")

    return response


@app.get("/api/me")
async def me(request: Request):

    user = get_current_user(request)

    if not user:
        return {
            "logged_in": False
        }

    return {
        "logged_in": True,
        "id": user["id"],
        "email": user["email"],
        "plan": user["plan"],
        "created_at": user["created_at"],
        "last_active": user["last_active"]
    }


# =========================================================
# CHAT HISTORY
# =========================================================

@app.get("/api/chats")
async def chats(request: Request):

    user = require_user(request)

    conn = db()

    rows = conn.execute("""
        SELECT id,title,created_at,updated_at
        FROM chats
        WHERE user_id=?
        ORDER BY updated_at DESC
        LIMIT 100
    """, (user["id"],)).fetchall()

    conn.close()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
        for row in rows
    ]


@app.get("/api/chats/{chat_id}")
async def get_chat(
    chat_id: int,
    request: Request
):

    user = require_user(request)

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

        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    messages = conn.execute("""
        SELECT role,content,created_at
        FROM messages
        WHERE chat_id=? AND user_id=?
        ORDER BY id ASC
    """, (
        chat_id,
        user["id"]
    )).fetchall()

    conn.close()

    return {
        "id": chat["id"],
        "title": chat["title"],
        "messages": [
            {
                "role": x["role"],
                "content": x["content"],
                "created_at": x["created_at"]
            }
            for x in messages
        ]
    }


@app.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: int,
    request: Request
):

    user = require_user(request)

    conn = db()

    conn.execute("""
        DELETE FROM messages
        WHERE chat_id=? AND user_id=?
    """, (
        chat_id,
        user["id"]
    ))

    conn.execute("""
        DELETE FROM chats
        WHERE id=? AND user_id=?
    """, (
        chat_id,
        user["id"]
    ))

    conn.commit()
    conn.close()

    return {"ok": True}


# =========================================================
# GEMINI
# =========================================================

def generate_ai_reply(message, image_data=None):

    if is_creator_question(message):
        return creator_answer()

    if not GOOGLE_API_KEY:
        return (
            "Gemini API key configure ಆಗಿಲ್ಲ. "
            "Render/local environmentನಲ್ಲಿ "
            "GOOGLE_API_KEY ಅಥವಾ GEMINI_API_KEY set ಮಾಡಿ."
        )

    try:

        genai.configure(
            api_key=GOOGLE_API_KEY
        )

        model = genai.GenerativeModel(
            GEMINI_MODEL
        )

        system_instruction = """
You are Nirale AI.

You were created by Nagesh Nirale.

Answer the user's question accurately and helpfully.

Important:
- Reply in the language used by the user whenever possible.
- Support Kannada, English, Hindi, Telugu, Tamil,
  Malayalam, Marathi, Bengali, Gujarati, Punjabi,
  Urdu and other commonly supported languages.
- If the user asks for code, provide clean code.
- Explain code clearly when useful.
- Use Markdown.
- Put programming code inside fenced code blocks.
- Do not claim that you performed an action you did not perform.
"""

        prompt = (
            system_instruction
            + "\n\nUSER:\n"
            + message
        )

        contents = [prompt]

        # Optional image input
        if image_data:

            try:
                if "," in image_data:
                    header, encoded = image_data.split(
                        ",",
                        1
                    )
                else:
                    header = ""
                    encoded = image_data

                raw = base64.b64decode(
                    encoded
                )

                mime = "image/jpeg"

                if "image/png" in header:
                    mime = "image/png"
                elif "image/webp" in header:
                    mime = "image/webp"

                contents.append({
                    "mime_type": mime,
                    "data": raw
                })

            except Exception:
                pass

        response = model.generate_content(
            contents
        )

        if getattr(response, "text", None):
            return response.text

        return "ಕ್ಷಮಿಸಿ, ಉತ್ತರ ಸಿಗಲಿಲ್ಲ."

    except Exception as e:

        return (
            "AI response error: "
            + str(e)
        )


# =========================================================
# CHAT
# =========================================================

@app.post("/api/chat")
async def api_chat(
    data: ChatRequest,
    request: Request
):

    user = require_user(request)

    message = data.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message required"
        )

    conn = db()

    chat_id = data.chat_id

    if chat_id:

        chat = conn.execute("""
            SELECT id
            FROM chats
            WHERE id=? AND user_id=?
        """, (
            chat_id,
            user["id"]
        )).fetchone()

        if not chat:
            conn.close()

            raise HTTPException(
                status_code=404,
                detail="Chat not found"
            )

    else:

        title = message[:60]

        cursor = conn.execute("""
            INSERT INTO chats(
                user_id,
                title,
                created_at,
                updated_at
            )
            VALUES(?,?,?,?)
        """, (
            user["id"],
            title,
            now(),
            now()
        ))

        chat_id = cursor.lastrowid

    conn.execute("""
        INSERT INTO messages(
            chat_id,
            user_id,
            role,
            content,
            created_at
        )
        VALUES(?,?,?,?,?)
    """, (
        chat_id,
        user["id"],
        "user",
        message,
        now()
    ))

    conn.execute("""
        INSERT INTO usage(
            user_id,
            chat_id,
            question,
            created_at
        )
        VALUES(?,?,?,?)
    """, (
        user["id"],
        chat_id,
        message,
        now()
    ))

    conn.execute("""
        UPDATE chats
        SET updated_at=?
        WHERE id=?
    """, (
        now(),
        chat_id
    ))

    conn.commit()
    conn.close()

    reply = generate_ai_reply(
        message,
        data.image_data
    )

    conn = db()

    conn.execute("""
        INSERT INTO messages(
            chat_id,
            user_id,
            role,
            content,
            created_at
        )
        VALUES(?,?,?,?,?)
    """, (
        chat_id,
        user["id"],
        "assistant",
        reply,
        now()
    ))

    conn.execute("""
        UPDATE chats
        SET updated_at=?
        WHERE id=?
    """, (
        now(),
        chat_id
    ))

    conn.execute("""
        UPDATE users
        SET last_active=?
        WHERE id=?
    """, (
        now(),
        user["id"]
    ))

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "chat_id": chat_id,
        "reply": reply
    }


# =========================================================
# ACCOUNT
# =========================================================

@app.get("/api/account")
async def account(request: Request):

    user = require_user(request)

    conn = db()

    count = conn.execute("""
        SELECT COUNT(*)
        FROM usage
        WHERE user_id=?
    """, (
        user["id"],
    )).fetchone()[0]

    chat_count = conn.execute("""
        SELECT COUNT(*)
        FROM chats
        WHERE user_id=?
    """, (
        user["id"],
    )).fetchone()[0]

    conn.close()

    return {
        "email": user["email"],
        "plan": user["plan"],
        "messages": count,
        "chats": chat_count,
        "created_at": user["created_at"],
        "last_active": user["last_active"]
    }


# =========================================================
# UPGRADE
# =========================================================

PLANS = {
    "Free": {
        "price": 0,
        "description": "Basic access"
    },
    "Plus": {
        "price": 499,
        "description": "More AI usage"
    },
    "Pro": {
        "price": 999,
        "description": "Higher usage and priority"
    }
}


@app.get("/api/plans")
async def plans():
    return PLANS


@app.post("/api/upgrade")
async def upgrade(
    data: PlanRequest,
    request: Request
):

    user = require_user(request)

    plan = data.plan

    if plan not in PLANS:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan"
        )

    if plan == "Free":

        conn = db()

        conn.execute(
            "UPDATE users SET plan=? WHERE id=?",
            ("Free", user["id"])
        )

        conn.commit()
        conn.close()

        return {
            "ok": True,
            "plan": "Free"
        }

    # Payment gateway intentionally not faked.
    return {
        "ok": False,
        "payment_required": True,
        "plan": plan,
        "price": PLANS[plan]["price"],
        "message": (
            "Payment gateway configuration is required "
            "before activating a paid plan."
        )
    }


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def is_owner(user):

    if not user:
        return False

    if not OWNER_EMAIL:
        return False

    return user["email"].lower() == OWNER_EMAIL


@app.get("/api/admin/users")
async def admin_users(request: Request):

    user = require_user(request)

    if not is_owner(user):
        raise HTTPException(
            status_code=403,
            detail="Owner access required"
        )

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

    return [
        dict(x)
        for x in users
    ]


@app.get("/api/admin/activity")
async def admin_activity(
    request: Request
):

    user = require_user(request)

    if not is_owner(user):
        raise HTTPException(
            status_code=403,
            detail="Owner access required"
        )

    conn = db()

    rows = conn.execute("""
        SELECT
            usage.id,
            users.email,
            users.plan,
            usage.question,
            usage.created_at
        FROM usage
        JOIN users
        ON users.id = usage.user_id
        ORDER BY usage.id DESC
        LIMIT 500
    """).fetchall()

    conn.close()

    return [
        dict(x)
        for x in rows
    ]


@app.get("/api/admin/stats")
async def admin_stats(
    request: Request
):

    user = require_user(request)

    if not is_owner(user):
        raise HTTPException(
            status_code=403,
            detail="Owner access required"
        )

    conn = db()

    users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    messages = conn.execute(
        "SELECT COUNT(*) FROM usage"
    ).fetchone()[0]

    chats = conn.execute(
        "SELECT COUNT(*) FROM chats"
    ).fetchone()[0]

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
 content="width=device-width, initial-scale=1.0"
>

<title>Nirale AI</title>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<script src="https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/lib/common.min.js"></script>

<link
 rel="stylesheet"
 href="https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/styles/github-dark.min.css"
>

<style>

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    background: #ffffff;
    color: #111111;
}

button,
input,
textarea {
    font: inherit;
}

button {
    cursor: pointer;
}

#app {
    display: flex;
    width: 100%;
    height: 100vh;
    overflow: hidden;
}


/* =====================================================
   SIDEBAR
   ===================================================== */

#sidebar {
    width: 270px;
    background: #f7f7f8;
    border-right: 1px solid #e5e5e5;
    display: flex;
    flex-direction: column;
    transition: transform .25s ease;
    z-index: 50;
}

.sidebar-top {
    padding: 14px;
}

.brand {
    font-size: 21px;
    font-weight: 800;
    margin-bottom: 14px;
}

.new-chat {
    width: 100%;
    border: 1px solid #ddd;
    background: white;
    border-radius: 10px;
    padding: 11px;
    text-align: left;
    font-weight: 600;
}

.side-item {
    padding: 11px 14px;
    margin: 4px 10px;
    border-radius: 9px;
    cursor: pointer;
}

.side-item:hover {
    background: #eaeaea;
}

.recents-title {
    padding: 16px 14px 7px;
    font-size: 12px;
    color: #777;
    font-weight: 700;
    text-transform: uppercase;
}

#recents {
    overflow-y: auto;
    flex: 1;
}

.recent-chat {
    padding: 10px 14px;
    margin: 2px 8px;
    border-radius: 8px;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.recent-chat:hover {
    background: #e7e7e7;
}

.account-area {
    border-top: 1px solid #ddd;
    padding: 12px;
}

.account-button {
    width: 100%;
    border: 0;
    background: transparent;
    text-align: left;
    padding: 9px;
    border-radius: 8px;
}

.account-button:hover {
    background: #e8e8e8;
}


/* =====================================================
   MAIN
   ===================================================== */

#main {
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
    border: 0;
    background: transparent;
    font-size: 24px;
}

.header-title {
    font-weight: 750;
    flex: 1;
}

.upgrade-btn {
    border: 0;
    border-radius: 9px;
    padding: 8px 13px;
    background: #111;
    color: white;
}


/* =====================================================
   CHAT
   ===================================================== */

#chatbox {
    flex: 1;
    overflow-y: auto;
    padding: 25px max(16px, calc((100% - 900px) / 2));
}

.welcome {
    text-align: center;
    padding-top: 16vh;
}

.welcome h1 {
    font-size: 30px;
}

.welcome p {
    color: #777;
}

.message {
    display: flex;
    margin: 18px 0;
}

.message.user {
    justify-content: flex-end;
}

.message-inner {
    max-width: 82%;
    line-height: 1.6;
}

.message.user .message-inner {
    background: #f0f0f0;
    border-radius: 16px;
    padding: 10px 14px;
}

.message.bot .message-inner {
    width: 100%;
}

.message img {
    max-width: 320px;
    max-height: 320px;
    border-radius: 12px;
    margin-top: 8px;
}

.thinking {
    color: #777;
    font-size: 14px;
    animation: pulse 1.2s infinite;
}

@keyframes pulse {
    50% {
        opacity: .35;
    }
}


/* =====================================================
   MARKDOWN / CODE
   ===================================================== */

.message-inner pre {
    position: relative;
    background: #111;
    color: #fff;
    padding: 14px;
    border-radius: 10px;
    overflow-x: auto;
}

.code-wrap {
    position: relative;
    margin: 12px 0;
}

.code-actions {
    position: absolute;
    top: 7px;
    right: 7px;
    display: flex;
    gap: 5px;
}

.code-actions button {
    border: 0;
    background: #333;
    color: white;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}

.message-inner code {
    font-family:
        "SFMono-Regular",
        Consolas,
        monospace;
}


/* =====================================================
   COMPOSER
   ===================================================== */

.composer-area {
    padding: 10px 16px 15px;
    border-top: 1px solid #eee;
}

.composer {
    max-width: 900px;
    margin: auto;
    border: 1px solid #ccc;
    border-radius: 18px;
    display: flex;
    align-items: flex-end;
    padding: 7px;
    background: white;
    box-shadow: 0 2px 12px rgba(0,0,0,.05);
}

.composer textarea {
    flex: 1;
    border: 0;
    outline: 0;
    resize: none;
    min-height: 44px;
    max-height: 150px;
    padding: 11px;
}

.icon-btn {
    width: 40px;
    height: 40px;
    border: 0;
    background: transparent;
    border-radius: 10px;
}

.icon-btn:hover {
    background: #eee;
}

.mic-btn.listening {
    background: #ff4444;
    color: white;
}

.send-btn {
    background: #111;
    color: white;
    border-radius: 11px;
}


/* =====================================================
   PLUS MENU
   ===================================================== */

.plus-menu {
    position: absolute;
    bottom: 75px;
    left: 15px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 13px;
    box-shadow: 0 8px 30px rgba(0,0,0,.15);
    padding: 7px;
    display: none;
    min-width: 190px;
    z-index: 100;
}

.plus-menu button {
    width: 100%;
    border: 0;
    background: white;
    padding: 11px;
    text-align: left;
    border-radius: 8px;
}

.plus-menu button:hover {
    background: #f0f0f0;
}


/* =====================================================
   AUTH
   ===================================================== */

#auth-screen {
    position: fixed;
    inset: 0;
    background: white;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

.auth-card {
    width: 100%;
    max-width: 420px;
    border: 1px solid #ddd;
    border-radius: 18px;
    padding: 30px;
    box-shadow: 0 10px 50px rgba(0,0,0,.08);
}

.auth-logo {
    font-size: 27px;
    font-weight: 800;
    margin-bottom: 8px;
}

.auth-sub {
    color: #777;
    margin-bottom: 24px;
}

.auth-card input {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 9px;
    margin-bottom: 12px;
    outline: none;
}

.auth-submit {
    width: 100%;
    border: 0;
    padding: 12px;
    border-radius: 10px;
    background: #111;
    color: white;
    font-weight: 700;
}

.auth-switch {
    margin-top: 18px;
    text-align: center;
    color: #666;
}

.auth-switch button {
    border: 0;
    background: transparent;
    font-weight: 700;
    text-decoration: underline;
}

.auth-error {
    color: #d00;
    margin-bottom: 10px;
    min-height: 20px;
}


/* =====================================================
   MODAL
   ===================================================== */

.modal {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.45);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 200;
    padding: 15px;
}

.modal-card {
    background: white;
    width: 100%;
    max-width: 700px;
    max-height: 90vh;
    overflow-y: auto;
    border-radius: 17px;
    padding: 25px;
}

.close {
    float: right;
    border: 0;
    background: transparent;
    font-size: 22px;
}

.plan-grid {
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
    gap: 12px;
}

.plan {
    border: 1px solid #ddd;
    border-radius: 12px;
    padding: 18px;
}

.plan button {
    width: 100%;
    padding: 9px;
    border: 0;
    background: #111;
    color: white;
    border-radius: 8px;
}


/* =====================================================
   MOBILE
   ===================================================== */

@media(max-width:700px) {

    #sidebar {
        position: fixed;
        left: 0;
        top: 0;
        bottom: 0;
        transform: translateX(-100%);
    }

    #sidebar.open {
        transform: translateX(0);
    }

    .message-inner {
        max-width: 92%;
    }

    .header {
        padding: 0 10px;
    }

    .upgrade-btn {
        padding: 7px 9px;
        font-size: 12px;
    }

    .plan-grid {
        grid-template-columns: 1fr;
    }

    #chatbox {
        padding: 18px 12px;
    }

    .composer-area {
        padding: 7px;
    }

}

</style>
</head>

<body>


<!-- =====================================================
     AUTH SCREEN
     ===================================================== -->

<div id="auth-screen">

    <div class="auth-card">

        <div class="auth-logo">
            ✨ Nirale AI
        </div>

        <div class="auth-sub">
            Your AI assistant
        </div>

        <div
            id="auth-error"
            class="auth-error"
        ></div>

        <input
            id="auth-email"
            type="email"
            placeholder="Email"
            autocomplete="email"
        >

        <input
            id="auth-password"
            type="password"
            placeholder="Password"
            autocomplete="current-password"
        >

        <button
            class="auth-submit"
            onclick="submitAuth()"
        >
            Login
        </button>

        <div class="auth-switch">

            <span id="auth-switch-text">
                Don't have an account?
            </span>

            <button
                onclick="toggleAuthMode()"
                id="auth-switch-btn"
            >
                Create account
            </button>

        </div>

    </div>

</div>


<!-- =====================================================
     APP
     ===================================================== -->

<div id="app">

    <aside id="sidebar">

        <div class="sidebar-top">

            <div class="brand">
                ✨ Nirale AI
            </div>

            <button
                class="new-chat"
                onclick="newChat()"
            >
                ＋ New Chat
            </button>

        </div>

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
            class="side-item"
            onclick="openAdmin()"
            id="admin-menu"
            style="display:none"
        >
            📊 Admin Dashboard
        </div>

        <div class="recents-title">
            Recents
        </div>

        <div id="recents"></div>

        <div class="account-area">

            <button
                class="account-button"
                onclick="openAccount()"
                id="account-bottom"
            >
                👤 Account
            </button>

        </div>

    </aside>


    <main id="main">

        <header class="header">

            <button
                class="menu-btn"
                onclick="toggleSidebar()"
            >
                ☰
            </button>

            <div class="header-title">
                Nirale AI
            </div>

            <button
                class="upgrade-btn"
                onclick="openUpgrade()"
            >
                ⭐ Upgrade
            </button>

        </header>


        <section id="chatbox">

            <div class="welcome">

                <h1>
                    How can I help you?
                </h1>

                <p>
                    Ask anything to Nirale AI
                </p>

            </div>

        </section>


        <div class="composer-area">

            <div
                id="plus-menu"
                class="plus-menu"
            >

                <button onclick="chooseFile()">
                    📎 Attach files
                </button>

                <button onclick="chooseCamera()">
                    📷 Camera
                </button>

                <button onclick="choosePhoto()">
                    🖼️ Photos / Gallery
                </button>

                <button onclick="webSearch()">
                    🌐 Web search
                </button>

                <button onclick="createImage()">
                    🎨 Create image
                </button>

                <button onclick="openMap()">
                    🗺️ Map
                </button>

            </div>


            <div class="composer">

                <button
                    class="icon-btn"
                    onclick="togglePlus()"
                >
                    ＋
                </button>

                <input
                    type="file"
                    id="file-input"
                    hidden
                    onchange="handleFile(event)"
                >

                <input
                    type="file"
                    id="camera-input"
                    accept="image/*"
                    capture="environment"
                    hidden
                    onchange="handleImage(event)"
                >

                <input
                    type="file"
                    id="photo-input"
                    accept="image/*"
                    hidden
                    onchange="handleImage(event)"
                >

                <textarea
                    id="message-input"
                    placeholder="Message Nirale AI..."
                    rows="1"
                    onkeydown="handleEnter(event)"
                ></textarea>

                <button
                    id="micBtn"
                    class="icon-btn"
                    onclick="startVoice()"
                    title="Voice"
                >
                    🎤
                </button>

                <button
                    class="icon-btn send-btn"
                    onclick="sendMessage()"
                    title="Send"
                >
                    ➤
                </button>

            </div>

        </div>

    </main>

</div>


<!-- =====================================================
     ACCOUNT MODAL
     ===================================================== -->

<div
    id="account-modal"
    class="modal"
>

    <div class="modal-card">

        <button
            class="close"
            onclick="closeModal('account-modal')"
        >
            ×
        </button>

        <h2>Account</h2>

        <div id="account-content">
            Loading...
        </div>

        <br>

        <button
            onclick="logout()"
        >
            Log out
        </button>

    </div>

</div>


<!-- =====================================================
     UPGRADE MODAL
     ===================================================== -->

<div
    id="upgrade-modal"
    class="modal"
>

    <div class="modal-card">

        <button
            class="close"
            onclick="closeModal('upgrade-modal')"
        >
            ×
        </button>

        <h2>⭐ Upgrade</h2>

        <div class="plan-grid">

            <div class="plan">

                <h3>Free</h3>

                <h2>₹0</h2>

                <p>
                    Basic access
                </p>

                <button
                    onclick="selectPlan('Free')"
                >
                    Current / Free
                </button>

            </div>


            <div class="plan">

                <h3>Plus</h3>

                <h2>₹499</h2>

                <p>
                    More AI usage
                </p>

                <button
                    onclick="selectPlan('Plus')"
                >
                    Upgrade
                </button>

            </div>


            <div class="plan">

                <h3>Pro</h3>

                <h2>₹999</h2>

                <p>
                    Higher usage
                </p>

                <button
                    onclick="selectPlan('Pro')"
                >
                    Upgrade
                </button>

            </div>

        </div>

        <p id="payment-message"></p>

    </div>

</div>


<!-- =====================================================
     ADMIN MODAL
     ===================================================== -->

<div
    id="admin-modal"
    class="modal"
>

    <div class="modal-card">

        <button
            class="close"
            onclick="closeModal('admin-modal')"
        >
            ×
        </button>

        <h2>📊 Admin Dashboard</h2>

        <div id="admin-stats">
            Loading...
        </div>

        <h3>Users</h3>

        <div id="admin-users"></div>

        <h3>Recent activity</h3>

        <div id="admin-activity"></div>

    </div>

</div>


<script>

let authMode = "login";

let currentChatId = null;

let currentImage = null;


/* =====================================================
   AUTH
   ===================================================== */

async function checkAuth() {

    try {

        const res =
            await fetch("/api/me");

        const data =
            await res.json();

        if (data.logged_in) {

            document
                .getElementById("auth-screen")
                .style.display = "none";

            document
                .getElementById("account-bottom")
                .textContent =
                "👤 " + data.email;

            loadRecents();

        } else {

            document
                .getElementById("auth-screen")
                .style.display = "flex";

        }

    } catch(e) {

        console.error(e);

    }

}


function toggleAuthMode() {

    authMode =
        authMode === "login"
            ? "signup"
            : "login";

    const button =
        document.getElementById(
            "auth-switch-btn"
        );

    const text =
        document.getElementById(
            "auth-switch-text"
        );

    const submit =
        document.querySelector(
            ".auth-submit"
        );

    if (authMode === "signup") {

        submit.textContent =
            "Create account";

        text.textContent =
            "Already have an account?";

        button.textContent =
            "Login";

    } else {

        submit.textContent =
            "Login";

        text.textContent =
            "Don't have an account?";

        button.textContent =
            "Create account";

    }

}


async function submitAuth() {

    const email =
        document
            .getElementById("auth-email")
            .value
            .trim();

    const password =
        document
            .getElementById("auth-password")
            .value;

    const error =
        document
            .getElementById("auth-error");

    error.textContent = "";

    if (!email || !password) {

        error.textContent =
            "Email and password required.";

        return;

    }

    const endpoint =
        authMode === "login"
            ? "/api/login"
            : "/api/signup";

    try {

        const res =
            await fetch(
                endpoint,
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

            error.textContent =
                data.detail ||
                "Authentication failed.";

            return;

        }

        document
            .getElementById("auth-screen")
            .style.display = "none";

        document
            .getElementById("auth-password")
            .value = "";

        loadRecents();

        checkOwner();

    } catch(e) {

        error.textContent =
            "Connection error.";

    }

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


function togglePlus() {

    const menu =
        document.getElementById(
            "plus-menu"
        );

    menu.style.display =
        menu.style.display === "block"
            ? "none"
            : "block";

}


function closePlus() {

    document
        .getElementById("plus-menu")
        .style.display = "none";

}


/* =====================================================
   CHAT
   ===================================================== */

function newChat() {

    currentChatId = null;

    currentImage = null;

    document
        .getElementById("chatbox")
        .innerHTML = `
            <div class="welcome">
                <h1>How can I help you?</h1>
                <p>Ask anything to Nirale AI</p>
            </div>
        `;

    document
        .getElementById("message-input")
        .value = "";

}


function handleEnter(event) {

    if (
        event.key === "Enter"
        &&
        !event.shiftKey
    ) {

        event.preventDefault();

        sendMessage();

    }

}


function addMessage(
    role,
    content
) {

    const chat =
        document.getElementById(
            "chatbox"
        );

    const div =
        document.createElement("div");

    div.className =
        "message " + role;

    const inner =
        document.createElement("div");

    inner.className =
        "message-inner";

    if (role === "bot") {

        inner.innerHTML =
            marked.parse(
                content || ""
            );

        addCodeButtons(inner);

        inner
            .querySelectorAll("pre code")
            .forEach(
                block => {
                    hljs.highlightElement(
                        block
                    );
                }
            );

    } else {

        inner.textContent =
            content;

    }

    div.appendChild(inner);

    chat.appendChild(div);

    chat.scrollTop =
        chat.scrollHeight;

}


function showThinking() {

    const chat =
        document.getElementById(
            "chatbox"
        );

    const div =
        document.createElement("div");

    div.id =
        "thinking-message";

    div.className =
        "message bot";

    div.innerHTML = `
        <div class="message-inner thinking">
            ಯೋಚಿಸುತ್ತಿದೆ...
        </div>
    `;

    chat.appendChild(div);

    chat.scrollTop =
        chat.scrollHeight;

}


function removeThinking() {

    const el =
        document.getElementById(
            "thinking-message"
        );

    if (el) {
        el.remove();
    }

}


async function sendMessage() {

    const input =
        document.getElementById(
            "message-input"
        );

    const message =
        input.value.trim();

    if (!message) {
        return;
    }

    closePlus();

    addMessage(
        "user",
        message
    );

    input.value = "";

    showThinking();

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
                        message,
                        chat_id:
                            currentChatId,
                        image_data:
                            currentImage
                    })
                }
            );

        const data =
            await res.json();

        removeThinking();

        if (res.status === 401) {

            document
                .getElementById("auth-screen")
                .style.display = "flex";

            return;

        }

        if (!res.ok) {

            addMessage(
                "bot",
                "Error: " +
                (
                    data.detail ||
                    "Request failed"
                )
            );

            return;

        }

        currentChatId =
            data.chat_id;

        addMessage(
            "bot",
            data.reply
        );

        currentImage = null;

        loadRecents();

    } catch(e) {

        removeThinking();

        addMessage(
            "bot",
            "Connection error."
        );

    }

}


/* =====================================================
   HISTORY
   ===================================================== */

async function loadRecents() {

    const res =
        await fetch("/api/chats");

    if (!res.ok) {
        return;
    }

    const chats =
        await res.json();

    const box =
        document.getElementById(
            "recents"
        );

    box.innerHTML = "";

    chats.forEach(chat => {

        const div =
            document.createElement("div");

        div.className =
            "recent-chat";

        div.textContent =
            chat.title || "New Chat";

        div.onclick =
            () => openChat(chat.id);

        box.appendChild(div);

    });

}


async function openChat(id) {

    const res =
        await fetch(
            "/api/chats/" + id
        );

    if (!res.ok) {
        return;
    }

    const data =
        await res.json();

    currentChatId =
        data.id;

    const chatbox =
        document.getElementById(
            "chatbox"
        );

    chatbox.innerHTML = "";

    data.messages.forEach(
        msg => {

            addMessage(
                msg.role === "user"
                    ? "user"
                    : "bot",
                msg.content
            );

        }
    );

    if (
        window.innerWidth <= 700
    ) {
        toggleSidebar();
    }

}


/* =====================================================
   CODE BUTTONS
   ===================================================== */

function addCodeButtons(container) {

    container
        .querySelectorAll("pre")
        .forEach(pre => {

            const code =
                pre.querySelector("code");

            if (!code) {
                return;
            }

            const wrap =
                document.createElement(
                    "div"
                );

            wrap.className =
                "code-wrap";

            pre.parentNode.insertBefore(
                wrap,
                pre
            );

            wrap.appendChild(pre);

            const actions =
                document.createElement(
                    "div"
                );

            actions.className =
                "code-actions";

            const copy =
                document.createElement(
                    "button"
                );

            copy.textContent =
                "Copy";

            copy.onclick =
                async () => {

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

                };

            const download =
                document.createElement(
                    "button"
                );

            download.textContent =
                "Download";

            download.onclick =
                () => {

                    const blob =
                        new Blob(
                            [
                                code.innerText
                            ],
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
                        document.createElement(
                            "a"
                        );

                    a.href = url;

                    a.download =
                        "nirale-code.txt";

                    a.click();

                    URL.revokeObjectURL(
                        url
                    );

                };

            actions.appendChild(copy);
            actions.appendChild(download);

            wrap.appendChild(actions);

        });

}


/* =====================================================
   VOICE
   ===================================================== */

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

    const recognition =
        new SpeechRecognition();

    recognition.continuous = false;

    recognition.interimResults = false;

    recognition.lang = "kn-IN";

    const mic =
        document.getElementById(
            "micBtn"
        );

    mic.classList.add(
        "listening"
    );

    recognition.start();

    recognition.onresult =
        event => {

            const text =
                event
                    .results[0][0]
                    .transcript;

            document
                .getElementById(
                    "message-input"
                )
                .value += text;

        };

    recognition.onerror =
        () => {

            mic.classList.remove(
                "listening"
            );

        };

    recognition.onend =
        () => {

            mic.classList.remove(
                "listening"
            );

        };

}


/* =====================================================
   FILE / CAMERA / PHOTO
   ===================================================== */

function chooseFile() {

    closePlus();

    document
        .getElementById("file-input")
        .click();

}


function chooseCamera() {

    closePlus();

    document
        .getElementById("camera-input")
        .click();

}


function choosePhoto() {

    closePlus();

    document
        .getElementById("photo-input")
        .click();

}


function handleFile(event) {

    const file =
        event.target.files[0];

    if (!file) {
        return;
    }

    document
        .getElementById("message-input")
        .value +=
        "\n[Attached file: " +
        file.name +
        "]";

}


function handleImage(event) {

    const file =
        event.target.files[0];

    if (!file) {
        return;
    }

    const reader =
        new FileReader();

    reader.onload =
        () => {

            currentImage =
                reader.result;

            const input =
                document
                    .getElementById(
                        "message-input"
                    );

            input.value +=
                "\n[Image attached]";

        };

    reader.readAsDataURL(
        file
    );

}


/* =====================================================
   WEB / IMAGE / MAP
   ===================================================== */

function webSearch() {

    closePlus();

    const q =
        prompt(
            "What do you want to search?"
        );

    if (!q) {
        return;
    }

    window.open(
        "https://www.google.com/search?q="
        +
        encodeURIComponent(q),
        "_blank"
    );

}


function createImage() {

    closePlus();

    addMessage(
        "bot",
        "🎨 Image creation option selected. Connect an image-generation API to generate images directly from Nirale AI."
    );

}


function openMap() {

    closePlus();

    const q =
        prompt(
            "Enter location:"
        );

    if (!q) {
        return;
    }

    window.open(
        "https://www.google.com/maps/search/"
        +
        encodeURIComponent(q),
        "_blank"
    );

}


/* =====================================================
   ACCOUNT
   ===================================================== */

async function openAccount() {

    const res =
        await fetch(
            "/api/account"
        );

    if (!res.ok) {
        return;
    }

    const data =
        await res.json();

    document
        .getElementById(
            "account-content"
        )
        .innerHTML = `
            <p><b>Email:</b> ${escapeHtml(data.email)}</p>
            <p><b>Plan:</b> ${escapeHtml(data.plan)}</p>
            <p><b>Messages:</b> ${data.messages}</p>
            <p><b>Chats:</b> ${data.chats}</p>
        `;

    document
        .getElementById(
            "account-modal"
        )
        .style.display = "flex";

}


function openUpgrade() {

    document
        .getElementById(
            "upgrade-modal"
        )
        .style.display = "flex";

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

    document
        .getElementById(
            "payment-message"
        )
        .textContent =
        data.message ||
        (
            data.ok
                ? "Plan updated."
                : "Payment required."
        );

}


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
   ADMIN
   ===================================================== */

async function checkOwner() {

    const res =
        await fetch(
            "/api/me"
        );

    if (!res.ok) {
        return;
    }

    const user =
        await res.json();

    /*
       OWNER_EMAIL is checked securely
       on the server.
       UI visibility alone is not security.
    */

    if (
        user.logged_in &&
        user.email
    ) {

        try {

            const test =
                await fetch(
                    "/api/admin/stats"
                );

            if (test.ok) {

                document
                    .getElementById(
                        "admin-menu"
                    )
                    .style.display =
                    "block";

            }

        } catch(e) {}

    }

}


async function openAdmin() {

    const statsRes =
        await fetch(
            "/api/admin/stats"
        );

    if (!statsRes.ok) {

        alert(
            "Owner access required."
        );

        return;

    }

    const stats =
        await statsRes.json();

    document
        .getElementById(
            "admin-stats"
        )
        .innerHTML = `
            <p>Users: <b>${stats.users}</b></p>
            <p>Messages: <b>${stats.messages}</b></p>
            <p>Chats: <b>${stats.chats}</b></p>
        `;

    const usersRes =
        await fetch(
            "/api/admin/users"
        );

    const users =
        await usersRes.json();

    document
        .getElementById(
            "admin-users"
        )
        .innerHTML =
        users.map(
            u => `
                <div style="
                    border-bottom:1px solid #ddd;
                    padding:8px 0;
                ">
                    <b>${escapeHtml(u.email)}</b>
                    <br>
                    Plan: ${escapeHtml(u.plan)}
                    <br>
                    Created:
                    ${escapeHtml(u.created_at)}
                    <br>
                    Last active:
                    ${escapeHtml(
                        u.last_active || "-"
                    )}
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
        .getElementById(
            "admin-activity"
        )
        .innerHTML =
        activity.map(
            x => `
                <div style="
                    border-bottom:1px solid #ddd;
                    padding:8px 0;
                ">
                    <b>${escapeHtml(x.email)}</b>
                    <br>
                    ${escapeHtml(x.question)}
                    <br>
                    <small>
                        ${escapeHtml(x.created_at)}
                    </small>
                </div>
            `
        ).join("");

    document
        .getElementById(
            "admin-modal"
        )
        .style.display = "flex";

}


function closeModal(id) {

    document
        .getElementById(id)
        .style.display = "none";

}


/* =====================================================
   SECURITY HELPER
   ===================================================== */

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


/* =====================================================
   START
   ===================================================== */

checkAuth();

checkOwner();

</script>

</body>
</html>
"""


# =========================================================
# ROOT
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def home():

    return HTMLResponse(
        HTML
    )
