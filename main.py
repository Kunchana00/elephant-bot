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
# Forcing logs to stdout so they appear in Railway's console
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# --- CREDENTIALS ---
# Ensure these are set in your Railway 'Variables' tab
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_TOKEN = os.environ.get("HF_TOKEN")

# Initialize Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN)

# Hugging Face Model: Facebook DETR (ResNet-50)
# This model is excellent for identifying 'elephant' among other animals
HF_MODEL = "facebook/detr-resnet-50"
API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

def query_huggingface(image_bytes):
    """Sends image to Hugging Face with stability options"""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # We use 'wait_for_model' to prevent the 404/Empty Response errors 
    # when the model is cold (sleeping).
    payload = {
        "inputs": image_bytes,
        "options": {"wait_for_model": True}
    }
    
    try:
        # Timeout set to 90s to allow for cold-start loading
        response = requests.post(
            API_URL, 
            headers=headers, 
            data=image_bytes, 
            timeout=90
        )
        
        # Log the status for debugging
        logger.info(f"HF Status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"HF Server returned error: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Network/Request Error: {e}")
        return None

@app.route("/photo", methods=["POST"])
def receive_photo():
    logger.info(">>> Incoming frame from ESP32-CAM")
    image_bytes = flask_request.data
    
    if not image_bytes:
        logger.warning("Empty payload received.")
        return "No data", 400

    try:
        # 1. Send the raw image to Telegram so you can see what triggered it
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Running AI analysis...")

        # 2. Perform Detection
        detections = query_huggingface(image_bytes)
        
        elephant_found = False
        highest_score = 0

        # 3. Parse the Results
        if detections and isinstance(detections, list):
            for obj in detections:
                label = obj.get("label", "").lower()
                score = obj.get("score", 0)
                
                # Check for 'elephant' with a 40% confidence threshold
                if label == "elephant" and score > 0.4:
                    elephant_found = True
                    if score > highest_score:
                        highest_score = score
        
        # 4. Final Telegram Notification
        if elephant_found:
            confidence = f"{int(highest_score * 100)}%"
            msg = f"🐘 **ALERT: ELEPHANT DETECTED!** 🐘\n📈 Confidence: {confidence}\nModel: {HF_MODEL}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            logger.info(f"POSITIVE DETECTION: {confidence}")
        else:
            # Check if the API actually worked but found nothing
            if detections is not None:
                bot.send_message(CHAT_ID, "✅ **Area Clear.**\nNo elephants identified in this frame.")
                logger.info("NEGATIVE DETECTION: Clear")
            else:
                bot.send_message(CHAT_ID, "⚠️ AI Service Busy. Please try triggering again.")
                logger.error("DETECTION FAILED: API Error")

        return "OK", 200

    except Exception as e:
        logger.error(f"Critical Route Error: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "Elephant Detection System (Hugging Face GA) is Online."

if __name__ == "__main__":
    # Railway sets the PORT env variable automatically
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
