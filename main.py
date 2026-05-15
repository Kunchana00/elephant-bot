import requests
import telebot
from flask import Flask, request as flask_request
from ultralytics import YOLO
from PIL import Image
import io

BOT_TOKEN = "8732051636:AAFzBWYlE6id1sfyidCseuIzmRR1Nmg_nHI"
CHAT_ID = "8241256348"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

print("Loading YOLOv8 model...")
model = YOLO("yolov8n.pt")
print("Model loaded!")

def check_elephant(image_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    results = model(image)
    
    detected_classes = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])
            detected_classes.append((class_name, confidence))
            print(f"Detected: {class_name} ({confidence:.2f})")
    
    for class_name, confidence in detected_classes:
        if class_name == "elephant" and confidence > 0.5:
            return True, confidence
    
    return False, 0.0

# ESP32 sends photo directly to this endpoint
@app.route("/photo", methods=["POST"])
def receive_photo():
    print("Photo received from ESP32!")
    
    image_bytes = flask_request.data
    print(f"Image size: {len(image_bytes)} bytes")
    
    if len(image_bytes) == 0:
        return "Error: no image received", 400
    
    # Send photo to Telegram first
    bot.send_photo(CHAT_ID, image_bytes, caption="📷 Motion detected!")
    
    # Run elephant detection
    is_elephant, confidence = check_elephant(image_bytes)
    
    if is_elephant:
        bot.send_message(CHAT_ID, f"🐘 ELEPHANT DETECTED! (confidence: {confidence:.0%})")
        print(f"Elephant confirmed! Confidence: {confidence:.0%}")
    else:
        bot.send_message(CHAT_ID, "✅ No elephant in photo.")
        print("No elephant detected.")
    
    return "OK", 200

@app.route("/")
def index():
    return "Elephant Detection Bot is running!"

if __name__ == "__main__":
    print("Starting Elephant Detection Bot...")
    app.run(host="0.0.0.0", port=5000)	