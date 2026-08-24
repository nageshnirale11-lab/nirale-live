import os
import base64
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

app = FastAPI()

# ಇಲ್ಲಿ ನಿಮ್ಮ AIzaSy... ಕೀಲಿಯನ್ನು ಹಾಕಿ
API_KEY = "AIzaSy..."
client = genai.Client(api_key=API_KEY)

class ChatRequest(BaseModel):
    message: str
    image_data: Optional[str] = None

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        contents = ["ದಯವಿಟ್ಟು ಈ ಪ್ರಶ್ನೆಗೆ ಕನ್ನಡದಲ್ಲೇ ಉತ್ತರಿಸಿ: " + request.message]
        if request.image_data:
            contents.append({"mime_type": "image/jpeg", "data": base64.b64decode(request.image_data)})
        response = client.models.generate_content(model="gemini-2.5-flash", contents=contents)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"ದೋಷ (API Error): {str(e)}"}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="kn">
    <head>
        <meta charset="UTF-8">
        <title>ನಾಗೇಶ್ ಜೆಮಿನಿ AI</title>
        <style>
            body { margin:0; background:#131314; color:#e3e3e3; font-family:sans-serif; display:flex; height:100vh; overflow:hidden; }
            #sidebar { width: 260px; background:#1e1e1f; padding:20px; display:flex; flex-direction:column; gap:15px; border-right:1px solid #333; }
            .nav-item { cursor:pointer; padding:12px; border-radius:10px; display:flex; align-items:center; gap:10px; color:#e3e3e3; font-size:15px; }
            .nav-item:hover { background:#2b2c2d; }
            #main { flex:1; display:flex; flex-direction:column; background:#131314; position:relative; }
            #chatbox { flex:1; overflow-y:auto; padding:30px 20%; display:flex; flex-direction:column; gap:20px; }
            .msg { max-width: 85%; line-height: 1.6; font-size: 16px; padding: 14px 20px; border-radius: 20px; }
            .user-msg { align-self: flex-end; color: #fff; background: #2b2c2d; border-bottom-right-radius: 4px; }
            .bot-msg { align-self: flex-start; color: #e3e3e3; background: transparent; }
            .input-container { padding: 20px 20% 30px 20%; width: 100%; box-sizing: border-box; background: #131314; }
            .input-box { background:#1e1e1f; padding:10px 15px; border-radius:30px; display:flex; align-items:center; gap:12px; border:1px solid #444; }
            input[type="text"] { flex:1; background:transparent; border:none; color:white; outline:none; font-size:16px; padding:8px; }
            .icon-btn { cursor:pointer; color:#a8c7fa; font-size:20px; border:none; background:transparent; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; }
            .icon-btn:hover { background: #333; }
            .send-btn { background:#a8c7fa; color:#131314; border-radius:50%; border:none; width:38px; height:38px; cursor:pointer; font-weight:bold; display:flex; align-items:center; justify-content:center; font-size:16px; }
            .send-btn:hover { background:#fff; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <div class="nav-item" style="font-weight:bold; font-size:18px; color:#a8c7fa;">Gemini AI</div>
            <div class="nav-item" onclick="location.reload()">+ ಹೊಸ ಚಾಟ್ (New Chat)</div>
        </div>
        <div id="main">
            <div id="chatbox">
                <div style="text-align:center; margin-top:20vh; color:#888;">
                    <h1 style="color:#e3e3e3; font-weight:400;">ನಮಸ್ಕಾರ ನಾಗೇಶ್</h1>
                    <p>ಇವತ್ತು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?</p>
                </div>
            </div>
            <div class="input-container">
                <div class="input-box">
                    <button class="icon-btn" id="plusBtn" type="button" title="ಫೋಟೋ ಸೇರಿಸಿ">+</button>
                    <input type="file" id="fileIn" style="display:none" accept="image/*">
                    <input type="text" id="msg" placeholder="Gemini ಬಳಿ ಕನ್ನಡದಲ್ಲಿ ಕೇಳಿ...">
                    <button class="icon-btn" id="micBtn" type="button" title="ಧ್ವನಿ ಮೂಲಕ">🎤</button>
                    <button class="send-btn" id="sendBtn" type="button">➔</button>
                </div>
            </div>
        </div>
        <script>
            let imgBase64 = null;
            document.getElementById('plusBtn').onclick = () => document.getElementById('fileIn').click();
            document.getElementById('fileIn').onchange = (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (ev) => {
                        imgBase64 = ev.target.result.split(',')[1];
                        const chat = document.getElementById('chatbox');
                        chat.innerHTML += '<div class="msg user-msg">📎 [ಫೋಟೋ ಲಗತ್ತಿಸಲಾಗಿದೆ: ' + file.name + ']</div>';
                        chat.scrollTop = chat.scrollHeight;
                    };
                    reader.readAsDataURL(file);
                }
            };
            document.getElementById('micBtn').onclick = () => {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (SpeechRecognition) {
                    const rec = new SpeechRecognition();
                    rec.lang = 'kn-IN';
                    rec.onresult = (e) => { document.getElementById('msg').value = e.results[0][0].transcript; };
                    rec.start();
                } else {
                    alert('ನಿಮ್ಮ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಮೈಕ್ ಸಪೋರ್ಟ್ ಆಗುವುದಿಲ್ಲ.');
                }
            };
            async function send() {
                const input = document.getElementById('msg');
                const chat = document.getElementById('chatbox');
                const text = input.value.trim();
                if (!text && !imgBase64) return;
                
                // Clear welcome text if present
                if(chat.children.length === 1 && chat.children[0].tagName === 'DIV' && chat.children[0].style.textAlign === 'center') {
                    chat.innerHTML = '';
                }

                if (text) chat.innerHTML += '<div class="msg user-msg">' + text + '</div>';
                const currentImg = imgBase64;
                input.value = '';
                imgBase64 = null;
                document.getElementById('fileIn').value = '';

                const botDiv = document.createElement('div');
                botDiv.className = 'msg bot-msg';
                botDiv.textContent = 'ಯೋಚಿಸುತ್ತಿದೆ...';
                chat.appendChild(botDiv);
                chat.scrollTop = chat.scrollHeight;

                try {
                    const res = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ message: text || "ಈ ಚಿತ್ರವನ್ನು ವಿವರಿಸಿ", image_data: currentImg })
                    });
                    const data = await res.json();
                    botDiv.textContent = data.reply;
                } catch(e) {
                    botDiv.textContent = "ಸಂಪರ್ಕ ದೋಷ ಉಂಟಾಗಿದೆ.";
                }
                chat.scrollTop = chat.scrollHeight;
            }
            document.getElementById('sendBtn').onclick = send;
            document.getElementById('msg').onkeypress = (e) => { if (e.key === 'Enter') send(); };
        </script>
    </body>
    </html>
    """
