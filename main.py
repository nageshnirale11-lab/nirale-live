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

API_KEY = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
)

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

OWNER_EMAIL = os.getenv(
    "OWNER_EMAIL",
    ""
).strip().lower()

if API_KEY:
    genai.configure(api_key=API_KEY)

app = FastAPI(title=APP_NAME)


# ============================================================
# DATABASE
# ============================================================

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
            title TEXT NOT NULL,
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
# PASSWORD
# ============================================================

def hash_password(password, salt=None):

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


def verify_password(
    password,
    password_hash,
    salt
):

    new_hash, _ = hash_password(
        password,
        salt
    )

    return secrets.compare_digest(
        new_hash,
        password_hash
    )


# ============================================================
# SESSION
# ============================================================

def current_user(request: Request):

    token = request.cookies.get(
        "nirale_session"
    )

    if not token:
        return None

    conn = db()

    user = conn.execute("""
        SELECT users.*
        FROM users
        JOIN sessions
        ON sessions.user_id = users.id
        WHERE sessions.token = ?
    """, (token,)).fetchone()

    conn.close()

    return user


def update_last_active(user_id):

    conn = db()

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
# MODELS
# ============================================================

class AuthData(BaseModel):
    email: str
    password: str


class ChatData(BaseModel):
    message: str = ""
    chat_id: Optional[int] = None
    image_data: Optional[str] = None


class UpgradeData(BaseModel):
    plan: str


# ============================================================
# CREATOR
# ============================================================

def creator_question(text):

    t = text.lower().strip()

    words = [
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
        "ನಿನ್ನನ್ನು ಯಾರು ಅಭಿವೃದ್ಧಿಪಡಿಸಿದರು"
    ]

    return any(
        word in t
        for word in words
    )


CREATOR_REPLY = (
    "ನನ್ನನ್ನು Nagesh Nirale ಅವರು ರಚಿಸಿದ್ದಾರೆ."
)


# ============================================================
# LANGUAGE
# ============================================================

def thinking_text(message):

    if re.search(
        r"[\u0C80-\u0CFF]",
        message
    ):
        return "ಯೋಚಿಸುತ್ತಿದೆ..."

    if re.search(
        r"[\u0900-\u097F]",
        message
    ):
        return "सोच रहा हूँ..."

    if re.search(
        r"[\u0C00-\u0C7F]",
        message
    ):
        return "ఆలోచిస్తోంది..."

    if re.search(
        r"[\u0B80-\u0BFF]",
        message
    ):
        return "யோசிக்கிறது..."

    if re.search(
        r"[\u0D00-\u0D7F]",
        message
    ):
        return "ചിന്തിക്കുന്നു..."

    if re.search(
        r"[\u0C00-\u0C7F]",
        message
    ):
        return "ಆಲೋಚಿಸುತ್ತಿದೆ..."

    return "Thinking..."


# ============================================================
# GEMINI
# ============================================================

SYSTEM_PROMPT = """
You are Nirale AI.

You are a helpful multilingual AI assistant.

IMPORTANT LANGUAGE RULE:

Reply in the SAME LANGUAGE that the user uses.

If the user writes Kannada, reply in Kannada.

If the user writes English, reply in English.

If the user writes Hindi, reply in Hindi.

If the user writes Telugu, reply in Telugu.

If the user writes Tamil, reply in Tamil.

If the user writes Malayalam, reply in Malayalam.

If the user mixes languages, naturally follow the language
used by the user.

Do not unnecessarily change the user's language.

You can answer questions about programming, cybersecurity,
Linux, technology, education, general knowledge and other
normal topics.

Use Markdown when useful.

Put programming code inside fenced code blocks.

Never reveal passwords, API keys, session tokens or secrets.

Never claim that a real-world action was completed when it
was not completed.
"""


def generate_reply(
    message,
    image_data=None
):

    if creator_question(message):
        return CREATOR_REPLY

    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY or GEMINI_API_KEY is missing."
        )

    model = genai.GenerativeModel(
        MODEL_NAME,
        system_instruction=SYSTEM_PROMPT
    )

    contents = []

    if message:
        contents.append(message)

    if image_data:

        try:

            if "," in image_data:
                image_data = image_data.split(
                    ",",
                    1
                )[1]

            image_bytes = base64.b64decode(
                image_data
            )

            contents.append({
                "mime_type": "image/jpeg",
                "data": image_bytes
            })

        except Exception:
            pass

    response = model.generate_content(
        contents
    )

    text = getattr(
        response,
        "text",
        None
    )

    if not text:
        return "Sorry, answer generate ಆಗಲಿಲ್ಲ."

    return text


# ============================================================
# GUEST COUNTER
# ============================================================

def guest_count(request):

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
async def signup(data: AuthData):

    email = data.email.strip().lower()
    password = data.password

    if not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email
    ):
        raise HTTPException(
            400,
            "Valid email enter madi."
        )

    if len(password) < 6:
        raise HTTPException(
            400,
            "Password minimum 6 characters ಇರಬೇಕು."
        )

    password_hash, salt = hash_password(
        password
    )

    conn = db()

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
            "ಈ email ಈಗಾಗಲೇ registered ಇದೆ."
        )

    conn.close()

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
        max_age=2592000
    )

    response.delete_cookie(
        "nirale_guest_count"
    )

    return response


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/login")
async def login(data: AuthData):

    email = data.email.strip().lower()

    conn = db()

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

    conn = db()

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
        "nirale_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=2592000
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

        conn = db()

        conn.execute(
            "DELETE FROM sessions WHERE token=?",
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
# ME
# ============================================================

@app.get("/api/me")
async def me(request: Request):

    user = current_user(request)

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
    data: ChatData
):

    message = data.message.strip()

    if not message and not data.image_data:
        raise HTTPException(
            400,
            "Message empty ide."
        )

    user = current_user(request)


    # ========================================================
    # GUEST
    # ========================================================

    if not user:

        count = guest_count(request)

        if count >= 4:

            raise HTTPException(
                401,
                "LOGIN_REQUIRED"
            )

        try:

            reply = generate_reply(
                message,
                data.image_data
            )

        except Exception as e:

            raise HTTPException(
                500,
                str(e)
            )

        new_count = count + 1

        response = JSONResponse({
            "ok": True,
            "guest": True,
            "guest_count": new_count,
            "remaining": max(
                0,
                4 - new_count
            ),
            "reply": reply
        })

        response.set_cookie(
            "nirale_guest_count",
            str(new_count),
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=86400
        )

        return response


    # ========================================================
    # LOGGED IN
    # ========================================================

    update_last_active(
        user["id"]
    )

    conn = db()

    chat_id = data.chat_id


    if chat_id:

        found = conn.execute("""
            SELECT *
            FROM chats
            WHERE id=?
            AND user_id=?
        """, (
            chat_id,
            user["id"]
        )).fetchone()

        if not found:

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

        reply = generate_reply(
            message,
            data.image_data
        )

    except Exception as e:

        raise HTTPException(
            500,
            str(e)
        )


    conn = db()

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
        "guest": False,
        "chat_id": chat_id,
        "reply": reply
    }


# ============================================================
# CHAT HISTORY
# ============================================================

@app.get("/api/chats")
async def chats(request: Request):

    user = current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM chats
        WHERE user_id=?
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
async def chat_history(
    chat_id: int,
    request: Request
):

    user = current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    conn = db()

    chat_row = conn.execute("""
        SELECT *
        FROM chats
        WHERE id=?
        AND user_id=?
    """, (
        chat_id,
        user["id"]
    )).fetchone()

    if not chat_row:

        conn.close()

        raise HTTPException(
            404,
            "Chat not found."
        )

    messages = conn.execute("""
        SELECT *
        FROM messages
        WHERE chat_id=?
        ORDER BY id ASC
    """, (
        chat_id,
    )).fetchall()

    conn.close()

    return {
        "chat": dict(chat_row),
        "messages": [
            dict(x)
            for x in messages
        ]
    }


@app.delete("/api/chats/{chat_id}")
async def remove_chat(
    chat_id: int,
    request: Request
):

    user = current_user(request)

    if not user:

        raise HTTPException(
            401,
            "Login madi."
        )

    conn = db()

    conn.execute("""
        DELETE FROM messages
        WHERE chat_id=?
    """, (
        chat_id,
    ))

    conn.execute("""
        DELETE FROM chats
        WHERE id=?
        AND user_id=?
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
async def get_plans():

    return {
        "plans": [
            {
                "name": "Free",
                "price": 0,
                "description": "Basic access"
            },
            {
                "name": "Plus",
                "price": 499,
                "description": "More AI usage"
            },
            {
                "name": "Pro",
                "price": 999,
                "description": "Higher usage"
            }
        ]
    }


@app.post("/api/upgrade")
async def upgrade(
    request: Request,
    data: UpgradeData
):

    user = current_user(request)

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
        "message":
            "Payment gateway connect madbeku."
    }


# ============================================================
# ADMIN
# ============================================================

def require_admin(request: Request):

    user = current_user(request)

    if not user:
        raise HTTPException(
            401,
            "Login madi."
        )

    if not OWNER_EMAIL:
        raise HTTPException(
            403,
            "OWNER_EMAIL not configured."
        )

    if user["email"].lower() != OWNER_EMAIL:
        raise HTTPException(
            403,
            "Admin access denied."
        )

    return user


@app.get("/api/admin/stats")
async def admin_stats(
    request: Request
):

    require_admin(request)

    conn = db()

    users = conn.execute(
        "SELECT COUNT(*) c FROM users"
    ).fetchone()["c"]

    chats = conn.execute(
        "SELECT COUNT(*) c FROM chats"
    ).fetchone()["c"]

    messages = conn.execute(
        "SELECT COUNT(*) c FROM usage"
    ).fetchone()["c"]

    conn.close()

    return {
        "users": users,
        "chats": chats,
        "messages": messages
    }


@app.get("/api/admin/users")
async def admin_users(
    request: Request
):

    require_admin(request)

    conn = db()

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
            dict(x)
            for x in rows
        ]
    }


@app.get("/api/admin/activity")
async def admin_activity(
    request: Request
):

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
        ON users.id=usage.user_id
        ORDER BY usage.id DESC
        LIMIT 200
    """).fetchall()

    conn.close()

    return {
        "activity": [
            dict(x)
            for x in rows
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
content="width=device-width,initial-scale=1.0"
>

<title>✨ Nirale AI</title>


<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>


<link
rel="stylesheet"
href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github-dark.min.css"
>


<script
src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js">
</script>


<style>

/* =========================================================
   RESET
========================================================= */

* {
    box-sizing: border-box;
}

html,
body {
    width: 100%;
    height: 100%;
    margin: 0;
}

body {
    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: #000;

    color: #fff;

    overflow: hidden;
}

button,
input,
textarea {
    font: inherit;
}

button {
    cursor: pointer;
}

.hidden {
    display: none !important;
}


/* =========================================================
   APP
========================================================= */

#app {
    width: 100%;
    height: 100vh;

    display: flex;

    background: #000;
}


/* =========================================================
   SIDEBAR
========================================================= */

.sidebar {
    width: 300px;

    height: 100vh;

    flex-shrink: 0;

    background: #0b0b0b;

    border-right:
        1px solid #292929;

    display: flex;

    flex-direction: column;

    overflow: hidden;

    transition:
        width .2s ease,
        transform .2s ease;
}


.sidebar-header {
    height: 66px;

    display: flex;

    align-items: center;

    padding:
        0 14px;

    gap: 7px;
}


.sidebar-logo {
    flex: 1;

    font-size: 19px;

    font-weight: 700;
}


.sidebar-top-button {
    width: 40px;
    height: 40px;

    border: 0;

    border-radius: 10px;

    color: #fff;

    background: transparent;

    font-size: 22px;
}


.sidebar-top-button:hover {
    background: #222;
}


/* =========================================================
   MENU
========================================================= */

.sidebar-menu {
    padding:
        5px 10px;
}


.menu-item {
    width: 100%;

    min-height: 48px;

    display: flex;

    align-items: center;

    gap: 13px;

    padding:
        9px 12px;

    margin-bottom: 2px;

    border: 0;

    border-radius: 11px;

    background: transparent;

    color: #fff;

    text-align: left;

    font-size: 16px;
}


.menu-item:hover {
    background: #202020;
}


.menu-item.active {
    background: #1f1f1f;
}


.menu-icon {
    width: 26px;

    text-align: center;

    font-size: 20px;
}


.menu-text {
    flex: 1;
}


.menu-plus {
    font-size: 24px;

    color: #aaa;
}


.more-content {
    display: none;
}


.more-content.open {
    display: block;
}


/* =========================================================
   RECENTS
========================================================= */

.recents-header {
    display: flex;

    align-items: center;

    padding:
        18px 15px 7px;

    color: #999;

    font-size: 14px;

    font-weight: 600;
}


.recents-title {
    flex: 1;
}


.small-action {
    border: 0;

    background: transparent;

    color: #aaa;

    font-size: 18px;

    padding: 4px;
}


.small-action:hover {
    color: #fff;
}


.recents {
    flex: 1;

    overflow-y: auto;

    padding:
        0 9px;
}


.recent-row {
    width: 100%;

    display: flex;

    align-items: center;

    gap: 5px;

    border-radius: 9px;

    padding:
        8px 8px;

    color: #eee;

    background: transparent;
}


.recent-row:hover {
    background: #1d1d1d;
}


.recent-title {
    flex: 1;

    min-width: 0;

    white-space: nowrap;

    overflow: hidden;

    text-overflow: ellipsis;

    font-size: 14px;

    text-align: left;
}


.recent-options {
    border: 0;

    background: transparent;

    color: #999;

    font-size: 16px;
}


/* =========================================================
   ACCOUNT
========================================================= */

.sidebar-account {
    border-top:
        1px solid #292929;

    padding: 10px;
}


.account-button {
    width: 100%;

    display: flex;

    align-items: center;

    gap: 10px;

    padding: 8px;

    border: 0;

    border-radius: 10px;

    background: transparent;

    color: #fff;

    text-align: left;
}


.account-button:hover {
    background: #202020;
}


.avatar {
    width: 38px;
    height: 38px;

    flex-shrink: 0;

    display: flex;

    align-items: center;

    justify-content: center;

    border-radius: 50%;

    background: #8c999d;

    font-weight: 700;
}


.account-details {
    min-width: 0;

    flex: 1;
}


.account-name {
    white-space: nowrap;

    overflow: hidden;

    text-overflow: ellipsis;

    font-size: 14px;
}


.account-plan {
    color: #999;

    font-size: 12px;

    margin-top: 2px;
}


/* =========================================================
   MAIN
========================================================= */

.main {
    min-width: 0;

    flex: 1;

    height: 100vh;

    display: flex;

    flex-direction: column;

    background: #000;
}


/* =========================================================
   HEADER
========================================================= */

.header {
    height: 62px;

    flex-shrink: 0;

    display: flex;

    align-items: center;

    gap: 10px;

    padding:
        0 14px;

    border-bottom:
        1px solid #1f1f1f;
}


.mobile-menu {
    display: none;

    border: 0;

    background: transparent;

    color: #fff;

    font-size: 24px;
}


.header-logo {
    font-size: 19px;

    font-weight: 700;
}


.header-space {
    flex: 1;
}


.upgrade {
    border: 0;

    border-radius: 10px;

    padding:
        9px 14px;

    background: #fff;

    color: #000;

    font-weight: 600;
}


.upgrade:hover {
    background: #ddd;
}


/* =========================================================
   CHAT
========================================================= */

.chatbox {
    flex: 1;

    overflow-y: auto;

    padding:
        28px 20px 120px;
}


.welcome {
    max-width: 850px;

    margin:
        110px auto 0;

    text-align: center;
}


.welcome h1 {
    font-size: 34px;

    margin-bottom: 10px;
}


.welcome p {
    color: #888;
}


/* =========================================================
   MESSAGES
========================================================= */

.message {
    max-width: 850px;

    margin:
        0 auto 22px;

    line-height: 1.65;

    word-wrap: break-word;
}


.user-message {
    display: flex;

    justify-content: flex-end;
}


.user-bubble {
    max-width: 78%;

    padding:
        11px 15px;

    border-radius:
        17px;

    background: #2a2a2a;
}


.assistant-message {
    color: #eee;
}


.assistant-message pre {
    position: relative;

    overflow-x: auto;

    padding:
        45px 14px 14px;

    border-radius: 12px;
}


.assistant-message img {
    max-width: 100%;
}


.code-actions {
    position: absolute;

    top: 8px;

    right: 8px;

    display: flex;

    gap: 5px;
}


.code-actions button {
    border: 1px solid #555;

    border-radius: 7px;

    background: #222;

    color: #fff;

    padding:
        5px 8px;

    font-size: 12px;
}


.thinking {
    max-width: 850px;

    margin:
        0 auto 20px;

    color: #888;

    font-size: 14px;
}


/* =========================================================
   FOOTER
========================================================= */

.footer {
    position: relative;

    flex-shrink: 0;

    padding:
        10px 18px 18px;

    background: #000;
}


.input-box {
    max-width: 850px;

    margin: auto;

    display: flex;

    align-items: flex-end;

    gap: 4px;

    padding: 7px;

    border:
        1px solid #404040;

    border-radius: 18px;

    background: #161616;
}


.message-input {
    flex: 1;

    min-height: 42px;

    max-height: 140px;

    resize: none;

    outline: none;

    border: 0;

    background: transparent;

    color: #fff;

    padding:
        10px 8px;
}


.message-input::placeholder {
    color: #777;
}


.icon-button {
    width: 40px;
    height: 40px;

    flex-shrink: 0;

    border: 0;

    border-radius: 10px;

    background: transparent;

    color: #fff;

    font-size: 19px;
}


.icon-button:hover {
    background: #292929;
}


.send-button {
    background: #fff;

    color: #000;

    border-radius: 50%;
}


.mic-listening {
    background: #d22;

    color: #fff;
}


/* =========================================================
   PLUS MENU
========================================================= */

.plus-menu {
    position: absolute;

    left: 18px;

    bottom: 78px;

    width: 245px;

    padding: 8px;

    background: #171717;

    border:
        1px solid #383838;

    border-radius: 14px;

    box-shadow:
        0 15px 45px rgba(0,0,0,.5);

    z-index: 50;
}


.plus-item {
    width: 100%;

    border: 0;

    background: transparent;

    color: #fff;

    text-align: left;

    padding:
        11px 12px;

    border-radius: 9px;
}


.plus-item:hover {
    background: #292929;
}


/* =========================================================
   MODALS
========================================================= */

.modal {
    position: fixed;

    inset: 0;

    z-index: 2000;

    display: flex;

    align-items: center;

    justify-content: center;

    padding: 20px;

    background:
        rgba(0,0,0,.65);
}


.modal-card {
    width: 100%;

    max-width: 520px;

    max-height: 90vh;

    overflow-y: auto;

    padding: 25px;

    border:
        1px solid #333;

    border-radius: 18px;

    background: #171717;

    color: #fff;
}


.close-modal {
    float: right;

    border: 0;

    background: transparent;

    color: #aaa;

    font-size: 25px;
}


.modal-card h2 {
    margin-top: 0;
}


/* =========================================================
   AUTH
========================================================= */

.auth-screen {
    position: fixed;

    inset: 0;

    z-index: 5000;

    display: flex;

    align-items: center;

    justify-content: center;

    padding: 20px;

    background: #000;
}


.auth-card {
    width: 100%;

    max-width: 420px;

    padding: 30px;

    border:
        1px solid #333;

    border-radius: 20px;

    background: #151515;
}


.auth-logo {
    text-align: center;

    font-size: 29px;

    font-weight: 700;

    margin-bottom: 8px;
}


.auth-description {
    text-align: center;

    color: #999;

    margin-bottom: 24px;
}


.auth-input {
    width: 100%;

    padding: 13px;

    margin-bottom: 12px;

    border:
        1px solid #444;

    border-radius: 11px;

    background: #0c0c0c;

    color: #fff;

    outline: none;
}


.auth-button {
    width: 100%;

    padding: 13px;

    border: 0;

    border-radius: 11px;

    background: #fff;

    color: #000;

    font-weight: 700;
}


.auth-switch {
    text-align: center;

    color: #888;

    margin-top: 18px;
}


.auth-switch button {
    border: 0;

    background: transparent;

    color: #fff;

    font-weight: 700;
}


/* =========================================================
   PLANS
========================================================= */

.plan {
    border:
        1px solid #3a3a3a;

    border-radius: 13px;

    padding: 16px;

    margin-top: 12px;
}


.plan button {
    border: 0;

    border-radius: 8px;

    padding:
        8px 12px;

    background: #fff;

    color: #000;

    font-weight: 600;
}


/* =========================================================
   MOBILE
========================================================= */

@media (max-width: 700px) {

    .sidebar {
        position: fixed;

        left: 0;
        top: 0;
        bottom: 0;

        z-index: 3000;

        transform:
            translateX(-100%);

        width: 300px;

        box-shadow:
            10px 0 40px rgba(0,0,0,.6);
    }


    .sidebar.open {
        transform:
            translateX(0);
    }


    .mobile-menu {
        display: block;
    }


    .sidebar-overlay {
        display: none;

        position: fixed;

        inset: 0;

        z-index: 2999;

        background:
            rgba(0,0,0,.6);
    }


    .sidebar-overlay.open {
        display: block;
    }


    .chatbox {
        padding:
            18px 13px 110px;
    }


    .footer {
        padding:
            8px 8px
            calc(
                8px +
                env(safe-area-inset-bottom)
            );
    }


    .welcome {
        margin-top: 80px;
    }


    .welcome h1 {
        font-size: 27px;
    }


    .user-bubble {
        max-width: 88%;
    }


    .header {
        height: 58px;
    }


    .upgrade {
        padding:
            8px 10px;

        font-size: 13px;
    }
}


/* =========================================================
   DESKTOP SCREEN BLOCK
========================================================= */

@media (min-width: 701px) {

    .sidebar.closed {
        width: 0;

        border: 0;
    }
}

</style>

</head>


<body>


<!-- ========================================================
     AUTH SCREEN
     Hidden when Nirale AI first opens.
======================================================== -->

<div
    id="authScreen"
    class="auth-screen hidden"
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
                class="auth-input"
                type="email"
                placeholder="Email"
            >

            <input
                id="loginPassword"
                class="auth-input"
                type="password"
                placeholder="Password"
            >

            <button
                class="auth-button"
                onclick="login()"
            >
                Login
            </button>

            <div class="auth-switch">

                Don't have an account?

                <button
                    onclick="showSignup()"
                >
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
                class="auth-input"
                type="email"
                placeholder="Email"
            >

            <input
                id="signupPassword"
                class="auth-input"
                type="password"
                placeholder="Password"
            >

            <button
                class="auth-button"
                onclick="signup()"
            >
                Create account
            </button>

            <div class="auth-switch">

                Already have an account?

                <button
                    onclick="showLogin()"
                >
                    Login
                </button>

            </div>

        </div>

    </div>

</div>


<!-- ========================================================
     APP
======================================================== -->

<div id="app">


    <!-- SIDEBAR -->

    <aside
        id="sidebar"
        class="sidebar"
    >

        <div class="sidebar-header">

            <div class="sidebar-logo">
                ✨ Nirale AI
            </div>

            <button
                class="sidebar-top-button"
                onclick="searchChats()"
                title="Search"
            >
                🔍
            </button>

            <button
                class="sidebar-top-button"
                onclick="closeSidebar()"
                title="Close"
            >
                ×
            </button>

        </div>


        <!-- MAIN OPTIONS -->

        <div class="sidebar-menu">


            <button
                class="menu-item active"
                onclick="newChat(); closeSidebar();"
            >
                <span class="menu-icon">
                    ✏️
                </span>

                <span class="menu-text">
                    New chat
                </span>
            </button>


            <button
                class="menu-item"
                onclick="openLibrary()"
            >
                <span class="menu-icon">
                    📚
                </span>

                <span class="menu-text">
                    Library
                </span>
            </button>


            <button
                class="menu-item"
                onclick="openProjects()"
            >
                <span class="menu-icon">
                    📁
                </span>

                <span class="menu-text">
                    Projects
                </span>

                <span class="menu-plus">
                    ＋
                </span>
            </button>


            <button
                class="menu-item"
                onclick="openScheduled()"
            >
                <span class="menu-icon">
                    🕐
                </span>

                <span class="menu-text">
                    Scheduled
                </span>
            </button>


            <button
                class="menu-item"
                onclick="openPlugins()"
            >
                <span class="menu-icon">
                    🔌
                </span>

                <span class="menu-text">
                    Plugins
                </span>
            </button>


            <button
                class="menu-item"
                onclick="openCodex()"
            >
                <span class="menu-icon">
                    💻
                </span>

                <span class="menu-text">
                    Codex
                </span>

                <span>
                    ↗
                </span>
            </button>


            <button
                class="menu-item"
                onclick="toggleMore()"
            >
                <span class="menu-icon">
                    •••
                </span>

                <span class="menu-text">
                    More
                </span>
            </button>


            <div
                id="moreContent"
                class="more-content"
            >

                <button
                    class="menu-item"
                    onclick="openSettings()"
                >
                    ⚙️
                    <span class="menu-text">
                        Settings
                    </span>
                </button>

                <button
                    class="menu-item"
                    onclick="openHelp()"
                >
                    ❓
                    <span class="menu-text">
                        Help
                    </span>
                </button>

            </div>

        </div>


        <!-- RECENTS HEADER -->

        <div class="recents-header">

            <span class="recents-title">
                Recents
            </span>

            <button
                class="small-action"
                onclick="newChat()"
                title="New chat"
            >
                ✏️
            </button>

            <button
                class="small-action"
                onclick="recentOptions()"
            >
                •••
            </button>

        </div>


        <!-- RECENTS -->

        <div
            id="recents"
            class="recents"
        >
        </div>


        <!-- ACCOUNT -->

        <div class="sidebar-account">

            <button
                class="account-button"
                onclick="openAccount()"
            >

                <div
                    id="avatar"
                    class="avatar"
                >
                    G
                </div>

                <div class="account-details">

                    <div
                        id="sideEmail"
                        class="account-name"
                    >
                        Guest
                    </div>

                    <div
                        id="sidePlan"
                        class="account-plan"
                    >
                        4 free questions
                    </div>

                </div>

                <span>
                    •••
                </span>

            </button>

        </div>

    </aside>


    <!-- MOBILE OVERLAY -->

    <div
        id="sidebarOverlay"
        class="sidebar-overlay"
        onclick="closeSidebar()"
    ></div>


    <!-- MAIN -->

    <main class="main">


        <!-- HEADER -->

        <header class="header">

            <button
                class="mobile-menu"
                onclick="openSidebar()"
            >
                ☰
            </button>

            <div class="header-logo">
                ✨ Nirale AI
            </div>

            <div class="header-space"></div>

            <!-- ONLY UPGRADE BUTTON -->

            <button
                class="upgrade"
                onclick="openUpgrade()"
            >
                ⭐ Upgrade
            </button>

        </header>


        <!-- CHAT -->

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

                <button
                    class="plus-item"
                    onclick="attachFile()"
                >
                    📎 Attach files
                </button>

                <button
                    class="plus-item"
                    onclick="openCamera()"
                >
                    📷 Camera
                </button>

                <button
                    class="plus-item"
                    onclick="openGallery()"
                >
                    🖼️ Photos / Gallery
                </button>

                <button
                    class="plus-item"
                    onclick="webSearch()"
                >
                    🔎 Web search
                </button>

                <button
                    class="plus-item"
                    onclick="createImage()"
                >
                    🎨 Create image
                </button>

                <button
                    class="plus-item"
                    onclick="openMap()"
                >
                    🗺️ Map
                </button>

            </div>


            <!-- INPUT -->

            <div class="input-box">

                <button
                    class="icon-button"
                    onclick="togglePlus()"
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
                    title="Voice"
                >
                    🎤
                </button>

                <button
                    class="icon-button send-button"
                    onclick="sendMessage()"
                >
                    ↑
                </button>

            </div>

        </div>

    </main>

</div>


<!-- FILE INPUT -->

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


<!-- ========================================================
     ACCOUNT MODAL
======================================================== -->

<div
    id="accountModal"
    class="modal hidden"
>

    <div class="modal-card">

        <button
            class="close-modal"
            onclick="closeModals()"
        >
            ×
        </button>

        <h2>
            👤 Account
        </h2>

        <p id="accountEmail">
            Email: Guest
        </p>

        <p id="accountPlan">
            Plan: Free
        </p>

        <button
            id="logoutBtn"
            class="auth-button hidden"
            onclick="logout()"
        >
            Logout
        </button>

    </div>

</div>


<!-- ========================================================
     UPGRADE
======================================================== -->

<div
    id="upgradeModal"
    class="modal hidden"
>

    <div class="modal-card">

        <button
            class="close-modal"
            onclick="closeModals()"
        >
            ×
        </button>

        <h2>
            ⭐ Upgrade Nirale AI
        </h2>


        <div class="plan">

            <h3>
                Free
            </h3>

            <p>
                ₹0
            </p>

            <button
                onclick="selectPlan('Free')"
            >
                Current
            </button>

        </div>


        <div class="plan">

            <h3>
                Plus
            </h3>

            <p>
                ₹499 / month
            </p>

            <button
                onclick="selectPlan('Plus')"
            >
                Upgrade
            </button>

        </div>


        <div class="plan">

            <h3>
                Pro
            </h3>

            <p>
                ₹999 / month
            </p>

            <button
                onclick="selectPlan('Pro')"
            >
                Upgrade
            </button>

        </div>

    </div>

</div>


<!-- ========================================================
     ADMIN
======================================================== -->

<div
    id="adminModal"
    class="modal hidden"
>

    <div class="modal-card">

        <button
            class="close-modal"
            onclick="closeModals()"
        >
            ×
        </button>

        <h2>
            👑 Admin Dashboard
        </h2>

        <div id="adminStats"></div>

        <h3>
            Users
        </h3>

        <div id="adminUsers"></div>

        <h3>
            Activity
        </h3>

        <div id="adminActivity"></div>

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
   SIDEBAR
============================================================ */

function openSidebar() {

    document
        .getElementById("sidebar")
        .classList
        .add("open");

    document
        .getElementById("sidebarOverlay")
        .classList
        .add("open");
}


function closeSidebar() {

    document
        .getElementById("sidebar")
        .classList
        .remove("open");

    document
        .getElementById("sidebarOverlay")
        .classList
        .remove("open");
}


function toggleMore() {

    document
        .getElementById("moreContent")
        .classList
        .toggle("open");
}


/* ============================================================
   AUTH UI
============================================================ */

function showLogin() {

    document
        .getElementById("loginForm")
        .classList
        .remove("hidden");

    document
        .getElementById("signupForm")
        .classList
        .add("hidden");
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
        await fetch(
            "/api/me"
        );


    const user =
        await res.json();


    /* GUEST */

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
            .getElementById("avatar")
            .textContent =
            "G";


        document
            .getElementById("logoutBtn")
            .classList
            .add("hidden");


        return;
    }


    /* LOGGED IN */

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
        user.plan;


    document
        .getElementById("accountEmail")
        .textContent =
        "Email: " +
        user.email;


    document
        .getElementById("accountPlan")
        .textContent =
        "Plan: " +
        user.plan;


    document
        .getElementById("avatar")
        .textContent =
        user.email
            .charAt(0)
            .toUpperCase();


    document
        .getElementById("logoutBtn")
        .classList
        .remove("hidden");


    loadRecents();


    const admin =
        await fetch(
            "/api/admin/stats"
        );


    if (admin.ok) {

        const menu =
            document.createElement(
                "button"
            );

        menu.className =
            "menu-item";

        menu.innerHTML = `
            👑
            <span class="menu-text">
                Admin Dashboard
            </span>
        `;

        menu.onclick =
            openAdmin;

        document
            .querySelector(".sidebar-menu")
            .appendChild(menu);
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

                <h1>
                    How can I help you?
                </h1>

                <p>
                    Ask Nirale AI anything.
                </p>

            </div>
        `;


    document
        .getElementById("messageInput")
        .focus();
}


/* ============================================================
   PLUS
============================================================ */

function togglePlus() {

    document
        .getElementById("plusMenu")
        .classList
        .toggle("hidden");
}


function closePlus() {

    document
        .getElementById("plusMenu")
        .classList
        .add("hidden");
}


/* ============================================================
   FILE
============================================================ */

function attachFile() {

    closePlus();

    document
        .getElementById("fileInput")
        .click();
}


function openCamera() {

    closePlus();

    document
        .getElementById("cameraInput")
        .click();
}


function openGallery() {

    closePlus();

    document
        .getElementById("galleryInput")
        .click();
}


function fileSelected(event) {

    const file =
        event.target.files[0];

    if (!file) return;

    addUserText(
        "📎 " +
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


            const wrapper =
                document
                    .createElement("div");


            wrapper.className =
                "message user-message";


            const img =
                document
                    .createElement("img");


            img.src =
                selectedImage;


            img.style.maxWidth =
                "300px";


            img.style.maxHeight =
                "300px";


            img.style.borderRadius =
                "15px";


            wrapper.appendChild(
                img
            );


            chat.appendChild(
                wrapper
            );


            chat.scrollTop =
                chat.scrollHeight;
        };


    reader.readAsDataURL(file);
}


/* ============================================================
   WEB SEARCH
============================================================ */

function webSearch() {

    closePlus();

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

    closePlus();

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
   IMAGE
============================================================ */

function createImage() {

    closePlus();

    addAssistant(
        "🎨 Create image option selected. " +
        "Actual image-generation service connect " +
        "madida mele image generate madabahudu."
    );
}


/* ============================================================
   USER MESSAGE
============================================================ */

function addUserText(text) {

    const welcome =
        document.getElementById(
            "welcome"
        );

    if (welcome)
        welcome.remove();


    const chat =
        document.getElementById(
            "chatbox"
        );


    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        "message user-message";


    const bubble =
        document.createElement(
            "div"
        );


    bubble.className =
        "user-bubble";


    bubble.textContent =
        text;


    wrapper.appendChild(
        bubble
    );


    chat.appendChild(
        wrapper
    );


    chat.scrollTop =
        chat.scrollHeight;
}


/* ============================================================
   ASSISTANT MESSAGE
============================================================ */

function addAssistant(text) {

    const welcome =
        document.getElementById(
            "welcome"
        );

    if (welcome)
        welcome.remove();


    const chat =
        document.getElementById(
            "chatbox"
        );


    const div =
        document.createElement(
            "div"
        );


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
   CODE
============================================================ */

function formatCode(container) {

    container
        .querySelectorAll("pre")
        .forEach(pre => {

            const code =
                pre.querySelector(
                    "code"
                );


            if (!code)
                return;


            try {
                hljs.highlightElement(
                    code
                );
            } catch(e) {}


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
                        1000
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
                        document.createElement(
                            "a"
                        );


                    a.href =
                        url;

                    a.download =
                        "nirale-code.txt";

                    a.click();


                    URL.revokeObjectURL(
                        url
                    );
                };


            actions.appendChild(
                copy
            );

            actions.appendChild(
                download
            );

            pre.appendChild(
                actions
            );

        });
}


/* ============================================================
   SEND
============================================================ */

async function sendMessage() {

    const input =
        document.getElementById(
            "messageInput"
        );


    const message =
        input.value.trim();


    if (
        !message &&
        !selectedImage
    ) {
        return;
    }


    if (message) {
        addUserText(message);
    }


    input.value = "";


    const chat =
        document.getElementById(
            "chatbox"
        );


    const thinking =
        document.createElement(
            "div"
        );


    thinking.className =
        "thinking";


    thinking.textContent =
        thinking_text_client(
            message
        );


    chat.appendChild(
        thinking
    );


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
                            message,

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


        if (
            data.detail ===
            "LOGIN_REQUIRED"
        ) {

            showLoginRequired();

            return;
        }


        if (!res.ok) {

            addAssistant(
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


        selectedImage =
            null;


        addAssistant(
            data.reply
        );


        if (
            data.guest &&
            data.guest_count >= 4
        ) {

            setTimeout(
                () => {
                    showLoginRequired();
                },
                900
            );
        }


        loadRecents();

    } catch(error) {

        thinking.remove();

        addAssistant(
            "❌ Server connection problem."
        );
    }
}


/* ============================================================
   THINKING LANGUAGE
============================================================ */

function thinking_text_client(text) {

    if (
        /[\u0C80-\u0CFF]/.test(text)
    ) {
        return "ಯೋಚಿಸುತ್ತಿದೆ...";
    }


    if (
        /[\u0900-\u097F]/.test(text)
    ) {
        return "सोच रहा हूँ...";
    }


    if (
        /[\u0C00-\u0C7F]/.test(text)
    ) {
        return "ఆలోచిస్తోంది...";
    }


    if (
        /[\u0B80-\u0BFF]/.test(text)
    ) {
        return "யோசிக்கிறது...";
    }


    if (
        /[\u0D00-\u0D7F]/.test(text)
    ) {
        return "ചിന്തിക്കുന്നു...";
    }


    return "Thinking...";
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
   ENTER
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
            "ಈ browser voice input support ಮಾಡಲ್ಲ."
        );

        return;
    }


    if (recognition) {

        recognition.stop();

        recognition = null;

        document
            .getElementById("micBtn")
            .classList
            .remove(
                "mic-listening"
            );

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
        document.getElementById(
            "micBtn"
        );


    mic.classList.add(
        "mic-listening"
    );


    recognition.onresult =
        function(event) {

            let text = "";


            for (
                let i =
                    event.resultIndex;

                i <
                    event.results.length;

                i++
            ) {

                text +=
                    event.results[i][0]
                        .transcript;
            }


            document
                .getElementById(
                    "messageInput"
                )
                .value =
                text;
        };


    recognition.onerror =
        function() {

            mic.classList.remove(
                "mic-listening"
            );

            recognition = null;
        };


    recognition.onend =
        function() {

            mic.classList.remove(
                "mic-listening"
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


    if (!res.ok)
        return;


    const data =
        await res.json();


    const box =
        document.getElementById(
            "recents"
        );


    box.innerHTML = "";


    data.chats.forEach(
        chat => {

            const row =
                document.createElement(
                    "div"
                );


            row.className =
                "recent-row";


            const title =
                document.createElement(
                    "button"
                );


            title.className =
                "recent-title";


            title.textContent =
                chat.title;


            title.onclick =
                () => openChat(
                    chat.id
                );


            const options =
                document.createElement(
                    "button"
                );


            options.className =
                "recent-options";


            options.textContent =
                "•••";


            options.onclick =
                (event) => {

                    event.stopPropagation();

                    if (
                        confirm(
                            "Delete this chat?"
                        )
                    ) {

                        deleteChat(
                            chat.id
                        );
                    }
                };


            row.appendChild(
                title
            );

            row.appendChild(
                options
            );


            box.appendChild(
                row
            );
        }
    );
}


/* ============================================================
   OPEN CHAT
============================================================ */

async function openChat(id) {

    const res =
        await fetch(
            "/api/chats/" +
            id
        );


    if (!res.ok)
        return;


    const data =
        await res.json();


    currentChatId =
        id;


    const chatbox =
        document.getElementById(
            "chatbox"
        );


    chatbox.innerHTML = "";


    data.messages.forEach(
        message => {

            if (
                message.role ===
                "user"
            ) {

                addUserText(
                    message.content
                );

            } else {

                addAssistant(
                    message.content
                );
            }
        }
    );


    chatbox.scrollTop =
        chatbox.scrollHeight;


    closeSidebar();
}


/* ============================================================
   DELETE CHAT
============================================================ */

async function deleteChat(id) {

    await fetch(
        "/api/chats/" +
        id,
        {
            method: "DELETE"
        }
    );


    if (
        currentChatId === id
    ) {
        newChat();
    }


    loadRecents();
}


/* ============================================================
   SEARCH
============================================================ */

async function searchChats() {

    const query =
        prompt(
            "Search chats"
        );


    if (!query)
        return;


    const res =
        await fetch(
            "/api/chats"
        );


    if (!res.ok)
        return;


    const data =
        await res.json();


    const box =
        document.getElementById(
            "recents"
        );


    box.innerHTML = "";


    data.chats
        .filter(
            chat =>
                chat.title
                    .toLowerCase()
                    .includes(
                        query.toLowerCase()
                    )
        )
        .forEach(
            chat => {

                const row =
                    document.createElement(
                        "div"
                    );


                row.className =
                    "recent-row";


                row.innerHTML = `
                    <button
                        class="recent-title"
                        onclick="openChat(${chat.id})"
                    >
                        ${escapeHtml(
                            chat.title
                        )}
                    </button>
                `;


                box.appendChild(
                    row
                );
            }
        );
}


/* ============================================================
   ACCOUNT
============================================================ */

function openAccount() {

    document
        .getElementById(
            "accountModal"
        )
        .classList
        .remove("hidden");
}


/* ============================================================
   UPGRADE
============================================================ */

function openUpgrade() {

    document
        .getElementById(
            "upgradeModal"
        )
        .classList
        .remove("hidden");
}


/* ============================================================
   MODALS
============================================================ */

function closeModals() {

    document
        .querySelectorAll(
            ".modal"
        )
        .forEach(
            x =>
                x.classList
                    .add("hidden")
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
                    plan: plan
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
            "Plan update failed."
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
        .getElementById(
            "adminStats"
        )
        .innerHTML = `
            <p>
                Users: ${stats.users}
            </p>

            <p>
                Chats: ${stats.chats}
            </p>

            <p>
                Messages: ${stats.messages}
            </p>
        `;


    const usersRes =
        await fetch(
            "/api/admin/users"
        );


    const users =
        await usersRes.json();


    document
        .getElementById(
            "adminUsers"
        )
        .innerHTML =
        users.users
            .map(
                user => `
                    <div
                        style="
                            padding:10px;
                            border-bottom:
                                1px solid #333;
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

                        Last active:
                        ${escapeHtml(
                            user.last_active ||
                            ""
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
        .getElementById(
            "adminActivity"
        )
        .innerHTML =
        activity.activity
            .map(
                item => `
                    <div
                        style="
                            padding:10px;
                            border-bottom:
                                1px solid #333;
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
        .getElementById(
            "adminModal"
        )
        .classList
        .remove("hidden");
}


/* ============================================================
   OTHER SIDEBAR OPTIONS
============================================================ */

function openLibrary() {

    alert(
        "Library"
    );
}


function openProjects() {

    alert(
        "Projects"
    );
}


function openScheduled() {

    alert(
        "Scheduled"
    );
}


function openPlugins() {

    alert(
        "Plugins"
    );
}


function openCodex() {

    alert(
        "Codex"
    );
}


function openSettings() {

    alert(
        "Settings"
    );
}


function openHelp() {

    alert(
        "Help"
    );
}


function recentOptions() {

    alert(
        "Recent chat options"
    );
}


/* ============================================================
   ESCAPE
============================================================ */

function escapeHtml(text) {

    const div =
        document.createElement(
            "div"
        );

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

@app.get(
    "/",
    response_class=HTMLResponse
)
async def root():

    return HTMLResponse(
        HTML
    )
