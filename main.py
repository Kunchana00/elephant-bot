import os
import telebot
import logging
import base64
import sys
import io
from anthropic import Anthropic
from flask import Flask, request as flask_request

# --- INITIALIZE FLASK ---
app = Flask(__name__)

# --- LOGGING SETUP ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# --- CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Initialize Clients
bot = telebot.TeleBot(BOT_TOKEN)
client = Anthropic(api_key=CLAUDE_KEY)

def analyze_with_claude(image_bytes):
    """Sends image to Claude Haiku 4.5 for high-speed analysis"""
    try:
        # Encode the ESP32-CAM frame to Base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # Using the stable 'claude-haiku-4-5' alias for 2026
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text", 
                            "text": "Check for elephants. Respond strictly: ANSWER: [YES/NO], CONFIDENCE: [percentage]."
                        }
                    ],
                }
            ],
        )
        
        result_text = message.content[0].text.strip().upper()
        logger.info(f"Claude Result: {result_text}")
        return result_text
    except Exception as e:
        logger.error(f"Claude API Error: {e}")
        return None

@app.route("/photo", methods=["POST"])
def receive_photo():
    logger.info(">>> Frame received from ESP32-CAM")
    image_bytes = flask_request.data
    
    if not image_bytes:
        return "No data", 400

    try:
        # 1. Immediate Telegram Feed
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Analyzing with Claude Haiku...")

        # 2. Get AI Analysis
        analysis = analyze_with_claude(image_bytes)
        
        # 3. Final Notification Logic
        if analysis and "YES" in analysis:
            msg = f"🐘 **ALERT: ELEPHANT DETECTED!** 🐘\n{analysis}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        elif analysis and "NO" in analysis:
            bot.send_message(CHAT_ID, "✅ **Result: Clear**")
        else:
            bot.send_message(CHAT_ID, "⚠️ AI Error. Please check API Key/Credits.")

        return "OK", 200

    except Exception as e:
        logger.error(f"System Error: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "Elephant Monitoring (Claude 4.5 Stable) is Online."

if __name__ == "__main__":
    # Railway automatically provides the PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
