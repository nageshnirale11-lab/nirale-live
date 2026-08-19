import os
import base64
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

class ChatRequest(BaseModel):
    message: str
    image_data: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nirale AI</title>
        <style>
            body { background: #131314; color: #e3e3e3; font-family: Arial, sans-serif; display: flex; height: 100vh; margin: 0; overflow: hidden; }
            #sidebar { width: 260px; background: #1e1e1f; padding: 20px; border-right: 1px solid #333; display: flex; flex-direction: column; justify-content: space-between; }
            #main { flex: 1; display: flex; flex-direction: column; background: #131314; }
            #chatbox { flex: 1; padding: 20px 15%; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
            .msg { padding: 12px 18px; border-radius: 15px; max-width: 80%; line-height: 1.5; word-break: break-word; font-size: 15px; }
            .user { background: #2b2c2d; align-self: flex-end; color: #fff; }
            .bot { align-self: flex-start; color: #e3e3e3; background: #1e1e1f; border: 1px solid #333; }
            .input-container { padding: 20px 15%; background: #131314; }
            .input-box { background: #1e1e1f; padding: 10px 15px; border-radius: 30px; display: flex; align-items: center; gap: 10px; border: 1px solid #444; }
            input[type="text"] { flex: 1; background: transparent; border: none; color: #fff; outline: none; font-size: 16px; padding: 5px; }
            .icon-btn { background: transparent; border: none; color: #a8c7fa; font-size: 20px; cursor: pointer; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
            .icon-btn:hover { background: #333; }
            .send { background: #ff4444 !important; color: #fff; font-weight: bold; border-radius: 50%; pointer: pointer; width: 38px; height: 38px; border: none; display: flex; align-items: center; justify-content: center; }
            .send:hover { background: #d3e3fd; }
            .new-chat { color: #a8c7fa; cursor: pointer; font-size: 14px; text-decoration: underline; margin-top: 15px; display: inline-block; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <div>
                <h2>✨ Nirale AI</h2>
                <p class="new-chat" onclick="location.reload()">+ New Chat</p>
            </div>
            <div style="color: #777; font-size: 12px;">Secured & Protected</div>
        </div>
        <div id="main">
            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>
            </div>
            <div class="input-container">
                <div class="input-box">
                    <button class="icon-btn" id="plusBtn" type="button" title="Upload Image">+</button>
                    <input type="file" id="fileIn" style="display:none" accept="image/*">
                    <input type="text" id="msg" placeholder="Ask Nirale AI...">
                    <button class="icon-btn" id="micBtn" type="button" title="Voice Input">🎤</button>
                    <button class="send" id="sendBtn" type="button">&#10140;</button>
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
                        chat.innerHTML += '<div class="msg user">Image attached: ' + file.name + '</div>';
                        chat.scrollTop = chat.scrollHeight;
                    };
                    reader.readAsDataURL(file);
                }
            };

            const micBtn = document.getElementById('micBtn');
            const msgInput = document.getElementById('msg');
            try {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (SpeechRecognition) {
                    const recognition = new SpeechRecognition();
                    recognition.continuous = false;
                    recognition.interimResults = false;
                    recognition.lang = 'en-US';

                    micBtn.onclick = () => {
                        recognition.start();
                        micBtn.classList.add('listening');
                    };

                    recognition.onresult = (event) => {
                        const transcript = event.results[0][0].transcript;
                        msgInput.value = transcript;
                        micBtn.classList.remove('listening');
                    };

                    recognition.onerror = () => {
                        micBtn.classList.remove('listening');
                    };

                    recognition.onend = () => {
                        micBtn.classList.remove('listening');
                    };
                } else {
                    micBtn.onclick = () => alert('Speech recognition is not supported in this browser.');
                }
            } catch(e) {
                micBtn.onclick = () => alert('Mic error occurred.');
            }

            async function send() {
                const input = document.getElementById('msg');
                const chat = document.getElementById('chatbox');
                const text = input.value.trim();
                if(!text && !imgBase64) return;

                if(text) chat.innerHTML += '<div class="msg user">' + text + '</div>';
                
                const currentImg = imgBase64;
                input.value = '';
                imgBase64 = null;
                document.getElementById('fileIn').value = '';

                const bot = document.createElement('div');
                bot.className = 'msg bot';
                bot.textContent = 'Thinking...';
                chat.appendChild(bot);
                chat.scrollTop = chat.scrollHeight;

                try {
                    const res = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: text || "Describe this image", image_data: currentImg})
                    });
                    const data = await res.json();
                    bot.textContent = data.reply;
                } catch(e) {
                    bot.textContent = 'Error occurred!';
                }
                chat.scrollTop = chat.scrollHeight;
            }

            document.getElementById('sendBtn').onclick = send;
            document.getElementById('msg').onkeypress = (e) => { if(e.key === 'Enter') send(); };
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        user_msg = request.message.lower() if request.message else ""
        
        if any(q in user_msg for q in ["who made you", "yar nirmisidddu", "yar madiddu", "madiddu"]):
            return {"reply": "Nagesh Nirale made me."}
        if any(q in user_msg for q in ["what languages", "yava bashe", "language"]):
            return {"reply": "I can understand and communicate in many languages including Kannada, English, Hindi, and more."}

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "I am ready: Please ask again."}
