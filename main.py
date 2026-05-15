import os
import telebot
import logging
import base64
import sys
import io
from anthropic import Anthropic
from flask import Flask, request as flask_request

# --- INITIALIZE ---
app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# --- CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = Anthropic(api_key=CLAUDE_KEY)

def analyze_with_claude(image_bytes):
    """Sends image to Claude 3.5 Haiku for analysis"""
    try:
        # Claude needs the image encoded in base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # We use Haiku because it is the fastest and cheapest vision model
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
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
                            "text": "Is there an elephant in this image? Respond only in this format: ANSWER: [YES/NO], CONFIDENCE: [percentage]. Example: ANSWER: YES, CONFIDENCE: 95%"
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
    logger.info(">>> Image received from ESP32-CAM")
    image_bytes = flask_request.data
    
    if not image_bytes:
        return "No data", 400

    try:
        # 1. Send to Telegram first
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Analyzing with Claude AI...")

        # 2. Get Claude's opinion
        analysis = analyze_with_claude(image_bytes)
        
        # 3. Process result
        if analysis and "YES" in analysis:
            msg = f"🐘 **ALERT: ELEPHANT DETECTED!** 🐘\n{analysis}"
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        elif analysis and "NO" in analysis:
            bot.send_message(CHAT_ID, "✅ **Result: Clear**")
        else:
            bot.send_message(CHAT_ID, "⚠️ Claude could not process the image.")

        return "OK", 200

    except Exception as e:
        logger.error(f"System Error: {e}")
        return "Error", 500

@app.route("/")
def index():
    return "Elephant Detection (Claude Edition) is Online."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
