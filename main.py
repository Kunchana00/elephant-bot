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

# --- INITIALIZE CLIENT ---
# Using the stable 'v1' API and the Google GenAI SDK
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={'api_version': 'v1'}
)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        prompt = (
            "Analyze this image for the presence of an elephant. "
            "Respond in exactly this format: ANSWER, CONFIDENCE. "
            "Example: YES, 99% or NO, 98%."
        )

        # Using the 'gemini-pro-latest' alias. 
        # In May 2026, this points to the Gemini 3.1 Pro stable/GA release.
        response = client.models.generate_content(
            model='gemini-pro-latest', 
            contents=[prompt, img]
        )
        
        if response and response.text:
            raw_result = response.text.strip().upper()
            logger.info(f"--- AI Result: {raw_result} ---")
            
            if "," in raw_result:
                answer, confidence = raw_result.split(",", 1)
                return answer.strip(), confidence.strip()
            return raw_result, "N/A"
                
        return None, None
    except Exception as e:
        logger.error(f"!!! AI Error: {e} !!!")
        return None, None

@app.route("/photo", methods=["POST"])
def receive_photo():
    logger.info(">>> Request received from ESP32-CAM")
    image_bytes = flask_request.data
    
    if not image_bytes:
        return "No data", 400

    try:
        # 1. Send the photo to your Telegram
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Analyzing with the latest Gemini Pro...")
        
        # 2. Get AI results
        answer, confidence = check_elephant(image_bytes)
        
        # 3. Final Output
        if answer == "YES":
            msg = f"🐘 **ELEPHANT DETECTED!** 🐘\n📈 **Confidence:** {confidence}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        elif answer == "NO":
            msg = f"✅ **Analysis: Clear**\n📈 **Confidence:** {confidence}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        else:
            bot.send_message(CHAT_ID, "⚠️ AI Error. Check Railway Logs for 404/429.")
            
        return "OK", 200
    except Exception as e:
        logger.error(f"!!! System Error: {e} !!!")
        return "Error", 500

@app.route("/")
def index():
    return "Elephant Bot (Pro-Latest) is Live."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
