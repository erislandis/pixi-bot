import os
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

# Modelos gratuitos de Hugging Face para texto a imagen
MODELOS = {
    "Anime": "Linaqruf/anything-v3.0",  # Anime-style Stable Diffusion
    "Realista": "runwayml/stable-diffusion-v1-5",  # Realistic SD 1.5
    "Estilo Flux": "stabilityai/stable-diffusion-2-1-base"  # Más detalle
}

# Cliente Hugging Face
client = InferenceClient(token=HF_TOKEN)

# Variable para guardar estilo/modelo elegido por usuario
usuario_modelo = {}

# /start → menú de selección
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=name)] for name in MODELOS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Por favor selecciona el estilo de imagen que deseas:",
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

# Función para generar imagen con HF
async def generar_imagen(prompt: str, modelo: str):
    image_bytes = client.text_to_image(prompt, model=modelo)
    return image_bytes  # Bytes de la imagen generada

# Manejar texto del usuario y generar imagen
async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id
    if usuario_id not in usuario_modelo:
        await update.message.reply_text("Primero selecciona un estilo usando /start.")
        return

    modelo_actual = MODELOS[usuario_modelo[usuario_id]]
    prompt = update.message.text
    await update.message.reply_text("Generando imagen... espera unos segundos.")

    try:
        image_bytes = await generar_imagen(prompt, modelo_actual)
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