import os
import asyncio
import logging
import httpx
from app.domain.use_cases.chat_use_case import ChatUseCase
from app.domain.services.gatekeeper import Gatekeeper
from app.infrastructure.shared.cache import global_cache

logger = logging.getLogger("zyrabit.telegram")

class TelegramBridgeWorker:
    """
    Sovereign Telegram Bridge: Listens for user messages and pipes them to the RAG Brain.
    """
    def __init__(self, chat_use_case: ChatUseCase, sio=None):
        self.chat_use_case = chat_use_case
        self.sio = sio
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip('"').strip("'")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip('"').strip("'")
        self.last_update_id = 0
        self.is_running = False


    async def start(self):
        if not self.token or not self.chat_id:
            logger.warning("⚠️ Telegram Bridge: Missing credentials. Polling disabled.")
            return

        logger.info("✈️ Telegram Bridge: Listening for sovereign commands...")
        self.is_running = True
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while self.is_running:
                try:
                    url = f"https://api.telegram.org/bot{self.token}/getUpdates"
                    params = {"offset": self.last_update_id + 1, "timeout": 20}
                    
                    res = await client.get(url, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            await self.handle_update(update)
                except Exception as e:
                    logger.error(f"❌ Telegram Bridge Error: {e}")
                    await asyncio.sleep(5)
                
                await asyncio.sleep(1)

    async def handle_update(self, update):
        message = update.get("message", {})
        text = message.get("text")
        sender_id = str(message.get("from", {}).get("id"))

        if not text or sender_id != self.chat_id:
            return

        logger.info(f"📥 Telegram Message from {sender_id}: {text[:20]}...")
        
        # 0. COMMAND INTERCEPTION (Zero-Lag)
        from app.domain.services.command_router import CommandRouter
        command_res = await CommandRouter.handle(text, source="TELEGRAM", session_id=self.chat_id)
        if command_res:
            response_text = command_res["response"]
            # Reply back to UI
            if self.sio:
                await self.sio.emit("chat_response", command_res)
            # Reply back to Telegram
            import requests
            reply_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(reply_url, json={
                "chat_id": self.chat_id,
                "text": f"🤖 Zyra (Command):\n\n{response_text}"
            }, timeout=10)
            return

        # 1. Immediate Feedback (Thinking...)

        try:
            import requests
            reply_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(reply_url, json={
                "chat_id": self.chat_id,
                "text": "🤖 Zyra está pensando..."
            }, timeout=5)
        except Exception as e:
            logger.error(f"❌ Error sending thinking to Telegram: {e}")

        # 1. Process via Sovereign RAG Brain

        try:
            # Notify UI that a Telegram message is being processed
            if self.sio:
                await self.sio.emit("chat_response", {
                    "response": f"📥 Recibido desde Telegram: {text}",
                    "metadata": {"source": "TELEGRAM"}
                })

            result = await self.chat_use_case.execute(text=text)
            response_text = result.get("response", "I'm sorry, I couldn't process that.")
            
            # 2. Reply back to UI
            if self.sio:
                await self.sio.emit("chat_response", {
                    "response": response_text,
                    "metadata": {"source": "TELEGRAM_REPLY"}
                })

            # 3. Reply back to Telegram
            import requests

            reply_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(reply_url, json={
                "chat_id": self.chat_id,
                "text": f"🤖 Zyra (Sovereign):\n\n{response_text}"
            }, timeout=10)
        except Exception as e:
            logger.error(f"❌ Error replying to Telegram: {e}")

    def stop(self):
        self.is_running = False
