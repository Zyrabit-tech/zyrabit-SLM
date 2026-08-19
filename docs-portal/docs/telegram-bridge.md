---
sidebar_position: 5
title: 'Telegram Bridge'
description: 'Set up a Telegram bot connected to your Zyrabit SLM instance via n8n webhooks'
---

# ✈️ Telegram Sovereign Bridge

> [!NOTE]
> This guide was originally written for Spanish-speaking teams.

Learn how to connect Zyra with your Telegram to receive notifications and commands in real-time, while keeping full control of your data.

---

## 🤖 Overview
The Telegram bridge allows Zyrabit to communicate with you outside the web console. Unlike commercial clouds, Zyrabit uses a direct connection via **MCP (Model Context Protocol)**, which means Zyra only sends what you ask for and nothing else.

> [!IMPORTANT]
> **Local Privacy**: Your Bot Token and Chat ID never leave your `api-rag` container. The communication with Telegram servers is direct from your local infrastructure.

---

## 🚀 Quick Start: Get your Credentials

Follow these 3 steps to activate the bridge in under 2 minutes.

### 1. Create your Bot (The Messenger)
Talk to the "father" of all bots on Telegram:
1. Open [@BotFather](https://t.me/BotFather) on Telegram.
2. Send the command `/newbot`.
3. Follow the instructions to give it a name (e.g., `Zyra_Sovereign_Bot`).
4. **Copy the HTTP API Token** provided. This is your `TELEGRAM_BOT_TOKEN`.

### 2. Get your Personal ID (The Recipient)
For Zyra to know who to write to, you need your unique user ID:
1. Talk to [@userinfobot](https://t.me/userinfobot).
2. Send any message.
3. The bot will reply with your **Id**. This is your `TELEGRAM_CHAT_ID`.

### 3. Configure Zyrabit
Open your `.env` file and paste your keys:

```bash
# zyrabit-slm/.env
TELEGRAM_BOT_TOKEN="123456789:ABCDefGhIJKlmNoPQRStuvWxyZ"
TELEGRAM_CHAT_ID="987654321"
```

---

## 🛠️ Verification
Once configured, you can test the connection from the Zyrabit terminal:

```bash
# Run the notification test via MCP
./zyra.sh notify "🛡️ Sovereign Connection Successful. Hello, Kai."
```

## 🩺 Sovereign Health Check

Before releasing your node to the community, verify that the synchronization is perfect. Run this command in your terminal to get a visual diagnostic:

```bash
curl -X GET http://localhost/v1/health
```

### What to look for:
- `core_status: "HEALTHY"`: The Zyrabit engine is ready.
- `mcp_bridge: "CONNECTED"`: The tools tunnel is open.
- `pii_shield: "ACTIVE"`: The Gatekeeper is protecting your data.

> [!TIP]
> If you see a `PENDING` status, wait 30 seconds. Zyra is loading the model into your local RAM.

---

## 🔒 Armored Privacy (PII Gatekeeper)
Zyrabit v2.0 includes an **Interception Shield**. Every message sent to Telegram passes through the `Gatekeeper` first.
- If you try to send: *"My API key is sk-12345"*
- Telegram will receive: *"My API key is `<USER_API_KEY_1>`"*

This guarantees that even if you use Telegram, your infrastructure remains **100% Sovereign**.

---

## 🔍 Troubleshooting
- **The bot is not responding**: Make sure you have clicked "START" on your bot in Telegram before trying to send messages from Zyra.
- **Error 401**: Your `TELEGRAM_BOT_TOKEN` is incorrect or has expired.
- **Error 400**: Your `TELEGRAM_CHAT_ID` is incorrect. Make sure to use only the numbers.

---

## Related Documentation
- [Integration Playbook](./integration-playbook.md)
