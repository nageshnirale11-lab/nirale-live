import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import google.generativeai as genai


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI()


# =========================================================
# API KEY
# =========================================================

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)


# =========================================================
# REQUEST MODEL
# =========================================================

class ChatRequest(BaseModel):
    message: str


# =========================================================
# HOME PAGE
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    return """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Nirale AI</title>

<style>

* {
    box-sizing: border-box;
}

html,
body {
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
    background: #131314;
}


/* ================= HEADER ================= */

.header {
    height: 58px;
    min-height: 58px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    padding: 0 12px;

    background: #1e1e1f;
    border-bottom: 1px solid #333;
}

.left,
.right {
    display: flex;
    align-items: center;
    gap: 8px;
}

.logo {
    color: white;
    font-size: 18px;
    font-weight: bold;
}

.icon {
    width: 40px;
    height: 40px;

    border: none;
    border-radius: 50%;

    background: transparent;
    color: white;

    font-size: 22px;

    cursor: pointer;
}

.icon:hover {
    background: #333;
}


/* PLUS BUTTON */

.plus {
    width: 40px;
    height: 40px;

    border: none;
    border-radius: 50%;

    background: #333;
    color: white;

    font-size: 25px;

    cursor: pointer;
}

.plus:hover {
    background: #444;
}


/* ================= MENU ================= */

.menu {
    display: none;

    position: fixed;

    top: 62px;
    right: 10px;

    width: 190px;

    padding: 6px;

    background: #1e1e1f;

    border: 1px solid #444;
    border-radius: 12px;

    z-index: 9999;
}

.menu.show {
    display: block;
}

.menu button {
    width: 100%;

    padding: 12px;

    border: none;

    background: transparent;
    color: white;

    text-align: left;

    border-radius: 8px;

    cursor: pointer;

    font-size: 14px;
}

.menu button:hover {
    background: #333;
}


/* ================= CHAT ================= */

.chat {
    flex: 1;

    overflow-y: auto;

    padding: 15px;

    display: flex;
    flex-direction: column;

    gap: 12px;
}

.message {
    max-width: 85%;

    padding: 11px 14px;

    border-radius: 14px;

    font-size: 15px;

    line-height: 1.5;

    word-break: break-word;
}

.bot {
    align-self: flex-start;

    background: #1e1e1f;

    border: 1px solid #333;
}

.user {
    align-self: flex-end;

    background: #2b2c2d;

    color: white;
}


/* ================= INPUT ================= */

.input-area {
    min-height: 70px;

    padding: 10px;

    display: flex;
    align-items: center;

    gap: 7px;

    background: #131314;

    border-top: 1px solid #222;
}

.input {
    flex: 1;

    min-width: 0;

    height: 45px;

    padding: 0 15px;

    border-radius: 23px;

    border: 1px solid #444;

    outline: none;

    background: #1e1e1f;

    color: white;

    font-size: 15px;
}

.input::placeholder {
    color: #999;
}

.mic {
    width: 45px;
    height: 45px;

    flex-shrink: 0;

    border-radius: 50%;

    border: 1px solid #444;

    background: #2b2c2d;

    color: white;

    font-size: 18px;

    cursor: pointer;
}

.send {
    height: 45px;

    padding: 0 17px;

    flex-shrink: 0;

    border: none;

    border-radius: 23px;

    background: #ff4444;

    color: white;

    font-weight: bold;

    cursor: pointer;
}


/* ================= MOBILE ================= */

@media (max-width: 600px) {

    .header {
        height: 54px;
        min-height: 54px;
        padding: 0 7px;
    }

    .logo {
        font-size: 16px;
    }

    .icon,
    .plus {
        width: 38px;
        height: 38px;
    }

    .chat {
        padding: 10px;
    }

    .message {
        max-width: 92%;
        font-size: 14px;
    }

    .input-area {
        min-height: 66px;
        padding: 8px;
        gap: 5px;
    }

    .input {
        height: 44px;
        font-size: 14px;
    }

    .mic {
        width: 44px;
        height: 44px;
    }

    .send {
        height: 44px;
        padding: 0 13px;
        font-size: 13px;
    }
}

</style>

</head>


<body>

<div class="app">


    <!-- HEADER -->

    <div class="header">

        <div class="left">

            <button
                class="icon"
                onclick="menuAlert()">
                ☰
            </button>

            <div class="logo">
                ✨ Nirale AI
            </div>

        </div>


        <div class="right">

            <button
                class="plus"
                onclick="newChat()"
                title="New Chat">
                +
            </button>

            <button
                class="icon"
                onclick="toggleMenu()"
                title="More">
                ⋮
            </button>

        </div>

    </div>


    <!-- THREE DOT MENU -->

    <div
        id="menu"
        class="menu">

        <button onclick="upgrade()">
            ⭐ Upgrade
        </button>

        <button onclick="aboutNirale()">
            ℹ About Nirale AI
        </button>

    </div>


    <!-- CHAT -->

    <div
        id="chat"
        class="chat">

        <div class="message bot">
            Hello! I am Nirale AI.
            How can I help you today?
        </div>

    </div>


    <!-- INPUT -->

    <div class="input-area">

        <button
            class="mic"
            onclick="startSpeech()"
            title="Voice Input">
            🎤
        </button>

        <input
            id="input"
            class="input"
            type="text"
            placeholder="Type a message..."
            autocomplete="off">

        <button
            class="send"
            onclick="sendMessage()">
            Send
        </button>

    </div>

</div>


<script>


// =========================================================
// MENU
// =========================================================

function toggleMenu() {

    const menu =
        document.getElementById("menu");

    menu.classList.toggle("show");
}


function menuAlert() {

    alert("Nirale AI Menu");

}


// =========================================================
// UPGRADE
// =========================================================

function upgrade() {

    alert(
        "Nirale AI Upgrade\\n\\nPremium features coming soon."
    );

    toggleMenu();
}


// =========================================================
// ABOUT
// =========================================================

function aboutNirale() {

    alert(
        "Nirale AI v1.0"
    );

    toggleMenu();
}


// =========================================================
// NEW CHAT
// =========================================================

function newChat() {

    const chat =
        document.getElementById("chat");

    chat.innerHTML = `
        <div class="message bot">
            Hello! I am Nirale AI.
            How can I help you today?
        </div>
    `;
}


// =========================================================
// VOICE
// =========================================================

function startSpeech() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        alert(
            "Speech recognition is not supported in this browser."
        );

        return;
    }

    const recognition =
        new SpeechRecognition();

    recognition.lang = "kn-IN";

    recognition.onresult =
        function(event) {

            document.getElementById("input").value =
                event.results[0][0].transcript;

        };

    recognition.start();
}


// =========================================================
// SEND MESSAGE
// =========================================================

async function sendMessage() {

    const input =
        document.getElementById("input");

    const chat =
        document.getElementById("chat");

    const text =
        input.value.trim();

    if (!text) {
        return;
    }


    // USER MESSAGE

    const userMessage =
        document.createElement("div");

    userMessage.className =
        "message user";

    userMessage.textContent =
        text;

    chat.appendChild(userMessage);


    input.value = "";


    // BOT THINKING

    const botMessage =
        document.createElement("div");

    botMessage.className =
        "message bot";

    botMessage.textContent =
        "Thinking...";

    chat.appendChild(botMessage);


    chat.scrollTop =
        chat.scrollHeight;


    try {

        const response =
            await fetch(
                "/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: text
                    })
                }
            );


        const data =
            await response.json();


        if (response.ok) {

            botMessage.textContent =
                data.reply || "No response.";

        } else {

            botMessage.textContent =
                data.reply || "Server error.";

        }


    } catch (error) {

        botMessage.textContent =
            "Connection error.";

    }


    chat.scrollTop =
        chat.scrollHeight;
}


// =========================================================
// ENTER KEY
// =========================================================

document
    .getElementById("input")
    .addEventListener(
        "keydown",
        function(event) {

            if (event.key === "Enter") {

                event.preventDefault();

                sendMessage();

            }

        }
    );

</script>

</body>

</html>
"""


# =========================================================
# CHAT API
# =========================================================

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


        message =
            request.message.strip()

        lower_message =
            message.lower()


        # =================================================
        # CREATOR QUESTION
        # =================================================

        creator_questions = [

            "who created you",
            "who made you",
            "who is your creator",
            "who created nirale ai",
            "who made nirale ai",
            "who developed you",
            "who built you",
            "who is behind nirale ai",
            "creator of nirale ai",
            "your creator",

            "ನಿನ್ನನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದ್ದಾರೆ",
            "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
            "ನಿನ್ನ creator ಯಾರು",
            "ನಿಮ್ಮ creator ಯಾರು",
            "ನಿರಲೆ ai creator ಯಾರು"

        ]


        if any(
            question in lower_message
            for question in creator_questions
        ):

            return {
                "reply":
                    "I was created by Nagesh Nirale."
            }


        # =================================================
        # GEMINI
        # =================================================

        genai.configure(
            api_key=current_key
        )


        model =
            genai.GenerativeModel(
                "gemini-3.6-flash"
            )


        response =
            model.generate_content(
                message
            )


        return {
            "reply":
                response.text
        }


    except Exception as e:

        error =
            str(e)


        if (
            "429" in error
            or "Quota" in error
        ):

            return {
                "reply":
                    "API quota limit reached."
            }


        return {
            "reply":
                "API Error: " + error
        }
