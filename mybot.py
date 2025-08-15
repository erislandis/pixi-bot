import os
from dotenv import load_dotenv
from io import BytesIO
import base64
from PIL import Image
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

# Modelos gratuitos
MODELOS = {
    "OpenJourney": "prompthero/openjourney-v4",
    "Stable Diffusion 2.1": "stabilityai/stable-diffusion-2-1",
    "Runway SD v1.5": "runwayml/stable-diffusion-v1-5",
}

# Cliente Hugging Face
client = InferenceClient(api_key=HF_TOKEN)

usuario_modelo = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=name)] for name in MODELOS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Por favor selecciona el tipo de imagen que deseas generar:", reply_markup=reply_markup
    )

async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_modelo.clear()
    await update.message.reply_text("El bot ha sido reiniciado. Usa /start para comenzar de nuevo.")

async def seleccionar_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    modelo_elegido = query.data
    usuario_id = query.from_user.id
    usuario_modelo[usuario_id] = modelo_elegido
    await query.edit_message_text(
        text=f"Modelo seleccionado: {modelo_elegido}. Ahora envíame el texto para generar la imagen."
    )

async def generar_imagen(prompt: str, modelo: str):
    # Solicitud a Hugging Face
    result = client.text_to_image(prompt, model=modelo)
    
    # La respuesta es un JSON con base64
    if isinstance(result, list) and "image" in result[0]:
        img_base64 = result[0]["image"]
        img_bytes = base64.b64decode(img_base64)
        return Image.open(BytesIO(img_bytes))
    
    # Si falla
    raise Exception("No se pudo procesar la imagen desde la respuesta de la API")

async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id
    if usuario_id not in usuario_modelo:
        await update.message.reply_text("Por favor, primero selecciona un modelo usando /start.")
        return

    modelo_actual = MODELOS[usuario_modelo[usuario_id]]
    prompt = update.message.text
    await update.message.reply_text("🎨 Generando imagen, por favor espera...")

    try:
        image = await generar_imagen(prompt, modelo_actual)
        bio = BytesIO()
        image.save(bio, format="PNG")
        bio.seek(0)
        await update.message.reply_photo(photo=bio)
    except Exception as e:
        await update.message.reply_text(f"⚠ Error generando la imagen: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(CallbackQueryHandler(seleccionar_modelo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_prompt))
    app.run_polling()

if __name__ == "__main__":
    main()
