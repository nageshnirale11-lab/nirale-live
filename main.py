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

        # -----------------------------------------
        # CREATOR ANSWER ONLY WHEN ASKED
        # -----------------------------------------

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
                "reply": "I was created by Nagesh Nirale."
            }

        # -----------------------------------------
        # GEMINI
        # -----------------------------------------

        genai.configure(
            api_key=current_key
        )

        model = genai.GenerativeModel(
            "gemini-3.6-flash"
        )

        # IMPORTANT:
        # Creator information should NOT be added
        # to every normal conversation.
        full_prompt = message

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
                "reply": "API quota limit reached."
            }

        return {
            "reply": f"API Error: {err_msg}"
        }
