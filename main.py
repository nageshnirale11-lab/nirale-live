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

<meta name="viewport"
      content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

<title>Nirale AI</title>

<style>

* {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background: #131314;
    color: #e3e3e3;
    font-family: Arial, sans-serif;
    overflow: hidden;
}

.app {
    width: 100%;
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
}


/* HEADER */

.header {
    height: 56px;
    min-height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 10px;
    background: #1e1e1f;
    border-bottom: 1px solid #333;
}

.header-left,
.header-right {
    display: flex;
    align-items: center;
    gap: 6px;
}

.logo {
    color: white;
    font-size: 17px;
    font-weight: bold;
}

.icon-btn {
    width: 40px;
    height: 40px;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: white;
    font-size: 22px;
    cursor: pointer;
}

.icon-btn:hover {
    background: #333;
}

.plus-btn {
    width: 40px;
    height: 40px;
    border: 0;
    border-radius: 50%;
    background: #333;
    color: white;
    font-size: 25px;
    cursor: pointer;
}

.plus-btn:hover {
    background: #444;
}


/* MENU */

.menu {
    display: none;
    position: fixed;
    top: 60px;
    right: 10px;
    width: 190px;
    background: #1e1e1f;
    border: 1px solid #444;
    border-radius: 12px;
    padding: 6px;
    z-index: 9999;
}

.menu.open {
    display: block;
}

.menu button {
    width: 100%;
    padding: 12px;
    border: 0;
    background: transparent;
    color: white;
    text-align: left;
    border-radius: 8px;
    cursor: pointer;
}

.menu button:hover {
    background: #333;
}


/* CHAT */

#chatbox {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.msg {
    max-width: 85%;
    padding: 10px 14px;
    border-radius: 13px;
    font-size: 14px;
    line-height: 1.5;
    word-break: break-word;
}

.user {
    align-self: flex-end;
    background: #2b2c2d;
    color: white;
}

.bot {
    align-self: flex-start;
    background: #1e1e1f;
    border: 1px solid #333;
    color: #e3e3e3;
}


/* INPUT */

.input-container {
    width: 100%;
    min-height: 68px;
    padding: 9px 10px;
    display: flex;
    align-items: center;
    gap: 7px;
    background: #131314;
    border-top: 1px solid #222;
}

#msg {
    flex: 1;
    min-width: 0;
    height: 44px;
    padding: 0 15px;
    border-radius: 22px;
    background: #1e1e1f;
    border: 1px solid #444;
    color: white;
    outline: none;
    font-size: 15px;
}

.mic-btn {
    flex-shrink: 0;
    background: #2b2c2d;
    border: 1px solid #444;
}

.send-btn {
    flex-shrink: 0;
    height: 44px;
    padding: 0 16px;
    border-radius: 22px;
    border: none;
    background: #ff4444;
    color: white;
    font-weight: bold;
    cursor: pointer;
}


/* MOBILE */

@media (max-width: 600px) {

    .header {
        height: 54px;
        min-height: 54px;
        padding: 0 6px;
    }

    .logo {
        font-size: 16px;
    }

    .icon-btn,
    .plus-btn {
        width: 38px;
        height: 38px;
    }

    #chatbox {
        padding: 10px;
    }

    .msg {
        max-width: 92%;
        font-size: 14px;
    }

    .input-container {
        min-height: 64px;
        padding: 8px;
    }

    #msg {
        height: 44px;
        font-size: 14px;
    }

    .mic-btn {
        width: 44px;
        height: 44px;
    }

    .send-btn {
        height: 44px;
        padding: 0 13px;
        font-size: 13px;
    }
}

</style>

</head>

<body>

<div class="app">

    <div class="header">

        <div class="header-left">

            <button
                class="icon-btn"
                onclick="alert('Nirale AI Menu')">
                ☰
            </button>

            <span class="logo">
                ✨ Nirale AI
            </span>

        </div>

        <div class="header-right">

            <button
                class="plus-btn"
                onclick="newChat()"
                title="New Chat">
                +
            </button>

            <button
                class="icon-btn"
                onclick="toggleMenu()"
                title="More">
                ⋮
            </button>

        </div>

    </div>


    <div id="menu" class="menu">

        <button onclick="upgrade()">
            ⭐ Upgrade
        </button>

        <button onclick="aboutNirale()">
            ℹ About Nirale AI
        </button>

    </div>


    <div id="chatbox">

        <div class="msg bot">
            Hello! I am Nirale AI. How can I help you today?
        </div>

    </div>


    <div class="input-container">

        <button
            class="icon-btn mic-btn"
            onclick="startSpeech()"
            title="Voice Input">
            🎤
        </button>

        <input
            type="text"
            id="msg"
            placeholder="Type a message..."
            autocomplete="off">

        <button
            class="send-btn"
            onclick="send()">
            Send
        </button>

    </div>

</div>


<script>

function toggleMenu() {

    document
        .getElementById("menu")
        .classList.toggle("open");

}


function upgrade() {

    alert("Nirale AI Upgrade - Coming Soon");

    toggleMenu();

}


function aboutNirale() {

    alert("Nirale AI v1.0");

    toggleMenu();

}


function newChat() {

    document.getElementById("chatbox").innerHTML =
        '<div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>';

}


function startSpeech() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        alert("Speech recognition is not supported.");

        return;
    }

    const rec = new SpeechRecognition();

    rec.lang = "kn-IN";

    rec.onresult = function(event) {

        document.getElementById("msg").value =
            event.results[0][0].transcript;

    };

    rec.start();

}


async function send() {

    const input =
        document.getElementById("msg");

    const chat =
        document.getElementById("chatbox");

    const text =
        input.value.trim();

    if (!text) {
        return;
    }


    const userDiv =
        document.createElement("div");

    userDiv.className =
        "msg user";

    userDiv.textContent =
        text;

    chat.appendChild(userDiv);

    input.value = "";


    const botDiv =
        document.createElement("div");

    botDiv.className =
        "msg bot";

    botDiv.textContent =
        "Thinking...";

    chat.appendChild(botDiv);

    chat.scrollTop =
        chat.scrollHeight;


    try {

        const response =
            await fetch("/chat", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: text
                })

            });


        const data =
            await response.json();


        if (response.ok) {

            botDiv.textContent =
                data.reply;

        } else {

            botDiv.textContent =
                "Error: " + (data.reply || "Server error");

        }

    } catch (error) {

        botDiv.textContent =
            "Connection error.";

    }


    chat.scrollTop =
        chat.scrollHeight;

}


document
    .getElementById("msg")
    .addEventListener("keydown", function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            send();

        }

    });

</script>

</body>

</html>
"""


@app.post("/chat")
async def chat(request: ChatRequest):

    try:

        current_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        if not current_key:
            return {
                "reply": "API Key is missing."
            }


        message = request.message.strip()
        lower_message = message.lower()


        # Creator name ONLY when user asks who created/made Nirale AI

        creator_words = [
            "who created you",
            "who made you",
            "who is your creator",
            "who created nirale ai",
            "who made nirale ai",
            "creator of nirale ai",
            "who developed you",
            "who built you",
            "your creator",
            "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
            "ನಿನ್ನನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದರು",
            "ನಿನ್ನ creator ಯಾರು",
            "ನಿರಲೆ ai ಯಾರು create ಮಾಡಿದರು",
            "ನಿರಲೆ ai creator ಯಾರು"
        ]


        if any(
            word in lower_message
            for word in creator_words
        ):

            return {
                "reply": "I was created by Nagesh Nirale."
            }


        genai.configure(
            api_key=current_key
        )


        # Keep the model setting simple.
        model = genai.GenerativeModel(
            "gemini-2.5-flash"
        )


        response = model.generate_content(
            message
        )


        return {
            "reply": response.text
        }


    except Exception as e:

        error_message = str(e)

        if (
            "429" in error_message
            or "Quota exceeded" in error_message
        ):

            return {
                "reply": "API quota limit reached."
            }


        return {
            "reply": "API Error: " + error_message
        }
