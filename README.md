
# Telegram Image Bot

## Funcionalidad
- Envía un prompt y el bot genera **1 sola imagen**.
- Usa `/regen` para regenerar con el mismo prompt.
- Mantén el servicio activo con Render + Colab + Ngrok + UptimeRobot.

## Archivos principales
- `mybot.py`: Código del bot para Render
- `colab_motor_sd_turbo.ipynb`: Notebook Colab para generar imágenes
- `requirements.txt`: Dependencias mínimas
- `.env.example`: Variables de entorno

## Flujo
1. Usuario envía prompt → Bot responde con 1 imagen.
2. Usuario escribe `/regen` → Bot regenera con el mismo prompt.