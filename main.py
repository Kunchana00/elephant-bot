import os
import telebot
import logging
from google import genai
from flask import Flask, request as flask_request
from PIL import Image
import io
import sys

# --- FORCING LOGS TO SHOW IN RAILWAY ---
# This part is critical to see your print statements
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('gunicorn.error')

# Get Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Clients
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Wire Flask logs to Gunicorn
app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)

def check_elephant(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
        )
        answer = response.text.strip().upper()
        app.logger.info(f"GEMINI RESULT: {answer}")
        return "YES" in answer
    except Exception as e:
        app.logger.error(f"GEMINI ERROR: {e}")
        return False

@app.route("/photo", methods=["POST"])
def receive_photo():
    app.logger.info("RECEIVED REQUEST AT /PHOTO")
    image_bytes = flask_request.data
    
    if not image_bytes:
        app.logger.warning("NO DATA RECEIVED IN POST")
        return "No data", 400

    app.logger.info(f"IMAGE SIZE: {len(image_bytes)} bytes")

    try:
        # 1. Send to Telegram
        app.logger.info("SENDING TO TELEGRAM...")
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")
        
        # 2. Check for Elephant
        is_elephant = check_elephant(image_bytes)
        
        if is_elephant:
            bot.send_message(CHAT_ID, "🐘 ELEPHANT DETECTED! 🐘")
        else:
            bot.send_message(CHAT_ID, "✅ No elephant detected.")
            
        return "OK", 200
    except Exception as e:
        app.logger.error(f"SYSTEM ERROR: {e}")
        return "Internal Error", 500

@app.route("/")
def index():
    app.logger.info("HEALTH CHECK ACCESSED")
    return "Elephant Bot is Active and Waiting for Photos!"

if __name__ == "__main__":
    # Ensure port 8080 is used
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
