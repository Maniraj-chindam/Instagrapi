from instagrapi import Client
from pathlib import Path

# --- Added a starting message for clarity ---
print("--- Starting Instagram Poster Script ---")

def post_picture_to_instagram(username: str, password: str, image_path: str, caption: str = ""):
    """
    Logs into Instagram and uploads a photo with a caption.
    """
    # 1. Initialize the Client
    cl = Client()
    print("Attempting to log in...")

    try:
        # 2. Log in to your Instagram account
        cl.login(username, password)
        print("Login successful.")

        # Ensure the image path is a Path object for best compatibility
        photo_path = Path(image_path)
        
        if not photo_path.exists():
            print(f"Error: Image file not found at {image_path}")
            return False

        # 3. Upload the photo
        print(f"Uploading photo: {image_path} with caption: '{caption[:20]}...'")
        
        # The photo_upload method handles the heavy lifting
        media = cl.photo_upload(
            path=photo_path,
            caption=caption
        )

        print(f"Photo successfully uploaded! Media PK: {media.pk}")
        return True

    except Exception as e:
        # **Crucial for finding login/upload issues**
        print(f"An error occurred during post: {e}")
        return False
    
    finally:
        # Important: Log out to close the session gracefully
        cl.logout()

# --- Example Usage (Credentials and Path) ---
INSTA_USERNAME = "secret.stories______"
INSTA_PASSWORD = "Preethi@103"
# NOTE: The forward slashes are correct for cross-platform compatibility!
IMAGE_FILE = r"C:\Users\shrut\OneDrive\Desktop\new instagrapi\Static\generated_images\generated_image_20251030_113543.jpg"
POST_CAPTION = "Check out this cool picture I posted using Python and instagrapi! #python #automation"

# ----------------------------------------------------
# ❗ THE FIX: UNCOMMENTED THE FUNCTION CALL TO ASSIGN 'success'
# ----------------------------------------------------
success = post_picture_to_instagram(INSTA_USERNAME, INSTA_PASSWORD, IMAGE_FILE, POST_CAPTION)

if success:
    print("Script finished successfully. Check Instagram!")
else:
    print("Script finished with an error. See the error message above.")