import os
import telebot
import logging
from google import genai
from flask import Flask, request as flask_request
from PIL import Image
import io
import sys

# --- FORCING LOGS TO SHOW IN RAILWAY ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# Get Credentials
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Clients
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    """Sends image to Gemini AI with a fallback mechanism for model names"""
    img = Image.open(io.BytesIO(image_bytes))
    
    # List of possible model identifiers to try
    models_to_try = ['gemini-1.5-flash', 'models/gemini-1.5-flash']
    
    for model_name in models_to_try:
        try:
            logger.info(f"Attempting analysis with model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
            )
            
            if response and response.text:
                answer = response.text.strip().upper()
                logger.info(f"--- SUCCESS with {model_name}: {answer} ---")
                return "YES" in answer
        except Exception as e:
            logger.warning(f"Failed with {model_name}: {e}")
            continue # Try the next model in the list
            
    return None # Both failed

@app.route("/photo", methods=["POST"])
def receive_photo():
    logger.info(">>> Incoming request at /photo")
    image_bytes = flask_request.data
    
    if not image_bytes:
        return "No data", 400

    try:
        # 1. Send photo to Telegram
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")
        
        # 2. Perform AI Detection
        result = check_elephant(image_bytes)
        
        if result is True:
            bot.send_message(CHAT_ID, "🐘 ALERT: ELEPHANT CONFIRMED! 🐘")
        elif result is False:
            bot.send_message(CHAT_ID, "✅ Analysis: No elephant detected.")
        else:
            # If all model attempts failed
            bot.send_message(CHAT_ID, "⚠️ AI Service Unavailable (404/Connection). Check API Key.")
            
        return "OK", 200
    except Exception as e:
        logger.error(f"!!! System Error: {e} !!!")
        return "Internal Error", 500

@app.route("/")
def index():
    return "Elephant Detection System is Online."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
