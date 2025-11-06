from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
 
load_dotenv(override=True)  # Load environment variables from .env file
 
client = genai.Client()
 
# Generate image
contents = "A majestic male lion, golden mane ablaze, gazes intently from the dense, mist-kissed tropical jungle. Dappled sunlight pierces the emerald canopy, illuminating exotic flora. Hyper-detailed, cinematic realism, golden hour glow."
 
response = client.models.generate_content(
    model="gemini-2.0-flash-preview-image-generation",
    contents=contents,
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
    )
)
 
 
for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        image = Image.open(BytesIO(part.inline_data.data))
        image.show()
 
 
 