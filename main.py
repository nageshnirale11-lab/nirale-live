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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nirale AI</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            body, html { margin:0; padding:0; background:#131314; color:#fff; font-family:sans-serif; height:100%; overflow:hidden; }
            #sidebar { position:fixed; left:-280px; width:280px; height:100%; background:#1e1e1f; border-right:1px solid #333; transition:0.3s; z-index:1000; padding:20px; box-sizing: border-box; }
            #sidebar.open { left:0; }
            #main-chat { height:100%; display:flex; flex-direction:column; background:#131314; }
            #top-nav { display:flex; justify-content:space-between; align-items:center; padding:15px; border-bottom:1px solid #333; background:#1e1e1f; }
            #chatbox { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:15px; }
            .msg { padding:12px 16px; border-radius:15px; max-width:80%; word-break: break-word; }
            .user { background:#444; align-self:flex-end; }
            .bot { background:#222; border:1px solid #444; align-self:flex-start; }
            .input-area { padding:15px; display:flex; gap:10px; align-items:center; background:#131314; }
            input { flex:1; padding:12px; border-radius:25px; border:1px solid #444; background:#222; color:white; outline:none; }
            .action-btn { background:#ff4444; border:none; color:white; padding:10px 15px; border-radius:50%; cursor:pointer; font-weight:bold; display:flex; align-items:center; justify-content:center; }
            .menu-btn { background:transparent; border:none; color:white; font-size:20px; cursor:pointer; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <h3 style="color:white; margin-top:0;">Menu</h3>
            <button onclick="location.reload()" style="width:100%; padding:10px; border-radius:10px; border:none; background:#333; color:white; cursor:pointer; font-weight:bold;">＋ New Chat</button>
        </div>
        
        <div id="main-chat">
            <div id="top-nav">
                <button class="menu-btn" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
                <span style="font-weight:bold; font-size:18px;">Nirale AI</span>
                <button class="menu-btn" onclick="alert('Nirale AI - Developed by Nagesh Nirale')">⋮</button>
            </div>
            
            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI, created by Nagesh Nirale. How can I help you?</div>
            </div>
            
            <div class="input-area">
                <button class="action-btn" onclick="startSpeech()" title="Voice Input">🎤</button>
                <input type="text" id="msg" placeholder="Ask me anything..." onkeypress="if(event.key === 'Enter') send()">
                <button class="action-btn" onclick="send()" title="Send">➔</button>
            </div>
        </div>

        <script>
            function startSpeech() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if(!SpeechRecognition) { alert("Speech recognition not supported in this browser."); return; }
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
                
                chat.innerHTML += '<div class="msg user">'+text+'</div>';
                input.value = '';
                
                const botDiv = document.createElement('div');
                botDiv.className = 'msg bot';
                botDiv.textContent = 'Thinking...';
                chat.appendChild(botDiv);
                chat.scrollTop = chat.scrollHeight;

                try {
                    const res = await fetch('/chat', { 
                        method:'POST', 
                        headers:{'Content-Type':'application/json'}, 
                        body:JSON.stringify({message:text}) 
                    });
                    const data = await res.json();
                    if(res.ok) {
                        botDiv.innerHTML = marked.parse(data.reply);
                    } else {
                        botDiv.textContent = data.reply || 'Error occurred';
                    }
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
        if not API_KEY:
            return {"reply": "API Key missing."}
        
        genai.configure(api_key=API_KEY)
        
        # ಇಲ್ಲಿ ನಿಮಗೆ ಬೇಕಾದ ಮಾಡೆಲ್ ಬಳಸಿ (ಯಾವುದು ವರ್ಕ್ ಆಗುತ್ತದೆಯೋ ಅದನ್ನು ಟ್ರೈ ಮಾಡಿ)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Your name is Nirale AI. You were exclusively created by Nagesh Nirale. Always state that you are created by Nagesh Nirale when asked about your creator. User message: {request.message}"
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}
