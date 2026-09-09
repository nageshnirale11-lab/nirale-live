# ============================================================
# NIRALE AI — CREATOR PROFILE BLOCK
# ============================================================

CREATOR_REPLY = r"""
<div class="creator-answer">
    <div class="creator-title">
        ನನ್ನನ್ನು <strong>Nagesh Nirale</strong> ಅವರು ರಚಿಸಿದ್ದಾರೆ.
    </div>

    <div class="creator-card">
        <div class="creator-name">Nagesh Nirale</div>
        <div class="creator-role">🛡️ Ethical Hacker</div>

        <div class="creator-photos">
            <img src="/creator-photo-1"
                 alt="Nagesh Nirale"
                 onclick="openCreatorPhoto('/creator-photo-1')">

            <img src="/creator-photo-2"
                 alt="Nagesh Nirale"
                 onclick="openCreatorPhoto('/creator-photo-2')">
        </div>

        <div class="creator-social">
            <a href="https://www.instagram.com/armor_728/"
               target="_blank"
               rel="noopener noreferrer">
                📸 Instagram — @armor_728
            </a>

            <a href="https://in.linkedin.com/in/nagesh-nirale-256a1b3b4"
               target="_blank"
               rel="noopener noreferrer">
                💼 LinkedIn — Nagesh Nirale
            </a>
        </div>
    </div>
</div>
"""

def is_creator_question(message: str) -> bool:
    text = message.strip().lower()

    creator_phrases = [
        "who created you",
        "who made you",
        "who is your creator",
        "who developed you",
        "who built you",
        "who created nirale ai",
        "who made nirale ai",

        "ನಿನ್ನನ್ನು ಯಾರು ರಚಿಸಿದರು",
        "ನಿನ್ನನ್ನು ಯಾರು ರಚಿಸಿದ್ದಾರೆ",
        "ನಿನ್ನನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದರು",
        "ನಿನ್ನನ್ನು ಯಾರು ಸೃಷ್ಟಿಸಿದ್ದಾರೆ",
        "ನಿನ್ನನ್ನು ಯಾರು create ಮಾಡಿದರು",
        "ನಿನ್ನನ್ನು ಯಾರು create ಮಾಡಿದ್ದಾರೆ",
        "ನಿನ್ನನ್ನು ಯಾರು create madiddu",
        "ನಿನ್ನನ್ನು ಯಾರು create madidare",
        "ನಿನ್ನ create madiddu yaru",
        "ninna create madiddu yaru",
        "ninna create madidavaru yaru",
        "ninnannu yaru create madidaru",
        "ninnannu yaru madidaru",
        "ninna creator yaru",
        "nimma creator yaru"
    ]

    return any(phrase in text for phrase in creator_phrases)


# ------------------------------------------------------------
# CREATOR PHOTOS
# ------------------------------------------------------------

from fastapi.responses import Response

@app.get("/creator-photo-1")
async def creator_photo_1():
    import base64

    # Put your first photo's base64 string here.
    # Example:
    # PHOTO_1_BASE64 = "...."
    PHOTO_1_BASE64 = ""

    if not PHOTO_1_BASE64:
        return Response(status_code=404)

    return Response(
        content=base64.b64decode(PHOTO_1_BASE64),
        media_type="image/jpeg"
    )


@app.get("/creator-photo-2")
async def creator_photo_2():
    import base64

    # Put your second photo's base64 string here.
    PHOTO_2_BASE64 = ""

    if not PHOTO_2_BASE64:
        return Response(status_code=404)

    return Response(
        content=base64.b64decode(PHOTO_2_BASE64),
        media_type="image/jpeg"
    )


# ------------------------------------------------------------
# CREATOR BLOCK CSS
# Put this CSS inside your existing <style> section.
# ------------------------------------------------------------

CREATOR_CSS = r"""
.creator-answer {
    width: 100%;
    max-width: 760px;
    margin: 12px 0;
}

.creator-title {
    font-size: 18px;
    line-height: 1.6;
    margin-bottom: 14px;
}

.creator-card {
    width: 100%;
    box-sizing: border-box;
    padding: 18px;
    border: 1px solid #d7d7d7;
    border-radius: 18px;
    background: #ffffff;
}

.creator-name {
    font-size: 23px;
    font-weight: 700;
    margin-bottom: 5px;
}

.creator-role {
    font-size: 16px;
    margin-bottom: 16px;
}

.creator-photos {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.creator-photos img {
    width: 100%;
    height: 330px;
    display: block;
    object-fit: cover;
    object-position: center;
    border-radius: 15px;
    cursor: zoom-in;
    transition: transform .2s ease;
}

.creator-photos img:hover {
    transform: scale(1.02);
}

.creator-social {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 16px;
}

.creator-social a {
    display: block;
    padding: 13px 15px;
    border: 1px solid #d8d8d8;
    border-radius: 12px;
    color: inherit;
    text-decoration: none;
    font-weight: 600;
}

.creator-social a:hover {
    background: #f3f3f3;
}

@media (max-width: 600px) {
    .creator-photos {
        grid-template-columns: 1fr;
    }

    .creator-photos img {
        height: 360px;
    }
}
"""


# ------------------------------------------------------------
# CREATOR PHOTO ZOOM JAVASCRIPT
# Put this inside your existing <script> section.
# ------------------------------------------------------------

CREATOR_JS = r"""
function openCreatorPhoto(src) {
    const viewer = document.createElement("div");

    viewer.style.cssText = `
        position: fixed;
        inset: 0;
        z-index: 999999;
        background: rgba(0,0,0,.90);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        cursor: zoom-out;
    `;

    const img = document.createElement("img");

    img.src = src;

    img.style.cssText = `
        max-width: 96vw;
        max-height: 96vh;
        width: auto;
        height: auto;
        object-fit: contain;
        border-radius: 14px;
        box-shadow: 0 10px 50px rgba(0,0,0,.5);
    `;

    viewer.appendChild(img);

    viewer.addEventListener("click", function () {
        viewer.remove();
    });

    document.body.appendChild(viewer);
}
"""


# ------------------------------------------------------------
# IMPORTANT:
# In your existing /api/chat function, BEFORE Gemini is called,
# use this:
# ------------------------------------------------------------

if is_creator_question(message):
    answer = CREATOR_REPLY

    # DO NOT call Gemini for creator questions.
    # Return the creator answer directly.

# For every other question:
# continue to your existing Gemini code normally.
