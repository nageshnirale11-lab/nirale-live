import os
import re
import sqlite3
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

try:
    import google.generativeai as genai
except Exception:
    genai = None

APP_TITLE = "Nirale AI"
DB_PATH = os.getenv("NIRALE_DB", "nirale.db")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

app = FastAPI(title=APP_TITLE)

if genai and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

CREATOR_REPLY = "ನನ್ನನ್ನು Nagesh Nirale ಅವರು ರಚಿಸಿದ್ದಾರೆ."

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        plan TEXT DEFAULT 'Free',
        created_at TEXT NOT NULL,
        last_active TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        email TEXT,
        question TEXT NOT NULL,
        created_at TEXT NOT NULL,
        plan TEXT DEFAULT 'Guest'
    );
    """)
    c.commit()
    c.close()

init_db()

class AuthBody(BaseModel):
    email: str
    password: str

class ChatBody(BaseModel):
    message: str
    chat_id: Optional[int] = None

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.scrypt(
        password.encode(),
        salt=salt.encode(),
        n=16384,
        r=8,
        p=1
    ).hex()
    return h, salt

def verify_password(password, stored, salt):
    h, _ = hash_password(password, salt)
    return secrets.compare_digest(h, stored)

def get_user(request: Request):
    token = request.cookies.get("nirale_session")
    if not token:
        return None
    c = db()
    row = c.execute("""
        SELECT users.* FROM users
        JOIN sessions ON sessions.user_id = users.id
        WHERE sessions.token=?
    """, (token,)).fetchone()
    if row:
        c.execute("UPDATE users SET last_active=? WHERE id=?", (now(), row["id"]))
        c.commit()
    c.close()
    return row

def is_creator_question(text):
    t = text.lower().strip()
    patterns = [
        "who created you", "who made you", "who built you",
        "who developed you", "who is your creator",
        "who's your creator", "who created nirale",
        "who made nirale", "who developed nirale",
        "nirale ai created", "nirale ai creator",
        "nagesh nirale", "nagesh created you",
        "nimmannu yaru create", "nimmannu yaaru create",
        "ninnannu yaru create", "ninnannu yaaru create",
        "ninnannu yaru madidru", "ninnannu yaaru madidru",
        "ninnannu yaaru rachisidaru", "nimmannu yaaru rachisidaru",
        "yaru create madidru", "yaru create madidaru",
        "yaru madidru", "yaru madidaru",
        "ನಿನ್ನನ್ನು ಯಾರು", "ನಿಮ್ಮನ್ನು ಯಾರು",
        "ಯಾರು ರಚಿಸಿದ್ದಾರೆ", "ಯಾರು ಸೃಷ್ಟಿಸಿದ್ದಾರೆ",
        "ಯಾರು create", "ಯಾರು ಮಾಡಿದರು"
    ]
    return any(p in t for p in patterns)

SYSTEM_PROMPT = """You are Nirale AI, a helpful multilingual AI assistant created by Nagesh Nirale.
Answer the user's question accurately and naturally. Reply in the same language the user uses whenever possible.
Support Kannada, English, Hindi, Telugu, Tamil, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu and other languages.
Do not claim that Nirale AI was created by Google or by Nirale AI itself. If asked who created you, the application handles that answer separately.
Use Markdown when useful. For programming code, use fenced code blocks with the correct language.
Do not expose passwords, API keys, session tokens or private user data.
"""

def ask_gemini(message, history=None):
    if not genai or not GEMINI_API_KEY:
        return "Gemini API is not configured. Please set GEMINI_API_KEY in the server environment."

    try:
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT
        )
        contents = []
        for item in (history or [])[-12:]:
            contents.append({
                "role": "user" if item["role"] == "user" else "model",
                "parts": [item["content"]]
            })
        contents.append({"role": "user", "parts": [message]})
        response = model.generate_content(contents)
        text = getattr(response, "text", None)
        return text.strip() if text else "Sorry, I could not generate a response."
    except Exception as e:
        return f"Gemini error: {str(e)}"

@app.post("/api/signup")
def signup(body: AuthBody):
    email = body.email.strip().lower()
    password = body.password
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return {"ok": False, "error": "Enter a valid email address."}
    if len(password) < 6:
        return {"ok": False, "error": "Password must be at least 6 characters."}

    ph, salt = hash_password(password)
    c = db()
    try:
        cur = c.execute("""
            INSERT INTO users(email,password_hash,salt,plan,created_at,last_active)
            VALUES(?,?,?,?,?,?)
        """, (email, ph, salt, "Free", now(), now()))
        uid = cur.lastrowid
        token = secrets.token_urlsafe(32)
        c.execute("INSERT INTO sessions VALUES(?,?,?)", (token, uid, now()))
        c.commit()
    except sqlite3.IntegrityError:
        c.close()
        return {"ok": False, "error": "An account with this email already exists."}
    c.close()

    from fastapi.responses import JSONResponse
    r = JSONResponse({"ok": True})
    r.set_cookie("nirale_session", token, httponly=True, samesite="lax", secure=False, max_age=60*60*24*30)
    r.delete_cookie("nirale_guest_count")
    return r

@app.post("/api/login")
def login(body: AuthBody):
    email = body.email.strip().lower()
    c = db()
    user = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or not verify_password(body.password, user["password_hash"], user["salt"]):
        c.close()
        return {"ok": False, "error": "Invalid email or password."}
    token = secrets.token_urlsafe(32)
    c.execute("INSERT INTO sessions VALUES(?,?,?)", (token, user["id"], now()))
    c.execute("UPDATE users SET last_active=? WHERE id=?", (now(), user["id"]))
    c.commit()
    c.close()

    from fastapi.responses import JSONResponse
    r = JSONResponse({"ok": True})
    r.set_cookie("nirale_session", token, httponly=True, samesite="lax", secure=False, max_age=60*60*24*30)
    r.delete_cookie("nirale_guest_count")
    return r

@app.post("/api/logout")
def logout(request: Request):
    token = request.cookies.get("nirale_session")
    c = db()
    if token:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))
    c.commit()
    c.close()
    from fastapi.responses import JSONResponse
    r = JSONResponse({"ok": True})
    r.delete_cookie("nirale_session")
    return r

@app.get("/api/me")
def me(request: Request):
    u = get_user(request)
    if not u:
        return {"logged_in": False}
    return {
        "logged_in": True,
        "email": u["email"],
        "plan": u["plan"],
        "created_at": u["created_at"],
        "last_active": u["last_active"]
    }

@app.get("/api/chats")
def chats(request: Request):
    u = get_user(request)
    if not u:
        return {"ok": True, "chats": []}
    c = db()
    rows = c.execute("""
        SELECT id,title,created_at,updated_at
        FROM chats WHERE user_id=? ORDER BY updated_at DESC
    """, (u["id"],)).fetchall()
    c.close()
    return {"ok": True, "chats": [dict(x) for x in rows]}

@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: int, request: Request):
    u = get_user(request)
    if not u:
        return {"ok": False, "error": "Login required."}
    c = db()
    chat = c.execute(
        "SELECT * FROM chats WHERE id=? AND user_id=?", (chat_id, u["id"])
    ).fetchone()
    msgs = c.execute(
        "SELECT role,content,created_at FROM messages WHERE chat_id=? ORDER BY id",
        (chat_id,)
    ).fetchall()
    c.close()
    if not chat:
        return {"ok": False, "error": "Chat not found."}
    return {"ok": True, "chat": dict(chat), "messages": [dict(x) for x in msgs]}

@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: int, request: Request):
    u = get_user(request)
    if not u:
        return {"ok": False, "error": "Login required."}
    c = db()
    c.execute("DELETE FROM messages WHERE chat_id=? AND chat_id IN (SELECT id FROM chats WHERE user_id=?)", (chat_id, u["id"]))
    c.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, u["id"]))
    c.commit()
    c.close()
    return {"ok": True}

@app.post("/api/chat")
def chat(body: ChatBody, request: Request):
    message = body.message.strip()
    if not message:
        return {"ok": False, "error": "Please type a message."}

    u = get_user(request)

    # Exactly four guest questions are allowed.
    if not u:
        count = int(request.cookies.get("nirale_guest_count", "0") or 0)
        if count >= 4:
            return {
                "ok": False,
                "error": "LOGIN_REQUIRED",
                "message": "Please login or create an account to continue."
            }

    if is_creator_question(message):
        answer = CREATOR_REPLY
    else:
        history = []
        chat_id = body.chat_id

        if u and chat_id:
            c = db()
            rows = c.execute("""
                SELECT role,content FROM messages
                WHERE chat_id=? AND chat_id IN (SELECT id FROM chats WHERE user_id=?)
                ORDER BY id DESC LIMIT 12
            """, (chat_id, u["id"])).fetchall()
            history = list(reversed([dict(x) for x in rows]))
            c.close()

        answer = ask_gemini(message, history)

    if u:
        c = db()
        chat_id = body.chat_id

        if chat_id:
            owned = c.execute(
                "SELECT id FROM chats WHERE id=? AND user_id=?",
                (chat_id, u["id"])
            ).fetchone()
        else:
            owned = None

        if not owned:
            title = re.sub(r"\s+", " ", message)[:55] or "New Chat"
            cur = c.execute("""
                INSERT INTO chats(user_id,title,created_at,updated_at)
                VALUES(?,?,?,?,?)
            """, (u["id"], title, now(), now()))
            chat_id = cur.lastrowid

        c.execute(
            "INSERT INTO messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
            (chat_id, "user", message, now())
        )
        c.execute(
            "INSERT INTO messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
            (chat_id, "assistant", answer, now())
        )
        c.execute("""
            INSERT INTO usage(user_id,email,question,created_at,plan)
            VALUES(?,?,?,?,?)
        """, (u["id"], u["email"], message, now(), u["plan"]))
        c.execute(
            "UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id)
        )
        c.commit()
        c.close()

        return {"ok": True, "answer": answer, "chat_id": chat_id}

    # guest usage
    old = int(request.cookies.get("nirale_guest_count", "0") or 0)
    new = old + 1
    c = db()
    c.execute("""
        INSERT INTO usage(user_id,email,question,created_at,plan)
        VALUES(NULL,NULL,?,?,?)
    """, (message, now(), "Guest"))
    c.commit()
    c.close()

    from fastapi.responses import JSONResponse
    r = JSONResponse({
        "ok": True,
        "answer": answer,
        "guest_count": new,
        "guest_remaining": max(0, 4-new)
    })
    r.set_cookie("nirale_guest_count", str(new), httponly=True, samesite="lax", secure=False, max_age=60*60*24*30)
    return r

@app.get("/api/admin/users")
def admin_users(request: Request):
    u = get_user(request)
    if not u or not OWNER_EMAIL or u["email"] != OWNER_EMAIL:
        return {"ok": False, "error": "Admin access denied."}
    c = db()
    rows = c.execute("""
        SELECT id,email,plan,created_at,last_active
        FROM users ORDER BY last_active DESC
    """).fetchall()
    c.close()
    return {"ok": True, "users": [dict(x) for x in rows]}

@app.get("/api/admin/activity")
def admin_activity(request: Request):
    u = get_user(request)
    if not u or not OWNER_EMAIL or u["email"] != OWNER_EMAIL:
        return {"ok": False, "error": "Admin access denied."}
    c = db()
    rows = c.execute("""
        SELECT email,question,created_at,plan
        FROM usage ORDER BY id DESC LIMIT 300
    """).fetchall()
    c.close()
    return {"ok": True, "activity": [dict(x) for x in rows]}

@app.get("/api/admin/stats")
def admin_stats(request: Request):
    u = get_user(request)
    if not u or not OWNER_EMAIL or u["email"] != OWNER_EMAIL:
        return {"ok": False, "error": "Admin access denied."}
    c = db()
    users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    messages = c.execute("SELECT COUNT(*) n FROM usage").fetchone()["n"]
    c.close()
    return {"ok": True, "users": users, "messages": messages}

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Nirale AI</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>
<style>
*{box-sizing:border-box}
html,body{margin:0;width:100%;height:100%;font-family:Arial,Helvetica,sans-serif;background:#fff;color:#202123}
button,input,textarea{font:inherit}
button{cursor:pointer}
.app{display:flex;width:100%;height:100dvh;overflow:hidden}
.sidebar{width:300px;flex:0 0 300px;height:100dvh;background:#f7f7f8;border-right:1px solid #ddd;display:flex;flex-direction:column;transition:width .2s,transform .25s;overflow:hidden;z-index:1000}
.sidebar.closed{width:0;flex-basis:0;border:0}
.sidebar-top{padding:12px}
.side-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.brand{font-size:19px;font-weight:700}
.icon-btn{border:0;background:transparent;border-radius:9px;padding:8px;font-size:19px}
.icon-btn:hover{background:#e5e5e5}
.sidebar-search{display:flex;width:100%;margin:0 0 10px}
.sidebar-search input{width:100%;height:44px;border:1px solid #d0d0d0;border-radius:12px;padding:0 13px;outline:none;background:#fff;color:#222}
.sidebar-search input:focus{border-color:#999}
.new-chat{width:100%;height:44px;border:1px solid #ccc;background:#fff;border-radius:11px;text-align:left;padding:0 13px;font-weight:600}
.menu-list{padding:4px 10px}
.menu-item{display:flex;align-items:center;gap:11px;width:100%;height:43px;border:0;background:transparent;border-radius:10px;text-align:left;padding:0 11px;color:#222}
.menu-item:hover{background:#e8e8e8}
.recents-title{font-size:12px;color:#777;padding:15px 13px 7px}
.recents{overflow:auto;flex:1;padding:0 10px}
.recent-chat{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px;border-radius:9px;cursor:pointer;font-size:14px}
.recent-chat:hover{background:#e8e8e8}
.recent-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.account{border-top:1px solid #ddd;padding:10px}
.account-btn{width:100%;display:flex;align-items:center;gap:9px;border:0;background:transparent;border-radius:10px;padding:9px;text-align:left}
.account-btn:hover{background:#e8e8e8}
.avatar{width:32px;height:32px;border-radius:50%;background:#111;color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px}
.account-text{min-width:0;flex:1}
.account-email{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.account-plan{font-size:11px;color:#777}
.main{min-width:0;flex:1;height:100dvh;display:flex;flex-direction:column;background:#fff}
.header{height:60px;flex:0 0 60px;border-bottom:1px solid #eee;display:flex;align-items:center;gap:10px;padding:0 14px}
.menu-open{border:0;background:transparent;font-size:22px;width:40px;height:40px;border-radius:9px}
.menu-open:hover{background:#f0f0f0}
.header-title{font-weight:700;flex:1}
.upgrade{border:0;border-radius:9px;background:#111;color:#fff;padding:9px 13px}
.chatbox{flex:1;overflow:auto;padding:25px max(14px,calc((100% - 850px)/2));scroll-behavior:smooth}
.welcome{text-align:center;margin:15vh auto 0;max-width:620px}
.welcome h1{font-size:30px;margin:0 0 10px}
.welcome p{color:#666;margin:0}
.msg-row{display:flex;margin:16px 0}
.msg-row.user{justify-content:flex-end}
.msg{max-width:82%;padding:12px 15px;border-radius:16px;line-height:1.55;overflow-wrap:anywhere}
.msg.user{background:#f1f1f1}
.msg.assistant{background:transparent}
.msg pre{position:relative;overflow:auto;background:#111;color:#eee;padding:14px;border-radius:10px}
.msg code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.code-wrap{position:relative}
.copy-code{position:absolute;right:8px;top:8px;border:1px solid #555;background:#222;color:#fff;border-radius:6px;padding:5px 8px;font-size:12px}
.thinking{color:#777;font-style:italic;padding:10px 5px}
.footer{padding:10px 14px calc(10px + env(safe-area-inset-bottom));background:#fff}
.composer{max-width:850px;margin:auto;border:1px solid #ccc;border-radius:18px;display:flex;align-items:flex-end;gap:6px;padding:7px;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.05)}
.composer textarea{flex:1;min-width:0;max-height:150px;resize:none;border:0;outline:0;padding:9px 6px;font-size:15px}
.round{width:40px;height:40px;flex:0 0 40px;border:0;border-radius:50%;background:transparent;font-size:20px}
.round:hover{background:#eee}
.send{background:#111;color:#fff}
.plus-menu{display:none;position:absolute;bottom:75px;left:14px;width:220px;background:#fff;border:1px solid #ddd;border-radius:13px;padding:7px;box-shadow:0 8px 30px rgba(0,0,0,.15);z-index:1200}
.plus-menu.open{display:block}
.plus-item{display:block;width:100%;border:0;background:transparent;text-align:left;padding:11px;border-radius:9px}
.plus-item:hover{background:#f1f1f1}
.overlay{display:none}
.auth{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:2000;align-items:center;justify-content:center;padding:18px}
.auth.open{display:flex}
.auth-card{width:100%;max-width:400px;background:#fff;border-radius:18px;padding:24px;box-shadow:0 15px 50px rgba(0,0,0,.25)}
.auth-card h2{margin-top:0}
.auth-card input{display:block;width:100%;height:46px;margin:10px 0;border:1px solid #ccc;border-radius:10px;padding:0 12px}
.auth-primary{width:100%;height:46px;border:0;border-radius:10px;background:#111;color:#fff;margin-top:8px}
.auth-switch{text-align:center;margin-top:16px;font-size:14px}
.auth-switch a{color:#111;font-weight:700;cursor:pointer;text-decoration:underline}
.close-auth{float:right;border:0;background:transparent;font-size:22px}
.account-pop{display:none;position:fixed;right:14px;bottom:70px;width:260px;background:#fff;border:1px solid #ddd;border-radius:14px;padding:12px;box-shadow:0 10px 30px rgba(0,0,0,.15);z-index:1500}
.account-pop.open{display:block}
.pop-btn{width:100%;height:40px;border:0;background:transparent;text-align:left;border-radius:8px;padding:0 10px}
.pop-btn:hover{background:#eee}
@media(max-width:700px){
 .sidebar{position:fixed;left:0;top:0;width:300px;max-width:86vw;transform:translateX(-100%);box-shadow:8px 0 30px rgba(0,0,0,.18)}
 .sidebar.open{transform:translateX(0)}
 .sidebar.closed{width:300px;flex-basis:auto}
 .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:999}
 .overlay.open{display:block}
 .header{height:56px;flex-basis:56px;padding:0 8px}
 .header-title{font-size:15px}
 .upgrade{padding:8px 10px;font-size:13px}
 .chatbox{padding:15px 9px 95px}
 .welcome{margin-top:18vh}
 .welcome h1{font-size:25px}
 .msg{max-width:94%;font-size:15px}
 .footer{padding:7px 7px calc(7px + env(safe-area-inset-bottom));position:relative;z-index:900}
 .composer{border-radius:17px;padding:6px}
 .composer textarea{font-size:15px}
 .plus-menu{position:fixed;left:8px;bottom:72px;width:calc(100vw - 16px);max-width:370px}
 .sidebar-search{display:flex!important;margin:0 0 10px}
 .sidebar-search input{display:block!important;height:44px;font-size:15px}
}
</style>
</head>
<body>
<div class="app">
<aside id="sidebar" class="sidebar">
  <div class="sidebar-top">
    <div class="side-head">
      <div class="brand">✨ Nirale AI</div>
      <button class="icon-btn" onclick="closeSidebar()" aria-label="Close sidebar">×</button>
    </div>
    <div class="sidebar-search">
      <input id="chatSearchInput" type="search" placeholder="Search chats..." autocomplete="off">
    </div>
    <button class="new-chat" onclick="newChat()">＋ New Chat</button>
  </div>

  <div class="menu-list">
    <button class="menu-item" onclick="showInfo('Library')">▣ <span>Library</span></button>
    <button class="menu-item" onclick="showInfo('Projects')">▦ <span>Projects</span></button>
    <button class="menu-item" onclick="showInfo('Scheduled')">◷ <span>Scheduled</span></button>
    <button class="menu-item" onclick="showInfo('Plugins')">⊞ <span>Plugins</span></button>
    <button class="menu-item" onclick="showInfo('Codex / Code')">⌘ <span>Codex / Code</span></button>
    <button class="menu-item" onclick="showInfo('More')">••• <span>More</span></button>
  </div>

  <div class="recents-title">Recents</div>
  <div id="recents" class="recents"></div>

  <div class="account">
    <button class="account-btn" onclick="toggleAccount()">
      <div id="avatar" class="avatar">G</div>
      <div class="account-text">
        <div id="accountEmail" class="account-email">Guest</div>
        <div id="accountPlan" class="account-plan">4 free questions</div>
      </div>
      <span>⋯</span>
    </button>
  </div>
</aside>

<div id="overlay" class="overlay" onclick="closeSidebar()"></div>

<main class="main">
  <header class="header">
    <button class="menu-open" onclick="openSidebar()" aria-label="Open sidebar">☰</button>
    <div class="header-title">Nirale AI</div>
    <button class="upgrade" onclick="upgrade()">⭐ Upgrade</button>
  </header>

  <section id="chatbox" class="chatbox">
    <div id="welcome" class="welcome">
      <h1>How can I help you?</h1>
      <p>Ask Nirale AI anything.</p>
    </div>
  </section>

  <div id="plusMenu" class="plus-menu">
    <button class="plus-item" onclick="document.getElementById('fileInput').click()">📎 Attach files</button>
    <button class="plus-item" onclick="document.getElementById('cameraInput').click()">📷 Camera</button>
    <button class="plus-item" onclick="document.getElementById('photoInput').click()">🖼️ Photos / Gallery</button>
    <button class="plus-item" onclick="webSearch()">🌐 Web search</button>
    <button class="plus-item" onclick="showInfo('Create image')">🎨 Create image</button>
    <button class="plus-item" onclick="openMap()">📍 Map</button>
  </div>

  <footer class="footer">
    <div class="composer">
      <button class="round" onclick="togglePlus()" aria-label="Attach">＋</button>
      <textarea id="messageInput" rows="1" placeholder="Message Nirale AI..." onkeydown="handleKey(event)"></textarea>
      <button id="micBtn" class="round" onclick="voiceInput()" aria-label="Voice">🎙️</button>
      <button class="round send" onclick="sendMessage()" aria-label="Send">➤</button>
    </div>
    <input id="fileInput" type="file" hidden>
    <input id="photoInput" type="file" accept="image/*" hidden>
    <input id="cameraInput" type="file" accept="image/*" capture="environment" hidden>
  </footer>
</main>
</div>

<div id="auth" class="auth">
 <div class="auth-card">
   <button class="close-auth" onclick="closeAuth()">×</button>
   <h2 id="authTitle">Login to Nirale AI</h2>
   <input id="authEmail" type="email" placeholder="Email">
   <input id="authPassword" type="password" placeholder="Password">
   <button class="auth-primary" onclick="submitAuth()">Continue</button>
   <div id="authMessage" style="color:#b00020;margin-top:9px;font-size:13px"></div>
   <div class="auth-switch" id="authSwitch">
     Don't have an account? <a onclick="switchAuth('signup')">Create account</a>
   </div>
 </div>
</div>

<div id="accountPop" class="account-pop">
  <button class="pop-btn" onclick="openAuth('login')">Login</button>
  <button class="pop-btn" onclick="openAuth('signup')">Create account</button>
  <button class="pop-btn" onclick="logout()">Logout</button>
</div>

<script>
let currentChatId = null;
let authMode = "login";

const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const chatbox = document.getElementById("chatbox");
const input = document.getElementById("messageInput");
const plusMenu = document.getElementById("plusMenu");

function openSidebar(){
  sidebar.classList.remove("closed");
  sidebar.classList.add("open");
  overlay.classList.add("open");
}
function closeSidebar(){
  sidebar.classList.remove("open");
  overlay.classList.remove("open");
  if(window.innerWidth > 700) sidebar.classList.add("closed");
}
function newChat(){
  currentChatId = null;
  chatbox.innerHTML = `<div id="welcome" class="welcome"><h1>How can I help you?</h1><p>Ask Nirale AI anything.</p></div>`;
  closeSidebar();
  input.focus();
}
function togglePlus(){
  plusMenu.classList.toggle("open");
}
function showInfo(name){
  plusMenu.classList.remove("open");
  alert(name + " is ready for Nirale AI.");
}
function webSearch(){
  const q = input.value.trim();
  window.open("https://www.google.com/search?q="+encodeURIComponent(q || "Nirale AI"), "_blank");
  plusMenu.classList.remove("open");
}
function openMap(){
  const q = input.value.trim() || "Google Maps";
  window.open("https://www.google.com/maps/search/"+encodeURIComponent(q), "_blank");
  plusMenu.classList.remove("open");
}
function upgrade(){
  alert("Upgrade plans: Free ₹0, Plus ₹499, Pro ₹999. Payment gateway can be connected separately.");
}
function toggleAccount(){
  document.getElementById("accountPop").classList.toggle("open");
}
function openAuth(mode){
  authMode = mode;
  document.getElementById("auth").classList.add("open");
  document.getElementById("accountPop").classList.remove("open");
  switchAuth(mode);
}
function closeAuth(){
  document.getElementById("auth").classList.remove("open");
}
function switchAuth(mode){
  authMode = mode;
  document.getElementById("authTitle").textContent =
    mode === "login" ? "Login to Nirale AI" : "Create your Nirale AI account";
  document.getElementById("authMessage").textContent = "";
  document.getElementById("authSwitch").innerHTML =
    mode === "login"
      ? `Don't have an account? <a onclick="switchAuth('signup')">Create account</a>`
      : `Already have an account? <a onclick="switchAuth('login')">Login</a>`;
}
async function submitAuth(){
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const out = document.getElementById("authMessage");
  if(!email || !password){ out.textContent="Enter email and password."; return; }

  const r = await fetch(authMode === "login" ? "/api/login" : "/api/signup", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({email,password})
  });
  const d = await r.json();
  if(!d.ok){ out.textContent=d.error || "Something went wrong."; return; }
  closeAuth();
  await loadMe();
  await loadRecents();
}
async function logout(){
  await fetch("/api/logout",{method:"POST"});
  document.getElementById("accountPop").classList.remove("open");
  await loadMe();
}
async function loadMe(){
  const d = await fetch("/api/me").then(r=>r.json());
  const email = document.getElementById("accountEmail");
  const plan = document.getElementById("accountPlan");
  const avatar = document.getElementById("avatar");
  if(d.logged_in){
    email.textContent=d.email;
    plan.textContent=d.plan;
    avatar.textContent=(d.email[0]||"N").toUpperCase();
  }else{
    email.textContent="Guest";
    plan.textContent="4 free questions";
    avatar.textContent="G";
  }
}
async function loadRecents(){
  const box=document.getElementById("recents");
  const d=await fetch("/api/chats").then(r=>r.json());
  box.innerHTML="";
  (d.chats||[]).forEach(c=>{
    const row=document.createElement("div");
    row.className="recent-chat";
    row.dataset.title=c.title.toLowerCase();
    row.innerHTML=`<span class="recent-title">${escapeHtml(c.title)}</span>`;
    row.onclick=()=>loadChat(c.id);
    box.appendChild(row);
  });
}
async function loadChat(id){
  const d=await fetch("/api/chats/"+id).then(r=>r.json());
  if(!d.ok)return;
  currentChatId=id;
  chatbox.innerHTML="";
  (d.messages||[]).forEach(m=>addMessage(m.role,m.content,false));
  chatbox.scrollTop=chatbox.scrollHeight;
  closeSidebar();
}
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}
function addMessage(role,text,scroll=true){
  const row=document.createElement("div");
  row.className="msg-row "+(role==="user"?"user":"assistant");
  const msg=document.createElement("div");
  msg.className="msg "+(role==="user"?"user":"assistant");
  if(role==="user"){
    msg.textContent=text;
  }else{
    msg.innerHTML=marked.parse(text);
    msg.querySelectorAll("pre code").forEach(block=>{
      try{hljs.highlightElement(block)}catch(e){}
      const pre=block.parentElement;
      pre.classList.add("code-wrap");
      const b=document.createElement("button");
      b.className="copy-code";
      b.textContent="Copy";
      b.onclick=()=>navigator.clipboard.writeText(block.innerText);
      pre.appendChild(b);
    });
  }
  row.appendChild(msg);
  chatbox.appendChild(row);
  if(scroll) chatbox.scrollTop=chatbox.scrollHeight;
}
function thinkingLanguage(text){
  if(/[ಕ-ೞ]/.test(text)) return "ಯೋಚಿಸುತ್ತಿದೆ...";
  if(/[अ-ह]/.test(text)) return "सोच रहा हूँ...";
  if(/[అ-హ]/.test(text)) return "ఆలోచిస్తోంది...";
  if(/[அ-ஹ]/.test(text)) return "யோசிக்கிறது...";
  if(/[അ-ഹ]/.test(text)) return "ചിന്തിക്കുന്നു...";
  return "Thinking...";
}
function handleKey(e){
  if(e.key==="Enter" && !e.shiftKey){
    e.preventDefault();
    sendMessage();
  }
}
async function sendMessage(){
  const text=input.value.trim();
  if(!text)return;
  plusMenu.classList.remove("open");
  input.value="";
  input.style.height="auto";

  const welcome=document.getElementById("welcome");
  if(welcome) welcome.remove();

  addMessage("user",text);

  const t=document.createElement("div");
  t.className="thinking";
  t.textContent=thinkingLanguage(text);
  chatbox.appendChild(t);
  chatbox.scrollTop=chatbox.scrollHeight;

  try{
    const r=await fetch("/api/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:text,chat_id:currentChatId})
    });
    const d=await r.json();
    t.remove();

    if(d.error==="LOGIN_REQUIRED"){
      openAuth("login");
      return;
    }
    if(!d.ok){
      addMessage("assistant",d.error||"Something went wrong.");
      return;
    }

    currentChatId=d.chat_id||currentChatId;
    addMessage("assistant",d.answer||"");
    await loadRecents();

    if(d.guest_count===4){
      setTimeout(()=>openAuth("login"),400);
    }
  }catch(e){
    t.remove();
    addMessage("assistant","Connection error. Please try again.");
  }
}
function voiceInput(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){
    alert("Voice input is not supported in this browser.");
    return;
  }
  const rec=new SR();
  rec.lang="kn-IN";
  rec.interimResults=false;
  rec.onstart=()=>document.getElementById("micBtn").textContent="🔴";
  rec.onend=()=>document.getElementById("micBtn").textContent="🎙️";
  rec.onerror=()=>document.getElementById("micBtn").textContent="🎙️";
  rec.onresult=e=>{
    input.value += (input.value?" ":"")+e.results[0][0].transcript;
    input.focus();
  };
  rec.start();
}
document.getElementById("chatSearchInput").addEventListener("input",function(){
  const q=this.value.toLowerCase().trim();
  document.querySelectorAll(".recent-chat").forEach(x=>{
    x.style.display=(!q || x.dataset.title.includes(q))?"flex":"none";
  });
});
document.getElementById("messageInput").addEventListener("input",function(){
  this.style.height="auto";
  this.style.height=Math.min(this.scrollHeight,150)+"px";
});
document.addEventListener("click",function(e){
  if(!e.target.closest(".plus-menu") && !e.target.closest(".round")){
    plusMenu.classList.remove("open");
  }
});
window.addEventListener("resize",()=>{
  if(window.innerWidth>700){
    overlay.classList.remove("open");
    sidebar.classList.remove("open");
  }
});
loadMe();
loadRecents();
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML
