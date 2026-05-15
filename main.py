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
# Powered by Gemini 2.5 Flash for 2026
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    """Sends image to Gemini AI and asks for YES/NO + Confidence"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Expert Prompt for Structured Data Extraction
        prompt = (
            "Analyze this image for the presence of an elephant. "
            "Respond in exactly this format: ANSWER, CONFIDENCE_PERCENTAGE. "
            "Example: YES, 98% or NO, 92%."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img]
        )
        
        if response and response.text:
            raw_result = response.text.strip().upper()
            logger.info(f"--- AI Result: {raw_result} ---")
            
            # Parsing the CSV-style response
            if "," in raw_result:
                answer, confidence = raw_result.split(",", 1)
                return answer.strip(), confidence.strip()
            else:
                # Fallback if AI ignores format
                return raw_result, "N/A"
        return None, None
    except Exception as e:
        logger.error(f"!!! AI Error: {e} !!!")
        return None, None

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
        # 1. Send the photo to your Telegram immediately
        logger.info(">>> Delivering photo to Telegram...")
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")
        
        # 2. Perform AI Elephant Detection with Confidence
        answer, confidence = check_elephant(image_bytes)
        
        if answer == "YES":
            msg = f"🐘 **ALERT: ELEPHANT DETECTED!** 🐘\n\n📈 **Confidence:** {confidence}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            logger.info(f">>> Result: Elephant ({confidence})")
        elif answer == "NO":
            msg = f"✅ **Analysis: Clear**\n\n📈 **Confidence:** {confidence}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            logger.info(f">>> Result: Clear ({confidence})")
        else:
            bot.send_message(CHAT_ID, "⚠️ AI Processing Error. Check Railway Logs.")
            logger.error(">>> Result: AI Error")
            
        return "OK", 200
    except Exception as e:
        logger.error(f"!!! System Error: {e} !!!")
        return "Internal Error", 500

@app.route("/")
def index():
    """Health check for Railway and browser testing"""
    logger.info(">>> Health check accessed")
    return "Elephant Detection System (v2026.5) is Running Successfully!"

if __name__ == "__main__":
    # Railway sets the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
