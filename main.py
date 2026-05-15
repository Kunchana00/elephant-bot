import os
import telebot
import logging
from google import genai
from flask import Flask
from PIL import Image
import io
import sys

# Setup Logging so you can see progress in Railway
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('ElephantBot')

# Get Variables from Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Clients
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def check_elephant(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Gemini 1.5 Flash is perfect for this
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=["Is there an elephant in this image? Respond with only 'YES' or 'NO'.", img]
        )
        answer = response.text.strip().upper()
        logger.info(f"AI Result: {answer}")
        return "YES" in answer
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return False

# This triggers when you upload a photo to the bot
@bot.message_handler(content_types=['photo'])
def handle_manual_upload(message):
    logger.info("New photo received from user!")
    bot.reply_to(message, "🔍 Looking for elephants...")
    
    try:
        # Download the photo from Telegram
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Analyze with Gemini
        is_elephant = check_elephant(downloaded_file)
        
        if is_elephant:
            bot.reply_to(message, "🐘 ELEPHANT DETECTED! 🐘")
        else:
            bot.reply_to(message, "✅ No elephant detected in this image.")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        bot.reply_to(message, "⚠️ System error during analysis.")

@app.route("/")
def health_check():
    return "Bot is alive and listening to Telegram!"

if __name__ == "__main__":
    import threading
    
    # Run the bot in a background thread
    logger.info("Starting Telegram Polling...")
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    # Run Flask to satisfy Railway's health check
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
