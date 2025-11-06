import os
import traceback
from datetime import datetime
from io import BytesIO

from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
from instagrapi import Client
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash

# Load environment variables
load_dotenv(override=True)

# 🔑 API & CONFIGURATION
API_KEY = os.getenv("GEMINI_API_KEY")
# Initialize the new SDK client
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"Error initializing Gemini Client: {e}")
    # Exit or handle gracefully if API key is missing/invalid

app = Flask(__name__)
# A secret key is required for Flask sessions
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a-default-secret-key-for-development")

# Output directory for saved images (must be under static for frontend access)
OUTPUT_DIR = "static/generated_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Instagrapi configuration (Fallback/Initial config)
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
INSTAGRAM_SESSION_FILE = 'instagrapi_session.json'
cl = Client() # Global Client instance
# -------------------------------


def generate_prompt(user_input: str) -> str:
    """
    Expands a short user idea into a creative, vivid image-generation prompt
    using the NEW official Google GenAI SDK (client).
    """
    print("\n🪄 STEP 1: Expanding short idea into a detailed prompt...")

    prompt_text = f"""
    Convert this short idea into a vivid, cinematic, and descriptive image prompt.
    Include artistic details like lighting, environment, and mood.
    Keep it under 60 words.

    User idea: "{user_input}"
    """

    try:
        # gemini-2.5-flash is ideal for this quick, creative task
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text
        )
        print("✅ Prompt expansion successful (New SDK).")
        return response.text.strip()

    except Exception as e:
        print(f"Error generating prompt (New SDK failed): {e}")
        # Fallback to user input if API call fails
        return user_input


def generate_image(prompt: str):
    """Generates an image, saves it, and returns its local path and static URL."""
    print("\n🖼️ STEP 2: Generating image using Gemini 2.0 Flash Image model...")

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
            # For Instagram, a 1:1 or 4:5 aspect ratio is ideal. We'll stick to the default for simplicity,
            # but you can add types.ImageGenerationConfig(aspect_ratio="1:1") here if needed.
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"]
            ),
        )

        image_data = None
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                image_data = part.inline_data.data
                break

        if not image_data:
            raise ValueError(f"No image data returned. Text response: {response.text}")

        image = Image.open(BytesIO(image_data))
        if image.mode != 'RGB':
            image = image.convert('RGB')

        image_filename = f"generated_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        image_path = os.path.join(OUTPUT_DIR, image_filename)
        image.save(image_path)

        # Return the path relative to the static folder (for Flask) and absolute path (for instagrapi)
        image_url = f"/{OUTPUT_DIR}/{image_filename}"
        print(f"✅ Image saved successfully at {image_path}")
        return image_path, image_url, "Image generation successful!"

    except Exception as e:
        print(f"❌ Error generating image: {e}")
        return None, None, f"Error generating image: {e}"

def login_instagram():
    """Handles instagrapi login and session management using a file."""
    global cl # Ensure you are referencing the global instance

    # Prioritize credentials from session for the currently logged-in user
    username = session.get('instagram_username')
    password = session.get('instagram_password')

    if not username or not password:
        # Fallback only if no session credentials exist, but for the current flow,
        # this path shouldn't be hit if the user is on the main page.
        username = INSTAGRAM_USERNAME
        password = INSTAGRAM_PASSWORD
        if not username or not password:
            raise ValueError("Instagram credentials not found in session or .env file.")

    # Check if a session file exists and load settings
    if os.path.exists(INSTAGRAM_SESSION_FILE):
        try:
            cl.load_settings(INSTAGRAM_SESSION_FILE)
            print("Instagrapi session loaded.")
        except Exception as e:
            print(f"❌ Error loading session file: {e}. Attempting full login.")

    # Check if client is already logged in (private attribute check for optimization)
    if getattr(cl, 'logged_in', False):
        print("Instagrapi is already logged in.")
        return

    try:
        # Perform a full login (or verify loaded session)
        cl.login(username, password)

        # Save the session *only* if the login was successful
        cl.dump_settings(INSTAGRAM_SESSION_FILE)
        print("✅ Instagrapi full login successful and session saved.")

    except Exception as e:
        print(f"❌ Instagrapi login failed: {e}")
        # If login fails, remove potentially corrupt session file
        os.remove(INSTAGRAM_SESSION_FILE) if os.path.exists(INSTAGRAM_SESSION_FILE) else None
        raise ConnectionError(f"Failed to log in to Instagram: {e}")

def post_to_instagram(image_path: str, caption: str) -> bool:
    """Posts the image to Instagram using instagrapi."""
    print(f"\n📸 STEP 3: Attempting to post image: {image_path}")

    # Use the absolute path for instagrapi
    full_image_path = Path(image_path)

    if not full_image_path.exists():
        print(f"❌ Post failed: Image file not found at {full_image_path}")
        return False

    try:
        login_instagram()
        cl.photo_upload(
            path=full_image_path,
            caption=caption
        )
        print("✅ Image posted to Instagram successfully.")
        return True
    except ConnectionError as ce:
        print(f"❌ Instagram connection error: {ce}")
        return False
    except Exception as e:
        print(f"❌ Error during Instagram post: {e}")
        traceback.print_exc()
        return False


# --- FLASK ROUTES ---

@app.route('/')
def index():
    """
    Renders the main generator page only if the Instagram credentials
    are successfully stored in the session. Passes the username for display.
    Also passes the last generated image data if available.
    """
    username = session.get('instagram_username')

    if not username:
        # If not logged in, redirect to the Instagram login page
        return redirect(url_for('instagram_login_page'))
    
    # Get the last successful result from the session for display on load
    last_result = session.get('last_generated_image_data', None)

    # Pass the username and last image data to the template
    return render_template('index.html', username=username, last_result=last_result)

@app.route('/login/instagram')
def instagram_login_page():
    """Renders the Instagram login page."""
    return render_template('instagram_login.html')

@app.route('/login/instagram/submit', methods=['POST'])
def handle_instagram_login():
    """Handles the Instagram login form submission."""
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Username and password are required.', 'error')
        return redirect(url_for('instagram_login_page'))

    # Store credentials in the session temporarily for verification and later use
    session['instagram_username'] = username
    session['instagram_password'] = password

    # Attempt to log in to verify credentials
    try:
        # Create a temporary client to test login without affecting the global one
        temp_cl = Client()
        temp_cl.login(username, password)
        # Save settings for the temporary client (which can be loaded by the global one)
        temp_cl.dump_settings(INSTAGRAM_SESSION_FILE)
        print(f"✅ Successfully verified Instagram credentials for user: {username}")

        # Flash success message and redirect to the main page
        flash('Login successful! You can now generate and post images.', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        print(f"❌ Instagram login verification failed: {e}")
        # Clear the invalid credentials from the session
        session.pop('instagram_username', None)
        session.pop('instagram_password', None)
        session.pop('last_generated_image_data', None) # Also clear image history on failed login

        # Also clean up any failed session file attempt
        os.remove(INSTAGRAM_SESSION_FILE) if os.path.exists(INSTAGRAM_SESSION_FILE) else None

        flash(f"Login failed. Please check your credentials. Error: {e}", 'error')
        return redirect(url_for('instagram_login_page'))

@app.route('/logout')
def logout():
    """Logs the user out by clearing the Instagram credentials from the session."""
    session.pop('instagram_username', None)
    session.pop('instagram_password', None)
    session.pop('last_generated_image_data', None) # Clear last image on logout
    # Also clear the global client and session file to ensure a fresh login next time
    os.remove(INSTAGRAM_SESSION_FILE) if os.path.exists(INSTAGRAM_SESSION_FILE) else None

    # Reset the global client instance
    global cl
    cl = Client()

    flash('You have been logged out.', 'success')
    return redirect(url_for('instagram_login_page'))

@app.route('/generate', methods=['POST'])
def generate():
    """Route to generate prompt and image."""
    user_idea = request.form.get('idea')
    if not user_idea:
        return jsonify({'error': 'Input cannot be empty.'}), 400

    detailed_prompt = generate_prompt(user_idea)
    image_path, image_url, image_status = generate_image(detailed_prompt)

    result = {
        'detailed_prompt': detailed_prompt,
        'image_url': image_url,
        'image_path': image_path, # Crucial: This absolute path is needed for instagrapi
        'image_status': image_status
    }
    
    # Store the successful generation result in the session
    if image_path and image_url:
        # We need a copy of the old data to provide the "back" function
        # The key for the *previous* successful image
        session['last_generated_image_data_prev'] = session.get('last_generated_image_data') 
        
        # The key for the *current* successful image
        session['last_generated_image_data'] = result 
    else:
        # If generation fails, we don't update 'last_generated_image_data', 
        # so the user can use the 'Back' button to restore the previous one.
        pass

    return jsonify(result)

@app.route('/last_image', methods=['GET'])
def get_last_image():
    """Route to retrieve the last successfully generated image data."""
    # This route is used to implement the 'back' button logic from the frontend.
    # It swaps the 'current' last image with the 'previous' last image.
    
    # Get the *previous* successfully generated image data
    prev_result = session.get('last_generated_image_data_prev', None)
    
    if prev_result:
        # SWAP: Make the previous one the current one
        session['last_generated_image_data'] = prev_result 
        # Clear the 'previous' history after moving it to 'current'
        session.pop('last_generated_image_data_prev', None) 
        return jsonify(prev_result)
    else:
        return jsonify({'error': 'No previous image data found.'}), 404

@app.route('/post', methods=['POST'])
def post():
    """Route to post the saved image to Instagram."""
    data = request.get_json()
    image_path = data.get('image_path')
    caption = data.get('caption', 'Generated by Gemini API.')

    # Check if user is logged into Instagram via the session
    if 'instagram_username' not in session:
        return jsonify({
            'success': False,
            'message': 'Please log in to Instagram first.',
            'redirect_to': url_for('instagram_login_page')
        }), 401 # Unauthorized

    if not image_path:
        return jsonify({'success': False, 'message': 'Image path is missing.'}), 400

    if post_to_instagram(image_path, caption):
        return jsonify({'success': True, 'message': 'Image posted to Instagram successfully!'})
    else:
        return jsonify({'success': False, 'message': 'Failed to post to Instagram. Check server logs for details or try logging out and back in.'}), 500


if __name__ == "__main__":
    app.run(debug=True)