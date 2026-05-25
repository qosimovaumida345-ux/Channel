"""
JARVIS AI - Intelligence Core (Brain)
=====================================
Ushbu modul Jarvisning asosiy aqli hisoblanadi. 
Foydalanuvchi so'rovini qabul qiladi, uni tahlil qiladi,
gar kerak bo'lsa internetdan yoki tizimdan ma'lumot izlaydi (Fetch/Scrape),
va so'rovni OpenRouter API orqali tegishli modelga yuboradi.

Xususiyatlar:
- HTTP Requests (sinxron, multi-thread)
- Web Web Scraping kiritilgan (BeautifulSoup)
- Uzundan uzun chat xotirasi (Long Term Memory) saqlanadi
- Kategoriyaga qarab mos AI Model tanlash
- Token hisoblash va tarixni tozalash
- Xatoliklarni boshqarish (429, 401, 500)
"""

import os
import json
import logging
import time
import requests
import threading
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from config import ConfigManager, MODEL_CATEGORIES

logger = logging.getLogger("JARVIS.Brain")

AI_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class WebSearcher:
    """Tizim ichidagi aqlli Veb qidiruv va Fetcher."""
    
    def __init__(self, settings: dict):
        self.settings = settings
        self.headers = {
            "User-Agent": self.settings.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        }
        self.timeout = self.settings.get("timeout", 10)
        
    def extract_urls(self, text: str) -> list:
        """Matn ichidan URL manzillarini ajratib oladi."""
        import re
        urls = re.findall(r'(https?://[^\s]+)', text)
        return urls

    def fetch_url(self, url: str) -> str:
        """Keltirilgan URL manzilidan asosiy matnni olib beradi HTML tagsiz."""
        try:
            logger.info(f"Veb yuklanmoqda: {url}")
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Keraksiz teglar tozalanadi (scriptlar, stillar)
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.extract()
                
            text = soup.get_text(separator=' ', strip=True)
            
            max_len = self.settings.get("max_content_length", 5000)
            if len(text) > max_len:
                text = text[:max_len] + "... (Ma'lumot davomi qisqartirildi)"
                
            return text
        except requests.exceptions.Timeout:
            return "Veb sayt javob bermadi (Timeout)."
        except requests.exceptions.HTTPError as e:
            return f"Veb saytda xatolik yuz berdi: HTTP {e.response.status_code}"
        except Exception as e:
            return f"Saytdan ma'lumot olishda xato: {str(e)}"


class Brain:
    """
    Jarvis miyasi - AI asosi. HTTP orqali API ga ulanadi,
    internet bilan ishlaydi, tarixni eslab qoladi.
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.memory_file = os.path.join(os.path.expanduser("~"), ".jarvis", "jarvis_memory.json")
        self.history = []
        self.long_term_data = {}
        self.web = WebSearcher(self.config.get_web_settings())
        self._lock = threading.Lock()
        
        self.load_memory()
    
    def load_memory(self):
        """Oldingi suhbatlarni xotiradan yuklash."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.long_term_data = data.get("facts", {})
                    # Oxirgi 20 xabarni qoldirish (System promplarga og'irlik tushmasligi uchun)
                    self.history = data.get("history", [])[-20:]
            except Exception as e:
                logger.error(f"Xotirani o'qishda xato: {e}")
    
    def save_memory(self):
        """Suhbat tarixini saqlash."""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({
                    "facts": self.long_term_data,
                    "history": self.history[-40:]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Xotirani saqlashda xato: {e}")
    
    def _prepare_system_prompt(self, category: str, web_context: str = "") -> str:
        """Har bir so'rov holatiga qarab murakkab tizim promptini yaratish."""
        base_prompt = self.config.get_system_prompt()
        
        # 1. Kategoriya bo'yicha urg'ular
        cat_info = MODEL_CATEGORIES.get(category, {})
        hint = cat_info.get("system_hint", "")
        if hint:
            base_prompt += f"\n\n[Joriy Kontekst: {hint}]"
            
        # 2. Xotira (Eslab qolingan faktlar)
        if self.long_term_data:
            facts = "\n".join([f"- {k}: {v}" for k, v in self.long_term_data.items()])
            base_prompt += f"\n\n[Foydalanuvchi Faktlari]:\n{facts}"
            
        # 3. Web Context (Agar link berilgan bo'lsa)
        if web_context:
            base_prompt += f"\n\n[Internetdan Olingan Ma'lumot (Linkdan)]: \n{web_context}\nShu ma'lumot asosida javob bering."
            
        return base_prompt
    
    def think(self, prompt: str) -> dict:
        """
        Asosiy miya tahlil jarayoni.
        1) Qaysi model, kalit, va parametr ekanini NLP bilan hisoblab topadi.
        2) Veb manzil borligini tekshiradi, bo'lsa yuklaydi.
        3) Barchasini birlashtirib AI Modelga so'rovni HTTP orqali uzatadi.
        
        Qaytaradi (dict): answer, category, model, status, time_taken
        """
        with self._lock:
            start_time = time.time()
            
            # --- NLP QILISH VA IDENTIFIKATSIYA ---
            category = self.config.detect_category(prompt)
            api_key = self.config.get_api_key_for_category(category)
            model_name = self.config.get_model_for_category(category)
            
            temperature = self.config.get_temperature_for_category(category)
            max_tokens = self.config.get_max_tokens_for_category(category)
            
            if not api_key:
                return {
                    "answer": "API kalit sozlanmagan. Tizim sozlamalaridan kalit qo'shing.",
                    "category": category,
                    "model": "None",
                    "status": "error_no_key",
                    "time": 0
                }
            
            # --- WEB SCRAPING ---
            web_context = ""
            urls = self.web.extract_urls(prompt)
            if urls:
                # Birinchi topilgan urldan fetch qilish
                web_context = self.web.fetch_url(urls[0])
                category = "web_search" # Majburiy o'zgartirish
            
            # --- XABARLARNI SHAKLLANTIRISH ---
            self.history.append({"role": "user", "content": prompt})
            
            sys_prompt = self._prepare_system_prompt(category, web_context)
            messages = [{"role": "system", "content": sys_prompt}]
            
            # Tarixdan faqat oxirgi 10 ta aylana (20 message)
            messages.extend(self.history[-15:])
            
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.9,
                "frequency_penalty": 0.2
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://jarvis-ai-client.local", # Standard req
                "X-Title": "Jarvis Desktop PRO"
            }
            
            # --- API SO'ROVI ---
            try:
                # Async emas, mutlaqo standard sinxron API so'rovi xuddi fastapi/requests dek
                resp = requests.post(AI_API_URL, headers=headers, json=payload, timeout=25)
                
                exec_time = round(time.time() - start_time, 2)
                
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["choices"][0]["message"]["content"]
                    
                    self.history.append({"role": "assistant", "content": answer})
                    self.save_memory()
                    
                    return {
                        "answer": answer.strip(),
                        "category": category,
                        "model": model_name,
                        "status": "success",
                        "time": exec_time
                    }
                    
                # XATOLIKLARNI KO'RISH
                err_msg = resp.text
                if resp.status_code == 401:
                    status_type = "auth_error"
                    text = f"Xato (401): Ushbu model uchun ({model_name}) kiritilgan API kalit xato yoki o'chirilgan."
                elif resp.status_code == 429:
                    status_type = "rate_limit"
                    text = f"Xato (429): API so'rovlar limiti tugadi yoki model ({model_name}) xaddan tashqari band."
                elif resp.status_code == 402:
                    status_type = "payment_required"
                    text = f"Xato (402): Ushbu model pullik va sizning balansingiz yetarli emas."
                elif resp.status_code >= 500:
                    status_type = "server_error"
                    text = f"Xato ({resp.status_code}): OpenRouter serverlari o'chib qoldi yoki ishlamayapti."
                else:
                    status_type = "unknown_error"
                    text = f"Noma'lum xato ({resp.status_code}): Model javob qaytara olmadi."
                    
                logger.error(f"API Xatosi [{resp.status_code}]: {err_msg}")
                return {
                    "answer": text,
                    "category": category,
                    "model": model_name,
                    "status": status_type,
                    "time": exec_time
                }
                
            except requests.exceptions.Timeout:
                return {
                    "answer": "Internet tezligi juda past yoki AI serveri kutilganidan uzoq javob qaytardi.",
                    "category": category,
                    "model": model_name,
                    "status": "timeout",
                    "time": round(time.time() - start_time, 2)
                }
            except requests.exceptions.ConnectionError:
                return {
                    "answer": "Kompyuterda umuman internet yo'q yoki VPN xalaqit qilyapti.",
                    "category": category,
                    "model": model_name,
                    "status": "no_internet",
                    "time": 0
                }
            except Exception as e:
                logger.error(f"Brain Kutilmagan Xato: {str(e)}")
                return {
                    "answer": f"Jarvisning miyasida ichki xatolik yuz berdi: {str(e)}",
                    "category": category,
                    "model": model_name,
                    "status": "exception",
                    "time": 0
                }
