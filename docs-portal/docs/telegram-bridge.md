# ✈️ Telegram Sovereign Bridge

Aprende a conectar Zyra con tu Telegram para recibir notificaciones y comandos en tiempo real, manteniendo el control total de tus datos.

---

## 🤖 Overview
El puente de Telegram permite que Zyrabit se comunique contigo fuera de la consola web. A diferencia de las nubes comerciales, Zyrabit utiliza una conexión directa vía **MCP (Model Context Protocol)**, lo que significa que Zyra solo envía lo que tú le pides y nada más.

> [!IMPORTANT]
> **Privacidad Local**: Tu Token de Bot y Chat ID nunca salen de tu contenedor `api-rag`. La comunicación con los servidores de Telegram es directa desde tu infraestructura local.

---

## 🚀 Quick Start: Obtener tus Credenciales

Sigue estos 3 pasos para activar el puente en menos de 2 minutos.

### 1. Crear tu Bot (El Mensajero)
Habla con el "padre" de todos los bots en Telegram:
1. Abre [@BotFather](https://t.me/BotFather) en Telegram.
2. Envía el comando `/newbot`.
3. Sigue las instrucciones para darle un nombre (ej: `Zyra_Sovereign_Bot`).
4. **Copia el HTTP API Token** que te proporcionará. Este es tu `TELEGRAM_BOT_TOKEN`.

### 2. Obtener tu ID Personal (El Destinatario)
Para que Zyra sepa a quién escribirle, necesitas tu ID único de usuario:
1. Habla con [@userinfobot](https://t.me/userinfobot).
2. Envía cualquier mensaje.
3. El bot te responderá con tu **Id**. Este es tu `TELEGRAM_CHAT_ID`.

### 3. Configurar Zyrabit
Abre tu archivo `.env` y pega tus llaves:

```bash
# zyrabit-slm/.env
TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRStuvWxyZ"
TELEGRAM_CHAT_ID="987654321"
```

---

## 🛠️ Verificación
Una vez configurado, puedes probar la conexión desde la terminal de Zyrabit:

```bash
# Ejecuta la prueba de notificación vía MCP
./zyra-up.sh notify "🛡️ Conexión Soberana Exitosa. Hola, Kai."
```

## 🩺 Sovereign Health Check

Antes de lanzar tu nodo a la comunidad, verifica que la sincronización sea perfecta. Ejecuta este comando en tu terminal para obtener un diagnóstico visual:

```bash
curl -X GET http://localhost/v1/health
```

### Qué buscar:
- `core_status: "HEALTHY"`: El motor de Zyrabit está listo.
- `mcp_bridge: "CONNECTED"`: El túnel de herramientas está abierto.
- `pii_shield: "ACTIVE"`: El Gatekeeper está protegiendo tus datos.

> [!TIP]
> Si ves un estado `PENDING`, espera 30 segundos. Zyra está cargando el modelo en tu RAM local.

---

## 🔒 Privacidad Blindada (PII Gatekeeper)
Zyrabit v2.0 incluye un **Escudo de Intercepción**. Todo mensaje enviado a Telegram pasa primero por el `Gatekeeper`.
- Si intentas enviar: *"Mi API key es sk-12345"*
- Telegram recibirá: *"Mi API key es <USER_API_KEY_1>"*

Esto garantiza que incluso si usas Telegram, tu infraestructura sigue siendo **100% Soberana**.

---

## 🔍 Troubleshooting
- **El bot no responde**: Asegúrate de haberle dado a "START" a tu bot en Telegram antes de intentar enviar mensajes desde Zyra.
- **Error 401**: Tu `TELEGRAM_BOT_TOKEN` es incorrecto o ha expirado.
- **Error 400**: Tu `TELEGRAM_CHAT_ID` es incorrecto. Asegúrate de usar solo los números.
