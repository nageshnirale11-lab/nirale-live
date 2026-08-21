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
            html, body { margin: 0; padding: 0; width: 100%; height: 100%; background: #131314; color: #e3e3e3; font-family: sans-serif; overflow: hidden; }
            #app { display: flex; flex-direction: column; height: 100vh; width: 100vw; position: relative; }
            #header { display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; background: #1e1e1f; border-bottom: 1px solid #333; font-size: 18px; font-weight: bold; color: #fff; height: 50px; flex-shrink: 0; }
            .header-left, .header-right { display: flex; gap: 10px; align-items: center; }
            #sidebar { position: fixed; top: 0; left: -250px; width: 250px; height: 100%; background: #1e1e1f; transition: 0.3s; z-index: 9999; padding: 20px; border-right: 1px solid #333; display: flex; flex-direction: column; gap: 15px; }
            #sidebar.open { left: 0; }
            #chatbox { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 20px; }
            .msg { padding: 10px 14px; border-radius: 12px; max-width: 85%; font-size: 14px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .input-container { padding: 12px 15px; background: #131314; display: flex; gap: 10px; align-items: center; width: 100%; border-top: 1px solid #222; flex-shrink: 0; }
            input { flex: 1; padding: 12px 16px; border-radius: 24px; background: #1e1e1f; border: 1px solid #444; color: white; outline: none; font-size: 15px; min-width: 0; }
            .icon-btn { background: transparent; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; display: flex; align-items: center; justify-content: center; }
            .mic-btn { background: #2b2c2d; width: 42px; height: 42px; border-radius: 50%; border: 1px solid #444; font-size: 16px; flex-shrink: 0; }
            .send-btn { background: #ff4444; color: white; border: none; padding: 10px 18px; border-radius: 20px; font-weight: bold; font-size: 14px; cursor: pointer; flex-shrink: 0; }
        </style>
    </head>
    <body>
        <div id="app">
            <div id="sidebar">
                <h3 style="color:white; margin:0;">Menu</h3>
                <button onclick="location.reload()" style="width:100%; padding:10px; border-radius:10px; background:#333; color:white; border:none; cursor:pointer;">＋ New Chat</button>
                <button onclick="document.getElementById('sidebar').classList.remove('open')" style="width:100%; padding:10px; border-radius:10px; background:#ff4444; color:white; border:none; cursor:pointer;">Close</button>
            </div>
            <div id="header">
                <div class="header-left">
                    <button class="icon-btn" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
                    <span>✨ Nirale AI</span>
                </div>
                <div class="header-right">
                    <button class="icon-btn" onclick="location.reload()" title="New Chat">＋</button>
                    <button class="icon-btn" onclick="alert('Nirale AI v1.0')">⋮</button>
                </div>
            </div>
            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>
            </div>
            <div class="input-container">
                <button class="icon-btn mic-btn" onclick="startSpeech()" title="Voice Input">🎤</button>
                <input type="text" id="msg" placeholder="Type a message..." onkeypress="if(event.key === 'Enter') send()">
                <button class="send-btn" onclick="send()">Send</button>
            </div>
        </div>
        <script>
            function startSpeech() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if(!SpeechRecognition) { alert("Speech recognition not supported."); return; }
                const rec = new SpeechRecognition();
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
                    botDiv.textContent = 'Connection error.';
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
            return {"reply": "API Key is missing."}
        
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel('gemini-3.5-flash')
        
        prompt = f"You are Nirale AI. If anyone asks who created you or who is your creator, you must state that you were created by Nagesh Nirale. User message: {request.message}"
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Quota exceeded" in err_msg:
            return {"reply": "API Quota limit reached (20 requests per day for free tier). Please wait a moment or use another API key."}
        return {"reply": f"API Error: {err_msg}"}
