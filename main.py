import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

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
            #chatbox { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 110px; }
            .msg { padding: 12px 16px; border-radius: 14px; max-width: 85%; font-size: 15px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .input-container { position: absolute; bottom: 12px; left: 0; width: 100%; padding: 0 12px; display: flex; justify-content: center; z-index: 4000; }
            .input-box { background: #1e1e1f; padding: 6px 10px; border-radius: 30px; display: flex; align-items: center; border: 1px solid #444; width: 100%; max-width: 750px; gap: 8px; }
            input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 15px; padding: 6px 4px; }
            .icon-btn { background: transparent; border: none; color: #aaa; cursor: pointer; font-size: 20px; display: flex; align-items: center; justify-content: center; padding: 4px; }
            .icon-btn:hover { color: white; }
            .send { background: #ff4444; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }
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
        <div id="main-chat">
            <div id="top-nav">
                <button class="menu-btn" onclick="toggleSidebar()">☰</button>
                <span style="font-weight:bold; color:#fff;">Nirale AI</span>
            </div>
            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI. Ask me anything.</div>
            </div>
            <div class="input-container">
                <div class="input-box">
                    <input type="text" id="msg" placeholder="Ask Nirale AI..." onkeypress="if(event.key === 'Enter') send()">
                    <button class="icon-btn" title="Microphone" onclick="startSpeech()">🎤</button>
                    <button class="send" onclick="send()">➔</button>
                </div>
            </div>
        </div>
        <script>
            function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
            function newChat() { document.getElementById('chatbox').innerHTML = '<div class="msg bot">Hello! I am Nirale AI. Ask me anything.</div>'; toggleSidebar(); }
            
            function startSpeech() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) { alert("Speech recognition not supported."); return; }
                const recognition = new SpeechRecognition();
                recognition.lang = 'en-US';
                recognition.onresult = function(event) {
                    document.getElementById('msg').value = event.results[0][0].transcript;
                };
                recognition.start();
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
        current_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not current_key:
            return {"reply": "API Key missing in environment."}
        
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"API Error: {str(e)}"}
