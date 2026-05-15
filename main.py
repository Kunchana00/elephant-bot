import os
import telebot
import logging
import time
import requests
import sys
import io
from flask import Flask, request as flask_request

# --- INITIALIZE FLASK ---
app = Flask(__name__)

# --- LOGGING SETUP ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# --- CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_TOKEN = os.environ.get("HF_TOKEN")

# Initialize Telegram
bot = telebot.TeleBot(BOT_TOKEN)

# Stable Classifier Model - Google ViT
# This model is 'Always On' and very fast for free tier users
HF_MODEL = "google/vit-base-patch16-224"
API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

def query_huggingface(image_bytes):
    """Sends image with correct binary headers to prevent HTML errors"""
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/octet-stream" 
    }
    
    # Passing wait_for_model as a parameter is more reliable in 2026
    params = {"wait_for_model": "true"}
    
    try:
        response = requests.post(
            API_URL, 
            headers=headers, 
            data=image_bytes, 
            params=params,
            timeout=60
        )
        
        logger.info(f"HF Status: {response.status_code}")

        # Safety check: If the response isn't JSON, it's an HTML error page
        if "application/json" not in response.headers.get("Content-Type", ""):
            logger.error("Hugging Face returned HTML/Text. Check if your Token is correct.")
            return None

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"HF Error {response.status_code}: {response.text[:100]}")
            return None
            
    except Exception as e:
        logger.error(f"Request Exception: {e}")
        return None

@app.route("/photo", methods=["POST"])
def receive_photo():
    logger.info(">>> Received image from ESP32-CAM")
    image_bytes = flask_request.data
    
    if not image_bytes:
        return "No data", 400

    try:
        # 1. Send the visual to Telegram immediately
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Analyzing frame...")

        # 2. Process with AI
        detections = query_huggingface(image_bytes)
        
        elephant_found = False
        highest_score = 0
        detected_label = ""

        # 3. Parse classification results
        if detections and isinstance(detections, list):
            for obj in detections:
                label = obj.get("label", "").lower()
                score = obj.get("score", 0)
                
                # Model recognizes 'African elephant' and 'Indian elephant'
                if "elephant" in label and score > 0.35:
                    elephant_found = True
                    if score > highest_score:
                        highest_score = score
                        detected_label = label
        
        # 4. Results logic
        if elephant_found:
            confidence = f"{int(highest_score * 100)}%"
            msg = f"🐘 **ALERT: {detected_label.upper()} DETECTED!** 🐘\n📈 Confidence: {confidence}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            logger.info(f"MATCH: {detected_label} ({confidence})")
        else:
            if detections is not None:
                bot.send_message(CHAT_ID, "✅ **Result: Clear**")
                logger.info("MATCH: None")
            else:
                bot.send_message(CHAT_ID, "⚠️ AI Service Error. Check Token.")

        return "OK", 200

    except Exception as e:
        logger.error(f"Route Error: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "Elephant Monitoring System v2026.STABLE is Live."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
