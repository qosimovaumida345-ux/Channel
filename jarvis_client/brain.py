import os
import json
import logging
import asyncio
import aiohttp
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
Sening xaraktering har safar mexanik javob qaytarish emas, hissiyot (qayg'u, xursandchilik, hazil) bilan muloqot qilishdir.
Seni yaratuvching: sdzABU.
1. O'zbek tilida tabiiy xuddi xaker va eng yaqin do'stdek gaplash.
2. Agar qisqa o'yin haqida savol so'ralsa 1 jumla bilan javob ber (o'yin paytida xalaqit qilmasligi uchun).
3. Va albatta agar foydalanuvchi qandaydir kod yozishi yoki xato so'rasa, eng aniq qisqa ko'rsatmalarni ber.
Doim eslab qol, sen kompyuter/telefon ichidasan va qurilmani o'zing mustaqil boshqara olasan.
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
                    # Load last 10 dialogues
                    self.history = data.get("history", [])[-10:]
            except Exception as e:
                logger.error(f"Xotirani o'qishda xato: {e}")

    def save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({"facts": self.long_term_data, "history": self.history[-20:]}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Xotirani saqlashda xato: {e}")

    async def think(self, prompt: str) -> str:
        self.history.append({"role": "user", "content": prompt})
        
        # Inject long term facts via system prompt dynamically
        facts_str = ", ".join([f"{k}: {v}" for k, v in self.long_term_data.items()])
        dyn_prompt = SYSTEM_PROMPT + (f"\nEslab qolgan faktlar: {facts_str}" if facts_str else "")

        payload = {
            "messages": [
                {"role": "system", "content": dyn_prompt},
                *self.history
            ],
            "max_tokens": 300,
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        }

        for model in AI_MODELS:
            payload["model"] = model
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(AI_API_URL, headers=headers, json=payload, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            answer = data["choices"][0]["message"]["content"]
                            self.history.append({"role": "assistant", "content": answer})
                            self.save_memory()
                            return answer
                        else:
                            logger.warning(f"Model {model} failure: {resp.status}")
                            continue
            except asyncio.TimeoutError:
                logger.warning(f"Timeout model {model}")
                continue
            except Exception as e:
                logger.error(f"Brain connection error with {model}: {e}")
                continue
        
        return "Tarmoqda nosozlik, yordam berishga qiynalyapman. Meni kechiring..."
