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

# Get Credentials from Railway Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Clients
# Note: Using the updated 2026 'google-genai' library
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    """Sends image to Gemini AI for classification"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Use the simplified model name to avoid 404 errors
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
        )
        
        answer = response.text.strip().upper()
        logger.info(f"--- Gemini Analysis: {answer} ---")
        return "YES" in answer
    except Exception as e:
        logger.error(f"!!! Gemini Error: {e} !!!")
        return False

@app.route("/photo", methods=["POST"])
def receive_photo():
    """Endpoint for ESP32-CAM to upload photos"""
    logger.info(">>> Incoming request at /photo")
    image_bytes = flask_request.data
    
    if not image_bytes:
        logger.warning("!!! No data received in POST request !!!")
        return "No data", 400

    logger.info(f">>> Image received: {len(image_bytes)} bytes")

    try:
        # 1. Send the photo to your Telegram chat immediately
        logger.info(">>> Delivering photo to Telegram...")
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")
        
        # 2. Perform AI Elephant Detection
        is_elephant = check_elephant(image_bytes)
        
        if is_elephant:
            bot.send_message(CHAT_ID, "🐘 ALERT: ELEPHANT DETECTED! 🐘")
            logger.info(">>> Result: Elephant Found")
        else:
            bot.send_message(CHAT_ID, "✅ Analysis: No elephant detected.")
            logger.info(">>> Result: Clear")
            
        return "OK", 200
    except Exception as e:
        logger.error(f"!!! System Error: {e} !!!")
        return "Internal Error", 500

@app.route("/")
def index():
    """Health check for Railway and browser testing"""
    logger.info(">>> Health check accessed")
    return "Elephant Detection Bot (New GenAI SDK) is Running Successfully!"

if __name__ == "__main__":
    # Railway automatically assigns a port; we listen on 8080 by default
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
