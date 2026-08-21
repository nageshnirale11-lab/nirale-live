import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import google.generativeai as genai


# =========================================================
# APP
# =========================================================

app = FastAPI()


# =========================================================
# GEMINI API KEY
# =========================================================

API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

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
async def read_root():

    return """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width,
               initial-scale=1.0,
               maximum-scale=1.0,
               user-scalable=no">

<title>Nirale AI</title>


<style>

* {
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
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


body {

    display: flex;

    justify-content: center;
}


.app-container {

    width: 100%;
    height: 100dvh;

    max-width: 900px;

    display: flex;
    flex-direction: column;

    background: #131314;

    position: relative;
}


/* =========================================================
   HEADER
   ========================================================= */

#header {

    height: 58px;
    min-height: 58px;

    display: flex;

    align-items: center;
    justify-content: space-between;

    padding: 0 12px;

    background: #1e1e1f;

    border-bottom: 1px solid #333;

    position: relative;

    z-index: 10;
}


.header-left,
.header-right {

    display: flex;

    align-items: center;

    gap: 8px;
}


.logo {

    font-size: 18px;

    font-weight: bold;

    color: white;

    white-space: nowrap;
}


.icon-btn {

    width: 40px;
    height: 40px;

    display: flex;

    align-items: center;
    justify-content: center;

    background: transparent;

    border: none;

    color: white;

    font-size: 22px;

    cursor: pointer;

    border-radius: 50%;
}


.icon-btn:hover {

    background: #333;
}


/* PLUS */

.new-chat-btn {

    width: 40px;
    height: 40px;

    border: none;

    border-radius: 50%;

    background: #333;

    color: white;

    font-size: 25px;

    cursor: pointer;

    display: flex;

    align-items: center;
    justify-content: center;
}


.new-chat-btn:hover {

    background: #444;
}


/* =========================================================
   SIDEBAR
   ========================================================= */

#overlay {

    display: none;

    position: fixed;

    inset: 0;

    background: rgba(0,0,0,0.55);

    z-index: 99;
}


#overlay.show {

    display: block;
}


#sidebar {

    position: fixed;

    top: 0;

    left: -280px;

    width: 280px;

    height: 100dvh;

    background: #1e1e1f;

    z-index: 100;

    padding: 20px;

    border-right: 1px solid #333;

    transition: left 0.25s ease;

    display: flex;

    flex-direction: column;

    gap: 14px;
}


#sidebar.open {

    left: 0;
}


.sidebar-title {

    color: white;

    margin: 0 0 10px 0;
}


.sidebar-btn {

    width: 100%;

    padding: 13px;

    border: none;

    border-radius: 10px;

    background: #333;

    color: white;

    font-size: 15px;

    cursor: pointer;
}


.close-btn {

    background: #ff4444;
}


/* =========================================================
   MORE MENU
   ========================================================= */

.more-menu {

    display: none;

    position: fixed;

    top: 62px;

    right: 10px;

    width: 190px;

    background: #1e1e1f;

    border: 1px solid #444;

    border-radius: 12px;

    padding: 6px;

    z-index: 9999;

    box-shadow: 0 8px 25px rgba(0,0,0,0.5);
}


.more-menu.show {

    display: block;
}


.more-menu button {

    width: 100%;

    padding: 12px;

    background: transparent;

    border: none;

    color: white;

    text-align: left;

    border-radius: 8px;

    font-size: 14px;

    cursor: pointer;
}


.more-menu button:hover {

    background: #333;
}


/* =========================================================
   CHAT
   ========================================================= */

#chatbox {

    flex: 1;

    overflow-y: auto;

    padding: 16px 14px;

    display: flex;

    flex-direction: column;

    gap: 12px;

    scroll-behavior: smooth;
}


.msg {

    padding: 11px 14px;

    border-radius: 14px;

    max-width: 82%;

    font-size: 15px;

    line-height: 1.5;

    word-wrap: break-word;

    overflow-wrap: break-word;
}


.user {

    background: #2b2c2d;

    align-self: flex-end;

    color: white;

    border-bottom-right-radius: 5px;
}


.bot {

    background: #1e1e1f;

    align-self: flex-start;

    border: 1px solid #333;

    color: #e3e3e3;

    border-bottom-left-radius: 5px;
}


/* =========================================================
   INPUT
   ========================================================= */

.input-container {

    min-height: 72px;

    padding: 10px 12px;

    background: #131314;

    display: flex;

    align-items: center;

    gap: 8px;

    width: 100%;

    border-top: 1px solid #222;
}


#msg {

    flex: 1;

    height: 46px;

    padding: 0 16px;

    border-radius: 23px;

    background: #1e1e1f;

    border: 1px solid #444;

    color: white;

    outline: none;

    font-size: 15px;

    min-width: 0;
}


#msg::placeholder {

    color: #888;
}


.mic-btn {

    width: 46px;
    height: 46px;

    flex-shrink: 0;

    background: #2b2c2d;

    border: 1px solid #444;

    border-radius: 50%;

    font-size: 18px;
}


.send-btn {

    height: 46px;

    padding: 0 18px;

    border-radius: 23px;

    background: #ff4444;

    color: white;

    border: none;

    font-weight: bold;

    font-size: 14px;

    cursor: pointer;

    flex-shrink: 0;
}


/* =========================================================
   MOBILE
   ========================================================= */

@media (max-width: 600px) {

    #header {

        height: 54px;

        min-height: 54px;

        padding: 0 8px;
    }


    .logo {

        font-size: 16px;
    }


    .icon-btn,
    .new-chat-btn {

        width: 38px;

        height: 38px;
    }


    #chatbox {

        padding: 12px 10px;

        gap: 10px;
    }


    .msg {

        max-width: 90%;

        font-size: 14px;

        padding: 10px 12px;
    }


    .input-container {

        min-height: 68px;

        padding: 8px;

        gap: 6px;
    }


    #msg {

        height: 44px;

        font-size: 14px;

        padding: 0 13px;
    }


    .mic-btn {

        width: 44px;

        height: 44px;
    }


    .send-btn {

        height: 44px;

        padding: 0 14px;

        font-size: 13px;
    }

}


@media (max-width: 380px) {

    .logo {

        font-size: 15px;
    }


    .send-btn {

        padding: 0 11px;
    }

}

</style>

</head>


<body>


<div id="overlay"
     onclick="closeSidebar()">
</div>


<!-- SIDEBAR -->

<div id="sidebar">

    <h3 class="sidebar-title">
        Nirale AI
    </h3>


    <button class="sidebar-btn"
            onclick="newChat()">

        ＋ New Chat

    </button>


    <button class="sidebar-btn close-btn"
            onclick="closeSidebar()">

        Close

    </button>

</div>


<!-- MAIN -->

<div class="app-container">


    <!-- HEADER -->

    <div id="header">


        <div class="header-left">


            <button class="icon-btn"
                    onclick="toggleSidebar()">

                ☰

            </button>


            <span class="logo">

                ✨ Nirale AI

            </span>


        </div>


        <div class="header-right">


            <button class="new-chat-btn"
                    onclick="newChat()"
                    title="New Chat">

                +

            </button>


            <button class="icon-btn"
                    onclick="showMenu()"
                    title="More">

                ⋮

            </button>


        </div>


    </div>


    <!-- MORE MENU -->

    <div id="moreMenu"
         class="more-menu">


        <button onclick="upgrade()">

            ⭐ Upgrade

        </button>


        <button onclick="showInfo()">

            ℹ About Nirale AI

        </button>


    </div>


    <!-- CHAT -->

    <div id="chatbox">


        <div class="msg bot">

            Hello! I am Nirale AI.
            How can I help you today?

        </div>


    </div>


    <!-- INPUT -->

    <div class="input-container">


        <button class="icon-btn mic-btn"
                onclick="startSpeech()"
                title="Voice Input">

            🎤

        </button>


        <input
            type="text"
            id="msg"
            placeholder="Type a message..."
            autocomplete="off"
        >


        <button class="send-btn"
                onclick="send()">

            Send

        </button>


    </div>


</div>


<script>


/* =========================================================
   SIDEBAR
   ========================================================= */

function toggleSidebar() {

    document
        .getElementById("sidebar")
        .classList.toggle("open");


    document
        .getElementById("overlay")
        .classList.toggle("show");
}


function closeSidebar() {

    document
        .getElementById("sidebar")
        .classList.remove("open");


    document
        .getElementById("overlay")
        .classList.remove("show");
}


/* =========================================================
   NEW CHAT
   ========================================================= */

function newChat() {

    const chat =
        document.getElementById("chatbox");


    chat.innerHTML = "";


    const welcome =
        document.createElement("div");


    welcome.className = "msg bot";


    welcome.textContent =
        "Hello! I am Nirale AI. How can I help you today?";


    chat.appendChild(welcome);


    closeSidebar();
}


/* =========================================================
   MORE MENU
   ========================================================= */

function showMenu() {

    document
        .getElementById("moreMenu")
        .classList.toggle("show");
}


function upgrade() {

    alert(
        "Nirale AI Upgrade\\n\\nPremium features coming soon."
    );


    document
        .getElementById("moreMenu")
        .classList.remove("show");
}


function showInfo() {

    alert(
        "Nirale AI v1.0\\n\\nCreated by Nagesh Nirale."
    );


    document
        .getElementById("moreMenu")
        .classList.remove("show");
}


/* =========================================================
   VOICE
   ========================================================= */

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


    const rec =
        new SpeechRecognition();


    rec.lang = "kn-IN";


    rec.interimResults = false;


    rec.onresult = function(event) {

        document.getElementById("msg").value =
            event.results[0][0].transcript;
    };


    rec.start();
}


/* =========================================================
   SEND
   ========================================================= */

async function send() {

    const input =
        document.getElementById("msg");


    const chat =
        document.getElementById("chatbox");


    const text =
        input.value.trim();


    if (!text) return;


    const userDiv =
        document.createElement("div");


    userDiv.className = "msg user";


    userDiv.textContent = text;


    chat.appendChild(userDiv);


    input.value = "";


    const botDiv =
        document.createElement("div");


    botDiv.className = "msg bot";


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
                    "Content-Type":
                        "application/json"
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
                "Error: " +
                (data.reply ||
                 "Server error");
        }


    } catch (error) {

        botDiv.textContent =
            "Connection error. Please check the server.";

    }


    chat.scrollTop =
        chat.scrollHeight;
}


/* =========================================================
   ENTER KEY
   ========================================================= */

document
    .getElementById("msg")
    .addEventListener(
        "keydown",
        function(event) {

            if (event.key === "Enter") {

                event.preventDefault();

                send();
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


        message = request.message.strip()


        lower_message =
            message.lower()


        # =================================================
        # CREATOR ANSWER ONLY WHEN ASKED
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
            "who is the creator of nirale ai",
            "your creator",
            "creator of nirale ai",

            # Kannada

            "ನಿನ್ನನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದ್ದಾರೆ",
            "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
            "ನಿನ್ನ creator ಯಾರು",
            "ನಿಮ್ಮ creator ಯಾರು",
            "ನಿರಲೆ ai ಯನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದ್ದಾರೆ",
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


        model = genai.GenerativeModel(
            "gemini-3.6-flash"
        )


        response = model.generate_content(
            message
        )


        return {
            "reply": response.text
        }


    except Exception as e:

        err_msg = str(e)


        if (
            "429" in err_msg
            or "Quota exceeded" in err_msg
        ):

            return {
                "reply":
                    "API quota limit reached."
            }


        return {
            "reply":
                f"API Error: {err_msg}"
        }
