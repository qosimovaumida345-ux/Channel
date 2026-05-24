import os
import time
import subprocess
from typing import Optional
from pynput.mouse import Button, Controller as MouseCtl
from pynput.keyboard import Controller as KbCtl

class ActionHandler:
    def __init__(self):
        self.mouse = MouseCtl()
        self.kb = KbCtl()
        self.holding = False

        self.FIRE_COMMANDS = ["ot", "fire", "shoot", "o't och"]
        self.HOLD_COMMANDS = ["bosib tur", "tur", "hold"]
        self.STOP_COMMANDS = ["toxta", "to'xta", "stop"]
        self.SYSTEM_APPS = {
            "browser": ["brauzer", "browser", "chrome"],
            "code": ["vs code", "kod", "vscode", "studio"],
            "telegram": ["telegram", "tg"]
        }

    # -- OS COMMANDS --
    def _open_app(self, app_name: str) -> str:
        try:
            if app_name == "browser":
                os.system("start https://google.com")
                return "Brauzer ochilmoqda."
            elif app_name == "code":
                os.system("code")
                return "VS Code dasturini ochyapman."
            elif app_name == "telegram":
                os.system("start telegram:")
                return "Telegramni ochyapman."
        except Exception:
            pass
        return "Bu dasturni ochishda xatolik."

    # -- GAME COMMANDS --
    def fire(self):
        self.mouse.click(Button.left)
    
    def hold_fire(self):
        if not self.holding:
            self.holding = True
            self.mouse.press(Button.left)
            
    def release_fire(self):
        if self.holding:
            self.holding = False
            self.mouse.release(Button.left)

    def handle(self, cmd: str) -> Optional[str]:
        """
        Parses text. Returns a string if it handled it instantly locally.
        Otherwise returns None, which means the Brain should handle it.
        """
        c = cmd.lower()

        # O'yin (Game Automation)
        if any(w in c for w in self.FIRE_COMMANDS):
            if any(w in c for w in self.HOLD_COMMANDS):
                self.hold_fire()
                return "O't ochilmoqda, qo'lim tepkisida!"
            self.fire()
            return "Otildi!"
            
        if any(w in c for w in self.STOP_COMMANDS):
            self.release_fire()
            return "To'xtatildi."

        # OS boshqaruv
        if "och" in c or "open" in c:
            for tag, keywords in self.SYSTEM_APPS.items():
                if any(w in c for w in keywords):
                    return self._open_app(tag)
        
        # Hech biriga tushmasa AI ga yuboramiz
        return None
