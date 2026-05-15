import os
import telebot
import logging
import time
import requests
import sys
from flask import Flask, request as flask_request

# --- INITIALIZE FLASK ---
app = Flask(__name__)

# --- LOGGING ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# --- CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_TOKEN = os.environ.get("HF_TOKEN")

# Initialize Telegram
bot = telebot.TeleBot(BOT_TOKEN)

# Hugging Face Model (Facebook's DETR is perfect for animal detection)
HF_MODEL = "facebook/detr-resnet-50"
API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

def query_huggingface(image_bytes):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Try up to 3 times in case the model is waking up
    for i in range(3):
        try:
            response = requests.post(API_URL, headers=headers, data=image_bytes, timeout=20)
            result = response.json()

            # If the model is still loading, wait and retry
            if isinstance(result, dict) and "estimated_time" in result:
                wait_time = result.get("estimated_time", 5)
                logger.info(f"Model is loading... waiting {wait_time}s (Attempt {i+1}/3)")
                time.sleep(wait_time)
                continue
            
            return result
        except Exception as e:
            logger.error(f"HF Attempt {i+1} failed: {e}")
            time.sleep(2)
    return None

@app.route("/photo", methods=["POST"])
def receive_photo():
    logger.info(">>> Photo received from ESP32-CAM")
    image_bytes = flask_request.data
    if not image_bytes: return "No data", 400

    try:
        # 1. Send immediate capture to Telegram
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")

        # 2. Analyze using Hugging Face
        detections = query_huggingface(image_bytes)
        
        elephant_found = False
        max_score = 0

        if detections and isinstance(detections, list):
            for obj in detections:
                label = obj.get("label", "").lower()
                score = obj.get("score", 0)
                
                if label == "elephant" and score > 0.4:  # 40% confidence threshold
                    elephant_found = True
                    if score > max_score: max_score = score

        # 3. Respond based on findings
        if elephant_found:
            confidence = f"{int(max_score * 100)}%"
            msg = f"🐘 **ALERT: ELEPHANT DETECTED!** 🐘\n📈 Confidence: {confidence}\nModel: {HF_MODEL}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            logger.info(f">>> RESULT: ELEPHANT ({confidence})")
        else:
            bot.send_message(CHAT_ID, "✅ **Result: Clear**\n(No elephants detected)")
            logger.info(">>> RESULT: CLEAR")

        return "OK", 200

    except Exception as e:
        logger.error(f"Error: {e}")
        return "Internal Error", 500

@app.route("/")
def index():
    return "Elephant Detection System (Hugging Face Edition) is Online."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
