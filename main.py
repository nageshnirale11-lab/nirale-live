import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Check for both possible API key environment variable names
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
        <meta name="description" content="Nirale AI is an advanced Artificial Intelligence chatbot platform created by Nagesh for programming, Linux, and general assistance.">
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
            body, html { margin: 0; padding: 0; width: 100%; height: 100%; background: #131314; color: #e3e3e3; font-family: sans-serif; overflow: hidden; }
            
            #sidebar { position: fixed; top: 0; left: -280px; width: 280px; height: 100%; background: #1e1e1f; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 16px; gap: 12px; z-index: 5000; transition: left 0.3s ease; }
            #sidebar.open { left: 0; }
            .sidebar-header { display: flex; justify-content: space-between; align-items: center; }
            .logo-text { font-size: 16px; font-weight: bold; color: #fff; }
            .new-chat-btn { background: #2b2c2d; color: white; border: 1px solid #444; padding: 10px 14px; border-radius: 20px; cursor: pointer; text-align: left; font-size: 14px; display: flex; align-items: center; gap: 8px; width: 100%; }
            .new-chat-btn:hover { background: #3c3d3e; }
            .history-title { font-size: 12px; color: #aaa; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }
            #history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
            .history-item { padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 14px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .history-item:hover { background: #2a2b2c; color: white; }

            #main-chat { display: flex; flex-direction: column; height: 100%; width: 100%; background: #131314; position: relative; }
            
            #top-nav { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; border-bottom: 1px solid #222; background: #131314; height: 56px; }
            .menu-btn { background: transparent; border: none; color: #aaa; font-size: 22px; cursor: pointer; padding: 4px; }
            .menu-btn:hover { color: #fff; }
            
            .dropdown { position: relative; display: inline-block; }
            .dropbtn { background: transparent; border: none; color: #aaa; font-size: 22px; cursor: pointer; padding: 4px 8px; border-radius: 50%; }
            .dropbtn:hover { background: #2b2c2d; color: #fff; }
            .dropdown-content { display: none; position: absolute; right: 0; top: 40px; background-color: #1e1e1f; min-width: 190px; box-shadow: 0px 8px 16px rgba(0,0,0,0.8); z-index: 6000; border: 1px solid #444; border-radius: 10px; overflow: hidden; }
            .dropdown-content a { color: #e3e3e3; padding: 12px 16px; text-decoration: none; display: block; font-size: 14px; border-bottom: 1px solid #2a2b2c; }
            .dropdown-content a:hover { background-color: #2b2c2d; color: #fff; }
            .show { display: block !important; }

            #chatbox { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 110px; }
            .msg { padding: 12px 16px; border-radius: 14px; max-width: 85%; font-size: 15px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .bot pre { background: #000; padding: 10px; border-radius: 6px; overflow-x: auto; border: 1px solid #444; margin: 6px 0; }
            .bot code { font-family: monospace; color: #a8c7fa; font-size: 13px; }
            .msg img { max-width: 200px; border-radius: 6px; margin-top: 6px; display: block; }

            .input-container { position: absolute; bottom: 12px; left: 0; width: 100%; padding: 0 12px; display: flex; flex-direction: column; gap: 6px; align-items: center; z-index: 4000; background: transparent; }
            
            #image-preview-container { display: none; width: 100%; max-width: 750px; background: #1e1e1f; padding: 6px 12px; border-radius: 10px; border: 1px solid #444; align-items: center; gap: 8px; }
            #image-preview-container img { width: 36px; height: 36px; border-radius: 4px; object-fit: cover; }
            #image-preview-container span { font-size: 13px; color: #aaa; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            #image-preview-container button { background: #333; color: #fff; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }

            .input-box { background: #1e1e1f; padding: 6px 10px; border-radius: 30px; display: flex; align-items: center; border: 1px solid #444; width: 100%; max-width: 750px; gap: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
            input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 15px; padding: 6px 4px; min-width: 0; }
            .icon-btn { background: transparent; border: none; color: #aaa; cursor: pointer; font-size: 20px; display: flex; align-items: center; justify-content: center; padding: 4px; flex-shrink: 0; }
            .icon-btn:hover { color: white; }
            .send { background: #ff4444; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; font-size: 15px; }

            #auth-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 7000; justify-content: center; align-items: center; }
            .modal-content { background: #1e1e1f; padding: 24px; border-radius: 14px; border: 1px solid #444; width: 90%; max-width: 340px; display: flex; flex-direction: column; gap: 14px; text-align: center; }
            .modal-content h2 { color: white; margin: 0; font-size: 20px; }
            .modal-content p { color: #aaa; font-size: 14px; margin: 0; line-height: 1.4; }
            .modal-input { background: #131314; border: 1px solid #444; padding: 10px; border-radius: 6px; color: white; outline: none; font-size: 14px; width: 100%; }
            .modal-btn { background: #ff4444; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }
            .close-modal { background: #333; color: #ccc; border: none; padding: 6px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        </style>
    </head>
    <body>

        <div id="sidebar">
            <div class="sidebar-header">
                <span class="logo-text">✨ Nirale AI</span>
                <button class="menu-btn" onclick="toggleSidebar()">✕</button>
            </div>
            <button class="new-chat-btn" onclick="newChat()">＋ New Chat</button>
            <div class="history-title">Recent Chats</div>
            <div id="history-list"></div>
        </div>

        <div id="main-chat">
            <div id="top-nav">
                <button class="menu-btn" onclick="toggleSidebar()">☰</button>
                <div class="dropdown">
                    <button onclick="toggleDropdown(event)" class="dropbtn">⋮</button>
                    <div id="myDropdown" class="dropdown-content">
                        <a href="javascript:void(0);" onclick="openLoginModal()">🔐 Login / Signup</a>
                        <a href="javascript:void(0);" onclick="openUpgradeModal()">🌟 Upgrade to Pro (₹450 / 3M)</a>
                        <a href="javascript:void(0);" onclick="clearHistory()">🗑️ Clear History</a>
                    </div>
                </div>
            </div>

            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI. Ask me anything or upload images to get started.</div>
            </div>

            <div class="input-container">
                <div id="image-preview-container">
                    <img id="preview-img" src="" alt="Preview">
                    <span id="preview-name">Image selected</span>
                    <button onclick="removeImage()">✕</button>
                </div>

                <div class="input-box">
                    <input type="file" id="file-input" style="display:none" accept="image/*" onchange="handleFileSelect(event)">
                    <button class="icon-btn" title="Upload Image" onclick="document.getElementById('file-input').click()">➕</button>
                    <input type="text" id="msg" placeholder="Ask Nirale AI..." onkeypress="if(event.key === 'Enter') send()">
                    <button class="icon-btn" title="Microphone" onclick="startSpeech()">🎤</button>
                    <button class="send" onclick="send()">➔</button>
                </div>
            </div>
        </div>

        <div id="auth-modal">
            <div class="modal-content">
                <h2 id="modal-title">Nirale AI Login</h2>
                <p id="modal-desc">Please enter your Gmail ID and Password.</p>
                <input type="email" id="login-email" class="modal-input" placeholder="Enter Gmail ID">
                <input type="password" id="login-pass" class="modal-input" placeholder="Enter Password">
                <button class="modal-btn" id="modal-action-btn" onclick="submitLogin()">Sign In</button>
                <button class="close-modal" onclick="closeModal()">Close</button>
            </div>
        </div>

        <script>
            let questionCount = localStorage.getItem('q_count') ? parseInt(localStorage.getItem('q_count')) : 0;
            let isLogged = localStorage.getItem('is_logged') === 'true';
            let isPro = localStorage.getItem('is_pro') === 'true';
            let selectedFileBase64 = null;

            function toggleSidebar() {
                document.getElementById('sidebar').classList.toggle('open');
            }

            function toggleDropdown(event) {
                event.stopPropagation();
                document.getElementById("myDropdown").classList.toggle("show");
            }

            window.onclick = function(event) {
                if (!event.target.matches('.dropbtn') && !event.target.matches('.dropbtn *')) {
                    var dropdowns = document.getElementsByClassName("dropdown-content");
                    for (let i = 0; i < dropdowns.length; i++) {
                        var openDropdown = dropdowns[i];
                        if (openDropdown.classList.contains('show')) {
                            openDropdown.classList.remove('show');
                        }
                    }
                }
            }

            function openLoginModal() {
                document.getElementById('auth-modal').style.display = 'flex';
                document.getElementById('modal-title').innerText = "Nirale AI Login";
                document.getElementById('modal-desc').innerText = "Please enter your Gmail ID and Password to get 30 more free questions.";
                document.getElementById('login-email').style.display = 'block';
                document.getElementById('login-pass').style.display = 'block';
                document.getElementById('modal-action-btn').innerText = "Sign In";
                document.getElementById('modal-action-btn').onclick = submitLogin;
                document.getElementById('myDropdown').classList.remove('show');
            }

            function openUpgradeModal() {
                document.getElementById('auth-modal').style.display = 'flex';
                document.getElementById('modal-title').innerText = "Upgrade to Pro";
                document.getElementById('modal-desc').innerText = "Get unlimited chats & uploads for 3 months at just ₹450!";
                document.getElementById('login-email').style.display = 'none';
                document.getElementById('login-pass').style.display = 'none';
                document.getElementById('modal-action-btn').innerText = "Pay ₹450 via Razorpay";
                document.getElementById('modal-action-btn').onclick = proceedToPayment;
                document.getElementById('myDropdown').classList.remove('show');
            }

            function closeModal() {
                document.getElementById('auth-modal').style.display = 'none';
            }

            function submitLogin() {
                const email = document.getElementById('login-email').value.trim();
                const pass = document.getElementById('login-pass').value.trim();
                if(!email.includes('@gmail.com')) {
                    alert("Please enter a valid Gmail ID.");
                    return;
                }
                if(pass.length < 4) {
                    alert("Password must be at least 4 characters.");
                    return;
                }
                isLogged = true;
                localStorage.setItem('is_logged', 'true');
                closeModal();
                alert("Login Successful! You have unlocked 30 more questions.");
            }

            function proceedToPayment() {
                window.location.href = "https://razorpay.com";
            }

            function handleFileSelect(event) {
                const file = event.target.files[0];
                if (!file) return;

                const reader = new FileReader();
                reader.onload = function(e) {
                    selectedFileBase64 = e.target.result;
                    document.getElementById('preview-img').src = selectedFileBase64;
                    document.getElementById('preview-name').innerText = file.name;
                    document.getElementById('image-preview-container').style.display = 'flex';
                };
                reader.readAsDataURL(file);
            }

            function removeImage() {
                selectedFileBase64 = null;
                document.getElementById('image-preview-container').style.display = 'none';
                document.getElementById('file-input').value = '';
            }

            function newChat() {
                document.getElementById('chatbox').innerHTML = '<div class="msg bot">Hello! I am Nirale AI. Ask me anything or upload images to get started.</div>';
                removeImage();
                document.getElementById('sidebar').classList.remove('open');
            }

            function clearHistory() {
                localStorage.removeItem('q_count');
                localStorage.removeItem('is_logged');
                alert("History cleared!");
                location.reload();
            }

            function addHistory(text) {
                const list = document.getElementById('history-list');
                const item = document.createElement('div');
                item.className = 'history-item';
                item.textContent = text;
                item.onclick = function() {
                    document.getElementById('msg').value = text;
                    document.getElementById('sidebar').classList.remove('open');
                };
                list.prepend(item);
            }

            function startSpeech() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert("Speech recognition not supported.");
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
                if(!text && !selectedFileBase64) return;

                if (!isPro) {
                    if (questionCount >= 20 && !isLogged) {
                        openLoginModal();
                        return;
                    }
                    if (questionCount >= 50 && isLogged) {
                        openUpgradeModal();
                        return;
                    }
                    questionCount++;
                    localStorage.setItem('q_count', questionCount);
                }

                let userHtml = '<div class="msg user">' + (text ? text : 'Uploaded an image') + (selectedFileBase64 ? '<br><img src="'+selectedFileBase64+'">' : '') + '</div>';
                chat.innerHTML += userHtml;
                if(text) addHistory(text);
                
                let currentText = text + (selectedFileBase64 ? " [Image Attached]" : "");
                input.value = '';
                removeImage();

                const botDiv = document.createElement('div');
                botDiv.className = 'msg bot';
                botDiv.textContent = 'Thinking...';
                chat.appendChild(botDiv);
                chat.scrollTop = chat.scrollHeight;

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: currentText})
                    });
                    const data = await response.json();
                    if(response.ok) {
                        botDiv.innerHTML = marked.parse(data.reply);
                    } else {
                        botDiv.textContent = 'Server Error: ' + (data.reply || 'Unknown error');
                    }
                } catch(e) {
                    botDiv.textContent = 'Error connecting to server. Please try again.';
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
            return {"reply": "Error: API Key not found in server environment variables."}
        
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"API Error: {str(e)}"}
