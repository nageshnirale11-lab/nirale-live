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
      content="width=device-width,
               initial-scale=1.0,
               maximum-scale=1.0,
               user-scalable=no">

<title>Nirale AI</title>

<!-- Markdown renderer -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<!-- HTML sanitizer -->
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.6/dist/purify.min.js"></script>

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

.app {
    width: 100%;
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
}


/* ================= HEADER ================= */

.header {
    height: 56px;
    min-height: 56px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    padding: 0 10px;

    background: #1e1e1f;

    border-bottom: 1px solid #333;

    z-index: 100;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 8px;
}

.logo {
    font-size: 17px;
    font-weight: bold;
    color: white;
}

.header-btn {
    width: 40px;
    height: 40px;

    border: 0;
    background: transparent;

    color: white;

    border-radius: 50%;

    font-size: 22px;

    display: flex;
    align-items: center;
    justify-content: center;

    cursor: pointer;
}

.header-btn:hover {
    background: #303134;
}


/* ================= SIDEBAR ================= */

.sidebar {
    position: fixed;

    top: 0;
    left: -285px;

    width: 280px;
    height: 100vh;
    height: 100dvh;

    background: #1e1e1f;

    border-right: 1px solid #444;

    z-index: 10000;

    padding: 18px;

    transition: left 0.25s ease;

    box-shadow: 5px 0 25px rgba(0,0,0,0.4);
}

.sidebar.open {
    left: 0;
}

.sidebar-title {
    display: flex;
    justify-content: space-between;
    align-items: center;

    margin-bottom: 20px;
}

.sidebar-title h3 {
    margin: 0;
    color: white;
}

.close-sidebar {
    border: 0;
    background: transparent;
    color: white;
    font-size: 22px;
    cursor: pointer;
}

.sidebar-btn {
    width: 100%;

    padding: 13px;

    margin-bottom: 10px;

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

    z-index: 9999;
}

.overlay.open {
    display: block;
}


/* ================= CHAT ================= */

#chatbox {
    flex: 1;

    overflow-y: auto;

    padding: 16px;

    display: flex;

    flex-direction: column;

    gap: 12px;

    scroll-behavior: smooth;
}

.msg {
    max-width: 88%;

    padding: 12px 15px;

    border-radius: 14px;

    font-size: 14px;

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


/* ================= MARKDOWN ================= */

.bot-content {
    width: 100%;
}

.bot-content p {
    margin: 0 0 12px 0;
}

.bot-content p:last-child {
    margin-bottom: 0;
}

.bot-content h1,
.bot-content h2,
.bot-content h3,
.bot-content h4 {
    margin: 16px 0 9px;
    color: white;
    line-height: 1.3;
}

.bot-content h1 {
    font-size: 22px;
}

.bot-content h2 {
    font-size: 19px;
}

.bot-content h3 {
    font-size: 17px;
}

.bot-content ul,
.bot-content ol {
    margin: 8px 0 12px 20px;
    padding: 0;
}

.bot-content li {
    margin: 5px 0;
}

.bot-content strong {
    color: white;
}

.bot-content a {
    color: #8ab4f8;
}


/* ================= CODE BLOCK ================= */

.code-wrapper {
    position: relative;

    margin: 12px 0;

    border: 1px solid #3c4043;

    border-radius: 10px;

    overflow: hidden;

    background: #0d0e0f;
}

.code-header {
    height: 36px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding: 0 10px;

    background: #252628;

    border-bottom: 1px solid #3c4043;

    color: #aaa;

    font-size: 12px;
}

.copy-code-btn {
    border: 1px solid #555;

    background: #303134;

    color: #eee;

    border-radius: 6px;

    padding: 5px 9px;

    font-size: 12px;

    cursor: pointer;
}

.copy-code-btn:hover {
    background: #414246;
}

.code-wrapper pre {
    margin: 0;

    padding: 14px;

    overflow-x: auto;

    white-space: pre;

    font-family:
        Consolas,
        Monaco,
        "Courier New",
        monospace;

    font-size: 13px;

    line-height: 1.55;
}

.code-wrapper code {
    color: #e8eaed;
}

.inline-code {
    background: #303134;

    border: 1px solid #444;

    border-radius: 5px;

    padding: 2px 5px;

    font-family: monospace;

    font-size: 13px;
}


/* ================= TABLE ================= */

.bot-content table {
    width: 100%;

    border-collapse: collapse;

    margin: 12px 0;

    overflow: hidden;
}

.bot-content th,
.bot-content td {
    border: 1px solid #444;

    padding: 8px;

    text-align: left;
}

.bot-content th {
    background: #303134;
}


/* ================= PHOTO ================= */

.photo-msg {
    padding: 7px !important;
}

.photo-preview {
    display: block;

    max-width: 280px;
    max-height: 320px;

    width: auto;
    height: auto;

    border-radius: 10px;

    object-fit: contain;

    margin-bottom: 6px;
}

.photo-name {
    font-size: 12px;
    color: #bbb;
    padding: 3px 5px;
}


/* ================= FOOTER ================= */

.footer {
    width: 100%;

    min-height: 70px;

    padding: 9px 10px;

    background: #131314;

    border-top: 1px solid #242424;

    display: flex;

    align-items: center;

    gap: 7px;

    flex-shrink: 0;
}


/* PLUS */

.plus-btn {
    width: 45px;
    height: 45px;

    min-width: 45px;

    border-radius: 50%;

    border: 1px solid #444;

    background: #2b2c2d;

    color: white;

    font-size: 26px;

    cursor: pointer;

    display: flex;

    align-items: center;
    justify-content: center;
}

.plus-btn:active {
    transform: scale(0.95);
}


/* INPUT */

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
    border-color: #666;
}

#msg::placeholder {
    color: #999;
}


/* MIC */

.mic-btn {
    width: 45px;
    height: 45px;

    min-width: 45px;

    border-radius: 50%;

    border: 1px solid #444;

    background: #2b2c2d;

    color: white;

    font-size: 18px;

    cursor: pointer;

    display: flex;

    align-items: center;
    justify-content: center;
}

.mic-btn.listening {
    background: #ff4444;
}


/* SEND */

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

.send-btn:active {
    transform: scale(0.96);
}


/* FILE */

#photoInput {
    display: none;
}


/* ================= MOBILE ================= */

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
        gap: 10px;
    }

    .msg {
        max-width: 94%;
        font-size: 14px;
    }

    .footer {
        min-height: 64px;

        padding: 8px 6px;

        padding-bottom:
            calc(
                8px +
                env(safe-area-inset-bottom)
            );
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
        max-height: 280px;
    }

    .sidebar {
        width: 275px;
        left: -280px;
    }

    .code-wrapper {
        max-width: 100%;
    }

    .code-wrapper pre {
        font-size: 12px;
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
            onclick="closeSidebar()">
            ×
        </button>

    </div>

    <button
        class="sidebar-btn"
        onclick="newChat()">
        ＋ New Chat
    </button>

    <button
        class="sidebar-btn"
        onclick="showUpgrade()">
        ⭐ Upgrade
    </button>

    <button
        class="sidebar-btn"
        onclick="closeSidebar()">
        Close Menu
    </button>

</div>


<!-- OVERLAY -->

<div
    id="overlay"
    class="overlay"
    onclick="closeSidebar()">
</div>


<!-- HEADER -->

<div class="header">

    <div class="header-left">

        <button
            class="header-btn"
            onclick="openSidebar()"
            title="Menu">
            ☰
        </button>

        <span class="logo">
            ✨ Nirale AI
        </span>

    </div>

    <button
        class="header-btn"
        onclick="showUpgrade()"
        title="Upgrade">
        ⋮
    </button>

</div>


<!-- CHAT -->

<div id="chatbox">

    <div class="msg bot">

        <div class="bot-content">
            Hello! I am Nirale AI. How can I help you today?
        </div>

    </div>

</div>


<!-- FOOTER -->

<div class="footer">

    <button
        class="plus-btn"
        onclick="openPhotoPicker()"
        title="Upload photo">
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
        title="Voice input">
        🎤
    </button>

    <button
        class="send-btn"
        onclick="send()">
        Send
    </button>

</div>

</div>


<script>

/* ================= MARKDOWN ================= */

marked.setOptions({
    breaks: true,
    gfm: true
});


function renderMarkdown(element, text) {

    const rawHTML = marked.parse(text);

    const safeHTML = DOMPurify.sanitize(rawHTML);

    element.innerHTML = safeHTML;

    addCodeCopyButtons(element);

    addInlineCodeClass(element);
}


function addInlineCodeClass(element) {

    const codes = element.querySelectorAll(
        "code"
    );

    codes.forEach(function(code) {

        if (!code.parentElement ||
            code.parentElement.tagName !== "PRE") {

            code.classList.add(
                "inline-code"
            );
        }

    });
}


function addCodeCopyButtons(element) {

    const blocks =
        element.querySelectorAll("pre");

    blocks.forEach(function(pre) {

        const code =
            pre.querySelector("code");

        if (!code) {
            return;
        }

        const wrapper =
            document.createElement("div");

        wrapper.className =
            "code-wrapper";

        const header =
            document.createElement("div");

        header.className =
            "code-header";

        const language =
            document.createElement("span");

        let languageName = "Code";

        const className =
            code.className || "";

        const match =
            className.match(
                /language-([a-zA-Z0-9_-]+)/
            );

        if (match) {
            languageName =
                match[1];
        }

        language.textContent =
            languageName;

        const button =
            document.createElement("button");

        button.className =
            "copy-code-btn";

        button.textContent =
            "Copy";

        button.onclick =
            async function() {

                try {

                    await navigator.clipboard.writeText(
                        code.textContent
                    );

                    button.textContent =
                        "Copied ✓";

                    setTimeout(
                        function() {

                            button.textContent =
                                "Copy";

                        },
                        1500
                    );

                } catch (error) {

                    const textarea =
                        document.createElement(
                            "textarea"
                        );

                    textarea.value =
                        code.textContent;

                    document.body.appendChild(
                        textarea
                    );

                    textarea.select();

                    document.execCommand(
                        "copy"
                    );

                    textarea.remove();

                    button.textContent =
                        "Copied ✓";

                    setTimeout(
                        function() {

                            button.textContent =
                                "Copy";

                        },
                        1500
                    );
                }

            };

        header.appendChild(language);

        header.appendChild(button);

        wrapper.appendChild(header);

        pre.parentNode.insertBefore(
            wrapper,
            pre
        );

        wrapper.appendChild(pre);

    });

}


/* ================= SIDEBAR ================= */

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
        .innerHTML = `
            <div class="msg bot">
                <div class="bot-content">
                    Hello! I am Nirale AI. How can I help you today?
                </div>
            </div>
        `;

    closeSidebar();
}


/* ================= UPGRADE ================= */

function showUpgrade() {

    alert(
        "Nirale AI Upgrade - Coming Soon"
    );

    closeSidebar();
}


/* ================= PHOTO ================= */

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

    if (
        !file.type.startsWith("image/")
    ) {

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


/* ================= MICROPHONE ================= */

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
                "not-allowed"
            ) {

                alert(
                    "Please allow microphone permission for Nirale AI in Chrome."
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


/* ================= SEND ================= */

async function send() {

    const input =
        document.getElementById(
            "msg"
        );

    const chat =
        document.getElementById(
            "chatbox"
        );

    const text =
        input.value.trim();

    if (!text) {
        return;
    }


    /* USER */

    const userDiv =
        document.createElement(
            "div"
        );

    userDiv.className =
        "msg user";

    userDiv.textContent =
        text;

    chat.appendChild(
        userDiv
    );

    input.value = "";


    /* THINKING */

    const botDiv =
        document.createElement(
            "div"
        );

    botDiv.className =
        "msg bot";

    const botContent =
        document.createElement(
            "div"
        );

    botContent.className =
        "bot-content";

    botContent.textContent =
        "Thinking...";

    botDiv.appendChild(
        botContent
    );

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

            renderMarkdown(
                botContent,
                data.reply ||
                "No response."
            );

        } else {

            botContent.textContent =
                "Error: " +
                (
                    data.reply ||
                    "Server error"
                );
        }

    } catch (error) {

        botContent.textContent =
            "Connection error.";

        console.error(
            error
        );
    }

    chat.scrollTop =
        chat.scrollHeight;
}


/* ================= ENTER ================= */

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



@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        current_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        if not current_key:
            return {"reply": "API Key is missing."}

        message = request.message.strip()
        lower_message = message.lower()

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
            "ನಿರಲೆ ai ಯನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದರು",
        ]

        if any(question in lower_message for question in creator_questions):
            return {"reply": "I was created by Nagesh Nirale."}

        genai.configure(api_key=current_key)

        model = genai.GenerativeModel("gemini-3.6-flash")

        system_instruction = """
You are Nirale AI.

Answer users naturally, accurately and helpfully.

IMPORTANT CREATOR RULE:
Only mention Nagesh Nirale when the user specifically asks who created,
made, developed, built, or is the creator of Nirale AI.

If the user does not ask about your creator, do not mention Nagesh Nirale.
Do not claim that Google or Gemini created Nirale AI.

IMPORTANT FORMATTING RULE:
Use clean Markdown formatting whenever useful.

For programming questions:
- Explain clearly.
- Use proper headings when needed.
- Put commands and code inside fenced code blocks.
- Always specify the language when possible.
- Keep code copy-paste friendly.
- Do not put ordinary explanations inside code blocks.

Answer in the user's language when possible.
"""

        full_prompt = system_instruction + "\n\nUser: " + message

        response = model.generate_content(full_prompt)

        reply = getattr(response, "text", None)

        if not reply:
            reply = "I could not generate a response."

        return {"reply": reply}

    except Exception as e:
        error_message = str(e)
        print("Gemini API Error:", error_message)

        if "429" in error_message or "quota" in error_message.lower():
            return {
                "reply": "API quota limit reached. Please check your Gemini API quota."
            }

        if "404" in error_message or "not found" in error_message.lower():
            return {
                "reply": (
                    "Gemini model is unavailable. Check GEMINI_MODEL or your "
                    "Google AI API model access."
                )
            }

        return {"reply": "API Error: " + error_message}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "10000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )
