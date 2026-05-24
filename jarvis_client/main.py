import os
import sys
import time
import asyncio
import threading
import queue
import tkinter as tk
from tkinter import Canvas, Text, Scrollbar, Frame, Button
import logging

from brain import Brain
from voice import Voice
from actions import ActionHandler

logging.basicConfig(level=logging.INFO, format="[JARVIS] %(message)s")
logger = logging.getLogger("JARVIS.Main")

class ModernUI:
    STATUS_COLORS = {
        "idle": "#555555",
        "listening": "#00ff88",
        "thinking": "#ffaa00",
        "speaking": "#00aaff",
        "action": "#ff3333",
        "error": "#ff0044",
    }
    
    def __init__(self, jarvis_engine):
        self.engine = jarvis_engine
        
        self.root = tk.Tk()
        self.root.title("JARVIS AI - Dashboard")
        self.root.geometry("400x600")
        self.root.configure(bg="#0a0a0a")
        self.root.attributes("-alpha", 0.95)
        
        # State
        self.is_minimized = False
        self.overlay_win = None
        self.status = "idle"
        
        # Main Window UI
        self._build_main_ui()
        
    def _build_main_ui(self):
        # Header
        header = Frame(self.root, bg="#111", height=50)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="🧠 JARVIS AI CORE", fg="#00d4ff", bg="#111", font=("Consolas", 14, "bold")).pack(side=tk.LEFT, padx=10, pady=10)
        
        btn_min = Button(header, text="O Overlay", bg="#333", fg="#fff", bd=0, command=self.minimize_to_overlay)
        btn_min.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Chat log
        self.chat_frame = Frame(self.root, bg="#0a0a0a")
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log = Text(self.chat_frame, bg="#141414", fg="#eee", font=("Consolas", 10), bd=0, wrap=tk.WORD)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll = Scrollbar(self.chat_frame, command=self.log.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.config(yscrollcommand=scroll.set)
        
        # Status Bar
        self.status_lbl = tk.Label(self.root, text="STATUS: IDLE", bg="#0a0a0a", fg=self.STATUS_COLORS["idle"], font=("Consolas", 10, "bold"))
        self.status_lbl.pack(fill=tk.X, pady=5)
        
        self.add_log("JARVIS faollashtirildi. 0-Delay rejim yoqilgan.", "system")

    def _build_overlay(self):
        size = 64
        self.overlay_win = tk.Toplevel(self.root)
        self.overlay_win.overrideredirect(True)
        self.overlay_win.attributes("-topmost", True)
        self.overlay_win.attributes("-alpha", 0.9)
        self.overlay_win.configure(bg="black")
        
        # Try transparent bg on windows
        try:
            self.overlay_win.attributes("-transparentcolor", "black")
        except:
            pass
            
        scr_w = self.overlay_win.winfo_screenwidth()
        self.overlay_win.geometry(f"{size}x{size}+{scr_w - size - 20}+20")
        
        self.canvas = Canvas(self.overlay_win, width=size, height=size, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        self.ring = self.canvas.create_oval(4, 4, size-4, size-4, fill="#111", outline=self.STATUS_COLORS[self.status], width=2)
        self.canvas.create_text(size//2, size//2, text="J", fill="#00d4ff", font=("Consolas", 22, "bold"))
        self.dot = self.canvas.create_oval(size-18, size-18, size-10, size-10, fill=self.STATUS_COLORS[self.status], outline="")
        
        # Drag mechanics & restoring
        self._dx, self._dy = 0, 0
        self.canvas.bind("<Button-1>", self._ov_click)
        self.canvas.bind("<B1-Motion>", self._ov_drag)
        self.canvas.bind("<Double-Button-1>", self.restore_from_overlay)

    def _ov_click(self, e):
        self._dx, self._dy = e.x, e.y

    def _ov_drag(self, e):
        x = self.overlay_win.winfo_x() + (e.x - self._dx)
        y = self.overlay_win.winfo_y() + (e.y - self._dy)
        self.overlay_win.geometry(f"+{x}+{y}")

    def minimize_to_overlay(self):
        self.root.withdraw() # Hide main win
        self._build_overlay()
        self.is_minimized = True
        
    def restore_from_overlay(self, e=None):
        if self.overlay_win:
            self.overlay_win.destroy()
            self.overlay_win = None
        self.root.deiconify() # Show main win
        self.is_minimized = False

    def set_status(self, st):
        self.status = st
        color = self.STATUS_COLORS.get(st, "#555")
        try:
            self.status_lbl.config(text=f"STATUS: {st.upper()}", fg=color)
            if self.is_minimized and self.overlay_win:
                self.canvas.itemconfig(self.dot, fill=color)
                self.canvas.itemconfig(self.ring, outline=color)
        except Exception as e:
            pass

    def add_log(self, msg, role="user"):
        self.log.insert(tk.END, f"[{role.upper()}] {msg}\n\n")
        self.log.see(tk.END)

    def run(self):
        # Trigger background threading logic
        self.root.after(100, self.engine.start_logic)
        self.root.mainloop()

class JarvisEngine:
    def __init__(self):
        self.brain = Brain()
        self.voice = Voice()
        self.actions = ActionHandler()
        self.ui = ModernUI(self)
        
        self.running = True
        self.active_mode = False
        self.command_queue = queue.Queue()

    def start_logic(self):
        self.voice.speak("Super Jarvis ishga tushdi. O'zbek tilida gapirishingiz mumkin, nol kechikish bilan ulandim.", emotion="excited")
        
        # Start async listeners
        t1 = threading.Thread(target=self._constant_listen_loop, daemon=True)
        t2 = threading.Thread(target=self._process_queue_loop, daemon=True)
        t1.start()
        t2.start()

    def _constant_listen_loop(self):
        """Zero-delay continuous listener in background thread."""
        while self.running:
            if not self.active_mode:
                self.ui.set_status("idle")
                if self.voice.detect_wake():
                    self.active_mode = True
                    self.ui.set_status("listening")
                    self.voice.speak("Xizmatdaman!", emotion="excited")
                    self.ui.add_log("Wake word detected! Listening...", "system")
                continue
            
            # Active Mode - Super fast Listening
            self.ui.set_status("listening")
            cmd = self.voice.listen(timeout=5, phrase_limit=5)
            
            if cmd:
                if "tinch" in cmd or "uxla" in cmd or "sleep" in cmd:
                    self.active_mode = False
                    self.voice.speak("Yaxshi, jim rejimga o'tdim.", emotion="calm")
                    self.ui.add_log("Sleep mode activated.", "system")
                else:
                    self.command_queue.put(cmd)

    def _process_queue_loop(self):
        """Processes commands instantly when passed via queue."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=1)
                self.ui.add_log(cmd, "Siz")
                
                # Check actions first
                local_result = self.actions.handle(cmd)
                if local_result:
                    self.ui.set_status("action")
                    self.voice.speak(local_result, emotion="excited")
                    self.ui.add_log(local_result, "jarvis")
                    continue
                
                # AI Brain
                self.ui.set_status("thinking")
                
                # Run async AI request
                ai_answer = loop.run_until_complete(self.brain.think(cmd))
                self.ui.add_log(ai_answer, "jarvis")
                
                self.ui.set_status("speaking")
                
                # Fast speak via thread
                emotion = "normal"
                if "!" in ai_answer:
                    emotion = "excited"
                elif "xato" in ai_answer or "uzr" in ai_answer:
                    emotion = "sad"
                    
                self.voice.speak(ai_answer, emotion=emotion)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Logic loop error: {e}")

if __name__ == "__main__":
    app = JarvisEngine()
    app.ui.run()
