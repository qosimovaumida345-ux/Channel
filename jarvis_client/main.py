import os
import sys
import time
import asyncio
import threading
import tkinter as tk
from tkinter import Canvas
import logging

from brain import Brain
from voice import Voice
from actions import ActionHandler

logging.basicConfig(level=logging.INFO, format="[JARVIS] %(message)s")
logger = logging.getLogger("JARVIS.Main")

class Overlay:
    STATUS_COLORS = {
        "idle": "#555555",
        "listening": "#00ff88",
        "thinking": "#ffaa00",
        "speaking": "#00aaff",
        "action": "#ff3333",
        "error": "#ff0044",
    }
    
    def __init__(self, size=64):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="black")
        try:
            self.root.attributes("-transparentcolor", "black")
        except:
            pass

        scr_w = self.root.winfo_screenwidth()
        self.root.geometry(f"{size}x{size}+{scr_w - size - 20}+20")
        
        self.canvas = Canvas(self.root, width=size, height=size, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        self.ring = self.canvas.create_oval(4, 4, size-4, size-4, fill="#111", outline="#00d4ff", width=2)
        self.canvas.create_text(size//2, size//2, text="J", fill="#00d4ff", font=("Consolas", 22, "bold"))
        self.dot = self.canvas.create_oval(size-18, size-18, size-10, size-10, fill="#555", outline="")
        
        self._dx = 0
        self._dy = 0
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<B1-Motion>", self._drag)

    def _click(self, e):
        self._dx = e.x
        self._dy = e.y

    def _drag(self, e):
        x = self.root.winfo_x() + (e.x - self._dx)
        y = self.root.winfo_y() + (e.y - self._dy)
        self.root.geometry(f"+{x}+{y}")

    def set_status(self, st):
        color = self.STATUS_COLORS.get(st, "#555")
        try:
            self.root.after(0, lambda: self.canvas.itemconfig(self.dot, fill=color))
            self.root.after(0, lambda: self.canvas.itemconfig(self.ring, outline=color))
        except:
            pass
            
    def run(self):
        self.root.mainloop()

class Jarvis:
    def __init__(self):
        self.brain = Brain()
        self.voice = Voice()
        self.actions = ActionHandler()
        self.overlay = Overlay()
        
        self.running = True
        self.active_mode = False

    def loop(self):
        time.sleep(1)
        self.voice.speak("Super Jarvis ishga tushdi va xizmatingizga tayyor.", emotion="calm")
        
        while self.running:
            try:
                if not self.active_mode:
                    self.overlay.set_status("idle")
                    if self.voice.detect_wake():
                        self.active_mode = True
                        self.overlay.set_status("listening")
                        self.voice.speak("Xizmatdaman!", emotion="excited")
                    continue
                
                self.overlay.set_status("listening")
                cmd = self.voice.listen(timeout=6)
                
                if not cmd:
                    continue
                
                logger.info(f"Yozib olindi: {cmd}")
                
                if "yopil" in cmd or "exit" in cmd or "o'chir" in cmd:
                    self.voice.speak("Xayr, do'stim. O'chmoqdaman.", emotion="sad")
                    self.actions.release_fire()
                    os._exit(0)

                if "tinch" in cmd or "uxla" in cmd or "sleep" in cmd:
                    self.active_mode = False
                    self.voice.speak("Yaxshi, kuzatuv rejimiga o'tdim.", emotion="calm")
                    continue

                # 1. Action Check (Local Macro / Game / System)
                local_result = self.actions.handle(cmd)
                if local_result:
                    self.overlay.set_status("action")
                    self.voice.speak(local_result, emotion="excited")
                    continue
                
                # 2. AI Brain Check (Code, Questions, Empathy)
                self.overlay.set_status("thinking")
                
                # Run async think in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ai_answer = loop.run_until_complete(self.brain.think(cmd))
                loop.close()

                self.overlay.set_status("speaking")
                
                # Dynamic feeling detection from text length/context for TTS
                emotion = "normal"
                if "xato" in cmd or "kechirasiz" in ai_answer:
                    emotion = "sad"
                elif "!" in ai_answer:
                    emotion = "excited"

                self.voice.speak(ai_answer, emotion=emotion)
            except Exception as e:
                logger.error(f"Xato: {e}")
                
    def start(self):
        t = threading.Thread(target=self.loop, daemon=True)
        t.start()
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            os._exit(0)

if __name__ == "__main__":
    j = Jarvis()
    j.start()
