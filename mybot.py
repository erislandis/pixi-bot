# -*- coding: utf-8 -*-
import os
import time
import requests
import base64
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# -------------------- Flask Keep-Alive --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot funcionando correctamente"

@app.route('/health')
def health():
    return "ok", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()

# -------------------- Configuración --------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AI_HORDE_API_KEY = os.getenv("AI_HORDE_API_KEY", "0000000000")

AI_HORDE_URL = "https://stablehorde.net/api/v2/generate/async"
CRAIYON_URL = "https://api.craiyon.com/v3"

user_state = {}  # {uid: {"last_prompt": str, "engine": str}}

# -------------------- Motores de Generación --------------------
def generar_horde(prompt):
    payload = {
        "prompt": prompt,
        "params": {"sampler_name": "k_euler", "width": 512, "height": 512, "steps": 20},
        "nsfw": False
    }
    headers = {"apikey": AI_HORDE_API_KEY, "Client-Agent": "TelegramBot:1.0"}
    r = requests.post(AI_HORDE_URL, json=payload, headers=headers)
    if r.status_code not in [200, 202]:
        return None
    job_id = r.json().get("id")
    status_url = f"https://stablehorde.net/api/v2/generate/status/{job_id}"
    start = time.time()
    while time.time() - start < 120:
        status = requests.get(status_url, headers=headers).json()
        if status.get("done") and "generations" in status:
            return status["generations"][0]["img"]
        time.sleep(3)
    return None

def generar_craiyon(prompt):
    try:
        r = requests.post(CRAIYON_URL, json={"prompt": prompt})
        if r.status_code == 200:
            data = r.json()
            if "images" in data and data["images"]:
                img_b64 = data["images"][0]
                img_bytes = base64.b64decode(img_b64)
                filename = f"/tmp/craiyon_{int(time.time())}.jpg"
                with open(filename, "wb") as f:
                    f.write(img_bytes)
                return filename
    except Exception as e:
        print("[Craiyon Error]", e)
    return None

def generar_huggingface(prompt):
    try:
        from gradio_client import Client
        client = Client("stabilityai/stable-diffusion")
        result = client.predict(
            prompt=prompt,
            negative="blurry, low quality, distorted",
            scale=9,
            api_name="/infer"
        )
        # Retorna lista de paths
        return [item["image"] for item in result]
    except Exception as e:
        print("[HuggingFace Error]", e)
        return None

# -------------------- Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_state[uid] = {"last_prompt": None, "engine": "horde"}
    await update.message.reply_text("👋 Bienvenido! Usa /menu para elegir motor de imágenes.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖼 Stable Horde", callback_data="horde")],
        [InlineKeyboardButton("🤖 HuggingFace SD", callback_data="huggingface")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona el motor de generación:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    choice = query.data
    user_state.setdefault(uid, {})["engine"] = choice
    await query.edit_message_text(f"✅ Motor seleccionado: {choice.upper()}")

async def generar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    prompt = update.message.text.strip()
    if not prompt or len(prompt) < 5:
        await update.message.reply_text("⚠️ El prompt es demasiado corto.")
        return

    user_state.setdefault(uid, {})["last_prompt"] = prompt
    engine = user_state[uid].get("engine", "horde")

    await update.message.reply_text(f"🎨 Generando imagen con {engine.upper()}...")

    # -------------------- Lógica de cada motor --------------------
    if engine == "horde":
        img_url = generar_horde(prompt)
        if not img_url:
            img_url = generar_craiyon(prompt)  # fallback
        if img_url:
            if isinstance(img_url, str) and img_url.startswith("http"):
                await update.message.reply_photo(img_url, caption=f"✅ Imagen generada con {engine.upper()}")
            else:
                with open(img_url, "rb") as f:
                    await update.message.reply_photo(f, caption=f"✅ Imagen generada con {engine.upper()}")
        else:
            await update.message.reply_text("❌ No se pudo generar la imagen.")

    elif engine == "huggingface":
        img_paths = generar_huggingface(prompt)
        if img_paths and len(img_paths) > 0:
            path = img_paths[0]  # ⚡ Solo la primera imagen
            with open(path, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Imagen generada con HuggingFace SD")
        else:
            await update.message.reply_text("❌ No se pudo generar la imagen con HuggingFace SD.")

async def regen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    last_prompt = user_state.get(uid, {}).get("last_prompt")
    if not last_prompt:
        await update.message.reply_text("❗ No hay prompt previo. Envía uno primero.")
        return
    await generar(update, context)

async def reload_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_state.pop(uid, None)
    await update.message.reply_text("🔄 Estado reiniciado. Usa /start para comenzar de nuevo.")

# -------------------- Main --------------------
def main():
    keep_alive()
    app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("menu", menu))
    app_bot.add_handler(CallbackQueryHandler(button))
    app_bot.add_handler(CommandHandler("regen", regen))
    app_bot.add_handler(CommandHandler("reload", reload_bot))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generar))
    app_bot.run_polling()

if __name__ == "__main__":
    main()