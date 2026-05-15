import os
import telebot
import google.generativeai as genai
from flask import Flask, request as flask_request
from PIL import Image
import io

# Credentials from Railway Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Setup Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant_with_gemini(image_bytes):
    try:
        # Load image from bytes
        img = Image.open(io.BytesIO(image_bytes))
        
        # Ask Gemini to analyze
        prompt = "Is there an elephant in this image? Respond with only 'YES' or 'NO'."
        response = model.generate_content([prompt, img])
        
        answer = response.text.strip().upper()
        print(f"Gemini Analysis: {answer}")
        return "YES" in answer
    except Exception as e:
        print(f"Gemini Error: {e}")
        return False

@app.route("/photo", methods=["POST"])
def receive_photo():
    image_bytes = flask_request.data
    if not image_bytes:
        return "No data received", 400

    try:
        # 1. Send the photo to your Telegram immediately
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")

        # 2. Perform AI Detection (Lightweight)
        is_elephant = check_elephant_with_gemini(image_bytes)

        if is_elephant:
            bot.send_message(CHAT_ID, "🐘 ELEPHANT DETECTED! 🐘")
        else:
            bot.send_message(CHAT_ID, "✅ No elephant detected.")

        return "OK", 200
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500

@app.route("/")
def index():
    return "Elephant Bot (Gemini Mode) is Running Successfully!"

if __name__ == "__main__":
    # Dynamic port for Railway
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
