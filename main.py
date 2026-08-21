import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# Direct API configuration to avoid environment issues
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
            body { margin: 0; padding: 0; background: #131314; color: #e3e3e3; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; }
            #chatbox { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
            .msg { padding: 12px 16px; border-radius: 12px; max-width: 80%; font-size: 15px; line-height: 1.4; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .input-box { padding: 12px; background: #131314; display: flex; gap: 8px; justify-content: center; }
            input { flex: 1; max-width: 700px; padding: 12px; border-radius: 24px; background: #1e1e1f; border: 1px solid #444; color: white; outline: none; font-size: 15px; }
            button { padding: 0 20px; border-radius: 24px; background: #ff4444; color: white; border: none; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div id="chatbox">
            <div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>
        </div>
        <div class="input-box">
            <input type="text" id="msg" placeholder="Type a message..." onkeypress="if(event.key === 'Enter') send()">
            <button onclick="send()">Send</button>
        </div>
        <script>
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
                    if(response.ok) {
                        botDiv.textContent = data.reply;
                    } else {
                        botDiv.textContent = 'Error: ' + (data.reply || 'Server error');
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
            return {"reply": "API Key is missing."}
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}
