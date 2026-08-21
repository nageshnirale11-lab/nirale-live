import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI()

# Gemini API Key
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

        /* ================= HEADER ================= */

        #header {
            height: 58px;
            min-height: 58px;

            display: flex;
            align-items: center;
            justify-content: space-between;

            padding: 0 14px;

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
            color: #ffffff;
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

        /* PLUS BUTTON */

        .new-chat-btn {
            width: 40px;
            height: 40px;

            border: none;
            border-radius: 50%;

            background: #333;
            color: white;

            font-size: 24px;
            line-height: 1;

            cursor: pointer;

            display: flex;
            align-items: center;
            justify-content: center;
        }

        .new-chat-btn:hover {
            background: #444;
        }

        /* ================= SIDEBAR ================= */

        #overlay {
            display: none;

            position: fixed;
            inset: 0;

            background: rgba(0, 0, 0, 0.55);

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

        .sidebar-btn:hover {
            background: #444;
        }

        .close-btn {
            background: #ff4444;
        }

        /* ================= CHAT ================= */

        #chatbox {
            flex: 1;

            overflow-y: auto;

            padding: 18px 15px;

            display: flex;
            flex-direction: column;

            gap: 12px;

            scroll-behavior: smooth;
        }

        #chatbox::-webkit-scrollbar {
            width: 5px;
        }

        #chatbox::-webkit-scrollbar-thumb {
            background: #444;
            border-radius: 10px;
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

        /* ================= INPUT ================= */

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

        #msg:focus {
            border-color: #666;
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

        .send-btn:hover {
            background: #ff5555;
        }

        /* ================= MOBILE ================= */

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

        /* VERY SMALL PHONES */

        @media (max-width: 380px) {

            .logo {
                font-size: 15px;
            }

            .send-btn {
                padding: 0 11px;
            }

            .input-container {
                gap: 4px;
            }

            .msg {
                max-width: 94%;
            }

        }

    </style>
</head>

<body>

<div id="overlay" onclick="closeSidebar()"></div>

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


<!-- MAIN APP -->

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

            <!-- PLUS BUTTON -->
            <button class="new-chat-btn"
                    onclick="newChat()"
                    title="New Chat">
                +
            </button>

            <button class="icon-btn"
                    onclick="showInfo()"
                    title="More">
                ⋮
            </button>

        </div>

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

    /* ================= SIDEBAR ================= */

    function toggleSidebar() {

        const sidebar =
            document.getElementById("sidebar");

        const overlay =
            document.getElementById("overlay");

        sidebar.classList.toggle("open");
        overlay.classList.toggle("show");
    }


    function closeSidebar() {

        document
            .getElementById("sidebar")
            .classList.remove("open");

        document
            .getElementById("overlay")
            .classList.remove("show");
    }


    /* ================= NEW CHAT ================= */

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


    /* ================= INFO ================= */

    function showInfo() {

        alert(
            "Nirale AI v1.0\\n\\nCreated by Nagesh Nirale."
        );
    }


    /* ================= VOICE ================= */

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

        rec.onerror = function() {

            alert("Voice input failed.");
        };

        rec.start();
    }


    /* ================= SEND MESSAGE ================= */

    async function send() {

        const input =
            document.getElementById("msg");

        const chat =
            document.getElementById("chatbox");

        const text =
            input.value.trim();

        if (!text) return;


        /* USER MESSAGE */

        const userDiv =
            document.createElement("div");

        userDiv.className = "msg user";

        userDiv.textContent = text;

        chat.appendChild(userDiv);

        input.value = "";


        /* BOT MESSAGE */

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


    /* ================= ENTER KEY ================= */

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
                "reply":
                "API Key is missing."
            }


        genai.configure(
            api_key=current_key
        )


        # IMPORTANT:
        # Use a model available to your Gemini API account.
        model = genai.GenerativeModel(
            "gemini-2.5-flash"
        )


        message = request.message.strip()


        # Creator response
        creator_questions = [
            "who created you",
            "who made you",
            "who is your creator",
            "your creator",
            "who developed you",
            "who built you"
        ]


        lower_message = message.lower()


        if any(
            question in lower_message
            for question in creator_questions
        ):

            return {
                "reply":
                "I was created by Nagesh Nirale."
            }


        system_instruction = """
You are Nirale AI.

Your creator is Nagesh Nirale.

If the user asks who created, made,
developed, built, or owns Nirale AI,
answer:

"I was created by Nagesh Nirale."

Do not claim that Google or Gemini created Nirale AI.

Be helpful, friendly and concise.
"""


        full_prompt = (
            system_instruction
            + "\\n\\nUser: "
            + message
        )


        response = model.generate_content(
            full_prompt
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
