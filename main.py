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
        <!-- Marked.js for Markdown parsing -->
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            body { background: #131314; color: #e3e3e3; font-family: sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }
            #chatbox { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
            .msg { padding: 12px 18px; border-radius: 15px; max-width: 85%; font-size: 15px; line-height: 1.5; word-break: break-word; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #333; color: #e3e3e3; }
            .bot pre { background: #000; padding: 10px; border-radius: 8px; overflow-x: auto; border: 1px solid #444; }
            .bot code { font-family: monospace; color: #a8c7fa; }
            .input-area { padding: 20px; background: #131314; display: flex; gap: 10px; }
            input { flex: 1; padding: 15px; border-radius: 25px; border: 1px solid #444; background: #1e1e1f; color: white; outline: none; }
            button { padding: 10px 20px; border-radius: 25px; border: none; background: #ff4444; color: white; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div id="chatbox">
            <div class="msg bot">Hello! Ask me any Linux or programming commands, and I will format them properly for you.</div>
        </div>
        <div class="input-area">
            <input type="text" id="msg" placeholder="Ask Nirale AI..." onkeypress="if(event.key === 'Enter') send()">
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
        prompt = f"{request.message}\n\n(Note: If this requires any terminal commands or code, please provide them strictly inside markdown code blocks like ```bash ... ``` so they are easy to copy)."
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Sorry, I am having trouble processing that right now."}
