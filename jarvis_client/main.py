import os
import sys
import time
import asyncio
import threading
import queue
import logging
import customtkinter as ctk
import tkinter as tk
from tkinter import Canvas
from PIL import Image

from brain import Brain
from voice import Voice
from actions import ActionHandler

logging.basicConfig(level=logging.INFO, format="[JARVIS] %(message)s")
logger = logging.getLogger("JARVIS.Main")

# CustomTkinter setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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
        
        self.root = ctk.CTk()
        self.root.title("JARVIS AI - Neural Core")
        self.root.geometry("450x650")
        self.root.attributes("-alpha", 0.95)
        # Attempt to set the icon generated for Jarvis
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
            
        self.is_minimized = False
        self.overlay_win = None
        self.status = "idle"
        
        self._build_main_ui()
        
    def _build_main_ui(self):
        # Header Frame
        header = ctk.CTkFrame(self.root, height=60, corner_radius=0, fg_color="#0a0a0d")
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Title
        title_lbl = ctk.CTkLabel(header, text="🧠 JARVIS SYSTEM", text_color="#00d4ff", font=("Consolas", 18, "bold"))
        title_lbl.pack(side=tk.LEFT, padx=15, pady=15)
        
        # Overlay Button
        btn_min = ctk.CTkButton(header, text="O Mini", width=60, font=("Consolas", 12), text_color="#fff", hover_color="#0055ff", fg_color="#1a1a2e", command=self.minimize_to_overlay)
        btn_min.pack(side=tk.RIGHT, padx=15, pady=15)
        
        # Chat log
        self.chat_frame = ctk.CTkFrame(self.root, fg_color="#121212")
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log = ctk.CTkTextbox(self.chat_frame, fg_color="#121212", text_color="#e0e0e0", font=("Consolas", 12), wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Input Frame (For manual text input)
        input_frame = ctk.CTkFrame(self.root, height=50, fg_color="#0a0a0d", corner_radius=0)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.input_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter command to JARVIS...", font=("Consolas", 12), fg_color="#1a1a2e", text_color="#00d4ff", border_color="#00d4ff", border_width=1)
        self.input_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))
        self.input_entry.bind("<Return>", self.send_manual_command)
        
        btn_send = ctk.CTkButton(input_frame, text="SEND", width=60, font=("Consolas", 12, "bold"), fg_color="#00d4ff", text_color="#000", hover_color="#00aacc", command=self.send_manual_command)
        btn_send.pack(side=tk.RIGHT)

        # Status Bar
        self.status_lbl = ctk.CTkLabel(self.root, text="STATUS: IDLE", text_color=self.STATUS_COLORS["idle"], font=("Consolas", 12, "bold"))
        self.status_lbl.pack(fill=tk.X, pady=(0,5))
        
        self.add_log("SYSTEM ON. Jarvis kutmoqda...", "system")

    def send_manual_command(self, event=None):
        cmd = self.input_entry.get().strip()
        if cmd:
            self.input_entry.delete(0, tk.END)
            # Push specifically to the engine queue
            self.engine.command_queue.put(cmd)

    def _build_overlay(self):
        size = 70
        self.overlay_win = tk.Toplevel(self.root)
        self.overlay_win.overrideredirect(True)
        self.overlay_win.attributes("-topmost", True)
        self.overlay_win.attributes("-alpha", 0.9)
        self.overlay_win.configure(bg="black")
        try:
            self.overlay_win.attributes("-transparentcolor", "black")
        except:
            pass
            
        scr_w = self.overlay_win.winfo_screenwidth()
        self.overlay_win.geometry(f"{size}x{size}+{scr_w - size - 20}+20")
        
        self.canvas = Canvas(self.overlay_win, width=size, height=size, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        # Cyberpunk glowing ring
        self.ring = self.canvas.create_oval(4, 4, size-4, size-4, fill="#0a0a0d", outline=self.STATUS_COLORS[self.status], width=3)
        self.canvas.create_text(size//2, size//2, text="JARVIS", fill="#00d4ff", font=("Consolas", 10, "bold"))
        
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
            self.status_lbl.configure(text=f"STATUS: {st.upper()}", text_color=color)
            if self.is_minimized and self.overlay_win:
                self.canvas.itemconfig(self.ring, outline=color)
        except Exception as e:
            pass

    def add_log(self, msg, role="user"):
        tag_color = "#00d4ff" if role == "jarvis" else "#00ff88" if role == "user" else "#555555"
        self.log.insert(tk.END, f"[{role.upper()}] ", tag_color)
        self.log.insert(tk.END, f"{msg}\n\n")
        self.log.see(tk.END)

    def run(self):
        self.root.after(500, self.engine.start_logic)
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
        # Notify user Jarvis is ready
        self.ui.add_log("Ovoz va Tizim moslashtirildi", "system")
        
        t1 = threading.Thread(target=self._constant_listen_loop, daemon=True)
        t2 = threading.Thread(target=self._process_queue_loop, daemon=True)
        t1.start()
        t2.start()

    def _constant_listen_loop(self):
        while self.running:
            if not self.active_mode:
                self.ui.set_status("idle")
                if self.voice.detect_wake():
                    self.active_mode = True
                    self.ui.set_status("listening")
                    self.voice.speak("Xizmatga tayyorman, gapiring", emotion="excited")
                    self.ui.add_log("Uyg'ondi, eshitilmoqda...", "system")
                continue
            
            self.ui.set_status("listening")
            cmd = self.voice.listen(timeout=5, phrase_limit=5)
            
            if cmd:
                if "uxla" in cmd or "sleep" in cmd or "tinch" in cmd:
                    self.active_mode = False
                    self.voice.speak("Jim rejimga o'tdim.", emotion="calm")
                    self.ui.add_log("Kutish (Idle) rejimiga o'tdi", "system")
                else:
                    self.command_queue.put(cmd)

    def _process_queue_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=1)
                self.ui.add_log(cmd, "user")
                
                local_result = self.actions.handle(cmd)
                if local_result:
                    self.ui.set_status("action")
                    self.voice.speak(local_result, emotion="excited")
                    self.ui.add_log(local_result, "jarvis")
                    continue
                
                self.ui.set_status("thinking")
                
                # Execute standard HTTP requests (through ASYNC wrapper)
                ai_answer = loop.run_until_complete(self.brain.async_think(cmd))
                self.ui.add_log(ai_answer, "jarvis")
                
                self.ui.set_status("speaking")
                
                emotion = "normal"
                if "!" in ai_answer or "xato" in ai_answer:
                    emotion = "excited"
                    
                self.voice.speak(ai_answer, emotion=emotion)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Logic loop error: {e}")

if __name__ == "__main__":
    app = JarvisEngine()
    app.ui.run()
