import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nirale AI</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            body { background: #131314; color: #e3e3e3; font-family: sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }
            #chatbox { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
            .msg { padding: 12px 18px; border-radius: 15px; max-width: 85%; font-size: 15px; line-height: 1.5; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .bot pre { background: #000000; padding: 12px; border-radius: 8px; overflow-x: auto; border: 1px solid #444; margin: 8px 0; }
            .bot code { font-family: monospace; color: #a8c7fa; font-size: 14px; }
            .input-container { padding: 15px 20px; background: #131314; display: flex; justify-content: center; }
            .input-box { background: #1e1e1f; padding: 8px 15px; border-radius: 30px; display: flex; align-items: center; border: 1px solid #444; width: 100%; max-width: 800px; gap: 10px; }
            input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 15px; padding: 5px; }
            .icon-btn { background: transparent; border: none; color: #aaa; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; padding: 5px; }
            .icon-btn:hover { color: white; }
            .send { background: #ff4444; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        </style>
    </head>
    <body>
        <div id="chatbox">
            <div class="msg bot">Hello! Ask me any Linux or programming commands, and I will format them properly for you.</div>
        </div>
        <div class="input-container">
            <div class="input-box">
                <button class="icon-btn" title="Add attachments" onclick="alert('Attachments feature coming soon!')">+</button>
                <input type="text" id="msg" placeholder="Ask Nirale AI..." onkeypress="if(event.key === 'Enter') send()">
                <button class="icon-btn" id="mic-btn" title="Use microphone" onclick="startSpeech()">🎤</button>
                <button class="send" onclick="send()">➔</button>
            </div>
        </div>
        <script>
            function startSpeech() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert("Speech recognition is not supported in this browser. Try Chrome.");
                    return;
                }
                const recognition = new SpeechRecognition();
                recognition.lang = 'en-US';
                recognition.onstart = function() {
                    document.getElementById('msg').placeholder = "Listening...";
                };
                recognition.onresult = function(event) {
                    const speechToText = event.results[0][0].transcript;
                    document.getElementById('msg').value = speechToText;
                    document.getElementById('msg').placeholder = "Ask Nirale AI...";
                };
                recognition.onerror = function() {
                    document.getElementById('msg').placeholder = "Ask Nirale AI...";
                    alert("Microphone error or permission denied.");
                };
                recognition.onend = function() {
                    document.getElementById('msg').placeholder = "Ask Nirale AI...";
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
                    botDiv.innerHTML = marked.parse(data.reply);
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
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"{request.message}\n\n(Note: If this response includes any terminal commands, file paths, or code snippets, you MUST format them inside markdown code blocks using triple backticks like ```bash ... ``` so they appear cleanly formatted)."
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Server Error: {str(e)}"}
