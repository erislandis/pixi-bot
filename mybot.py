import os
import asyncio
from io import BytesIO
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

# Cargar variables de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Modelos gratuitos de Hugging Face
MODELOS = {
    "Anime": "Linaqruf/anything-v3.0",
    "Realista": "runwayml/stable-diffusion-v1-5",
    "Estilo Flux": "stabilityai/stable-diffusion-2-1-base"
}

# Descriptores extra por estilo para mejorar calidad
DESCRIPTORES = {
    "Anime": "masterpiece, best quality, anime style, vibrant colors, detailed character",
    "Realista": "ultra realistic, photorealistic, high detail, 8k, cinematic lighting",
    "Estilo Flux": "futuristic, cyberpunk, abstract art, high detail, vivid colors"
}

# Cliente Hugging Face
client = InferenceClient(token=HF_TOKEN)

# Variable global para guardar estilo/modelo del usuario
usuario_modelo = {}

# /start → menú de selección
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=name)] for name in MODELOS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Selecciona el estilo de imagen que deseas:",
        reply_markup=reply_markup
    )

# /reload → reinicia selección
async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_modelo.clear()
    await update.message.reply_text(
        "Bot reiniciado. Usa /start para elegir estilo de nuevo."
    )

# Selección de modelo
async def seleccionar_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    modelo_elegido = query.data
    usuario_id = query.from_user.id
    usuario_modelo[usuario_id] = modelo_elegido
    await query.edit_message_text(
        text=f"Estilo seleccionado: {modelo_elegido}. Ahora envíame el texto para generar la imagen."
    )

# Función SÍNCRONA para generar imagen
def generar_imagen(prompt: str, modelo: str):
    return client.text_to_image(prompt, model=modelo)

# Manejar prompt del usuario
async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id
    if usuario_id not in usuario_modelo:
        await update.message.reply_text("Primero selecciona un estilo usando /start.")
        return

    estilo = usuario_modelo[usuario_id]
    modelo_actual = MODELOS[estilo]
    prompt_usuario = update.message.text
    # Añadir descriptores para mejorar calidad según estilo
    prompt_final = f"{prompt_usuario}, {DESCRIPTORES[estilo]}"

    await update.message.reply_text("Generando imagen... esto puede tardar unos segundos.")

    try:
        # Ejecutar función síncrona en thread separado
        loop = asyncio.get_running_loop()
        image_bytes = await loop.run_in_executor(None, generar_imagen, prompt_final, modelo_actual)

        bio = BytesIO(image_bytes)
        bio.name = "imagen.png"
        bio.seek(0)
        await update.message.reply_photo(photo=bio)
    except Exception as e:
        await update.message.reply_text(f"Error generando imagen: {str(e)}")

# Main
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(CallbackQueryHandler(seleccionar_modelo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_prompt))
    app.run_polling()

if __name__ == "__main__":
    main()