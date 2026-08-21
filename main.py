import os
from fastapi import FastAPI, UploadFile, File
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

.header-left {
    display: flex;
    align-items: center;
    gap: 8px;
}

.logo {
    color: white;
    font-size: 17px;
    font-weight: bold;
}

.menu-btn {
    width: 40px;
    height: 40px;

    border: 0;
    border-radius: 50%;

    background: transparent;
    color: white;

    font-size: 22px;
}


/* THREE DOT MENU */

.menu {
    display: none;

    position: fixed;

    top: 61px;
    right: 10px;

    width: 170px;

    background: #1e1e1f;

    border: 1px solid #444;
    border-radius: 12px;

    padding: 6px;

    z-index: 9999;

    box-shadow: 0 8px 30px rgba(0,0,0,0.5);
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

    font-size: 14px;
}

.menu button:hover {
    background: #333;
}


/* CHAT */

#chatbox {
    flex: 1;

    overflow-y: auto;

    padding: 15px;

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


/* INPUT BAR */

.input-container {
    width: 100%;

    min-height: 68px;

    padding: 9px;

    display: flex;

    align-items: center;

    gap: 7px;

    background: #131314;

    border-top: 1px solid #222;
}


/* ONE PLUS BUTTON */

.plus-btn {
    width: 45px;
    height: 45px;

    flex-shrink: 0;

    border-radius: 50%;

    border: 1px solid #444;

    background: #2b2c2d;

    color: white;

    font-size: 25px;

    cursor: pointer;

    display: flex;
    align-items: center;
    justify-content: center;
}


/* MESSAGE */

#msg {
    flex: 1;

    min-width: 0;

    height: 45px;

    padding: 0 15px;

    border-radius: 23px;

    background: #1e1e1f;

    border: 1px solid #444;

    color: white;

    outline: none;

    font-size: 15px;
}

#msg::placeholder {
    color: #999;
}


/* MIC */

.mic-btn {
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


/* SEND */

.send-btn {
    height: 45px;

    flex-shrink: 0;

    padding: 0 17px;

    border: 0;

    border-radius: 23px;

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

    #chatbox {
        padding: 10px;
    }

    .msg {
        max-width: 92%;
        font-size: 14px;
    }

    .input-container {
        min-height: 65px;
        padding: 8px;
        gap: 5px;
    }

    .plus-btn,
    .mic-btn {
        width: 43px;
        height: 43px;
    }

    #msg {
        height: 43px;
        font-size: 14px;
        padding: 0 12px;
    }

    .send-btn {
        height: 43px;
        padding: 0 12px;
        font-size: 13px;
    }
}

</style>
</head>


<body>

<div class="app">


    <!-- HEADER -->

    <div class="header">

        <div class="header-left">

            <button
                class="menu-btn"
                onclick="newChat()">
                ☰
            </button>

            <span class="logo">
                ✨ Nirale AI
            </span>

        </div>

        <button
            class="menu-btn"
            onclick="toggleMenu()">
            ⋮
        </button>

    </div>


    <!-- ONLY UPGRADE -->

    <div id="menu" class="menu">

        <button onclick="upgrade()">
            ⭐ Upgrade
        </button>

    </div>


    <!-- CHAT -->

    <div id="chatbox">

        <div class="msg bot">
            Hello! I am Nirale AI. How can I help you today?
        </div>

    </div>


    <!-- INPUT -->

    <div class="input-container">


        <!-- PHOTO + BUTTON -->

        <button
            class="plus-btn"
            onclick="document.getElementById('photoInput').click()"
            title="Upload photo">
            +
        </button>


        <!-- HIDDEN PHOTO INPUT -->

        <input
            type="file"
            id="photoInput"
            accept="image/*"
            style="display:none"
            onchange="photoSelected(this)"
        >


        <!-- MESSAGE -->

        <input
            type="text"
            id="msg"
            placeholder="Type a message..."
            autocomplete="off"
        >


        <!-- MIC -->

        <button
            class="mic-btn"
            onclick="startSpeech()"
            title="Voice input">
            🎤
        </button>


        <!-- SEND -->

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

    alert(
        "Nirale AI Upgrade - Coming Soon"
    );

    toggleMenu();

}


function newChat() {

    document
        .getElementById("chatbox")
        .innerHTML =
        '<div class="msg bot">Hello! I am Nirale AI. How can I help you today?</div>';

}


function photoSelected(input) {

    if (!input.files || !input.files.length) {
        return;
    }

    const file = input.files[0];

    const chat =
        document.getElementById("chatbox");

    const msg =
        document.createElement("div");

    msg.className = "msg user";

    msg.textContent =
        "📷 Photo selected: " + file.name;

    chat.appendChild(msg);

    chat.scrollTop =
        chat.scrollHeight;

}


function startSpeech() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        alert(
            "Speech recognition is not supported."
        );

        return;
    }

    const rec =
        new SpeechRecognition();

    rec.lang = "kn-IN";

    rec.onresult =
        function(event) {

            document
                .getElementById("msg")
                .value =
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

            botDiv.textContent =
                data.reply || "No response.";

        } else {

            botDiv.textContent =
                "Error: " +
                (data.reply || "Server error");

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


        # Creator name ONLY for creator questions.

        creator_questions = [

            "who created you",
            "who made you",
            "who is your creator",
            "who created nirale ai",
            "who made nirale ai",
            "who is the creator",
            "creator of nirale ai",
            "who developed you",
            "who built you",
            "your creator",

            "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
            "ನಿನ್ನನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದರು",
            "ನಿನ್ನ creator ಯಾರು",
            "ನಿರಲೆ ai creator ಯಾರು",
            "ನಿರಲೆ ai ಯಾರು create ಮಾಡಿದರು",
            "ನಿರಲೆ ai ಅನ್ನು ಯಾರು ಮಾಡಿದರು",
            "ನಿರಲೆ ai ಯನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದರು"
        ]


        if any(
            question in lower_message
            for question in creator_questions
        ):

            return {
                "reply":
                    "I was created by Nagesh Nirale."
            }


        # Prevent normal questions from changing the creator.

        system_instruction = """
You are Nirale AI.

Answer the user's question naturally and helpfully.

Your creator is Nagesh Nirale.

IMPORTANT:
Only mention Nagesh Nirale when the user specifically asks who created,
made, developed, built, or is the creator of Nirale AI.

If the user does not ask about your creator, do not mention the creator
and do not discuss Google or Gemini as your creator.
"""


        genai.configure(
            api_key=current_key
        )


        model = genai.GenerativeModel(
            "gemini-3.6-flash"
        )


        full_prompt = (
            system_instruction
            + "\n\nUser: "
            + message
        )


        response = model.generate_content(
            full_prompt
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
                "reply":
                    "API quota limit reached."
            }


        return {
            "reply":
                "API Error: "
                + error_message
        }
