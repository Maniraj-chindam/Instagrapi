import google.generativeai as genai

# ⚙️ Configure your Gemini API key
genai.configure(api_key="AIzaSyDmwEiM1gSSjx9Cxz_pNo5-j2jahsrDD34")  # ← replace with your valid Gemini API key

def generate_prompt(user_input: str) -> str:
    """
    Takes a short user input and returns a detailed, creative image prompt
    suitable for image generation models.
    """
    # Updated model to a supported one
    model = genai.GenerativeModel("gemini-2.5-flash")  

    prompt_text = f"""
    Convert this short idea into a vivid and descriptive image generation prompt.
    Make it detailed, visual, and artistic — suitable for generating AI images.
    Keep it under 60 words.

    User idea: "{user_input}"
    """

    try:
        response = model.generate_content(prompt_text)
        return response.text.strip()
    except Exception as e:
        return f"Error generating prompt: {e}"


# 🧠 Little test block — run directly in terminal
if __name__ == "__main__":
    print("✨ Gemini Prompt Generator ✨")
    print("------------------------------------")
    user_idea = input("Enter your idea: ")
    print("\n🪄 Generating creative prompt...\n")
    prompt = generate_prompt(user_idea)
    print("✨ Generated Prompt:\n")
    print(prompt)
    print("\n------------------------------------")
