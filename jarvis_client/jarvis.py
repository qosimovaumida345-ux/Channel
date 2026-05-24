"""
╔══════════════════════════════════════════════╗
║   JARVIS AI  —  PUBG Voice Assistant         ║
║   Developed by sdzABU                        ║
║   Version 1.0.0                              ║
╚══════════════════════════════════════════════╝

Floating overlay + voice wake-word + game automation + AI brain.
Runs on Windows.  Build to .exe via PyInstaller / GitHub Actions.
"""

import os
import sys
import time
import json
import logging
import asyncio
import threading
from typing import Optional

# ── UI ───────────────────────────────────────
import tkinter as tk
from tkinter import Canvas

# ── Voice ────────────────────────────────────
import speech_recognition as sr
import pyttsx3

# ── Game Control ─────────────────────────────
from pynput.mouse import Button, Controller as MouseCtl
from pynput.keyboard import Controller as KbCtl

# ── AI ───────────────────────────────────────
import aiohttp

# ─────────────────────────────────────────────
# PATHS & LOGGING
# ─────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, "jarvis.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [JARVIS] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("JARVIS")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
AI_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL = "openrouter/free"

WAKE_WORDS = ["jarvis", "hey jarvis", "jarvis yordam", "jarvis help"]

FIRE_WORDS = ["ot", "o't", "fire", "shoot", "o't och", "ot och"]
HOLD_WORDS = ["tur", "bosib", "hold", "davom", "pressing", "bosib tur"]
STOP_WORDS = ["toxta", "to'xta", "stop", "bas", "qo'y", "release"]
RELOAD_WORDS = ["reload", "zaryadla", "qayta yukla"]
CROUCH_WORDS = ["cho'k", "crouch", "yot", "prone"]
HEAL_WORDS = ["davolay", "heal", "medkit", "aptechka"]
MAP_WORDS = ["xarita", "map", "karta"]
EXIT_WORDS = ["yopil", "o'chir", "exit", "quit", "shut down"]
SLEEP_WORDS = ["uxla", "sleep", "tinch", "dam ol"]


# ═════════════════════════════════════════════
#  AI BRAIN
# ═════════════════════════════════════════════
class Brain:
    """Connects to OpenRouter for intelligent responses."""

    def __init__(self):
        self.history: list[dict] = []

    async def think(self, prompt: str) -> str:
        self.history.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": AI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sen 'Jarvis' nomli shaxsiy AI yordamchisan. "
                        "Yaratuvching: sdzABU. "
                        "Sen PUBG Mobile bo'yicha ekspertsan va foydalanuvchiga "
                        "o'yin davomida ovozli maslahat berasan. "
                        "Javoblarni qisqa ber (3-4 jumla), lekin foydali va aniq."
                    ),
                },
                *self.history[-8:],
            ],
            "max_tokens": 200,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    AI_API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        answer = data["choices"][0]["message"]["content"]
                        self.history.append({"role": "assistant", "content": answer})
                        return answer
                    else:
                        body = await resp.text()
                        logger.warning("AI HTTP %s: %s", resp.status, body[:200])
                        return "Server javob bermadi, keyinroq urinib ko'ring."
        except asyncio.TimeoutError:
            return "Server javob berishda kechikdi."
        except Exception as exc:
            logger.error("Brain error: %s", exc)
            return "Serverga ulanishda xatolik yuz berdi."


# ═════════════════════════════════════════════
#  VOICE ENGINE
# ═════════════════════════════════════════════
class Voice:
    """Speech recognition + text-to-speech (lazy-init for thread safety)."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self._engine: Optional[pyttsx3.Engine] = None
        self._engine_lock = threading.Lock()

    # ── TTS ──────────────────────────────────
    def _get_engine(self) -> pyttsx3.Engine:
        """Lazy-initialise pyttsx3 inside the calling thread."""
        if self._engine is None:
            with self._engine_lock:
                if self._engine is None:
                    engine = pyttsx3.init()
                    # Pick best available voice
                    for v in engine.getProperty("voices"):
                        if "david" in v.id.lower():
                            engine.setProperty("voice", v.id)
                            break
                    engine.setProperty("rate", 170)
                    engine.setProperty("volume", 1.0)
                    self._engine = engine
        return self._engine

    def speak(self, text: str) -> None:
        try:
            engine = self._get_engine()
            engine.say(text)
            engine.runAndWait()
        except RuntimeError:
            # Engine busy — reinit
            with self._engine_lock:
                self._engine = None
            try:
                engine = self._get_engine()
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                logger.error("TTS fallback error: %s", exc)
        except Exception as exc:
            logger.error("TTS error: %s", exc)

    # ── STT ──────────────────────────────────
    def listen(self, timeout: int = 5, phrase_limit: int = 8) -> Optional[str]:
        """Listen via microphone and return lower-cased text, or None."""
        try:
            with sr.Microphone() as mic:
                audio = self.recognizer.listen(
                    mic, timeout=timeout, phrase_time_limit=phrase_limit
                )
                text = self.recognizer.recognize_google(audio, language="en-US")
                return text.lower().strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except sr.RequestError as exc:
            logger.error("Google STT error: %s", exc)
            return None
        except Exception as exc:
            logger.error("Listen error: %s", exc)
            return None

    def detect_wake(self) -> bool:
        """Quick listen for a wake word."""
        text = self.listen(timeout=3, phrase_limit=3)
        if text:
            return any(w in text for w in WAKE_WORDS)
        return False


# ═════════════════════════════════════════════
#  GAME CONTROLLER
# ═════════════════════════════════════════════
class GameController:
    """Simulates mouse / keyboard input for PUBG."""

    def __init__(self):
        self.mouse = MouseCtl()
        self.kb = KbCtl()
        self.holding = False

    def fire(self) -> None:
        self.mouse.click(Button.left)

    def hold_fire(self) -> None:
        if not self.holding:
            self.holding = True
            self.mouse.press(Button.left)

    def release_fire(self) -> None:
        if self.holding:
            self.holding = False
            self.mouse.release(Button.left)

    def tap_key(self, key: str) -> None:
        self.kb.press(key)
        time.sleep(0.05)
        self.kb.release(key)

    def handle(self, cmd: str) -> Optional[str]:
        """Parse a command and act.  Returns a response or None."""
        c = cmd.lower()

        # Fire
        if any(w in c for w in FIRE_WORDS):
            if any(w in c for w in HOLD_WORDS):
                self.hold_fire()
                return "O't ochilmoqda, bosib turyapman!"
            self.fire()
            return "Bir marta otildi!"

        # Stop
        if any(w in c for w in STOP_WORDS):
            self.release_fire()
            return "To'xtatildi!"

        # Reload
        if any(w in c for w in RELOAD_WORDS):
            self.tap_key("r")
            return "Zaryadlanmoqda!"

        # Crouch / Prone
        if any(w in c for w in CROUCH_WORDS):
            self.tap_key("z")
            return "Cho'kdim!"

        # Heal
        if any(w in c for w in HEAL_WORDS):
            self.tap_key("7")
            return "Davolanmoqda!"

        # Map
        if any(w in c for w in MAP_WORDS):
            self.tap_key("m")
            return "Xarita ochildi."

        return None


# ═════════════════════════════════════════════
#  FLOATING OVERLAY (tkinter)
# ═════════════════════════════════════════════
class Overlay:
    """Small always-on-top circle with a status dot."""

    STATUS_COLORS = {
        "idle": "#555555",
        "listening": "#00ff88",
        "thinking": "#ffaa00",
        "speaking": "#00aaff",
        "firing": "#ff3333",
        "error": "#ff0044",
    }

    def __init__(self, size: int = 64):
        self.size = size
        self.root = tk.Tk()
        self.root.title("Jarvis")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.configure(bg="black")

        try:
            self.root.attributes("-transparentcolor", "black")
        except tk.TclError:
            pass

        scr_w = self.root.winfo_screenwidth()
        self.root.geometry(f"{size}x{size}+{scr_w - size - 30}+30")

        self.canvas = Canvas(
            self.root, width=size, height=size, bg="black", highlightthickness=0
        )
        self.canvas.pack()

        pad = 4
        self.ring = self.canvas.create_oval(
            pad, pad, size - pad, size - pad,
            fill="#0d1117", outline="#00d4ff", width=3,
        )
        self.letter = self.canvas.create_text(
            size // 2, size // 2,
            text="J", fill="#00d4ff", font=("Consolas", 24, "bold"),
        )
        dot_s = 10
        self.dot = self.canvas.create_oval(
            size - dot_s - 8, size - dot_s - 8,
            size - 8, size - 8,
            fill="#555555", outline="",
        )

        # Draggable
        self._dx = 0
        self._dy = 0
        self.canvas.bind("<Button-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)

    def _press(self, e: tk.Event) -> None:
        self._dx, self._dy = e.x, e.y

    def _drag(self, e: tk.Event) -> None:
        x = self.root.winfo_x() + (e.x - self._dx)
        y = self.root.winfo_y() + (e.y - self._dy)
        self.root.geometry(f"+{x}+{y}")

    # Thread-safe helpers
    def set_status(self, status: str) -> None:
        color = self.STATUS_COLORS.get(status, "#555555")
        try:
            self.root.after(0, self._apply_color, color)
        except Exception:
            pass

    def _apply_color(self, color: str) -> None:
        self.canvas.itemconfig(self.dot, fill=color)
        self.canvas.itemconfig(self.ring, outline=color)

    def mainloop(self) -> None:
        self.root.mainloop()

    def quit(self) -> None:
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass


# ═════════════════════════════════════════════
#  AUTO-START (Windows Registry)
# ═════════════════════════════════════════════
def register_autostart() -> bool:
    """Add Jarvis to Windows startup (Run key)."""
    try:
        import winreg

        exe = sys.executable
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "JarvisAI", 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        logger.info("Autostart registered: %s", exe)
        return True
    except Exception as exc:
        logger.warning("Autostart registration failed: %s", exc)
        return False


# ═════════════════════════════════════════════
#  MAIN JARVIS ORCHESTRATOR
# ═════════════════════════════════════════════
class Jarvis:
    def __init__(self):
        logger.info("Initialising Jarvis …")
        self.brain = Brain()
        self.voice = Voice()
        self.game = GameController()
        self.overlay = Overlay()
        self.active = False      # actively listening for commands
        self.running = True

    # ── Background worker ────────────────────
    def _worker(self) -> None:
        time.sleep(0.8)  # let tkinter initialise
        self.voice.speak("Jarvis tayyor. Hey Jarvis deb chaqiring.")

        while self.running:
            try:
                if not self.active:
                    # === IDLE: wait for wake word ===
                    self.overlay.set_status("idle")
                    if self.voice.detect_wake():
                        self.active = True
                        self.overlay.set_status("listening")
                        self.voice.speak("Ha, eshitaman, buyuring!")
                    continue

                # === ACTIVE: listen for commands ===
                self.overlay.set_status("listening")
                cmd = self.voice.listen(timeout=6, phrase_limit=10)

                if cmd is None:
                    continue

                logger.info("Heard: %s", cmd)

                # ── Exit ──
                if any(w in cmd for w in EXIT_WORDS):
                    self.voice.speak("Xayr, Jarvis o'chmoqda.")
                    self.running = False
                    self.overlay.quit()
                    break

                # ── Sleep ──
                if any(w in cmd for w in SLEEP_WORDS):
                    self.active = False
                    self.voice.speak("Yaxshi, dam olaman. Hey Jarvis deb chaqiring.")
                    continue

                # ── Game commands (instant, no network delay) ──
                result = self.game.handle(cmd)
                if result:
                    status = "firing" if self.game.holding else "speaking"
                    self.overlay.set_status(status)
                    self.voice.speak(result)
                    continue

                # ── AI Brain (needs network) ──
                self.overlay.set_status("thinking")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    answer = loop.run_until_complete(self.brain.think(cmd))
                finally:
                    loop.close()

                self.overlay.set_status("speaking")
                self.voice.speak(answer)

            except Exception as exc:
                logger.error("Worker error: %s", exc)
                self.overlay.set_status("error")
                time.sleep(2)

    # ── Entry point ──────────────────────────
    def run(self) -> None:
        logger.info("Starting Jarvis …")
        register_autostart()

        worker = threading.Thread(target=self._worker, daemon=True)
        worker.start()

        try:
            self.overlay.mainloop()
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.game.release_fire()
            logger.info("Jarvis shut down.")


# ─────────────────────────────────────────────
def main():
    jarvis = Jarvis()
    jarvis.run()


if __name__ == "__main__":
    main()
