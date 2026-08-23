@app.post("/chat")
async def chat(request: ChatRequest):

    try:

        message = request.message.strip()

        if not message:
            return {
                "reply": "Please enter a message."
            }

        if is_creator_question(message):
            return {
                "reply": "I was created by Nagesh Nirale."
            }

        current_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        if not current_key:
            return {
                "reply": "API Key is missing. Please set GEMINI_API_KEY in Render Environment Variables."
            }

        genai.configure(
            api_key=current_key
        )

        model = genai.GenerativeModel(
            "gemini-3.6-flash"
        )

        system_instruction = """
You are Nirale AI.

Answer the user's question naturally,
accurately and helpfully.

Use the language the user uses when practical.

Your creator is Nagesh Nirale.

Only mention Nagesh Nirale when the user
specifically asks who created, made,
developed, built, or owns Nirale AI.

Do not claim that Google created Nirale AI.

When giving programming answers:
- Use clear markdown.
- Put commands and code inside fenced code blocks.
- Keep code easy to copy and paste.
- Do not put # before every normal line.
- Give complete code when the user asks for complete code.
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
            reply = "I could not generate a response."

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
                "reply": "API quota limit reached. Please check your Gemini API quota."
            }

        return {
            "reply": "API Error: " + error_message
        }
