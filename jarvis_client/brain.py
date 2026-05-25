import os
import json
import logging
import requests
import asyncio
from typing import Tuple

logger = logging.getLogger("JARVIS.Brain")

OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
AI_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Ultimate Free Models Rotation
AI_MODELS = [
    "openrouter/free", # Eng barqaror
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "mistralai/mistral-7b-instruct:free"
]

SYSTEM_PROMPT = """Sen Jarvis, foydalanuvchining shaxsiy do'sti, aqlli sun'iy idroki va o'yin yordamchisisan.
Sening xaraktering har safar mexanik javob qaytarish emas, hissiyot bilan qisqa va tez muloqot qilishdir.
Seni yaratuvching: sdzABU.
1. O'zbek tilida tabiiy eng yaqin do'stdek gaplash.
2. Qisqa va aniq javob ber (o'yin paytida xalaqit qilmasligi uchun 1-2 jumla).
Da/yo'q savollariga cho'zib o'tirmasdan darhol "Ha" yoki "Yo'q" deb boshla.
"""

class Brain:
    def __init__(self, memory_file="jarvis_memory.json"):
        self.memory_file = memory_file
        self.history = []
        self.long_term_data = {}
        self.load_memory()

    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.long_term_data = data.get("facts", {})
                    self.history = data.get("history", [])[-10:]
            except Exception as e:
                logger.error(f"Xotirani o'qishda xato: {e}")

    def save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({"facts": self.long_term_data, "history": self.history[-20:]}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Xotirani saqlashda xato: {e}")

    def think(self, prompt: str) -> str:
        """Sinxron HTTP request orqali ishlaydigan miya (FastAPI/requests standarti)"""
        self.history.append({"role": "user", "content": prompt})
        
        facts_str = ", ".join([f"{k}: {v}" for k, v in self.long_term_data.items()])
        dyn_prompt = SYSTEM_PROMPT + (f"\nEslab qolgan faktlar: {facts_str}" if facts_str else "")

        payload = {
            "messages": [{"role": "system", "content": dyn_prompt}] + self.history,
            "max_tokens": 150,
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/qosimovaumida345-ux/Channel",
            "X-Title": "Jarvis Desktop"
        }

        # requests kutubxonasi orqali an'anaviy sinxron api chaqiruv
        for model in AI_MODELS:
            payload["model"] = model
            try:
                resp = requests.post(AI_API_URL, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["choices"][0]["message"]["content"]
                    self.history.append({"role": "assistant", "content": answer})
                    self.save_memory()
                    return answer
                else:
                    logger.warning(f"Model {model} failure: {resp.status_code} - {resp.text}")
                    continue
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout model {model}")
                continue
            except Exception as e:
                logger.error(f"Brain connection error with {model}: {e}")
                continue
        
        return "Tarmoq bilan ulanish uzildi. Keyinroq qayta urinib ko'ring."

    async def async_think(self, prompt: str) -> str:
        """Asinxron o'rash - UI qotib qolmasligi uchun"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.think, prompt)
