import os
import html

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai


app = FastAPI()

CREATOR_NAME = "Nagesh Nirale"
MODEL_NAME = "gemini-3.6-flash"


class ChatRequest(BaseModel):
    message: str


def is_creator_question(message: str) -> bool:
    text = message.lower().strip()

    questions = [
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
        "who owns nirale ai",
        "ನಿನ್ನನ್ನು ಯಾರು ಮಾಡಿದರು",
        "ನಿನ್ನನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದರು",
        "ನಿನ್ನ creator ಯಾರು",
        "ನಿರಲೆ ai creator ಯಾರು",
        "ನಿರಲೆ ai ಯಾರು create ಮಾಡಿದರು",
        "ನಿರಲೆ ai ಅನ್ನು ಯಾರು ಮಾಡಿದರು",
        "ನಿರಲೆ ai ಯನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದರು",
        "ನಿರಲೆ ai creator",
    ]

    return any(q in text for q in questions)


HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0,
maximum-scale=1.0, user-scalable=no">

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
    color: #e8eaed;
    font-family: Arial, sans-serif;
    overflow: hidden;
}

body {
    min-height: 100dvh;
}

.app {
    width: 100%;
    height: 100dvh;
    display: flex;
    flex-direction: column;
}


/* HEADER */

.header {
    height: 58px;
    min-height: 58px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    padding: 0 10px;

    background: #1e1e1f;
    border-bottom: 1px solid #333;

    z-index: 20;
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

.header-btn {
    width: 42px;
    height: 42px;

    border: 0;
    border-radius: 50%;

    background: transparent;
    color: white;

    font-size: 22px;

    display: flex;
    align-items: center;
    justify-content: center;

    cursor: pointer;
}

.header-btn:hover {
    background: #333;
}


/* SIDEBAR */

.sidebar {
    position: fixed;

    top: 0;
    left: -290px;

    width: 280px;
    height: 100dvh;

    padding: 18px;

    background: #1e1e1f;
    border-right: 1px solid #444;

    z-index: 100;

    transition: left 0.25s ease;

    box-shadow: 5px 0 25px rgba(0,0,0,0.4);
}

.sidebar.open {
    left: 0;
}

.sidebar-title {
    display: flex;
    align-items: center;
    justify-content: space-between;

    margin-bottom: 20px;
}

.sidebar-title h3 {
    margin: 0;
}

.close-sidebar {
    border: 0;
    background: transparent;
    color: white;

    font-size: 24px;
    cursor: pointer;
}

.sidebar-btn {
    width: 100%;

    margin-bottom: 10px;
    padding: 13px;

    border: 0;
    border-radius: 10px;

    background: #303133;
    color: white;

    text-align: left;
    font-size: 14px;

    cursor: pointer;
}

.sidebar-btn:hover {
    background: #3a3b3d;
}

.overlay {
    display: none;

    position: fixed;
    inset: 0;

    background: rgba(0,0,0,0.45);

    z-index: 90;
}

.overlay.open {
    display: block;
}


/* CHAT */

#chatbox {
    flex: 1;

    overflow-y: auto;

    padding: 18px;

    display: flex;
    flex-direction: column;

    gap: 13px;

    scroll-behavior: smooth;
}

.msg {
    max-width: 88%;

    padding: 12px 14px;

    border-radius: 15px;

    font-size: 15px;
    line-height: 1.55;

    word-break: break-word;
}

.user {
    align-self: flex-end;

    background: #303134;
    color: white;

    border-bottom-right-radius: 5px;
}

.bot {
    align-self: flex-start;

    background: #1e1e1f;
    color: #e8eaed;

    border: 1px solid #333;

    border-bottom-left-radius: 5px;
}

.bot p {
    margin: 0 0 10px;
}

.bot p:last-child {
    margin-bottom: 0;
}

.bot h1,
.bot h2,
.bot h3 {
    margin: 10px 0 6px;
}

.bot ul,
.bot ol {
    padding-left: 22px;
}

.bot a {
    color: #8ab4f8;
}

.bot pre {
    position: relative;

    margin: 10px 0;

    padding: 42px 14px 14px;

    background: #0d0e10;

    border: 1px solid #333;

    border-radius: 10px;

    overflow-x: auto;
}

.bot code {
    font-family: Consolas, Monaco, monospace;
    font-size: 13px;
}

.inline-code {
    padding: 2px 5px;

    background: #303134;

    border-radius: 5px;

    font-family: Consolas, Monaco, monospace;
}

.copy-code {
    position: absolute;

    top: 8px;
    right: 8px;

    padding: 5px 9px;

    border: 1px solid #555;
    border-radius: 6px;

    background: #252628;
    color: white;

    cursor: pointer;

    font-size: 12px;
}

.copy-code:hover {
    background: #3a3b3d;
}


/* PHOTO */

.photo-msg {
    padding: 7px !important;
}

.photo-preview {
    display: block;

    max-width: min(320px, 75vw);
    max-height: 360px;

    width: auto;
    height: auto;

    border-radius: 11px;

    object-fit: contain;

    margin-bottom: 6px;
}

.photo-name {
    color: #bbb;

    font-size: 12px;

    padding: 3px 5px;
}


/* FOOTER */

.footer {
    width: 100%;

    min-height: 72px;

    padding: 10px;

    background: #131314;

    border-top: 1px solid #242424;

    display: flex;
    align-items: center;

    gap: 7px;

    flex-shrink: 0;
}

.plus-btn,
.mic-btn {
    width: 45px;
    height: 45px;
    min-width: 45px;

    border-radius: 50%;

    border: 1px solid #444;

    background: #2b2c2d;
    color: white;

    display: flex;
    align-items: center;
    justify-content: center;

    cursor: pointer;
}

.plus-btn {
    font-size: 27px;
}

.mic-btn {
    font-size: 18px;
}

.mic-btn.listening {
    background: #b3261e;
}

#msg {
    flex: 1;

    min-width: 0;

    height: 45px;

    padding: 0 15px;

    border-radius: 24px;

    border: 1px solid #444;

    background: #1e1e1f;
    color: white;

    outline: none;

    font-size: 15px;
}

#msg:focus {
    border-color: #777;
}

#msg::placeholder {
    color: #999;
}

.send-btn {
    height: 45px;
    min-width: 64px;

    padding: 0 16px;

    border: 0;
    border-radius: 24px;

    background: #ff4444;
    color: white;

    font-size: 14px;
    font-weight: bold;

    cursor: pointer;
}

#photoInput {
    display: none;
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
        max-width: 94%;
        font-size: 14px;
    }

    .footer {
        min-height: 64px;

        padding: 8px 6px;

        padding-bottom:
            calc(8px + env(safe-area-inset-bottom));
    }

    .plus-btn,
    .mic-btn {
        width: 42px;
        height: 42px;
        min-width: 42px;
    }

    #msg {
        height: 42px;
        font-size: 14px;
        padding: 0 12px;
    }

    .send-btn {
        height: 42px;
        min-width: 58px;
        padding: 0 11px;
        font-size: 13px;
    }

    .photo-preview {
        max-width: 240px;
        max-height: 300px;
    }

    .sidebar {
        width: 275px;
        left: -285px;
    }
}

</style>

</head>

<body>

<div class="app">


<!-- SIDEBAR -->

<div id="sidebar" class="sidebar">

    <div class="sidebar-title">

        <h3>Menu</h3>

        <button
            class="close-sidebar"
            onclick="closeSidebar()"
        >
            ×
        </button>

    </div>

    <button
        class="sidebar-btn"
        onclick="newChat()"
    >
        ＋ New Chat
    </button>

    <button
        class="sidebar-btn"
        onclick="showUpgrade()"
    >
        ⭐ Upgrade
    </button>

    <button
        class="sidebar-btn"
        onclick="closeSidebar()"
    >
        Close Menu
    </button>

</div>


<!-- OVERLAY -->

<div
    id="overlay"
    class="overlay"
    onclick="closeSidebar()"
></div>


<!-- HEADER -->

<div class="header">

    <div class="header-left">

        <button
            class="header-btn"
            onclick="openSidebar()"
            title="Menu"
        >
            ☰
        </button>

        <span class="logo">
            ✨ Nirale AI
        </span>

    </div>

    <button
        class="header-btn"
        onclick="showUpgrade()"
        title="Upgrade"
    >
        ⋮
    </button>

</div>


<!-- CHAT -->

<div id="chatbox">

    <div class="msg bot">
        Hello! I am Nirale AI. How can I help you today?
    </div>

</div>


<!-- FOOTER -->

<div class="footer">

    <button
        class="plus-btn"
        onclick="openPhotoPicker()"
        title="Upload photo"
    >
        +
    </button>

    <input
        type="file"
        id="photoInput"
        accept="image/*"
        onchange="handlePhoto(this)"
    >

    <input
        type="text"
        id="msg"
        placeholder="Type a message..."
        autocomplete="off"
    >

    <button
        id="micBtn"
        class="mic-btn"
        onclick="startSpeech()"
        title="Voice input"
    >
        🎤
    </button>

    <button
        class="send-btn"
        onclick="send()"
    >
        Send
    </button>

</div>

</div>


<script>


/* SIDEBAR */

function openSidebar() {

    document
        .getElementById("sidebar")
        .classList.add("open");

    document
        .getElementById("overlay")
        .classList.add("open");
}


function closeSidebar() {

    document
        .getElementById("sidebar")
        .classList.remove("open");

    document
        .getElementById("overlay")
        .classList.remove("open");
}


function newChat() {

    document
        .getElementById("chatbox")
        .innerHTML =
        '<div class="msg bot">' +
        'Hello! I am Nirale AI. How can I help you today?' +
        '</div>';

    closeSidebar();
}


function showUpgrade() {

    alert(
        "Nirale AI Upgrade - Coming Soon"
    );

    closeSidebar();
}


/* PHOTO UPLOAD */

function openPhotoPicker() {

    document
        .getElementById("photoInput")
        .click();
}


function handlePhoto(input) {

    if (
        !input.files ||
        input.files.length === 0
    ) {
        return;
    }

    const file =
        input.files[0];

    if (!file.type.startsWith("image/")) {

        alert(
            "Please select an image."
        );

        input.value = "";

        return;
    }

    const reader =
        new FileReader();

    reader.onload =
        function(event) {

            const chat =
                document.getElementById(
                    "chatbox"
                );

            const photoDiv =
                document.createElement(
                    "div"
                );

            photoDiv.className =
                "msg user photo-msg";

            const image =
                document.createElement(
                    "img"
                );

            image.className =
                "photo-preview";

            image.src =
                event.target.result;

            image.alt =
                "Uploaded photo";

            const name =
                document.createElement(
                    "div"
                );

            name.className =
                "photo-name";

            name.textContent =
                file.name;

            photoDiv.appendChild(
                image
            );

            photoDiv.appendChild(
                name
            );

            chat.appendChild(
                photoDiv
            );

            chat.scrollTop =
                chat.scrollHeight;
        };

    reader.readAsDataURL(file);

    input.value = "";
}


/* MICROPHONE */

let recognition = null;
let isListening = false;


function startSpeech() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        alert(
            "Voice input is not supported by this browser. Please use Chrome."
        );

        return;
    }

    if (
        isListening &&
        recognition
    ) {

        recognition.stop();

        return;
    }

    recognition =
        new SpeechRecognition();

    recognition.lang =
        "kn-IN";

    recognition.continuous =
        false;

    recognition.interimResults =
        false;

    recognition.maxAlternatives =
        1;

    const micBtn =
        document.getElementById(
            "micBtn"
        );

    recognition.onstart =
        function() {

            isListening = true;

            micBtn.classList.add(
                "listening"
            );

            micBtn.textContent =
                "⏹";
        };

    recognition.onresult =
        function(event) {

            const transcript =
                event.results[0][0]
                .transcript;

            document
                .getElementById("msg")
                .value =
                transcript;
        };

    recognition.onerror =
        function(event) {

            console.log(
                "Speech error:",
                event.error
            );

            if (
                event.error ===
                    "not-allowed" ||
                event.error ===
                    "service-not-allowed"
            ) {

                alert(
                    "Please allow microphone permission for this site in Chrome."
                );
            }
        };

    recognition.onend =
        function() {

            isListening = false;

            micBtn.classList.remove(
                "listening"
            );

            micBtn.textContent =
                "🎤";
        };

    try {

        recognition.start();

    } catch (error) {

        console.log(error);
    }
}


/* HTML ESCAPE */

function escapeHtml(value) {

    return value.replace(
        /[&<>"']/g,
        function(char) {

            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;"
            }[char];
        }
    );
}


/* INLINE MARKDOWN */

function inlineMarkdown(text) {

    let value =
        escapeHtml(text);

    value =
        value.replace(
            /`([^`]+)`/g,
            '<span class="inline-code">$1</span>'
        );

    value =
        value.replace(
            /\*\*([^*]+)\*\*/g,
            "<strong>$1</strong>"
        );

    value =
        value.replace(
            /\*([^*]+)\*/g,
            "<em>$1</em>"
        );

    value =
        value.replace(
            /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener">$1</a>'
        );

    return value;
}


/* MARKDOWN RENDER */

function renderMarkdown(text) {

    const lines =
        text
            .replace(/\r/g, "")
            .split("\n");

    let output = "";

    let inCode = false;

    let codeLines = [];

    let listType = null;


    function closeList() {

        if (!listType) {
            return;
        }

        if (listType === "ul") {
            output += "</ul>";
        } else {
            output += "</ol>";
        }

        listType = null;
    }


    function flushCode() {

        const code =
            codeLines.join("\n");

        output +=
            '<pre>' +
            '<button class="copy-code" ' +
            'onclick="copyCode(this)">' +
            'Copy' +
            '</button>' +
            '<code>' +
            escapeHtml(code) +
            '</code>' +
            '</pre>';

        codeLines = [];
    }


    for (
        let i = 0;
        i < lines.length;
        i++
    ) {

        const line =
            lines[i];


        if (
            line.trim().startsWith("```")
        ) {

            if (inCode) {

                flushCode();

                inCode = false;

            } else {

                closeList();

                inCode = true;
            }

            continue;
        }


        if (inCode) {

            codeLines.push(line);

            continue;
        }


        if (!line.trim()) {

            closeList();

            continue;
        }


        const heading =
            line.match(
                /^(#{1,3})\s+(.*)$/
            );

        if (heading) {

            closeList();

            const level =
                heading[1].length;

            output +=
                "<h" +
                level +
                ">" +
                inlineMarkdown(
                    heading[2]
                ) +
                "</h" +
                level +
                ">";

            continue;
        }


        if (
            /^\s*[-*]\s+/.test(line)
        ) {

            if (listType !== "ul") {

                closeList();

                output += "<ul>";

                listType = "ul";
            }

            output +=
                "<li>" +
                inlineMarkdown(
                    line.replace(
                        /^\s*[-*]\s+/,
                        ""
                    )
                ) +
                "</li>";

            continue;
        }


        if (
            /^\s*\d+\.\s+/.test(line)
        ) {

            if (listType !== "ol") {

                closeList();

                output += "<ol>";

                listType = "ol";
            }

            output +=
                "<li>" +
                inlineMarkdown(
                    line.replace(
                        /^\s*\d+\.\s+/,
                        ""
                    )
                ) +
                "</li>";

            continue;
        }


        closeList();

        output +=
            "<p>" +
            inlineMarkdown(line) +
            "</p>";
    }


    if (inCode) {
        flushCode();
    }

    closeList();

    return output;
}


/* COPY CODE */

async function copyCode(button) {

    const code =
        button.parentElement
            .querySelector("code")
            .innerText;

    try {

        await navigator.clipboard.writeText(
            code
        );

        const oldText =
            button.textContent;

        button.textContent =
            "Copied";

        setTimeout(
            function() {

                button.textContent =
                    oldText;

            },
            1200
        );

    } catch (error) {

        alert(
            "Copy failed. Please copy manually."
        );
    }
}


/* SEND */

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

    chat.appendChild(
        userDiv
    );

    input.value = "";


    const botDiv =
        document.createElement("div");

    botDiv.className =
        "msg bot";

    botDiv.textContent =
        "Thinking...";

    chat.appendChild(
        botDiv
    );

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

                    body:
                        JSON.stringify({
                            message: text
                        })
                }
            );


        const data =
            await response.json();


        if (response.ok) {

            botDiv.innerHTML =
                renderMarkdown(
                    data.reply ||
                    "No response."
                );

        } else {

            botDiv.textContent =
                "Error: " +
                (
                    data.reply ||
                    "Server error"
                );
        }


    } catch (error) {

        botDiv.textContent =
            "Connection error.";

        console.error(error);
    }


    chat.scrollTop =
        chat.scrollHeight;
}


/* ENTER KEY */

document
    .getElementById("msg")
    .addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter"
            ) {

                event.preventDefault();

                send();
            }
        }
    );

</script>

</body>
</html>
"""


@app.get(
    "/",
    response_class=HTMLResponse
)
async def read_root():

    return HTML_PAGE


@app.post("/chat")
async def chat(request: ChatRequest):

    try:

        message = request.message.strip()

        if not message:

            return {
                "reply":
                    "Please enter a message."
            }


        if is_creator_question(message):

            return {
                "reply":
                    "I was created by Nagesh Nirale."
            }


        current_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )


        if not current_key:

            return {
                "reply":
                    "API Key is missing. Please set GEMINI_API_KEY in Render Environment Variables."
            }


        genai.configure(
            api_key=current_key
        )


        model = genai.GenerativeModel(
            MODEL_NAME
        )


        system_instruction = """
You are Nirale AI.

Answer the user's question naturally,
accurately and helpfully.

Use the same language as the user
whenever practical.

Your creator is Nagesh Nirale.

Only mention Nagesh Nirale when the
user specifically asks who created,
made, developed, built, or owns
Nirale AI.

Do not claim that Google created
Nirale AI.

For programming questions:

- Give accurate answers.
- Use Markdown when useful.
- Put commands and code inside
  fenced code blocks.
- Make code easy to copy and paste.
- Do not put # before every normal
  line of code.
- If the user asks for complete code,
  provide complete code.
- Explain steps clearly.
"""


        full_prompt = (
            system_instruction
            + "\n\nUser: "
            + message
        )


        response = model.generate_content(
            full_prompt
        )


        reply = getattr(
            response,
            "text",
            None
        )


        if not reply:

            reply = (
                "I could not generate a response."
            )


        return {
            "reply": reply
        }


    except Exception as e:

        error_message = str(e)


        if (
            "429" in error_message
            or "Quota exceeded" in error_message
        ):

            return {
                "reply":
                    "API quota limit reached. Please check your Gemini API quota."
            }


        return {
            "reply":
                "API Error: "
                + error_message
        }
