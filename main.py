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
        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <style>
            body { background: #131314; color: #e3e3e3; font-family: sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
            
            /* Sidebar Styling */
            #sidebar { width: 260px; background: #1e1e1f; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 15px; gap: 15px; }
            .new-chat-btn { background: #2b2c2d; color: white; border: 1px solid #444; padding: 10px 15px; border-radius: 20px; cursor: pointer; text-align: left; font-size: 14px; display: flex; align-items: center; gap: 8px; }
            .new-chat-btn:hover { background: #3c3d3e; }
            .history-title { font-size: 12px; color: #aaa; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }
            #history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 5px; }
            .history-item { padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 14px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .history-item:hover { background: #2a2b2c; color: white; }

            /* Top Bar & Login */
            #top-bar { position: absolute; top: 15px; right: 20px; display: flex; align-items: center; z-index: 10; }

            /* Main Chat Area Styling */
            #main-chat { flex: 1; display: flex; flex-direction: column; height: 100vh; background: #131314; position: relative; }
            #chatbox { flex: 1; overflow-y: auto; padding: 20px; padding-top: 60px; display: flex; flex-direction: column; gap: 15px; }
            .msg { padding: 12px 18px; border-radius: 15px; max-width: 80%; font-size: 15px; line-height: 1.5; word-break: break-word; }
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

        <!-- Sidebar -->
        <div id="sidebar">
            <button class="new-chat-btn" onclick="newChat()">＋ New Chat</button>
            <div class="history-title">Recent Chats</div>
            <div id="history-list"></div>
        </div>

        <!-- Main Chat -->
        <div id="main-chat">
            <!-- Google Login Button Top Right -->
            <div id="top-bar">
                <div id="g_id_onload"
                     data-client_id="871572564566-kuia506dos7nl6asrotga5t0ii44f0n7.apps.googleusercontent.com"
                     data-callback="handleCredentialResponse">
                </div>
                <div class="g_id_signin" data-type="standard" data-shape="pill" data-theme="filled_black"></div>
            </div>

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
        </div>

        <script>
            function handleCredentialResponse(response) {
                console.log("Encoded JWT ID token: " + response.credential);
                alert("Successfully logged in with Google!");
            }

            function newChat() {
                document.getElementById('chatbox').innerHTML = '<div class="msg bot">Hello! Ask me any Linux or programming commands, and I will format them properly for you.</div>';
            }

            function addHistory(text) {
                const list = document.getElementById('history-list');
                const item = document.createElement('div');
                item.className = 'history-item';
                item.textContent = text;
                item.onclick = function() {
                    document.getElementById('msg').value = text;
                };
                list.prepend(item);
            }

            function startSpeech() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert("Speech recognition not supported. Use Chrome.");
                    return;
                }
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
                addHistory(text);
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
