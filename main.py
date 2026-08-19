import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Nirale AI</title>
        <meta name="description" content="Nirale AI - Advanced Artificial Intelligence Platform">
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
            html, body { background: #131314; color: #e3e3e3; font-family: sans-serif; margin: 0; padding: 0; height: 100%; width: 100%; overflow: hidden; position: fixed; }
            
            #sidebar { width: 260px; background: #1e1e1f; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 15px; gap: 15px; z-index: 5000; position: fixed; height: 100%; left: -260px; top: 0; transition: left 0.3s ease; }
            #sidebar.open { left: 0; }
            .sidebar-header { display: flex; justify-content: space-between; align-items: center; }
            .logo-text { font-size: 16px; font-weight: bold; color: #fff; }
            .new-chat-btn { background: #2b2c2d; color: white; border: 1px solid #444; padding: 10px 15px; border-radius: 20px; cursor: pointer; text-align: left; font-size: 14px; display: flex; align-items: center; gap: 8px; width: 100%; }
            .new-chat-btn:hover { background: #3c3d3e; }
            .history-title { font-size: 12px; color: #aaa; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }
            #history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 5px; }
            .history-item { padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 14px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .history-item:hover { background: #2a2b2c; color: white; }

            #main-chat { display: flex; flex-direction: column; height: 100vh; width: 100vw; background: #131314; position: absolute; top: 0; left: 0; }
            
            #top-nav { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-bottom: 1px solid #222; background: #131314; min-height: 60px; }
            .menu-btn { background: transparent; border: none; color: #aaa; font-size: 24px; cursor: pointer; padding: 5px; }
            .menu-btn:hover { color: #fff; }
            
            .dropdown { position: relative; display: inline-block; }
            .dropbtn { background: transparent; border: none; color: #aaa; font-size: 24px; cursor: pointer; padding: 8px 12px; border-radius: 50%; }
            .dropbtn:hover { background: #2b2c2d; color: #fff; }
            .dropdown-content { display: none; position: absolute; right: 0; top: 45px; background-color: #1e1e1f; min-width: 210px; box-shadow: 0px 8px 16px rgba(0,0,0,0.8); z-index: 6000; border: 1px solid #444; border-radius: 12px; overflow: hidden; }
            .dropdown-content a { color: #e3e3e3; padding: 14px 18px; text-decoration: none; display: block; font-size: 14px; border-bottom: 1px solid #2a2b2c; }
            .dropdown-content a:hover { background-color: #2b2c2d; color: #fff; }
            .show { display: block !important; }

            #chatbox { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; padding-bottom: 130px; }
            .msg { padding: 12px 18px; border-radius: 15px; max-width: 85%; font-size: 15px; line-height: 1.5; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .bot pre { background: #000000; padding: 12px; border-radius: 8px; overflow-x: auto; border: 1px solid #444; margin: 8px 0; }
            .bot code { font-family: monospace; color: #a8c7fa; font-size: 14px; }
            .msg img { max-width: 200px; border-radius: 8px; margin-top: 5px; display: block; }

            /* Fixed Bottom Search / Input Container */
            .input-container { position: absolute; bottom: 15px; left: 0; width: 100%; padding: 0 12px; background: transparent; display: flex; flex-direction: column; gap: 8px; align-items: center; z-index: 4000; }
            
            /* Image Preview Container inside Input area */
            #image-preview-container { display: none; width: 100%; max-width: 800px; background: #1e1e1f; padding: 8px 12px; border-radius: 12px; border: 1px solid #444; align-items: center; gap: 10px; }
            #image-preview-container img { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; }
            #image-preview-container span { font-size: 13px; color: #aaa; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            #image-preview-container button { background: #333; color: #fff; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }

            .input-box { background: #1e1e1f; padding: 6px 10px; border-radius: 30px; display: flex; align-items: center; border: 1px solid #444; width: 100%; max-width: 800px; gap: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
            input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 16px; padding: 8px 4px; min-width: 0; }
            .icon-btn { background: transparent; border: none; color: #aaa; cursor: pointer; font-size: 20px; display: flex; align-items: center; justify-content: center; padding: 6px; flex-shrink: 0; }
            .icon-btn:hover { color: white; }
            .send { background: #ff4444; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; }

            /* Modal Styling */
            #auth-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 7000; justify-content: center; align-items: center; }
            .modal-content { background: #1e1e1f; padding: 30px; border-radius: 15px; border: 1px solid #444; width: 90%; max-width: 350px; display: flex; flex-direction: column; gap: 15px; text-align: center; }
            .modal-content h2 { color: white; margin: 0; font-size: 22px; }
            .modal-content p { color: #aaa; font-size: 14px; margin: 0; line-height: 1.5; }
            .modal-input { background: #131314; border: 1px solid #444; padding: 12px; border-radius: 8px; color: white; outline: none; font-size: 14px; width: 100%; }
            .modal-btn { background: #ff4444; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 15px; }
            .modal-btn:hover { background: #ff2222; }
            .close-modal { background: #333; color: #ccc; border: none; padding: 8px; border-radius: 8px; cursor: pointer; font-size: 13px; }
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
                <!-- Image Preview Preview Box (Appears right above search bar when image is selected) -->
                <div id="image-preview-container">
                    <img id="preview-img" src="" alt="Preview">
                    <span id="preview-name">Image selected</span>
                    <button onclick="removeImage()">✕ Remove</button>
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

        <!-- Auth / Modal -->
        <div id="auth-modal">
            <div class="modal-content">
                <h2 id="modal-title">Nirale AI Login</h2>
                <p id="modal-desc">You have completed 20 questions. Please login to get 30 more free questions.</p>
                <input type="email" id="login-email" class="modal-input" placeholder="Enter Gmail ID">
                <input type="password" id="login-pass" class="modal-input" placeholder="Enter Password">
                <button class="modal-btn" id="modal-action-btn" onclick="submitLogin()">Sign In</button>
                <button class="close-modal" onclick="closeModal()">Close</button>
            </div>
        </div>

        <script>
            let questionCount = localStorage.getItem('q_count') ? parseInt(localStorage.getItem('q_count')) : 0;
            let imageCount = localStorage.getItem('img_count') ? parseInt(localStorage.getItem('img_count')) : 0;
            let isLogged = localStorage.getItem('is_logged') === 'true';
            let isPro = localStorage.getItem('is_pro') === 'true';
            let selectedFileBase64 = null;

            function toggleSidebar() {
                document.getElementById('sidebar').classList.toggle('open');
            }

            function toggleDropdown(event) {
                event.stopPropagation();
                const dropdown = document.getElementById("myDropdown");
                dropdown.classList.toggle("show");
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
                document.getElementById('modal-desc').innerText = "You have completed your free questions. Get unlimited chats & uploads for 3 months at just ₹450!";
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

                if (!isPro && imageCount >= 20) {
                    openUpgradeModal();
                    alert("You have reached the limit of 20 image uploads. Please upgrade.");
                    return;
                }

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
                localStorage.removeItem('img_count');
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
                    alert("Speech recognition not supported in this browser.");
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

                    if (selectedFileBase64) {
                        imageCount++;
                        localStorage.setItem('img_count', imageCount);
                    }
                }

                let userHtml = '<div class="msg user">' + (text ? text : 'Uploaded an image') + (selectedFileBase64 ? '<br><img src="'+selectedFileBase64+'">' : '') + '</div>';
                chat.innerHTML += userHtml;
                if(text) addHistory(text);
                
                input.value = '';
                let currentFile = selectedFileBase64;
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
                        body: JSON.stringify({message: text + (currentFile ? " [Image Attached]" : "")})
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
        if not api_key:
            return {"reply": "API key not configured."}
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"{request.message}\n\n(Note: Format terminal commands and code inside markdown code blocks using triple backticks like ```bash ... ```)."
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Server Error: {str(e)}"}
