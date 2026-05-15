import os
import telebot
import logging
import time
import io
import sys
from google import genai
from flask import Flask, request as flask_request
from PIL import Image

# --- LOGGING SETUP ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# --- CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- INITIALIZE CLIENTS ---
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    """
    Sends image to Gemini AI. 
    Includes retry logic to handle 'Too Many Requests' (429) errors.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        prompt = (
            "Is there an elephant in this image? "
            "Respond in exactly this format: ANSWER, CONFIDENCE. "
            "Example: YES, 98% or NO, 90%."
        )

        # Retry logic: Try twice if rate limited
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model='gemini-3.1-pro',
                    contents=[prompt, img]
                )
                
                if response and response.text:
                    raw_result = response.text.strip().upper()
                    logger.info(f"--- AI Result: {raw_result} ---")
                    
                    if "," in raw_result:
                        answer, confidence = raw_result.split(",", 1)
                        return answer.strip(), confidence.strip()
                    return raw_result, "N/A"
                
            except Exception as e:
                # If hit with Rate Limit (429), wait and retry once
                if "429" in str(e) and attempt == 0:
                    logger.warning("Rate limit hit. Waiting 10 seconds to retry...")
                    time.sleep(10)
                    continue
                raise e # Raise other errors or second-time 429
                
        return None, None
    except Exception as e:
        logger.error(f"!!! AI Error: {e} !!!")
        return None, None

@app.route("/photo", methods=["POST"])
def receive_photo():
    """Endpoint for ESP32-CAM uploads"""
    logger.info(">>> Incoming request from ESP32-CAM")
    image_bytes = flask_request.data
    
    if not image_bytes:
        logger.warning("!!! No image data received !!!")
        return "No data", 400

    logger.info(f">>> Processing image: {len(image_bytes)} bytes")

    try:
        # 1. Immediate Feedback to Telegram
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")
        
        # 2. Call AI for Analysis
        answer, confidence = check_elephant(image_bytes)
        
        # 3. Handle Results
        if answer == "YES":
            msg = f"🐘 **ALERT: ELEPHANT DETECTED!** 🐘\n📈 **Confidence:** {confidence}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            logger.info(f">>> Result: ELEPHANT ({confidence})")
        elif answer == "NO":
            msg = f"✅ **Analysis: Clear**\n📈 **Confidence:** {confidence}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            logger.info(f">>> Result: CLEAR ({confidence})")
        else:
            bot.send_message(CHAT_ID, "⚠️ AI Error: Quota Exhausted. Please wait 1 minute.")
            logger.error(">>> Result: QUOTA ERROR")
            
        return "OK", 200
    except Exception as e:
        logger.error(f"!!! System Error: {e} !!!")
        return "Internal Error", 500

@app.route("/")
def index():
    return "Elephant Detection System (2026.v5) is Online and Ready."

if __name__ == "__main__":
    # Railway assigns a port; default to 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
