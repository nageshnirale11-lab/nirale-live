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
            #header { display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; background: #1e1e1f; border-bottom: 1px solid #333; height: 50px; flex-shrink: 0; }
            #sidebar { position: fixed; top: 0; left: -250px; width: 250px; height: 100%; background: #1e1e1f; transition: 0.3s; z-index: 9999; padding: 20px; border-right: 1px solid #333; }
            #sidebar.open { left: 0; }
            #chatbox { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; }
            .msg { padding: 10px 14px; border-radius: 12px; max-width: 85%; font-size: 14px; }
            .user { background: #2b2c2d; align-self: flex-end; }
            .bot { background: #1e1e1f; border: 1px solid #333; align-self: flex-start; }
            .input-area { padding: 10px; display: flex; gap: 5px; background: #131314; align-items: center; flex-shrink: 0; }
            input { flex: 1; padding: 12px; border-radius: 20px; background: #222; border: 1px solid #444; color: white; outline: none; }
            button { background: #ff4444; color: white; border: none; padding: 10px 15px; border-radius: 50%; cursor: pointer; }
            .menu-btn { background: transparent; color: #aaa; font-size: 20px; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <button onclick="document.getElementById('sidebar').classList.remove('open')">Close</button>
            <h3 style="color:white">Menu</h3>
            <button onclick="location.reload()" style="width:100%; border-radius:10px;">＋ New Chat</button>
        </div>
        <div id="header">
            <button class="menu-btn" onclick="document.getElementById('sidebar').classList.add('open')">☰</button>
            <span style="font-weight:bold;">Nirale AI</span>
            <button class="menu-btn" onclick="alert('Nirale AI v1.0')">⋮</button>
        </div>
        <div id="chatbox"><div class="msg bot">Hello! I am Nirale AI, created by Nagesh Nirale.</div></div>
        <div class="input-area">
            <button onclick="startSpeech()">🎤</button>
            <input type="text" id="msg" placeholder="Ask...">
            <button onclick="send()">➔</button>
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
                const text = input.value.trim();
                if(!text) return;
                document.getElementById('chatbox').innerHTML += '<div class="msg user">'+text+'</div>';
                input.value = '';
                const res = await fetch('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text}) });
                const data = await res.json();
                document.getElementById('chatbox').innerHTML += '<div class="msg bot">'+data.reply+'</div>';
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"You are Nirale AI, created by Nagesh Nirale. Always mention your creator Nagesh Nirale if asked. User: {request.message}"
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Error, try again."}
