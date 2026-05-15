import os
import telebot
import logging
from google import genai
from flask import Flask
from PIL import Image
import io
import sys
import threading

# Setup Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('bot')

# Get Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Clients
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
        )
        answer = response.text.strip().upper()
        return "YES" in answer
    except Exception as e:
        logger.error(f"GEMINI ERROR: {e}")
        return False

# --- THIS PART HANDLES YOUR MANUAL UPLOADS ---
@bot.message_handler(content_types=['photo'])
def handle_manual_photo(message):
    logger.info("MANUAL PHOTO RECEIVED IN CHAT")
    bot.reply_to(message, "🔍 Analyzing your photo...")
    
    try:
        # Get the highest resolution version of the photo
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Check for elephant
        is_elephant = check_elephant(downloaded_file)
        
        if is_elephant:
            bot.reply_to(message, "🐘 ELEPHANT DETECTED! 🐘")
        else:
            bot.reply_to(message, "✅ No elephant detected.")
    except Exception as e:
        logger.error(f"CHAT ERROR: {e}")
        bot.reply_to(message, "⚠️ Error processing image.")

@app.route("/")
def index():
    return "Elephant Bot is listening to the Telegram Chat!"

# Run both Flask (for Railway health) and Bot (for Chat)
if __name__ == "__main__":
    # Start the bot in a separate thread so it doesn't block Flask
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    # Run Flask on the port Railway expects
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
