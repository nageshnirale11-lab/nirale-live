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
        <title>Nirale AI</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            body, html { margin: 0; padding: 0; width: 100%; height: 100%; background: #131314; color: #e3e3e3; font-family: sans-serif; overflow: hidden; }
            #sidebar { position: fixed; top: 0; left: -280px; width: 280px; height: 100%; background: #1e1e1f; border-right: 1px solid #333; z-index: 5000; transition: left 0.3s ease; padding: 20px; }
            #sidebar.open { left: 0; }
            #main-chat { height: 100%; display: flex; flex-direction: column; background: #131314; }
            #top-nav { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #333; }
            #chatbox { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
            .msg { padding: 12px 16px; border-radius: 12px; max-width: 80%; }
            .user { background: #2b2c2d; align-self: flex-end; }
            .bot { background: #1e1e1f; border: 1px solid #333; }
            .input-box { padding: 15px; display: flex; gap: 10px; }
            input { flex: 1; padding: 12px; border-radius: 20px; background: #222; border: 1px solid #444; color: white; outline: none; }
            button { padding: 10px 20px; border-radius: 20px; border: none; background: #ff4444; color: white; cursor: pointer; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <h3 style="color:white">Menu</h3>
            <button onclick="newChat()" style="width:100%; padding:10px; background:#444; color:white; border:none; cursor:pointer;">＋ New Chat</button>
        </div>
        <div id="main-chat">
            <div id="top-nav">
                <button onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
                <span style="font-weight:bold">Nirale AI</span>
                <button onclick="alert('Options')">⋮</button>
            </div>
            <div id="chatbox"><div class="msg bot">Hello! I am Nirale AI.</div></div>
            <div class="input-box">
                <input type="text" id="msg" placeholder="Ask something...">
                <button onclick="send()">Send</button>
            </div>
        </div>
        <script>
            function newChat() { document.getElementById('chatbox').innerHTML = '<div class="msg bot">Hello! I am Nirale AI.</div>'; document.getElementById('sidebar').classList.remove('open'); }
            async function send() {
                const input = document.getElementById('msg');
                const text = input.value.trim();
                if(!text) return;
                document.getElementById('chatbox').innerHTML += '<div class="msg user">' + text + '</div>';
                input.value = '';
                const res = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message: text}) });
                const data = await res.json();
                document.getElementById('chatbox').innerHTML += '<div class="msg bot">' + marked.parse(data.reply) + '</div>';
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-3.5-flash')
        # ಇಲ್ಲಿ ನಿಮ್ಮ ಹೆಸರು ಸೇರಿಸಲಾಗಿದೆ
        prompt = f"You are Nirale AI, created by Nagesh Nirale. Always introduce yourself as created by Nagesh Nirale. User says: {request.message}"
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Server error. Please try again."}
