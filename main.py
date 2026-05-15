import os
import telebot
from google import genai
from flask import Flask, request as flask_request
from PIL import Image
import io

# Credentials
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route("/photo", methods=["POST"])
def receive_photo():
    image_bytes = flask_request.data
    if not image_bytes:
        return "No data", 400

    # 1. Send photo to your Telegram so you can see it
    bot.send_photo(CHAT_ID, image_bytes, caption="📷 ESP32-CAM Motion Detected!")

    # 2. AI Analysis
    try:
        img = Image.open(io.BytesIO(image_bytes))
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
        )
        answer = response.text.strip().upper()
        
        if "YES" in answer:
            bot.send_message(CHAT_ID, "🐘 ALERT: ELEPHANT CONFIRMED! 🐘")
        else:
            bot.send_message(CHAT_ID, "✅ Analysis: No elephant detected.")
    except Exception as e:
        print(f"Error: {e}")

    return "OK", 200

@app.route("/")
def index():
    return "Server is ready for ESP32-CAM photos!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
