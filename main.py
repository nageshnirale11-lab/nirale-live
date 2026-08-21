import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# API Key check
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
        <style>
            body { margin:0; background:#131314; color:#fff; font-family:sans-serif; height:100vh; display:flex; flex-direction:column; }
            #chatbox { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:15px; }
            .msg { padding:12px 18px; border-radius:15px; max-width:85%; }
            .user { background:#444; align-self:flex-end; }
            .bot { background:#222; align-self:flex-start; border:1px solid #444; }
            .input-area { padding:20px; background:#131314; display:flex; gap:10px; }
            input { flex:1; padding:12px; border-radius:20px; border:1px solid #555; background:#222; color:#fff; }
            button { padding:10px 20px; border-radius:20px; border:none; background:#ff4444; color:#fff; cursor:pointer; }
        </style>
    </head>
    <body>
        <div id="chatbox"><div class="msg bot">Hello! I am Nirale AI. How can I help you?</div></div>
        <div class="input-area">
            <input type="text" id="msg" placeholder="Ask me...">
            <button onclick="send()">Send</button>
        </div>
        <script>
            async function send() {
                const input = document.getElementById('msg');
                const text = input.value.trim();
                if(!text) return;
                document.getElementById('chatbox').innerHTML += '<div class="msg user">' + text + '</div>';
                input.value = '';
                try {
                    const res = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: text})
                    });
                    const data = await res.json();
                    document.getElementById('chatbox').innerHTML += '<div class="msg bot">' + (data.reply || 'Error') + '</div>';
                } catch(e) {
                    document.getElementById('chatbox').innerHTML += '<div class="msg bot" style="color:red">Connection Failed!</div>';
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        if not API_KEY: return {"reply": "API Key Error"}
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Limit Reached or Server Error. Please check API Key."}
