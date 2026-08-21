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
            #header { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: #1e1e1f; border-bottom: 1px solid #333; font-size: 18px; font-weight: bold; color: #fff; flex-shrink: 0; }
            #chatbox { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
            .msg { padding: 12px 16px; border-radius: 12px; max-width: 85%; font-size: 15px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .input-box { padding: 12px 10px; background: #131314; display: flex; gap: 6px; justify-content: center; align-items: center; flex-shrink: 0; }
            input { flex: 1; padding: 12px 15px; border-radius: 24px; background: #1e1e1f; border: 1px solid #444; color: white; outline: none; font-size: 15px; min-width: 0; }
            button { padding: 10px 16px; border-radius: 24px; background: #ff4444; color: white; border: none; cursor: pointer; font-weight: bold; font-size: 14px; flex-shrink: 0; }
            .mic-btn { background: #2b2c2d; border: 1px solid #444; font-size: 18px; padding: 10px; border-radius: 50%; }
        </style>
    </head>
    <body>
        <div id="header">
            <span>✨ Nirale AI</span>
        </div>
        <div id="chatbox">
            <div class="msg bot">Hello! I am Nirale AI, created by Nagesh Nirale. How can I help you today?</div>
        </div>
        <div class="input-box">
            <button class="mic-btn" onclick="startSpeech()" title="Voice Input">🎤</button>
            <input type="text" id="msg" placeholder="Type a message..." onkeypress="if(event.key === 'Enter') send()">
            <button onclick="send()">Send</button>
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
                    botDiv.textContent = data.reply || 'Server error';
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
        active_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not active_key:
            return {"reply": "API Key is missing."}
        genai.configure(api_key=active_key)
        model = genai.GenerativeModel('gemini-3.5-flash')
        # ಇಲ್ಲಿ ನೇರವಾಗಿ ನಿಮ್ಮ ಹೆಸರು ಬರುವಂತೆ ಸೆಟ್ ಮಾಡಲಾಗಿದೆ
        prompt = f"You are Nirale AI. You were created by Nagesh Nirale. If asked, clearly state 'I was created by Nagesh Nirale'. User message: {request.message}"
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}
