import os
import base64
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
import google.generativeai as genai

app = FastAPI()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

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
            * { box-sizing: border-box; }
            body, html { margin: 0; padding: 0; width: 100%; height: 100%; background: #131314; color: #e3e3e3; font-family: sans-serif; overflow: hidden; }
            #sidebar { position: fixed; top: 0; left: -280px; width: 280px; height: 100%; background: #1e1e1f; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 16px; gap: 12px; z-index: 5000; transition: left 0.3s ease; }
            #sidebar.open { left: 0; }
            .sidebar-header { display: flex; justify-content: space-between; align-items: center; }
            .logo-text { font-size: 16px; font-weight: bold; color: #fff; }
            .new-chat-btn { background: #2b2c2d; color: white; border: 1px solid #444; padding: 10px 14px; border-radius: 20px; cursor: pointer; text-align: left; font-size: 14px; width: 100%; display: flex; align-items: center; gap: 8px; font-weight: bold; }
            .chat-history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
            .history-item { background: #222; padding: 10px; border-radius: 8px; font-size: 13px; color: #ccc; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border: 1px solid #333; }
            .history-item:hover { background: #2b2c2d; color: #fff; }
            #main-chat { display: flex; flex-direction: column; height: 100%; width: 100%; background: #131314; position: relative; }
            #top-nav { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; border-bottom: 1px solid #222; background: #131314; height: 56px; }
            .menu-btn { background: transparent; border: none; color: #aaa; font-size: 22px; cursor: pointer; padding: 4px; }
            .menu-dropdown { position: relative; }
            .dropdown-content { display: none; position: absolute; right: 0; top: 35px; background: #1e1e1f; border: 1px solid #333; border-radius: 8px; width: 140px; z-index: 6000; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
            .dropdown-content button { width: 100%; background: transparent; border: none; color: #fff; padding: 10px 14px; text-align: left; cursor: pointer; font-size: 14px; }
            .dropdown-content button:hover { background: #2b2c2d; }
            #chatbox { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 110px; align-items: center; }
            .chat-inner { width: 100%; max-width: 800px; display: flex; flex-direction: column; gap: 12px; }
            .msg { padding: 12px 16px; border-radius: 14px; max-width: 85%; font-size: 15px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .msg img { max-width: 200px; border-radius: 8px; display: block; margin-top: 8px; }
            .input-container { position: absolute; bottom: 12px; left: 0; width: 100%; padding: 0 12px; display: flex; justify-content: center; z-index: 4000; }
            .input-box { background: #1e1e1f; padding: 6px 10px; border-radius: 30px; display: flex; align-items: center; border: 1px solid #444; width: 100%; max-width: 750px; gap: 8px; }
            input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 15px; padding: 6px 4px; }
            .icon-btn { background: transparent; border: none; color: #aaa; font-size: 18px; cursor: pointer; padding: 6px; display: flex; align-items: center; }
            .send { background: #ff4444; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }
            #login-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 7000; justify-content: center; align-items: center; }
            .modal-content { background: #1e1e1f; padding: 24px; border-radius: 12px; width: 90%; max-width: 320px; border: 1px solid #333; display: flex; flex-direction: column; gap: 12px; }
            .modal-content input { background: #131314; border: 1px solid #444; padding: 8px; border-radius: 6px; color: white; outline: none; }
            #file-name-preview { font-size: 12px; color: #ff4444; padding-left: 10px; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <div class="sidebar-header">
                <span class="logo-text">✨ Nirale AI</span>
                <button class="menu-btn" onclick="toggleSidebar()">✕</button>
            </div>
            <button class="new-chat-btn" onclick="addNewChat()">＋ New Chat</button>
            <div class="chat-history-list" id="history-list"></div>
        </div>

        <div id="login-modal">
            <div class="modal-content">
                <h3 style="margin:0; color:#fff;">Login</h3>
                <input type="text" id="username" placeholder="Username">
                <input type="password" id="password" placeholder="Password">
                <button onclick="alert('Login feature coming soon!'); closeLogin();" style="background:#ff4444; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer;">Submit</button>
                <button onclick="closeLogin()" style="background:#333; color:white; border:none; padding:6px; border-radius:6px; cursor:pointer;">Cancel</button>
            </div>
        </div>

        <div id="main-chat">
            <div id="top-nav">
                <button class="menu-btn" onclick="toggleSidebar()">☰</button>
                <span style="font-weight:bold; color:#fff;">Nirale AI</span>
                <div class="menu-dropdown">
                    <button class="menu-btn" onclick="toggleDropdown()">⋮</button>
                    <div id="dropdown-menu" class="dropdown-content">
                        <button onclick="openLogin()">🔐 Login</button>
                    </div>
                </div>
            </div>
            <div id="chatbox">
                <div class="chat-inner" id="chat-inner">
                    <div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>
                </div>
            </div>
            <div class="input-container">
                <div class="input-box">
                    <input type="file" id="file-input" accept="image/*" style="display:none" onchange="previewFile()">
                    <button class="icon-btn" onclick="document.getElementById('file-input').click()" title="Upload Photo">📷</button>
                    <button class="icon-btn" onclick="startSpeech()" title="Voice Input">🎤</button>
                    <input type="text" id="msg" placeholder="Ask Nirale AI or upload photo..." onkeypress="if(event.key === 'Enter') send()">
                    <span id="file-name-preview"></span>
                    <button class="send" onclick="send()">➔</button>
                </div>
            </div>
        </div>

        <script>
            let selectedFile = null;
            function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
            function toggleDropdown() { const m = document.getElementById('dropdown-menu'); m.style.display = m.style.display === 'block' ? 'none' : 'block'; }
            function openLogin() { document.getElementById('login-modal').style.display = 'flex'; toggleDropdown(); }
            function closeLogin() { document.getElementById('login-modal').style.display = 'none'; }
            
            function addNewChat() { 
                document.getElementById('chat-inner').innerHTML = '<div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>';
                toggleSidebar(); 
            }

            function addHistory(text) {
                const list = document.getElementById('history-list');
                const item = document.createElement('div');
                item.className = 'history-item';
                item.textContent = text;
                item.onclick = () => { toggleSidebar(); };
                list.prepend(item);
            }

            function previewFile() {
                const fileInput = document.getElementById('file-input');
                if (fileInput.files.length > 0) {
                    selectedFile = fileInput.files[0];
                    document.getElementById('file-name-preview').textContent = "📎 " + selectedFile.name;
                }
            }
            
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
                const chatInner = document.getElementById('chat-inner');
                const text = input.value.trim();
                if(!text && !selectedFile) return;

                let userHtml = '<div class="msg user">';
                if(text) userHtml += text;
                if(selectedFile) {
                    userHtml += '<br><img src="' + URL.createObjectURL(selectedFile) + '">';
                }
                userHtml += '</div>';
                chatInner.innerHTML += userHtml;
                if(text) addHistory(text);

                const formData = new FormData();
                formData.append('message', text || "Describe this image");
                if(selectedFile) {
                    formData.append('file', selectedFile);
                }

                input.value = '';
                selectedFile = null;
                document.getElementById('file-name-preview').textContent = '';
                document.getElementById('file-input').value = '';

                const botDiv = document.createElement('div');
                botDiv.className = 'msg bot';
                botDiv.textContent = 'Thinking...';
                chatInner.appendChild(botDiv);
                const chatbox = document.getElementById('chatbox');
                chatbox.scrollTop = chatbox.scrollHeight;

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if(response.ok) {
                        botDiv.innerHTML = marked.parse(data.reply);
                    } else {
                        botDiv.textContent = data.reply || 'Server Error';
                    }
                } catch(e) {
                    botDiv.textContent = 'Connection error.';
                }
                chatbox.scrollTop = chatbox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(message: str = Form(...), file: UploadFile = File(None)):
    try:
        active_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not active_key:
            return {"reply": "API Key is missing."}
        
        genai.configure(api_key=active_key)
        model = genai.GenerativeModel('gemini-3.5-flash')
        
        system_instruction = "You are Nirale AI. If anyone asks who created you or who is your creator, you must state that you were created by Nagesh Nirale."
        
        # 1.5 ಮಾಡೆಲ್‌ಗೆ ತಕ್ಕಂತೆ ಪ್ರಾಂಪ್ಟ್ ಮತ್ತು ಫೈಲ್ ಹ್ಯಾಂಡ್ಲಿಂಗ್
        contents = [f"{system_instruction}\nUser: {message}"]
        
        if file and file.filename:
            image_bytes = await file.read()
            image_part = {
                "mime_type": file.content_type,
                "data": base64.b64encode(image_bytes).decode("utf-8")
            }
            contents.append(image_part)
        
        response = model.generate_content(contents)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"API Error: {str(e)}"}
