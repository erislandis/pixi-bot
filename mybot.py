import os
from io import BytesIO
import requests
from dotenv import load_dotenv
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

# Diccionario con modelos gratuitos
MODELOS = {
    "OpenJourney v4": "prompthero/openjourney-v4",
    "Stable Diffusion 2.1": "stabilityai/stable-diffusion-2-1"
}

# Variable global para guardar el modelo seleccionado por usuario
usuario_modelo = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=name)] for name in MODELOS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Selecciona el tipo de imagen que deseas generar:", reply_markup=reply_markup
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

# Función para generar imagen usando la API pública de Hugging Face
def generar_imagen_hf(prompt: str, modelo: str):
    url = f"https://api-inference.huggingface.co/models/{modelo}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt
    }
    response = requests.post(url, headers=headers, json=payload)
    content_type = response.headers.get("content-type")

    if content_type.startswith("image/"):
        return response.content
    elif content_type == "application/json":
        data = response.json()
        if "error" in data:
            raise Exception(data["error"])
        if isinstance(data, list) and "image" in data[0]:
            import base64
            return base64.b64decode(data[0]["image"])
        raise Exception(f"Respuesta desconocida de la API: {data}")
    else:
        raise Exception(f"Tipo de contenido inesperado: {content_type}")

async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id
    if usuario_id not in usuario_modelo:
        await update.message.reply_text(
            "Por favor, primero selecciona un modelo usando /start."
        )
        return

    modelo_actual = MODELOS[usuario_modelo[usuario_id]]
    prompt = update.message.text
    await update.message.reply_text("Generando imagen, por favor espera...")

    try:
        img_bytes = generar_imagen_hf(prompt, modelo_actual)
        bio = BytesIO(img_bytes)
        await update.message.reply_photo(photo=bio)
    except Exception as e:
        await update.message.reply_text(f"Error generando la imagen: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(CallbackQueryHandler(seleccionar_modelo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_prompt))
    app.run_polling()

if __name__ == "__main__":
    main()
