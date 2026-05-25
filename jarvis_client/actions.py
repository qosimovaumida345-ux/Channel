"""
JARVIS AI - OS & Automation Controller (Actions)
================================================
Tizim, o'yin, va kompyuter ustidan to'liq nazorat moduli.
App ochish, makrolarni ishlatish, va skriptlarni bajarish.

Xususiyatlar:
- Sichqoncha va klaviatura ustidan to'liq avtomatlashtirilgan nazorat (pynput, pyautogui)
- O'yin makrolari (Hold/Release/Clicking)
- Operatsion tizim amallari (shutdown, volume, open apps)
"""

import os
import time
import subprocess
import threading
import logging
from typing import Optional, Dict

# Local actions requiring system control
try:
    from pynput.mouse import Button, Controller as MouseCtl
    from pynput.keyboard import Controller as KbCtl
    from pynput.keyboard import Key
    import pyautogui
    import psutil
except ImportError:
    pass

logger = logging.getLogger("JARVIS.Actions")


class ActionHandler:
    """Kompyuter qurilmalarini va jarayonlarni 0-delay bilan boshqaradi."""
    
    def __init__(self):
        try:
            self.mouse = MouseCtl()
            self.kb = KbCtl()
            pyautogui.FAILSAFE = False
        except:
            self.mouse = None
            self.kb = None
            
        self.holding_button = False
        self._action_lock = threading.Lock()
        
        # Mahalliy buyruqlar lug'ati (Local Execution Dictionaries)
        self.GAME_MACROS = {
            "fire": ["ot", "fire", "shoot", "o't och", "otishni boshla"],
            "hold": ["bosib tur", "ushlab tur", "tur", "hold"],
            "stop": ["toxta", "to'xta", "stop", "qo'yib yubor", "release"]
        }
        
        self.SYSTEM_APPS = {
            "browser": {
                "keywords": ["brauzer", "browser", "chrome", "google", "internetni och"],
                "cmd": "start chrome" if os.name == 'nt' else "google-chrome"
            },
            "code": {
                "keywords": ["vs code", "kod", "vscode", "studio", "dasturlash muhiti"],
                "cmd": "code"
            },
            "telegram": {
                "keywords": ["telegram", "tg", "telegramni och"],
                "cmd": "start telegram:" if os.name == 'nt' else "telegram-desktop"
            },
            "notepad": {
                "keywords": ["bloknot", "yozish", "notepad", "daftar"],
                "cmd": "notepad"
            },
            "calculator": {
                "keywords": ["kalkulyator", "hisoblagich", "calculator"],
                "cmd": "calc"
            }
        }
        
        self.MEDIA_CONTROLS = {
            "vol_up": ["ovozni ko'tar", "ovozini ko'tar", "balandroq", "volume up"],
            "vol_down": ["ovozni pasaytir", "ovozini pasaytir", "sekinroq", "volume down"],
            "mute": ["ovozni o'chir", "jim qil", "mute"],
            "play_pause": ["to'xtat", "davom et", "play", "pause"]
        }

    # ==========================================================
    # GAME & MACRO AUTOMATION
    # ==========================================================
    def trigger_fire(self):
        """Bir marta bosish."""
        if self.mouse:
            self.mouse.click(Button.left)
            
    def trigger_hold(self):
        """Tugmani bosib turish."""
        if self.mouse and not self.holding_button:
            self.holding_button = True
            self.mouse.press(Button.left)
            
    def trigger_release(self):
        """Tugmani qo'yib yuborish."""
        if self.mouse and self.holding_button:
            self.holding_button = False
            self.mouse.release(Button.left)

    # ==========================================================
    # OS & SYSTEM AUTOMATION
    # ==========================================================
    def open_application(self, tag: str) -> str:
        """Kiritilgan Dastur nomini OS terminali orqali tezkor ochadi."""
        app = self.SYSTEM_APPS.get(tag)
        if not app:
            return "Bu dastur ro'yxatda yo'q."
        
        try:
            # Agar Windows bo'lsa
            if os.name == 'nt':
                os.system(app["cmd"])
            else:
                subprocess.Popen(app["cmd"].split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"{tag.capitalize()} ochilmoqda."
        except Exception as e:
            logger.error(f"App ochishda xato: {e}")
            return f"Dasturni ochib bo'lmadi: {str(e)}"
    
    def control_media(self, action: str):
        """Klaviatura media kalitlarini emulyatsiya qiladi."""
        if not self.kb:
            return "Media nazorati sozlanmagan."
            
        try:
            if action == "vol_up":
                for _ in range(5):
                    pyautogui.press('volumeup')
                return "Ovoz balandlatildi."
            elif action == "vol_down":
                for _ in range(5):
                    pyautogui.press('volumedown')
                return "Ovoz pasaytirildi."
            elif action == "mute":
                pyautogui.press('volumemute')
                return "Ovoz holati o'zgartirildi."
            elif action == "play_pause":
                pyautogui.press('playpause')
                return "Media to'xtatildi yoki davom ettirildi."
        except Exception as e:
            return f"Media nazoratida xato: {e}"
            
    def get_system_status(self) -> str:
        """CPU va RAM holatini qaytaradi."""
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory().percent
            return f"Tizim holati: CPU {cpu}%, RAM {ram}% band."
        except:
            return "Tizim holatini o'qish imkonsiz."

    # ==========================================================
    # MAIN HANDLER (ROUTING)
    # ==========================================================
    def handle(self, cmd: str) -> Optional[str]:
        """
        Matnni qabul qilib, mahalliy triggerga to'g'ri kelsa uni darhol bajarib
        NATIJANI str ko'rinishida qaytaradi. Aks holda API ga ruxsat berish uchun None qaytaradi.
        """
        c = cmd.lower()
        
        with self._action_lock:
            # 1. Game Actions
            if any(w in c for w in self.GAME_MACROS["fire"]):
                if any(w in c for w in self.GAME_MACROS["hold"]):
                    self.trigger_hold()
                    return "Diqqat qiling, O't ochilmoqda (Hold)!"
                self.trigger_fire()
                return "Shaytonbosar bosildi (Fire)!"
                
            if any(w in c for w in self.GAME_MACROS["stop"]):
                self.trigger_release()
                return "Bosish to'xtatildi."
                
            # 2. System Apps
            if "och" in c or "open" in c or "ishga tushir" in c:
                for tag, data in self.SYSTEM_APPS.items():
                    if any(w in c for w in data["keywords"]):
                        return self.open_application(tag)
                        
            # 3. Media Controls
            for act_tag, keywords in self.MEDIA_CONTROLS.items():
                if any(w in c for w in keywords):
                    return self.control_media(act_tag)
                    
            # 4. System Diagnostics
            if any(w in c for w in ["holat", "status", "qot", "sekun"]):
                if "cpu" in c or "ram" in c or "tizim" in c:
                    return self.get_system_status()
            
            # Agar yuqoridagilarga to'g'ri kelmasa, Brain.py ga oshiriladi
            return None
