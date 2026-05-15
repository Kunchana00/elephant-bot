import os
import telebot
import logging
from google import genai
from flask import Flask, request as flask_request
from PIL import Image
import io
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Updated to Gemini 2.5 Flash (Standard for 2026)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
        )
        
        if response and response.text:
            answer = response.text.strip().upper()
            logger.info(f"--- AI Analysis: {answer} ---")
            return "YES" in answer
        return None
    except Exception as e:
        logger.error(f"!!! AI Error: {e} !!!")
        return None

@app.route("/photo", methods=["POST"])
def receive_photo():
    image_bytes = flask_request.data
    if not image_bytes: return "No data", 400

    try:
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Image captured! Analyzing...")
        result = check_elephant(image_bytes)
        
        if result is True:
            bot.send_message(CHAT_ID, "🐘 ALERT: ELEPHANT DETECTED! 🐘")
        elif result is False:
            bot.send_message(CHAT_ID, "✅ Result: No elephant detected.")
        else:
            bot.send_message(CHAT_ID, "⚠️ AI Service Error (Model Retired or API Issue).")
            
        return "OK", 200
    except Exception as e:
        logger.error(f"!!! Error: {e} !!!")
        return "Error", 500

@app.route("/")
def index():
    return "Elephant Detection System (Gemini 2.5) is Running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
