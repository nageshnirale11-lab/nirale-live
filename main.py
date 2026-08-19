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
            * { box-sizing: border-box; }
            body { background: #131314; color: #e3e3e3; font-family: sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
            
            /* Sidebar Styling */
            #sidebar { width: 260px; background: #1e1e1f; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 15px; gap: 15px; z-index: 100; position: absolute; height: 100%; left: -260px; transition: left 0.3s ease; }
            #sidebar.open { left: 0; }
            .sidebar-header { display: flex; justify-content: space-between; align-items: center; }
            .logo-text { font-size: 16px; font-weight: bold; color: #fff; letter-spacing: 0.5px; }
            .new-chat-btn { background: #2b2c2d; color: white; border: 1px solid #444; padding: 10px 15px; border-radius: 20px; cursor: pointer; text-align: left; font-size: 14px; display: flex; align-items: center; gap: 8px; width: 100%; }
            .new-chat-btn:hover { background: #3c3d3e; }
            .history-title { font-size: 12px; color: #aaa; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }
            #history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 5px; }
            .history-item { padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 14px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .history-item:hover { background: #2a2b2c; color: white; }

            /* Main Chat Area */
            #main-chat { flex: 1; display: flex; flex-direction: column; height: 100vh; background: #131314; position: relative; width: 100%; }
            
            /* Top Navigation Bar with 3-dot menu */
            #top-nav { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-bottom: 1px solid #222; background: #131314; }
            .menu-btn { background: transparent; border: none; color: #aaa; font-size: 22px; cursor: pointer; padding: 5px; }
            .menu-btn:hover { color: #fff; }
            
            /* 3-Dot Dropdown Menu Fixed */
            .dropdown { position: relative; display: inline-block; }
            .dropbtn { background: transparent; border: none; color: #aaa; font-size: 22px; cursor: pointer; padding: 5px 12px; border-radius: 50%; }
            .dropbtn:hover { background: #2b2c2d; color: #fff; }
            .dropdown-content { display: none; position: absolute; right: 0; top: 40px; background-color: #1e1e1f; min-width: 180px; box-shadow: 0px 8px 16px rgba(0,0,0,0.6); z-index: 1000; border: 1px solid #444; border-radius: 10px; overflow: hidden; }
            .dropdown-content a { color: #e3e3e3; padding: 12px 16px; text-decoration: none; display: block; font-size: 14px; }
            .dropdown-content a:hover { background-color: #2b2c2d; color: #fff; }
            .show { display: block; }

            #chatbox { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
            .msg { padding: 12px 18px; border-radius: 15px; max-width: 85%; font-size: 15px; line-height: 1.5; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .bot pre { background: #000000; padding: 12px; border-radius: 8px; overflow-x: auto; border: 1px solid #444; margin: 8px 0; }
            .bot code { font-family: monospace; color: #a8c7fa; font-size: 14px; }
            .msg img { max-width: 200px; border-radius: 8px; margin-top: 5px; display: block; }

            /* Input Container */
            .input-container { padding: 15px 20px; background: #131314; display: flex; justify-content: center; }
            .input-box { background: #1e1e1f; padding: 8px 15px; border-radius: 30px; display: flex; align-items: center; border: 1px solid #444; width: 100%; max-width: 800px; gap: 10px; }
            input[type="text"] { flex: 1; background: transparent; border: none; color: white; outline: none; font-size: 15px; padding: 5px; }
            .icon-btn { background: transparent; border: none; color: #aaa; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; padding: 5px; }
            .icon-btn:hover { color: white; }
            .send { background: #ff4444; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; }

            /* Upgrade Modal Styling */
            #upgrade-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 2000; justify-content: center; align-items: center; }
            .modal-content { background: #1e1e1f; padding: 30px; border-radius: 15px; border: 1px solid #444; width: 90%; max-width: 350px; display: flex; flex-direction: column; gap: 15px; text-align: center; }
            .modal-content h2 { color: white; margin: 0; font-size: 22px; }
            .modal-content p { color: #aaa; font-size: 14px; margin: 0; line-height: 1.5; }
            .modal-btn { background: #ff4444; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 15px; margin-top: 5px; }
            .modal-btn:hover { background: #ff2222; }
            .close-modal { background: #333; color: #ccc; border: none; padding: 8px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        </style>
    </head>
    <body>

        <!-- Sidebar -->
        <div id="sidebar">
            <div class="sidebar-header">
                <span class="logo-text">✨ Nirale AI</span>
                <button class="menu-btn" onclick="toggleSidebar()">✕</button>
            </div>
            <button class="new-chat-btn" onclick="newChat()">＋ New Chat</button>
            <div class="history-title">Recent Chats</div>
            <div id="history-list"></div>
        </div>

        <!-- Main Chat Area -->
        <div id="main-chat">
            <!-- Top Bar with Gemini-like 3-Dot Menu -->
            <div id="top-nav">
                <button class="menu-btn" onclick="toggleSidebar()">☰</button>
                <div class="dropdown">
                    <button onclick="toggleDropdown(event)" class="dropbtn">⋮</button>
                    <div id="myDropdown" class="dropdown-content">
                        <a href="#" onclick="showUpgradeModal()">🌟 Upgrade to Pro (₹500 / 3 Months)</a>
                        <a href="#" onclick="clearHistory()">🗑️ Clear History</a>
                        <a href="#" onclick="alert('Nirale AI v2.0 - Powered by Google Gemini API')">ℹ️ About</a>
                    </div>
                </div>
            </div>

            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI. Ask me anything or upload images to get started.</div>
            </div>

            <div class="input-container">
                <div class="input-box">
                    <input type="file" id="file-input" style="display:none" accept="image/*" onchange="handleFileSelect(event)">
                    <button class="icon-btn" title="Upload Image" onclick="document.getElementById('file-input').click()">➕</button>
                    <input type="text" id="msg" placeholder="Ask Nirale AI..." onkeypress="if(event.key === 'Enter') send()">
                    <button class="icon-btn" id="mic-btn" title="Use microphone" onclick="startSpeech()">🎤</button>
                    <button class="send" onclick="send()">➔</button>
                </div>
            </div>
        </div>

        <!-- Upgrade Modal -->
        <div id="upgrade-modal">
            <div class="modal-content">
                <h2 id="modal-title">Upgrade to Nirale AI Pro</h2>
                <p id="modal-desc">You have reached your limit. Get unlimited chats & image uploads for 3 months at just <b>₹500</b>!</p>
                <button class="modal-btn" onclick="proceedToPayment()">Pay ₹500 via UPI / Razorpay</button>
                <button class="close-modal" onclick="closeModal()">Close</button>
            </div>
        </div>

        <script>
            let questionCount = localStorage.getItem('q_count') ? parseInt(localStorage.getItem('q_count')) : 0;
            let imageCount = localStorage.getItem('img_count') ? parseInt(localStorage.getItem('img_count')) : 0;
            let isPro = localStorage.getItem('is_pro') === 'true';
            let freeTierExhausted = localStorage.getItem('free_exhausted') === 'true';
            let nextResetTime = localStorage.getItem('reset_time') ? parseInt(localStorage.getItem('reset_time')) : 0;
            let dailyQCount = localStorage.getItem('daily_q') ? parseInt(localStorage.getItem('daily_q')) : 0;
            let selectedFileBase64 = null;

            function toggleSidebar() {
                const sb = document.getElementById('sidebar');
                sb.classList.toggle('open');
            }

            function toggleDropdown(event) {
                event.stopPropagation();
                document.getElementById("myDropdown").classList.toggle("show");
            }

            window.onclick = function(event) {
                if (!event.target.matches('.dropbtn') && !event.target.matches('.dropbtn *')) {
                    var dropdowns = document.getElementsByClassName("dropdown-content");
                    for (let i = 0; i < dropdowns.length; i++) {
                        let openDropdown = dropdowns[i];
                        if (openDropdown.classList.contains('show')) {
                            openDropdown.classList.remove('show');
                        }
                    }
                }
            }

            function showUpgradeModal() {
                document.getElementById('upgrade-modal').style.display = 'flex';
                document.getElementById('myDropdown').classList.remove('show');
            }

            function closeModal() {
                document.getElementById('upgrade-modal').style.display = 'none';
            }

            function proceedToPayment() {
                window.location.href = "https://razorpay.com"; 
            }

            function handleFileSelect(event) {
                const file = event.target.files[0];
                if (!file) return;

                if (!isPro && imageCount >= 20) {
                    showUpgradeModal();
                    alert("You have reached the limit of 20 image uploads. Please recharge for unlimited access.");
                    return;
                }

                const reader = new FileReader();
                reader.onload = function(e) {
                    selectedFileBase64 = e.target.result;
                    alert("Image attached successfully: " + file.name);
                };
                reader.readAsDataURL(file);
            }

            function newChat() {
                document.getElementById('chatbox').innerHTML = '<div class="msg bot">Hello! I am Nirale AI. Ask me anything or upload images to get started.</div>';
                selectedFileBase64 = null;
                document.getElementById('sidebar').classList.remove('open');
            }

            function clearHistory() {
                localStorage.removeItem('q_count');
                localStorage.removeItem('img_count');
                localStorage.removeItem('daily_q');
                localStorage.removeItem('free_exhausted');
                localStorage.removeItem('reset_time');
                alert("History and limits reset successfully!");
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

                const now = new Date().getTime();

                if (!isPro) {
                    if (freeTierExhausted) {
                        if (now < nextResetTime) {
                            const hoursLeft = Math.ceil((nextResetTime - now) / (1000 * 60 * 60));
                            showUpgradeModal();
                            document.getElementById('modal-desc').innerHTML = `You have exhausted your 50 free questions limit. You can wait <b>${hoursLeft} hours</b> for 10 free daily questions, or recharge right now for unlimited access at just <b>₹500</b>!`;
                            return;
                        } else {
                            if (dailyQCount >= 10) {
                                nextResetTime = now + (24 * 60 * 60 * 1000);
                                localStorage.setItem('reset_time', nextResetTime);
                                showUpgradeModal();
                                return;
                            }
                        }
                    } else {
                        if (questionCount >= 50) {
                            freeTierExhausted = true;
                            localStorage.setItem('free_exhausted', 'true');
                            nextResetTime = now + (24 * 60 * 60 * 1000);
                            localStorage.setItem('reset_time', nextResetTime);
                            showUpgradeModal();
                            return;
                        }
                        questionCount++;
                        localStorage.setItem('q_count', questionCount);
                    }

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
                selectedFileBase64 = null;

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
        if not api_key:
            return {"reply": "API key not configured on server."}
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"{request.message}\n\n(Note: If this response includes any terminal commands, file paths, or code snippets, format them inside markdown code blocks using triple backticks like ```bash ... ``` so they appear cleanly formatted)."
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Server Error: {str(e)}"}
