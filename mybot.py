import os
import asyncio
from io import BytesIO
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters,
)
import requests
from PIL import Image

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # API key para OpenRouter

# Sistemas para elegir
SISTEMAS = ["huggingface", "openrouter"]

# Modelos disponibles en Hugging Face con proveedores
MODELOS_HF = {
    "Stable Diffusion 2.1 Base": {
        "id": "stabilityai/stable-diffusion-2-1-base",
        "proveedores": ["auto", "replicate", "fal-ai", "together"]
    },
    "FLUX 1 Schnell": {
        "id": "black-forest-labs/FLUX.1-schnell",
        "proveedores": ["fal-ai", "together", "replicate"]
    },
    "Hyper-SD": {
        "id": "ByteDance/Hyper-SD",
        "proveedores": ["fal-ai", "replicate", "auto"]
    },
}

# Modelos disponibles en OpenRouter
MODELOS_OR = {
    "Stable Diffusion 2.1 Base": "stabilityai/stable-diffusion-2-1-base",
    "FLUX 1 Schnell": "black-forest-labs/FLUX.1-schnell",
    "Hyper-SD": "ByteDance/Hyper-SD",
    "Flux Realism LoRA": "XLabs-AI/flux-RealismLora",
}

# Guardar elecciones usuario
usuario_sistema = {}
usuario_modelo = {}
usuario_proveedor = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(s, callback_data=f"sistema|{s}")] for s in SISTEMAS]
    await update.message.reply_text("Selecciona el sistema para generación de imágenes:", reply_markup=InlineKeyboardMarkup(keyboard))

async def seleccionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    usuario_id = query.from_user.id

    if data[0] == "sistema":
        sistema = data[1]
        usuario_sistema[usuario_id] = sistema
        if sistema == "huggingface":
            keyboard = [[InlineKeyboardButton(m, callback_data=f"model|{m}")] for m in MODELOS_HF.keys()]
        else:  # openrouter
            keyboard = [[InlineKeyboardButton(m, callback_data=f"model|{m}")] for m in MODELOS_OR.keys()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"Sistema '{sistema}' seleccionado. Ahora elige el modelo:", reply_markup=reply_markup)

    elif data[0] == "model":
        modelo = data[1]
        usuario_modelo[usuario_id] = modelo

        sistema = usuario_sistema.get(usuario_id)
        if sistema == "huggingface":
            proveedores = MODELOS_HF[modelo]["proveedores"]
            keyboard = [[InlineKeyboardButton(p, callback_data=f"provider|{p}")] for p in proveedores]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=f"Modelo '{modelo}' seleccionado.\nElige proveedor:", reply_markup=reply_markup)
        else:
            usuario_proveedor[usuario_id] = "openrouter"
            await query.edit_message_text(text=f"Modelo '{modelo}' seleccionado en OpenRouter.\nAhora envía el texto para generar la imagen.")

    elif data[0] == "provider":
        proveedor = data[1]
        usuario_proveedor[usuario_id] = proveedor
        modelo = usuario_modelo.get(usuario_id)
        await query.edit_message_text(text=f"Proveedor '{proveedor}' seleccionado.\nAhora envía el texto para generar la imagen con el modelo '{modelo}'.")

def generar_imagen_hf(prompt, modelo, proveedor):
    client = InferenceClient(provider=proveedor, api_key=HF_TOKEN)
    model_id = MODELOS_HF[modelo]["id"]
    image = client.text_to_image(prompt, model=model_id)
    return image

def generar_imagen_or(prompt, modelo):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": modelo,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    # La imagen suele estar en "images" como lista con URLs
    image_url = result.get("images", [None])[0]

    if image_url is None:
        raise Exception("No se encontró imagen en la respuesta de OpenRouter")

    image_response = requests.get(image_url)
    image_response.raise_for_status()
    return Image.open(BytesIO(image_response.content))

async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id

    if usuario_id not in usuario_sistema or usuario_id not in usuario_modelo or usuario_id not in usuario_proveedor:
        await update.message.reply_text("Por favor, usa /start para seleccionar sistema, modelo y proveedor primero.")
        return

    sistema = usuario_sistema[usuario_id]
    modelo = usuario_modelo[usuario_id]
    proveedor = usuario_proveedor[usuario_id]
    prompt = update.message.text

    await update.message.reply_text("Generando imagen, por favor espera...")

    try:
        loop = asyncio.get_event_loop()
        if sistema == "huggingface":
            imagen = await loop.run_in_executor(None, generar_imagen_hf, prompt, modelo, proveedor)
        else:
            imagen = await loop.run_in_executor(None, generar_imagen_or, prompt, MODELOS_OR[modelo])

        bio = BytesIO()
        imagen.save(bio, format="PNG")
        bio.seek(0)
        await update.message.reply_photo(photo=bio)

    except Exception as e:
        await update.message.reply_text(f"Error generando la imagen: {str(e)}")

async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_sistema.clear()
    usuario_modelo.clear()
    usuario_proveedor.clear()
    await update.message.reply_text("Bot reiniciado. Usa /start para comenzar nuevamente.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(CallbackQueryHandler(seleccionar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_prompt))
    app.run_polling()

if __name__ == "__main__":
    main()
