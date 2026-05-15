import os
import telebot
import requests
import logging
import io
import sys
from flask import Flask, request as flask_request

# --- CREDENTIALS ---
HF_TOKEN = os.environ.get("HF_TOKEN")
# A very accurate object detection model for animals
HF_MODEL = "facebook/detr-resnet-50" 

def check_elephant_huggingface(image_bytes):
    """Backup: Uses Hugging Face to detect animals"""
    API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes)
        results = response.json()
        
        # Hugging Face returns a list of detected objects
        for item in results:
            label = item.get('label', '').lower()
            score = item.get('score', 0)
            
            # Check if an elephant is detected with over 50% confidence
            if "elephant" in label and score > 0.5:
                confidence = f"{int(score * 100)}%"
                logger.info(f"--- HF SUCCESS: Elephant Found ({confidence}) ---")
                return True, confidence
                
        return False, "0%"
    except Exception as e:
        logger.error(f"!!! Hugging Face Error: {e} !!!")
        return None, None

# --- UPDATED receive_photo() logic ---
@app.route("/photo", methods=["POST"])
def receive_photo():
    image_bytes = flask_request.data
    
    # 1. Send photo to Telegram immediately
    bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion! Analyzing...")

    # 2. Try Gemini first (Best reasoning)
    ans, conf = check_elephant_gemini(image_bytes)

    # 3. If Gemini fails (Quota/Error), use Hugging Face
    if ans is None:
        logger.warning("Gemini Failed/Quota Full. Switching to Hugging Face...")
        ans, conf = check_elephant_huggingface(image_bytes)

    # 4. Send the result
    if ans is True:
        bot.send_message(CHAT_ID, f"🐘 ALERT: Elephant ({conf})")
    elif ans is False:
        bot.send_message(CHAT_ID, "✅ Clear")
    else:
        bot.send_message(CHAT_ID, "⚠️ All AI services down.")
        
    return "OK", 200
