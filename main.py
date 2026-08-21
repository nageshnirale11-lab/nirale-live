import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nirale AI | Advanced AI Chatbot</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
            body, html { margin: 0; padding: 0; width: 100%; height: 100%; background: #131314; color: #e3e3e3; font-family: sans-serif; overflow: hidden; }
            #sidebar { position: fixed; top: 0; left: -280px; width: 280px; height: 100%; background: #1e1e1f; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 16px; gap: 12px; z-index: 5000; transition: left 0.3s ease; }
            #sidebar.open { left: 0; }
            .sidebar-header { display: flex; justify-content: space-between; align-items: center; }
            .logo-text { font-size: 16px; font-weight: bold; color: #fff; }
            .new-chat-btn { background: #2b2c2d; color: white; border: 1px solid #444; padding: 10px 14px; border-radius: 20px; cursor: pointer; text-align: left; font-size: 14px; display: flex; align-items: center; gap: 8px; width: 100%; }
            #main-chat { display: flex; flex-direction: column; height: 100%; width: 100%; background: #131314; position: relative; }
            #top-nav { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; border-bottom: 1px solid #222; background: #131314; height: 56px; }
            .menu-btn { background: transparent; border: none; color: #aaa; font-size: 22px; cursor: pointer; padding: 4px; }
            .menu-dropdown { position: relative; }
            .dropdown-content { display: none; position: absolute; right: 0; top: 35px; background: #1e1e1f; border: 1px solid #333; border-radius: 8px; width: 160px; z-index: 6000; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
            .dropdown-content button { width: 100%; background: transparent; border: none; color: #fff; padding: 10px 14px; text-align: left; cursor: pointer; font-size: 14px; }
            .dropdown-content button:hover { background: #2b2c2d; }
            #chatbox { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 110px; }
            .msg { padding: 12px 16px; border-radius: 14px; max-width: 85%; font-size: 15px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .input-container { position: absolute; bottom: 12px; left: 0; width: 100%; padding: 0 12px; display: flex; justify-content: center; z-index: 4000; }
            .input-box { background: #1e1e1f; padding: 6px 10px; border-radius: 30px; display: flex; align-items: center; border: 1px solid #444; width: 100%; max-width: 750px; gap: 8px; }
            input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 15px; padding: 6px 4px; }
            .send { background: #ff4444; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }
            #login-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 7000; justify-content: center; align-items: center; }
            .modal-content { background: #1e1e1f; padding: 24px; border-radius: 12px; width: 90%; max-width: 350px; border: 1px solid #333; display: flex; flex-direction: column; gap: 14px; }
            .modal-content h3 { margin: 0; color: #fff; font-size: 18px; }
            .modal-content input { background: #131314; border: 1px solid #444; padding: 10px; border-radius: 6px; color: white; outline: none; }
            .modal-content button { background: #ff4444; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <div class="sidebar-header">
                <span class="logo-text">✨ Nirale AI</span>
                <button class="menu-btn" onclick="toggleSidebar()">✕</button>
            </div>
            <button class="new-chat-btn" onclick="newChat()">＋ New Chat</button>
        </div>

        <div id="login-modal">
            <div class="modal-content">
                <h3>Login to Nirale AI</h3>
                <input type="text" id="username" placeholder="Username">
                <input type="password" id="password" placeholder="Password">
                <button onclick="loginUser()">Login</button>
                <button style="background: #333;" onclick="closeLogin()">Cancel</button>
            </div>
        </div>

        <div id="main-chat">
            <div id="top-nav">
                <button class="menu-btn" onclick="toggleSidebar()">☰</button>
                <span style="font-weight:bold; color:#fff;">Nirale AI</span>
                <div class="menu-dropdown">
                    <button class="menu-btn" onclick="toggleDropdown()">⋮</button>
                    <div id="dropdown-menu" class="dropdown-content">
                        <button onclick="openLogin()">🔐 Login</button>
                    </div>
                </div>
            </div>
            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI. Ask me anything.</div>
            </div>
            <div class="input-container">
                <div class="input-box">
                    <input type="text" id="msg" placeholder="Ask Nirale AI..." onkeypress="if(event.key === 'Enter') send()">
                    <button class="send" onclick="send()">➔</button>
                </div>
            </div>
        </div>
        <script>
            function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
            function newChat() { document.getElementById('chatbox').innerHTML = '<div class="msg bot">Hello! I am Nirale AI. Ask me anything.</div>'; toggleSidebar(); }
            function toggleDropdown() { const m = document.getElementById('dropdown-menu'); m.style.display = m.style.display === 'block' ? 'none' : 'block'; }
            function openLogin() { document.getElementById('login-modal').style.display = 'flex'; toggleDropdown(); }
            function closeLogin() { document.getElementById('login-modal').style.display = 'none'; }
            function loginUser() { alert('Login successful!'); closeLogin(); }

            async function send() {
                const input = document.getElementById('msg');
                const chat = document.getElementById('chatbox');
                const text = input.value.trim();
                if(!text) return;

                chat.innerHTML += '<div class="msg user">' + text + '</div>';
                input.value = '';

                const botDiv = document.createElement('div');
                botDiv.className = 'msg bot';
                botDiv.textContent = 'Thinking...';
                chat.appendChild(botDiv);
                chat.scrollTop = chat.scrollHeight;

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: text})
                    });
                    const data = await response.json();
                    if(response.ok) {
                        botDiv.innerHTML = marked.parse(data.reply);
                    } else {
                        botDiv.textContent = 'Server Error: ' + (data.reply || 'Unknown error');
                    }
                } catch(e) {
                    botDiv.textContent = 'Error connecting to server.';
                }
                chat.scrollTop = chat.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        if not API_KEY:
            return {"reply": "API Key is missing."}
        
        genai.configure(api_key=API_KEY)
        # Using the correct stable model name gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}
