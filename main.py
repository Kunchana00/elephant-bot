import os
import telebot
from google import genai
from flask import Flask, request as flask_request
from PIL import Image
import io

# Get Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Clients
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Updated for the 2026 google-genai SDK
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
        )
        answer = response.text.strip().upper()
        print(f"--- Gemini Analysis: {answer} ---")
        return "YES" in answer
    except Exception as e:
        print(f"!!! Gemini Error: {e} !!!")
        return False

@app.route("/photo", methods=["POST"])
def receive_photo():
    print(">>> Request received at /photo endpoint")
    image_bytes = flask_request.data
    
    if not image_bytes:
        print("!!! Error: No bytes received !!!")
        return "No data", 400

    print(f">>> Image received: {len(image_bytes)} bytes")

    try:
        # 1. Send to Telegram
        print(">>> Sending to Telegram...")
        bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected! Analyzing...")
        
        # 2. Check for Elephant
        is_elephant = check_elephant(image_bytes)
        
        if is_elephant:
            bot.send_message(CHAT_ID, "🐘 ELEPHANT DETECTED! 🐘")
        else:
            bot.send_message(CHAT_ID, "✅ No elephant detected.")
            
        return "OK", 200
    except Exception as e:
        print(f"!!! System Error: {e} !!!")
        return "Internal Error", 500

@app.route("/")
def index():
    return "Elephant Bot is Active and Waiting for Photos!"

if __name__ == "__main__":
    # Railway sets the PORT variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
