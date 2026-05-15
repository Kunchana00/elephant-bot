import os
import telebot
import logging
import time
import io
import sys
import requests
from google import genai
from flask import Flask, request as flask_request
from PIL import Image

# --- 1. INITIALIZE FLASK FIRST ---
app = Flask(__name__)

# --- 2. LOGGING SETUP ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# --- 3. CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")

# --- 4. INITIALIZE CLIENTS ---
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={'api_version': 'v1'}
)
bot = telebot.TeleBot(BOT_TOKEN)

# Hugging Face Configuration
HF_MODEL = "facebook/detr-resnet-50"

# --- 5. DETECTION FUNCTIONS ---

def check_elephant_gemini(image_bytes):
    """Primary Detection: Gemini Pro"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Is there an elephant in this image? Respond exactly: ANSWER, CONFIDENCE. Example: YES, 98%."
        
        response = client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=[prompt, img]
        )
        
        if response and response.text:
            res = response.text.strip().upper()
            if "," in res:
                ans, conf = res.split(",", 1)
                return ans.strip(), conf.strip()
            return res, "N/A"
        return None, None
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return None, None

def check_elephant_hf(image_bytes):
    """Backup Detection: Hugging Face"""
    API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes)
        results = response.json()
        
        # If model is loading, it returns an 'estimated_time'
        if isinstance(results, dict) and "estimated_time" in results:
            logger.info("HF Model is waking up... waiting 5 seconds.")
            time.sleep(5)
            return check_elephant_hf(image_bytes)

        for item in results:
            if item.get('label') == 'elephant' and item.get('score') > 0.5:
                return "YES", f"{int(item['score']*100)}%"
        return "NO", "0%"
    except Exception as e:
        logger.error(f"HF Error: {e}")
        return None, None

# --- 6. ROUTES ---

@app.route("/photo", methods=["POST"])
def receive_photo():
    logger.info(">>> Photo received from ESP32-CAM")
    image_bytes = flask_request.data
    if not image_bytes: return "No data", 400

    try:
        # 1. Immediate Telegram Feed
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion! Analyzing...")
        
        # 2. Try Gemini
        answer, confidence = check_elephant_gemini(image_bytes)
        source = "Gemini"

        # 3. Failover to Hugging Face if Gemini fails
        if answer is None:
            logger.warning("Gemini failed. Switching to Hugging Face...")
            answer, confidence = check_elephant_hf(image_bytes)
            source = "Hugging Face"

        # 4. Final Alert
        if answer == "YES":
            msg = f"🐘 **ELEPHANT DETECTED!** 🐘\n📈 Confidence: {confidence}\nSource: {source}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        elif answer == "NO":
            msg = f"✅ **Clear**\n📈 Confidence: {confidence}\nSource: {source}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        else:
            bot.send_message(CHAT_ID, "⚠️ Both AI services failed.")
            
        return "OK", 200
    except Exception as e:
        logger.error(f"System Error: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "Elephant Failover System is Online."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
