# Prox-Noty: Notificador RSS de Proxmox con Telegram + IA

Prox-Noty es un bot de Telegram que monitorea feeds RSS de repositorios Gitweb (por ejemplo, Proxmox), detecta nuevos commits y envía un resumen en español de los cambios usando IA.

## ¿Qué hace?

- 🔄 **Monitoreo por polling**: consulta RSS periódicamente sin necesidad de webhooks.
- 🧠 **Resumen con IA y fallback**: intenta proveedores en orden (`SambaNova`, `Groq`, `Gemini`).
- 🔖 **Detección de nuevas versiones**: identifica commits tipo `bump version`.
- 🐱 **Integración opcional con The Cat API**: envía una imagen cuando detecta un cambio de versión.
- 🕒 **Conversión de zona horaria**: convierte fechas UTC al huso horario configurado.

## Flujo general

1. Lee los feeds RSS configurados.
2. Compara con el último commit procesado (estado local en `state.json`).
3. Descarga el `commitdiff`.
4. Genera resumen en español con IA (según prioridad y disponibilidad).
5. Envía notificación a Telegram (con imagen de gato en version bumps, si aplica).

---

## Requisitos

- Python **3.14+**
- `uv` (recomendado) o `pip`
- Token de bot de Telegram y `chat_id`
- Al menos una API key de IA (opcional pero recomendado para resúmenes)

## Instalación

```bash
uv sync
```

> Si no usas `uv`, instala dependencias equivalentes con `pip` desde tu entorno.

## Configuración

1. Copia el archivo de ejemplo:

   ```bash
   cp .env.example .env
   ```

2. Edita `.env` y completa tus variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `PROXMOX_BACKUP_RSS`
- `PVE_MANAGER_RSS`
- `AI_PRIORITY` (ejemplo: `sambanova,groq,gemini`)
- `GEMINI_API_KEY`, `GROQ_API_KEY`, `SAMBANOVA_API_KEY` (las que tengas)
- `CAT_API_KEY` (opcional)
- `TIMEZONE` (ejemplo: `America/Caracas`)
- `CHECK_INTERVAL` en segundos

## Ejecución

```bash
uv run python main.py
```

---

## Proveedores de IA: notas rápidas

No necesitas los tres proveedores. Si una API key no está configurada, el bot la omite automáticamente.

- **SambaNova**: puede devolver `410 GONE` si el modelo ya no existe. Actualiza `SAMBANOVA_MODEL`.
- **Groq**: puede devolver `429 TOO MANY REQUESTS` por límite de cuota.
- **Gemini**: puede devolver `429 RESOURCE_EXHAUSTED` por rate limit.

El bot continuará con el siguiente proveedor según `AI_PRIORITY`.

---

## Seguridad y buenas prácticas

- ❗ **Nunca subas tu `.env` al repositorio**.
- Usa tokens/API keys con privilegios mínimos.
- Rota credenciales si sospechas filtración.
- Revisa logs antes de compartirlos (pueden contener datos sensibles).

## Integración con The Cat API (opcional)

Para commits detectados como nueva versión, el bot puede enviar imagen:

- Obtén API key gratuita en [TheCatAPI](https://thecatapi.com/).
- Configúrala en `CAT_API_KEY`.
- Si falla o está vacía, el bot envía solo texto sin romper el flujo.
