import asyncio
import os
import requests
from io import BytesIO
from PIL import Image

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# --- Reemplaza con tus tokens y claves ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") # Define como variable de entorno
HF_TOKEN = os.environ.get("HF_TOKEN") # Define como variable de entorno
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") # Define como variable de entorno

# --- Define tus modelos y proveedores ---
MODELOS_HF = {
    "sdxl": {"id": "stabilityai/stable-diffusion-xl-base-1.0"}, # Ejemplo
    "sdv15": {"id": "runwayml/stable-diffusion-v1-5"}, # Ejemplo
}

MODELOS_OR = {
    "dall-e-3": "openai/dall-e-3", # Ejemplo
    "sdxl-openrouter": "stabilityai/stable-diffusion-xl-base-1.0", # Ejemplo
}

PROVEEDORES_HF = ["huggingface", "aws", "google"] # Ejemplo

# --- Variables para almacenar la selección del usuario ---
usuario_sistema = {} # {usuario_id: "huggingface" o "openrouter"}
usuario_modelo = {} # {usuario_id: "modelo"}
usuario_proveedor = {} # {usuario_id: "proveedor"}

# --- Importante: Usa InferenceClient solo si eliges huggingface como proveedor ---
try:
    from huggingface_hub import InferenceClient
except ImportError:
    print("Advertencia: No se pudo importar InferenceClient. Asegúrate de instalar huggingface_hub si usas Hugging Face.")
    InferenceClient = None # Para evitar errores si no se usa Hugging Face

# --- Funciones de generación de imágenes ---
def generar_imagen_hf(prompt, modelo, proveedor):
    if InferenceClient is None:
        raise Exception("InferenceClient no está disponible. Asegúrate de instalar huggingface_hub.")

    client = InferenceClient(provider=proveedor, api_key=HF_TOKEN)
    model_id = MODELOS_HF[modelo]["id"]
    image = client.text_to_image(prompt, model=model_id)
    return image


def generar_imagen_or(prompt, modelo):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    image_url = result.get("images", [None])[0]
    if image_url is None:
        raise Exception("No se encontró imagen en la respuesta de OpenRouter")
    img_resp = requests.get(image_url)
    img_resp.raise_for_status()
    return Image.open(BytesIO(img_resp.content))


# --- Funciones de Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los botones de selección de sistema."""
    keyboard = [
        [
            InlineKeyboardButton("Hugging Face", callback_data="sistema_huggingface"),
            InlineKeyboardButton("OpenRouter", callback_data="sistema_openrouter"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Por favor, selecciona el sistema que deseas utilizar:", reply_markup=reply_markup
    )


async def seleccionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las selecciones del usuario (sistema, modelo, proveedor)."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("sistema_"):
        sistema = data.split("_")[1]
        usuario_sistema[query.from_user.id] = sistema
        await query.edit_message_text(f"Has seleccionado el sistema: {sistema}")
        await mostrar_modelos(update, context) # Muestra la selección de modelos
    elif data.startswith("modelo_"):
        modelo = data.split("_")[1]
        usuario_modelo[query.from_user.id] = modelo
        await query.edit_message_text(f"Has seleccionado el modelo: {modelo}")
        if usuario_sistema[query.from_user.id] == "huggingface":
            await mostrar_proveedores(update, context) # Muestra la selección de proveedores (solo para Hugging Face)
        else:
            await query.message.reply_text(
                "¡Listo! Ahora envíame un prompt para generar una imagen."
            ) # Salta la selección de proveedor si es OpenRouter
    elif data.startswith("proveedor_"):
        proveedor = data.split("_")[1]
        usuario_proveedor[query.from_user.id] = proveedor
        await query.edit_message_text(f"Has seleccionado el proveedor: {proveedor}")
        await query.message.reply_text(
            "¡Listo! Ahora envíame un prompt para generar una imagen."
        )
    else:
        await query.message.reply_text("Opción inválida.")


async def mostrar_modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los botones de selección de modelo."""
    query = update.callback_query

    if usuario_sistema.get(query.from_user.id) == "huggingface":
        modelos = MODELOS_HF.keys()
    elif usuario_sistema.get(query.from_user.id) == "openrouter":
        modelos = MODELOS_OR.keys()
    else:
        await query.message.reply_text(
            "Por favor, usa /start para seleccionar sistema primero."
        )
        return

    keyboard = [
        [InlineKeyboardButton(modelo, callback_data=f"modelo_{modelo}") for modelo in modelos]
    ] # Una fila de botones para cada modelo
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "Por favor, selecciona el modelo que deseas utilizar:", reply_markup=reply_markup
    )


async def mostrar_proveedores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los botones de selección de proveedor (solo para Hugging Face)."""
    query = update.callback_query
    keyboard = [
        [
            InlineKeyboardButton(proveedor, callback_data=f"proveedor_{proveedor}")
            for proveedor in PROVEEDORES_HF
        ]
    ] # Una fila de botones para cada proveedor
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "Por favor, selecciona el proveedor de Hugging Face:", reply_markup=reply_markup
    )


async def manejar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_id = update.message.from_user.id

    if (
        usuario_id not in usuario_sistema
        or usuario_id not in usuario_modelo
        or (usuario_sistema[usuario_id] == "huggingface" and usuario_id not in usuario_proveedor)
    ):
        await update.message.reply_text(
            "Por favor, usa /start para seleccionar sistema, modelo y proveedor primero."
        )
        return

    sistema = usuario_sistema[usuario_id]
    modelo = usuario_modelo[usuario_id]
    proveedor = usuario_proveedor.get(usuario_id) # 'get' para manejar el caso de OpenRouter

    prompt = update.message.text

    await update.message.reply_text("Generando imagen, por favor espera...")

    try:
        loop = asyncio.get_event_loop()
        if sistema == "huggingface":
            imagen = await loop.run_in_executor(
                None, generar_imagen_hf, prompt, modelo, proveedor
            )
        else:
            imagen = await loop.run_in_executor(
                None, generar_imagen_or, prompt, MODELOS_OR[modelo]
            )
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
    await update.message.reply_text(
        "Bot reiniciado. Usa /start para comenzar nuevamente."
    )


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", reload))
    app.add_handler(CallbackQueryHandler(seleccionar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_prompt))
    app.run_polling()


if __name__ == "__main__":
    main()