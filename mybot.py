import os
from dotenv import load_dotenv
from io import BytesIO
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

# Diccionario con modelos gratuitos
MODELOS = {
    "OpenJourney": "prompthero/openjourney-v4",             # Estilo anime/realista
    "StableDiffusion": "stabilityai/stable-diffusion-2-1",  # Imagen realista
    "Runway": "runwayml/stable-diffusion-v1-5",             # Imagen realista
}

# Cliente Hugging Face Inference
client = InferenceClient(api_key=HF_TOKEN)

# Variable global para guardar el modelo seleccionado por usuario
usuario_modelo = {}

# ---- COMANDOS ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(nombre, callback_data=nombre)] for nombre in MODELOS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Por favor selecciona el tipo de imagen que deseas generar:", reply_markup=reply_markup
    )

async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_modelo.clear()
    await update.message.reply_text("El bot ha sido reiniciado. Usa /start para comenzar de nuevo.")

# ---- CALLBACK PARA SELECCIÓN DE MODELO ----
async def seleccionar_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    modelo_elegido = query.data
    usuario_id = query.from_user.id
    usuario_modelo[usuario_id] = modelo_elegido
    await query.edit_message_text(
        text=f"Modelo seleccionado: {modelo_elegido}. Ahora envíame el texto para generar la imagen."
    )

# ---- FUNCIONES DE GENERACIÓN DE IMAGEN ----
async def generar_imagen(prompt: str, modelo: str):
    """
    Genera imagen usando Hugging Face Inference API gratuita.
    Devuelve un objeto PIL.Image.
    """
    image = client.text_to_image(
        prompt,
        model=modelo
    )
    return image

# ---- HANDLER DE MENSAJES ----
async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id

    if usuario_id not in usuario_modelo:
        await update.message.reply_text("Por favor, primero selecciona un modelo usando /start.")
        return

    modelo_actual = MODELOS[usuario_modelo[usuario_id]]
    prompt = update.message.text
    await update.message.reply_text("Generando imagen, por favor espera...")

    try:
        image = await generar_imagen(prompt, modelo_actual)
        bio = BytesIO()
        image.save(bio, format="PNG")
        bio.seek(0)
        await update.message.reply_photo(photo=bio)
    except Exception as e:
        await update.message.reply_text(f"Error generando la imagen: {str(e)}")

# ---- MAIN ----
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(CallbackQueryHandler(seleccionar_modelo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_prompt))
    app.run_polling()

if __name__ == "__main__":
    main()