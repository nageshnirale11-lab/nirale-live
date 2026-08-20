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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nirale AI | Advanced AI Chatbot</title>
        <meta name="description" content="Nirale AI is an advanced Artificial Intelligence chatbot platform for coding, Linux, and general assistance.">
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
        <style>
            * { box-sizing: border-box; }
            body, html { margin: 0; padding: 0; width: 100%; height: 100%; background: #131314; color: #e3e3e3; font-family: sans-serif; overflow: hidden; }
            #main-chat { display: flex; flex-direction: column; height: 100%; width: 100%; background: #131314; }
            #top-nav { padding: 15px 20px; border-bottom: 1px solid #333; font-weight: bold; font-size: 18px; color: #fff; }
            #chatbox { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
            .msg { padding: 12px 16px; border-radius: 12px; max-width: 80%; }
            .user { background: #2b2c2d; align-self: flex-end; color: white; }
            .bot { background: #1e1e1f; align-self: flex-start; border: 1px solid #444; }
            .input-area { padding: 20px; display: flex; gap: 10px; background: #131314; }
            input { flex: 1; padding: 12px; border-radius: 20px; border: 1px solid #444; background: #1e1e1f; color: white; }
            button { padding: 10px 20px; border-radius: 20px; border: none; background: #ff4444; color: white; cursor: pointer; }
        </style>
    </head>
    <body>
        <div id="main-chat">
            <div id="top-nav">✨ Nirale AI</div>
            <div id="chatbox">
                <div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>
            </div>
            <div class="input-area">
                <input type="text" id="msg" placeholder="Ask Nirale AI..." onkeypress="if(event.key === 'Enter') send()">
                <button onclick="send()">Send</button>
            </div>
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
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: text})
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
            return {"reply": "API Key missing."}
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}
