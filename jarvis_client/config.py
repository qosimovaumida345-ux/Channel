"""
JARVIS AI - Configuration & Intelligence Router
================================================
Ko'p API kalitlari, model sozlamalari, kategoriya aniqlash,
va barcha tizim konfiguratsiyalarini boshqarish moduli.

Xususiyatlar:
- Ko'p API kalit saqlash va boshqarish
- 10+ kategoriya bo'yicha aqlli model yo'naltirish
- Ovoz, UI, va tizim sozlamalari
- JSON-based persistent storage
- Avtomatik kategoriya aniqlash (NLP-like scoring)
"""

import os
import json
import logging
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("JARVIS.Config")

# Konfiguratsiya fayl joylashuvi
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".jarvis")
CONFIG_FILE = os.path.join(CONFIG_DIR, "jarvis_config.json")
MEMORY_FILE = os.path.join(CONFIG_DIR, "jarvis_memory.json")
LOG_FILE = os.path.join(CONFIG_DIR, "jarvis.log")
HISTORY_FILE = os.path.join(CONFIG_DIR, "jarvis_history.json")


# ===================================================================
# OPENROUTER MODELLARI RO'YXATI
# ===================================================================
AVAILABLE_MODELS = [
    # Bepul modellar
    {"id": "openrouter/free", "name": "OpenRouter Free (Auto)", "type": "free", "best_for": "general"},
    {"id": "google/gemini-2.0-flash-lite-preview-02-05:free", "name": "Gemini Flash Lite", "type": "free", "best_for": "general"},
    {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Llama 3.2 3B", "type": "free", "best_for": "coding"},
    {"id": "mistralai/mistral-7b-instruct:free", "name": "Mistral 7B", "type": "free", "best_for": "creative"},
    {"id": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek v3", "type": "free", "best_for": "coding"},
    {"id": "qwen/qwen3-8b:free", "name": "Qwen 3 8B", "type": "free", "best_for": "general"},
    # Pullik modellar (agar kalit bo'lsa)
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "type": "paid", "best_for": "general"},
    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "type": "paid", "best_for": "coding"},
    {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "type": "paid", "best_for": "general"},
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "type": "paid", "best_for": "coding"},
]

AVAILABLE_MODELS_IDS = [m["id"] for m in AVAILABLE_MODELS]


# ===================================================================
# KATEGORIYALAR VA KALIT SO'ZLAR
# ===================================================================
MODEL_CATEGORIES = {
    "general": {
        "name": "Umumiy Suhbat",
        "description": "Oddiy suhbat, savol-javob, maslahat, fikrlar",
        "keywords": [
            "salom", "nima", "qanday", "gapir", "suhbat", "fikr", "ayt",
            "tushuntir", "izohla", "nima bo'ldi", "qachon", "qaerda",
            "kim", "nega", "sabab", "ma'no", "ta'rif", "tarjima",
            "hello", "hi", "how", "what", "why", "when", "where", "who",
            "yaxshi", "yomon", "bor", "yo'q", "kerak", "bilasanmi",
            "gapirsana", "menga ayt", "bilaman", "bilmayman"
        ],
        "system_hint": "Oddiy suhbat so'rovi. Samimiy va tabiiy javob ber.",
        "default_model": "openrouter/free",
        "temperature": 0.7,
        "max_tokens": 500
    },
    "coding": {
        "name": "Dasturlash",
        "description": "Kod yozish, debugging, dasturlash savollari",
        "keywords": [
            "kod", "code", "python", "javascript", "java", "html", "css",
            "react", "function", "class", "variable", "loop", "array",
            "database", "sql", "api", "server", "bug", "xato", "error",
            "debug", "program", "dastur", "script", "terminal", "command",
            "git", "github", "pip", "npm", "install", "import", "module",
            "framework", "library", "kutubxona", "algoritm", "algorithm",
            "yoz", "tuzat", "ishlamayapti", "qanday qilib", "misol",
            "syntax", "compile", "runtime", "exception", "try", "catch",
            "def", "return", "print", "input", "output", "file", "read",
            "write", "json", "xml", "yaml", "docker", "deploy"
        ],
        "system_hint": "Dasturlash savoli. Aniq, ishlaydigan kod yoz. Tushuntirish qisqa bo'lsin.",
        "default_model": "openrouter/free",
        "temperature": 0.3,
        "max_tokens": 1000
    },
    "creative": {
        "name": "Ijodiy / G'oyalar",
        "description": "G'oyalar, hikoyalar, kontent, dizayn",
        "keywords": [
            "g'oya", "idea", "hikoya", "story", "ijod", "yarat",
            "dizayn", "design", "style", "uslub", "kontent", "content",
            "matn", "maqola", "article", "blog", "post", "rasm", "video",
            "logo", "brend", "brand", "marketing", "reklama", "slogan",
            "she'r", "poem", "qo'shiq", "song", "scenario", "film",
            "o'ylab ber", "tavsiya", "mashvarat", "yangi", "original",
            "noyob", "kreativ", "creative", "innovatsiya", "innovation",
            "loyiha", "project", "plan", "strategiya", "strategy",
            "presentation", "taqdimot", "pitch", "startup"
        ],
        "system_hint": "Ijodiy so'rov. Original, qiziqarli va ilhomlantiruvchi javob ber.",
        "default_model": "openrouter/free",
        "temperature": 0.9,
        "max_tokens": 800
    },
    "emotional": {
        "name": "Hissiy / Motivatsion",
        "description": "His-tuyg'u, motivatsiya, ruhiy qo'llab-quvvatlash",
        "keywords": [
            "his", "feel", "qayg'u", "xursand", "motivatsiya", "ruhiy",
            "sevgi", "love", "g'amgin", "sad", "yolg'iz", "lonely",
            "qo'rqish", "fear", "stress", "xavotir", "anxiety",
            "depressiya", "depression", "umid", "hope", "kuch", "strength",
            "ishonch", "confidence", "muvaffaqiyat", "success", "baxt",
            "happiness", "do'st", "friend", "oila", "family",
            "munosabat", "relationship", "yordam", "help", "maslahat",
            "advice", "hayot", "life", "ma'no", "meaning", "maqsad",
            "goal", "orzu", "dream", "ilhom", "inspiration",
            "charchagan", "tired", "bezdi", "zerikkdi", "bored"
        ],
        "system_hint": "Hissiy so'rov. Samimiy, yumshoq va qo'llab-quvvatlovchi gapir.",
        "default_model": "openrouter/free",
        "temperature": 0.8,
        "max_tokens": 600
    },
    "gaming": {
        "name": "O'yin / PUBG",
        "description": "PUBG, o'yin strategiyalari, taktikalar",
        "keywords": [
            "pubg", "o'yin", "game", "taktika", "tactic", "strategy",
            "qurol", "weapon", "gun", "sniper", "assault", "smg",
            "map", "xarita", "erangel", "miramar", "sanhok", "vikendi",
            "livik", "karakin", "squad", "duo", "solo", "drop",
            "loot", "zone", "circle", "doira", "vehicle", "mashina",
            "scope", "attachment", "armor", "vest", "helmet", "med",
            "kill", "chicken dinner", "rank", "tier", "season",
            "sensitivity", "settings", "control", "gyroscope",
            "push", "rush", "camp", "position", "cover", "smoke",
            "grenade", "molotov", "flashbang", "recoil", "spray",
            "headshot", "knock", "revive", "heal", "boost"
        ],
        "system_hint": "O'yin savoli. Qisqa va taktik javob ber. PUBG eksperti sifatida gapir.",
        "default_model": "openrouter/free",
        "temperature": 0.5,
        "max_tokens": 400
    },
    "web_search": {
        "name": "Veb Qidiruv / Fetch",
        "description": "Saytlardan ma'lumot olish, veb qidiruv",
        "keywords": [
            "sayt", "site", "website", "url", "link", "sahifa", "page",
            "izla", "search", "qidir", "topib ber", "internet",
            "google", "yukla", "download", "fetch", "scrape",
            "ochib ber", "ko'rsat", "oxirgi", "latest", "news",
            "yangilik", "narx", "price", "kurs", "valyuta", "dollar",
            "bitcoin", "crypto", "ob-havo", "weather", "temperatura",
            "bozor", "market", "statistika", "statistics", "malumot",
            "data", "wiki", "wikipedia", "github", "youtube"
        ],
        "system_hint": "Foydalanuvchi vebdan ma'lumot istayapti. Qo'lingdagi veb tool dan foydalan.",
        "default_model": "openrouter/free",
        "temperature": 0.3,
        "max_tokens": 600
    },
    "system": {
        "name": "Tizim Boshqaruvi",
        "description": "Kompyuter, tizim, dastur boshqaruvi",
        "keywords": [
            "kompyuter", "computer", "tizim", "system", "dastur", "app",
            "application", "o'rnat", "install", "o'chir", "delete",
            "uninstall", "restart", "qayta", "ishga tushir", "run",
            "ochiq", "open", "yop", "close", "oyna", "window",
            "ekran", "screen", "screenshot", "rasm ol", "clipboard",
            "nusxala", "copy", "qo'y", "paste", "kesish", "cut",
            "ovoz", "volume", "brightness", "yorug'lik", "wifi",
            "bluetooth", "printer", "fayl", "file", "papka", "folder",
            "disk", "memory", "xotira", "ram", "cpu", "processor",
            "battery", "batareya", "zaryadka", "power", "shutdown",
            "sleep", "hibernate", "task", "process", "terminal",
            "cmd", "powershell", "browser", "brauzer", "chrome",
            "firefox", "edge", "telegram", "discord", "vscode"
        ],
        "system_hint": "Tizim buyrug'i. Aniq va qisqa javob ber, kerak bo'lsa buyruqni bajara ol.",
        "default_model": "openrouter/free",
        "temperature": 0.3,
        "max_tokens": 300
    },
    "math": {
        "name": "Matematika / Hisoblash",
        "description": "Hisob-kitob, tenglamalar, matematik savollar",
        "keywords": [
            "hisob", "math", "calculate", "hisobla", "nechta", "qancha",
            "son", "number", "formula", "tenglama", "equation",
            "foiz", "percent", "ko'payt", "bo'l", "qo'sh", "ayir",
            "ildiz", "root", "daraja", "power", "quadrat", "square",
            "kub", "cube", "integral", "differensial", "logarifm",
            "sin", "cos", "tan", "pi", "geometriya", "geometry",
            "algebra", "trigonometriya", "statistika", "ehtimol",
            "probability", "o'rtacha", "average", "summa", "sum",
            "minimum", "maksimum", "maximum", "grafik", "graph",
            "konvertatsiya", "convert", "valyuta", "currency",
            "metr", "kilometr", "litr", "kilogramm", "gradus"
        ],
        "system_hint": "Matematik savol. Aniq hisoblash va formulalar bilan javob ber.",
        "default_model": "openrouter/free",
        "temperature": 0.1,
        "max_tokens": 400
    }
}


# ===================================================================
# DOIMIY SOZLAMALAR
# ===================================================================
DEFAULT_CONFIG = {
    "api_keys": [],
    "model_assignments": {},
    "voice_settings": {
        "voice_name": "uz-UZ-SardorNeural",
        "speed": "+0%",
        "pitch": "+0Hz",
        "language": "uz-UZ",
        "volume": 1.0
    },
    "ui_settings": {
        "theme": "dark",
        "window_width": 520,
        "window_height": 720,
        "opacity": 0.96,
        "font_size": 12,
        "font_family": "Segoe UI"
    },
    "system_prompt": (
        "Sen Jarvis - foydalanuvchining shaxsiy aqlli AI yordamchisisan. "
        "Seni yaratuvching: sdzABU. "
        "O'zbek tilida tabiiy va samimiy gaplash. "
        "Javoblarni qisqa, aniq va foydali qil. "
        "Agar kod so'ralsa, ishlashi kafolatlangan kod yoz. "
        "Agar hissiy savol bo'lsa, samimiy va iliq gapir. "
        "Agar o'yin haqida so'ralsa, qisqa taktik javob ber. "
        "Har doim foydalanuvchiga hurmat bilan munosabatda bo'l. "
        "Sen har qanday savolga javob bera olasan - koddan tortib hayotiy maslahatlargacha."
    ),
    "web_settings": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "timeout": 10,
        "max_content_length": 5000
    },
    "fastapi_settings": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 8765
    },
    "created_at": "",
    "last_used": ""
}


# ===================================================================
# KONFIGURATSIYA MENEJERI
# ===================================================================
class ConfigManager:
    """
    Jarvis konfiguratsiya menejeri.
    Barcha sozlamalar, API kalitlari va model tayinlashlarini boshqaradi.
    """
    
    def __init__(self):
        self.config: Dict = {}
        self._ensure_dirs()
        self.load()
    
    def _ensure_dirs(self):
        """Kerakli papkalarni yaratish."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
    
    def load(self):
        """Konfiguratsiya faylini o'qish yoki yangisini yaratish."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                # Yangi maydonlar qo'shilgan bo'lsa, default bilan to'ldirish
                for key, value in DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value
                logger.info(f"Konfiguratsiya yuklandi: {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"Config o'qishda xato: {e}")
                self.config = DEFAULT_CONFIG.copy()
                self.config["created_at"] = datetime.now().isoformat()
                self.save()
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.config["created_at"] = datetime.now().isoformat()
            self.save()
            logger.info("Yangi konfiguratsiya yaratildi.")
    
    def save(self):
        """Konfiguratsiyani faylga saqlash."""
        try:
            self.config["last_used"] = datetime.now().isoformat()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Config saqlashda xato: {e}")
    
    # ==========================================================
    # API KALITLARI BOSHQARUVI
    # ==========================================================
    def get_api_keys(self) -> List[str]:
        """Barcha API kalitlarni qaytar."""
        return self.config.get("api_keys", [])
    
    def add_api_key(self, key: str) -> bool:
        """Yangi API kalit qo'shish. Dublikat bo'lsa False."""
        key = key.strip()
        if not key:
            return False
        if key in self.config.get("api_keys", []):
            return False
        self.config.setdefault("api_keys", []).append(key)
        self.save()
        logger.info(f"Yangi API kalit qo'shildi (total: {len(self.config['api_keys'])})")
        return True
    
    def remove_api_key(self, index: int) -> bool:
        """API kalitni indeks bo'yicha o'chirish."""
        keys = self.config.get("api_keys", [])
        if 0 <= index < len(keys):
            removed = keys.pop(index)
            self.save()
            logger.info(f"API kalit o'chirildi: ...{removed[-4:]}")
            return True
        return False
    
    def get_api_key_for_category(self, category: str) -> Optional[str]:
        """Kategoriya uchun belgilangan API kalitini qaytarish."""
        keys = self.get_api_keys()
        if not keys:
            return None
        
        assignments = self.config.get("model_assignments", {})
        cat_config = assignments.get(category, {})
        idx = cat_config.get("api_key_index", 0)
        
        if 0 <= idx < len(keys):
            return keys[idx]
        return keys[0]
    
    def get_first_valid_key(self) -> Optional[str]:
        """Birinchi mavjud API kalitni qaytarish."""
        keys = self.get_api_keys()
        return keys[0] if keys else None
    
    # ==========================================================
    # MODEL SOZLAMALARI
    # ==========================================================
    def get_model_for_category(self, category: str) -> str:
        """Kategoriya uchun belgilangan modelni qaytarish."""
        assignments = self.config.get("model_assignments", {})
        cat_config = assignments.get(category, {})
        default = MODEL_CATEGORIES.get(category, {}).get("default_model", "openrouter/free")
        return cat_config.get("model", default)
    
    def set_model_for_category(self, category: str, model: str, api_key_index: int = 0):
        """Kategoriya uchun model belgilash."""
        if "model_assignments" not in self.config:
            self.config["model_assignments"] = {}
        self.config["model_assignments"][category] = {
            "model": model,
            "api_key_index": api_key_index
        }
        self.save()
    
    def get_temperature_for_category(self, category: str) -> float:
        """Kategoriya uchun temperature parametrini qaytarish."""
        return MODEL_CATEGORIES.get(category, {}).get("temperature", 0.7)
    
    def get_max_tokens_for_category(self, category: str) -> int:
        """Kategoriya uchun max_tokens ni qaytarish."""
        return MODEL_CATEGORIES.get(category, {}).get("max_tokens", 500)
    
    # ==========================================================
    # KATEGORIYANI ANIQLASH (NLP-like scoring)
    # ==========================================================
    def detect_category(self, text: str) -> str:
        """
        Foydalanuvchi so'rovini tahlil qilib, eng mos kategoriyani aniqlash.
        NLP-ga o'xshash ball tizimi ishlatiladi.
        """
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower))
        
        scores: Dict[str, float] = {}
        
        for cat_id, cat_info in MODEL_CATEGORIES.items():
            score = 0.0
            keywords = cat_info.get("keywords", [])
            
            for keyword in keywords:
                kw_lower = keyword.lower()
                # To'g'ridan-to'g'ri moslik (eng kuchli signal)
                if kw_lower in words:
                    score += 3.0
                # Qisman moslik (substringda)
                elif kw_lower in text_lower:
                    score += 1.5
            
            # URL aniqlash -> web_search
            if cat_id == "web_search":
                if re.search(r'https?://|www\.|\.\w{2,3}/', text_lower):
                    score += 10.0
            
            # Kod belgilari -> coding
            if cat_id == "coding":
                code_signs = ['def ', 'class ', 'import ', 'print(', 'return ', '= ', '==',
                              'if ', 'for ', 'while ', '{', '}', '()', '[]', '//', '#']
                for sign in code_signs:
                    if sign in text_lower:
                        score += 2.0
            
            # Matematik belgilar -> math
            if cat_id == "math":
                math_signs = ['+', '-', '*', '/', '=', '%', '^', 'x', 'y']
                # Faqat agar raqamlar ham bilan birga kelsa
                if any(c.isdigit() for c in text):
                    for sign in math_signs:
                        if sign in text:
                            score += 1.5
            
            scores[cat_id] = score
        
        # Eng yuqori balli kategoriya
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "general"
        return best
    
    # ==========================================================
    # OVOZ SOZLAMALARI
    # ==========================================================
    def get_voice_settings(self) -> dict:
        return self.config.get("voice_settings", DEFAULT_CONFIG["voice_settings"])
    
    def set_voice_name(self, name: str):
        self.config.setdefault("voice_settings", {})["voice_name"] = name
        self.save()
    
    def set_voice_speed(self, speed: str):
        self.config.setdefault("voice_settings", {})["speed"] = speed
        self.save()
    
    # ==========================================================
    # TIZIM PROMPTI
    # ==========================================================
    def get_system_prompt(self) -> str:
        return self.config.get("system_prompt", DEFAULT_CONFIG["system_prompt"])
    
    def set_system_prompt(self, prompt: str):
        self.config["system_prompt"] = prompt
        self.save()
    
    # ==========================================================
    # VEB SOZLAMALARI
    # ==========================================================
    def get_web_settings(self) -> dict:
        return self.config.get("web_settings", DEFAULT_CONFIG["web_settings"])
    
    # ==========================================================
    # FASTAPI SOZLAMALARI
    # ==========================================================
    def get_fastapi_settings(self) -> dict:
        return self.config.get("fastapi_settings", DEFAULT_CONFIG["fastapi_settings"])
    
    def set_fastapi_enabled(self, enabled: bool):
        self.config.setdefault("fastapi_settings", {})["enabled"] = enabled
        self.save()
    
    # ==========================================================
    # UI SOZLAMALARI
    # ==========================================================
    def get_ui_settings(self) -> dict:
        return self.config.get("ui_settings", DEFAULT_CONFIG["ui_settings"])
