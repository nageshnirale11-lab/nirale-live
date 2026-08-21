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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Nirale AI</title>
        <style>
            * { box-sizing: border-box; }
            body { margin: 0; padding: 0; background: #131314; color: #e3e3e3; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
            #header { display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; background: #1e1e1f; border-bottom: 1px solid #333; font-size: 18px; font-weight: bold; color: #fff; flex-shrink: 0; height: 55px; }
            .header-left, .header-right { display: flex; gap: 10px; align-items: center; }
            #sidebar { position: fixed; top: 0; left: -260px; width: 260px; height: 100%; background: #1e1e1f; transition: 0.3s; z-index: 9999; padding: 20px; border-right: 1px solid #333; display: flex; flex-direction: column; gap: 15px; }
            #sidebar.open { left: 0; }
            #chatbox { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
            .msg { padding: 10px 14px; border-radius: 12px; max-width: 85%; font-size: 14px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .input-box { padding: 10px; background: #131314; display: flex; gap: 6px; align-items: center; flex-shrink: 0; width: 100%; }
            input { flex: 1; padding: 12px; border-radius: 20px; background: #1e1e1f; border: 1px solid #444; color: white; outline: none; font-size: 14px; min-width: 0; }
            button { padding: 10px 14px; border-radius: 20px; background: #ff4444; color: white; border: none; cursor: pointer; font-weight: bold; font-size: 13px; flex-shrink: 0; }
            .icon-btn { background: transparent; border: none; color: white; font-size: 18px; cursor: pointer; padding: 6px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <h3 style="color:white; margin:0;">Menu</h3>
            <button onclick="location.reload()" style="width:100%; border-radius:10px; background:#333;">＋ New Chat</button>
            <button onclick="document.getElementById('sidebar').classList.remove('open')" style="width:100%; border-radius:10px; background:#ff4444;">Close</button>
        </div>
        <div id="header">
            <div class="header-left">
                <button class="icon-btn" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
                <span>✨ Nirale AI</span>
            </div>
            <div class="header-right">
                <button class="icon-btn" onclick="alert('Login Required')" title="Login">⋮</button>
            </div>
        </div>
        <div id="chatbox">
            <div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>
        </div>
        <div class="input-box">
            <button class="icon-btn" onclick="location.reload()" title="New Chat">＋</button>
            <button class="icon-btn" onclick="startSpeech()" title="Voice Input">🎤</button>
            <input type="text" id="msg" placeholder="Type a message..." onkeypress="if(event.key === 'Enter') send()">
            <button onclick="send()">Send</button>
        </div>
        <script>
            function startSpeech() {
                const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                rec.lang = 'kn-IN';
                rec.onresult = (e) => { document.getElementById('msg').value = e.results[0][0].transcript; };
                rec.start();
            }
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
                        botDiv.textContent = data.reply;
                    } else {
                        botDiv.textContent = 'Error: ' + (data.reply || 'Server error');
                    }
                } catch(e) {
                    botDiv.textContent = 'Connection error. Please check server.';
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
        current_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not current_key:
            return {"reply": "API Key is missing in environment variables."}
        
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel('gemini-3.6-flash')
        
        prompt = f"You are Nirale AI. If anyone asks who created you or who is your creator, you must state that you were created by Nagesh Nirale. User message: {request.message}"
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"API Error: {str(e)}"}
