import os
from io import BytesIO
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
from craiyon import Craiyon

# Cargar variables de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Diccionario de estilos (solo texto para reforzar el prompt)
MODELOS = {
    "Anime": "en estilo anime",
    "Realista": "en estilo realista y fotográfico",
    "Estilo Flux": "con estética futurista y abstracta",
}

# Variable global para guardar el modelo seleccionado por usuario
usuario_modelo = {}

# Función para generar imágenes con Craiyon
def generar_imagen_craiyon(prompt: str):
    generator = Craiyon()
    result = generator.generate(prompt)
    imagenes = []
    for idx, img in enumerate(result.images):
        bio = BytesIO()
        img.save(bio, format="JPEG")
        bio.name = f"imagen_{idx}.jpg"
        bio.seek(0)
        imagenes.append(bio)
    return imagenes

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=name)] for name in MODELOS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Por favor selecciona el estilo que deseas para tu imagen:",
        reply_markup=reply_markup
    )

# Comando /reload
async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_modelo.clear()
    await update.message.reply_text(
        "El bot ha sido reiniciado. Usa /start para seleccionar el estilo de nuevo."
    )

# Callback de selección de modelo
async def seleccionar_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    modelo_elegido = query.data
    usuario_id = query.from_user.id
    usuario_modelo[usuario_id] = modelo_elegido
    await query.edit_message_text(
        text=f"Estilo seleccionado: {modelo_elegido}. Ahora envíame el texto para generar la imagen."
    )

# Manejar prompt del usuario
async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id
    if usuario_id not in usuario_modelo:
        await update.message.reply_text(
            "Por favor, primero selecciona un estilo usando /start."
        )
        return

    estilo = MODELOS[usuario_modelo[usuario_id]]
    prompt_usuario = update.message.text
    prompt_completo = f"{prompt_usuario}, {estilo}"

    await update.message.reply_text("Generando imagen, por favor espera 20-40 segundos...")

    try:
        imagenes = generar_imagen_craiyon(prompt_completo)
        for img in imagenes:
            await update.message.reply_photo(photo=img)
    except Exception as e:
        await update.message.reply_text(f"Error generando la imagen: {str(e)}")

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