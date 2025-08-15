import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ApplicationBuilder,
    ContextTypes,
)
import requests
import io
from PIL import Image
from os import environ  # Para leer variables de entorno

# --- Configuración ---
TELEGRAM_TOKEN = environ.get("TELEGRAM_TOKEN") or "TU_TOKEN_DE_TELEGRAM"  # Reemplaza con tu token de Telegram
HUGGINGFACE_API_TOKEN = environ.get("HUGGINGFACE_API_TOKEN") or "TU_API_TOKEN_DE_HUGGINGFACE"  # Reemplaza con tu token de Hugging Face
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"  # Modelo Stable Diffusion 2 (puedes cambiarlo)

# --- Variables Globales (Asegúrate de que estén inicializadas en algún lugar) ---
usuario_sistema = []  # Ejemplo: lista
usuario_modelo = []  # Ejemplo: lista
usuario_proveedor = []  # Ejemplo: lista

# --- Funciones auxiliares ---
def generate_image(text):
    """Genera una imagen a partir de un texto usando la API de Hugging Face."""
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": text}
    response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        image_bytes = io.BytesIO(response.content)
        try:
            image = Image.open(image_bytes)
            return image
        except Exception as e:
            print(f"Error al abrir la imagen: {e}")
            return None
    else:
        print(f"Error en la API de Hugging Face: {response.status_code} - {response.text}")
        return None

def send_image_to_telegram(image, chat_id, bot):
    """Envía la imagen a Telegram."""
    if image:
        bio = io.BytesIO()
        bio.name = 'image.png'
        image.save(bio, 'PNG')
        bio.seek(0)  # Regresar al inicio del buffer
        bot.send_photo(chat_id=chat_id, photo=bio)
    else:
        bot.send_message(chat_id=chat_id, text="No se pudo generar la imagen. Intenta con otro texto.")


# --- Handlers del bot ---
def start(update: Update, context: CallbackContext):
    """Maneja el comando /start."""
    context.bot.send_message(chat_id=update.effective_chat.id, text="¡Hola! Soy un bot que genera imágenes a partir de texto. Usa /imagen [tu texto] para crear una imagen.")
    # Aquí podrías agregar botones para seleccionar proveedores/modelos

def reload(update: Update, context: CallbackContext):
    """Maneja el comando /reload."""
    usuario_sistema.clear()
    usuario_modelo.clear()
    usuario_proveedor.clear()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bot reiniciado. Usa /start para comenzar nuevamente."
    )


def seleccionar(update: Update, context: CallbackContext):
    """Maneja las selecciones desde los botones Inline."""
    query = update.callback_query
    query.answer()  # Siempre responde a la query

    # Ejemplo: Asumiendo que la data del botón es algo como "modelo_123" o "proveedor_456"
    data = query.data
    if data.startswith("modelo_"):
        modelo_id = data[len("modelo_"):]
        # Aquí deberías cargar el modelo (usando modelo_id)
        # Y verificar que tenga un proveedor asociado
        if tiene_proveedor_asociado(modelo_id): # Reemplaza con tu función
            usuario_modelo.append(modelo_id)  # O como estés guardando la selección
            query.edit_message_text(text=f"Modelo {modelo_id} seleccionado.")
        else:
            query.edit_message_text(text=f"El modelo {modelo_id} no tiene un proveedor asociado y no puede ser usado.")


    elif data.startswith("proveedor_"):
        proveedor_id = data[len("proveedor_"):]
        # Aquí deberías cargar el proveedor (usando proveedor_id)
        usuario_proveedor.append(proveedor_id)  # O como estés guardando la selección
        query.edit_message_text(text=f"Proveedor {proveedor_id} seleccionado.")
    else:
        query.edit_message_text(text="Opción inválida.")


def manejar_prompt(update: Update, context: CallbackContext):
    """Maneja el prompt del usuario."""
    chat_id = update.effective_chat.id
    prompt = update.message.text

    # ***AQUI ES DONDE DEBERIAS HACER LA VALIDACION FINAL***
    if not usuario_modelo or not usuario_proveedor:
        context.bot.send_message(chat_id=chat_id, text="Por favor, selecciona un modelo y un proveedor antes de enviar un prompt.")
        return

    # **Validar que el modelo y el proveedor seleccionados son compatibles**
    # if not es_compatible(usuario_modelo[-1], usuario_proveedor[-1]):  # Reemplaza con tu lógica
    #     context.bot.send_message(chat_id=chat_id, text="El modelo y el proveedor seleccionados no son compatibles.")
    #     return

    context.bot.send_message(chat_id=chat_id, text="Generando imagen... (Esto puede tardar)")
    image = generate_image(prompt)  # Reemplaza con tu función de generación
    send_image_to_telegram(image, chat_id, context.bot)


def error(update: Update, context: CallbackContext):
    """Logea errores causados por updates."""
    print(f"Update {update} causó error {context.error}")


# --- Funciones para validar que el modelo tiene proveedor (reemplaza con tu lógica) ---
def tiene_proveedor_asociado(modelo_id):
    """Reemplaza esto con la lógica para verificar si el modelo tiene un proveedor"""
    # Esto es solo un ejemplo. En la realidad, consultarías una base de datos, etc.
    # para verificar que el modelo tiene un proveedor asociado.
    # Por ejemplo:
    # if modelo_id in base_de_datos_de_modelos and base_de_datos_de_modelos[modelo_id]["proveedor"] is not None:
    #     return True
    # else:
    #     return False

    # Para este ejemplo, simplemente retornamos True para el modelo 1 y False para los demás
    if modelo_id == "1":
        return True
    else:
        return False


def es_compatible(modelo_id, proveedor_id):
     """Reemplaza esto con la lógica para verificar si el modelo y proveedor son compatibles"""
     # Esto es solo un ejemplo. En la realidad, consultarías una base de datos, etc.
     return True

# --- Configuración del bot ---
def main():
    """Inicia el bot."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(CallbackQueryHandler(seleccionar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_prompt))
    app.add_error_handler(error)  # Añadido el handler de errores

    # Iniciar el bot
    app.run_polling()


if __name__ == "__main__": # Corrección de sintaxis
    main()
