"""
JARVIS AI - Main Application
Professional CustomTkinter UI with Settings Panel, Multi-API Key Management,
Smart Model Router, Chat Interface, and Animated Overlay.
"""

import os
import sys
import time
import threading
import queue
import logging
import customtkinter as ctk
import tkinter as tk
from tkinter import Canvas

from config import ConfigManager, MODEL_CATEGORIES
from brain import Brain
from voice import Voice
from actions import ActionHandler

logging.basicConfig(level=logging.INFO, format="[JARVIS] %(levelname)s - %(message)s")
logger = logging.getLogger("JARVIS.Main")

# ===================================================================
# THEME & COLORS
# ===================================================================
COLORS = {
    "bg_primary": "#0a0a0f",
    "bg_secondary": "#12121a",
    "bg_tertiary": "#1a1a2e",
    "bg_card": "#16161f",
    "accent": "#00d4ff",
    "accent_hover": "#00a8cc",
    "accent_dim": "#005577",
    "text_primary": "#e8e8e8",
    "text_secondary": "#888899",
    "text_muted": "#555566",
    "success": "#00ff88",
    "warning": "#ffaa00",
    "error": "#ff3355",
    "border": "#2a2a3e",
    "user_msg": "#00d4ff",
    "jarvis_msg": "#00ff88",
    "system_msg": "#555577",
}

STATUS_MAP = {
    "idle": {"color": "#555566", "text": "KUTISH"},
    "listening": {"color": "#00ff88", "text": "TINGLASH"},
    "thinking": {"color": "#ffaa00", "text": "FIKRLASH"},
    "speaking": {"color": "#00d4ff", "text": "GAPIRISH"},
    "action": {"color": "#ff3355", "text": "BAJARILMOQDA"},
    "error": {"color": "#ff0044", "text": "XATO"},
}

ctk.set_appearance_mode("dark")


# ===================================================================
# SETTINGS PANEL (API Keys, Models, Voice)
# ===================================================================
class SettingsPanel(ctk.CTkToplevel):
    """Sozlamalar oynasi - API kalitlari va model boshqaruvi."""
    
    def __init__(self, parent, config: ConfigManager, on_close_callback=None):
        super().__init__(parent)
        self.config = config
        self.on_close_callback = on_close_callback
        
        self.title("JARVIS - Sozlamalar")
        self.geometry("550x650")
        self.configure(fg_color=COLORS["bg_primary"])
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_ui(self):
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_primary"])
        scroll.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # --- API KEYS ---
        ctk.CTkLabel(scroll, text="API KALITLARI", font=("Segoe UI", 16, "bold"),
                     text_color=COLORS["accent"]).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(scroll, text="OpenRouter.ai dan API kalit oling va pastga kiriting.",
                     font=("Segoe UI", 11), text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 10))
        
        # Existing keys
        self.keys_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=8)
        self.keys_frame.pack(fill=tk.X, pady=(0, 5))
        self._refresh_key_list()
        
        # Add new key
        add_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        add_frame.pack(fill=tk.X, pady=(5, 15))
        
        self.new_key_entry = ctk.CTkEntry(
            add_frame, placeholder_text="sk-or-v1-...",
            font=("Consolas", 12), fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"], border_color=COLORS["border"],
            border_width=1, height=38
        )
        self.new_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        ctk.CTkButton(
            add_frame, text="+ Qo'shish", width=100, height=38,
            font=("Segoe UI", 12, "bold"), fg_color=COLORS["accent"],
            text_color="#000", hover_color=COLORS["accent_hover"],
            command=self._add_key
        ).pack(side=tk.RIGHT)
        
        # --- SEPARATOR ---
        ctk.CTkFrame(scroll, height=1, fg_color=COLORS["border"]).pack(fill=tk.X, pady=15)
        
        # --- MODEL ASSIGNMENTS ---
        ctk.CTkLabel(scroll, text="MODEL SOZLAMALARI", font=("Segoe UI", 16, "bold"),
                     text_color=COLORS["accent"]).pack(anchor="w", pady=(0, 5))
        
        ctk.CTkLabel(scroll, text="Har bir kategoriya uchun qaysi modelni ishlatishni tanlang.",
                     font=("Segoe UI", 11), text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 10))
        
        available_models = [
            "openrouter/free",
            "google/gemini-2.0-flash-lite-preview-02-05:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "deepseek/deepseek-chat-v3-0324:free",
            "qwen/qwen3-8b:free",
        ]
        
        self.model_vars = {}
        self.key_idx_vars = {}
        
        for cat_id, cat_info in MODEL_CATEGORIES.items():
            cat_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=8)
            cat_frame.pack(fill=tk.X, pady=4)
            
            ctk.CTkLabel(cat_frame, text=cat_info["name"],
                        font=("Segoe UI", 13, "bold"),
                        text_color=COLORS["text_primary"]).pack(anchor="w", padx=12, pady=(8, 2))
            
            ctk.CTkLabel(cat_frame, text=cat_info["description"],
                        font=("Segoe UI", 10), text_color=COLORS["text_muted"]).pack(anchor="w", padx=12, pady=(0, 5))
            
            current_model = self.config.get_model_for_category(cat_id)
            model_var = ctk.StringVar(value=current_model)
            self.model_vars[cat_id] = model_var
            
            ctk.CTkOptionMenu(
                cat_frame, variable=model_var, values=available_models,
                font=("Consolas", 11), fg_color=COLORS["bg_tertiary"],
                button_color=COLORS["accent_dim"], button_hover_color=COLORS["accent"],
                dropdown_fg_color=COLORS["bg_secondary"],
                width=400
            ).pack(padx=12, pady=(0, 10), fill=tk.X)
        
        # --- SEPARATOR ---
        ctk.CTkFrame(scroll, height=1, fg_color=COLORS["border"]).pack(fill=tk.X, pady=15)
        
        # --- SAVE ---
        ctk.CTkButton(
            scroll, text="SAQLASH", height=42,
            font=("Segoe UI", 14, "bold"), fg_color=COLORS["success"],
            text_color="#000", hover_color="#00cc66",
            command=self._save_all
        ).pack(fill=tk.X, pady=10)
    
    def _refresh_key_list(self):
        """API kalitlar ro'yxatini yangilash."""
        for widget in self.keys_frame.winfo_children():
            widget.destroy()
        
        keys = self.config.get_api_keys()
        if not keys:
            ctk.CTkLabel(self.keys_frame, text="Hech qanday API kalit kiritilmagan",
                        font=("Segoe UI", 11), text_color=COLORS["text_muted"]).pack(pady=15)
            return
        
        for i, key in enumerate(keys):
            row = ctk.CTkFrame(self.keys_frame, fg_color="transparent")
            row.pack(fill=tk.X, padx=8, pady=3)
            
            masked = key[:8] + "..." + key[-4:] if len(key) > 14 else key
            ctk.CTkLabel(row, text=f"Kalit #{i+1}: {masked}",
                        font=("Consolas", 11), text_color=COLORS["text_primary"]).pack(side=tk.LEFT)
            
            ctk.CTkButton(
                row, text="X", width=30, height=26,
                font=("Segoe UI", 11, "bold"), fg_color=COLORS["error"],
                text_color="#fff", hover_color="#cc0033",
                command=lambda idx=i: self._remove_key(idx)
            ).pack(side=tk.RIGHT)
    
    def _add_key(self):
        key = self.new_key_entry.get().strip()
        if key:
            self.config.add_api_key(key)
            self.new_key_entry.delete(0, tk.END)
            self._refresh_key_list()
    
    def _remove_key(self, idx):
        self.config.remove_api_key(idx)
        self._refresh_key_list()
    
    def _save_all(self):
        keys = self.config.get_api_keys()
        for cat_id, var in self.model_vars.items():
            self.config.set_model_for_category(cat_id, var.get(), api_key_index=0)
        self.config.save()
        self._on_close()
    
    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


# ===================================================================
# MAIN CHAT UI
# ===================================================================
class JarvisUI:
    """Asosiy Jarvis interfeysi - Chat, Status, Overlay."""
    
    def __init__(self, engine):
        self.engine = engine
        
        self.root = ctk.CTk()
        self.root.title("JARVIS AI")
        self.root.geometry("500x700")
        self.root.configure(fg_color=COLORS["bg_primary"])
        self.root.attributes("-alpha", 0.96)
        self.root.minsize(420, 550)
        
        # Icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        self.is_minimized = False
        self.overlay_win = None
        self.status = "idle"
        self.settings_open = False
        
        self._build_ui()
    
    def _build_ui(self):
        """Asosiy oynani qurish."""
        
        # === HEADER ===
        header = ctk.CTkFrame(self.root, height=55, fg_color=COLORS["bg_secondary"], corner_radius=0)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Title (Without Emoji)
        title_lbl = ctk.CTkLabel(header, text="[ JARVIS SYSTEM ]", text_color="#00d4ff", font=("Consolas", 18, "bold"))
        title_lbl.pack(side=tk.LEFT, padx=15, pady=15)
        
        # Subtitle
        self.model_indicator = ctk.CTkLabel(
            header, text="v3.0 Neural Core",
            font=("Segoe UI", 10), text_color=COLORS["text_muted"]
        )
        self.model_indicator.pack(side=tk.LEFT, padx=5, pady=(4, 0))
        
        # Header buttons
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side=tk.RIGHT, padx=10)
        
        ctk.CTkButton(
            btn_frame, text="SOZLAMALAR", width=100, height=32,
            font=("Consolas", 11, "bold"), fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"], hover_color=COLORS["accent_dim"],
            border_width=1, border_color=COLORS["border"],
            command=self._open_settings
        ).pack(side=tk.LEFT, padx=5)
        
        ctk.CTkButton(
            btn_frame, text="[ MINI ]", width=70, height=32,
            font=("Consolas", 11, "bold"), fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["accent"], hover_color=COLORS["accent_dim"],
            border_width=1, border_color=COLORS["border"],
            command=self.minimize_to_overlay
        ).pack(side=tk.LEFT, padx=5)
        
        # === STATUS BAR ===
        self.status_bar = ctk.CTkFrame(self.root, height=30, fg_color=COLORS["bg_primary"], corner_radius=0)
        self.status_bar.pack(fill=tk.X)
        self.status_bar.pack_propagate(False)
        
        self.status_dot = ctk.CTkLabel(
            self.status_bar, text=">>",
            font=("Consolas", 14, "bold"), text_color=COLORS["text_muted"]
        )
        self.status_dot.pack(side=tk.LEFT, padx=(15, 5))
        
        self.status_label = ctk.CTkLabel(
            self.status_bar, text="KUTISH",
            font=("Consolas", 10, "bold"), text_color=COLORS["text_muted"]
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.category_label = ctk.CTkLabel(
            self.status_bar, text="",
            font=("Segoe UI", 9), text_color=COLORS["text_muted"]
        )
        self.category_label.pack(side=tk.RIGHT, padx=15)
        
        # === CHAT LOG ===
        self.chat_frame = ctk.CTkFrame(self.root, fg_color=COLORS["bg_primary"], corner_radius=0)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)
        
        self.chat_log = ctk.CTkTextbox(
            self.chat_frame,
            fg_color=COLORS["bg_secondary"],
            text_color=COLORS["text_primary"],
            font=("Segoe UI", 12),
            wrap=tk.WORD,
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.chat_log.pack(fill=tk.BOTH, expand=True)
        self.chat_log.configure(state="disabled")
        
        # === INPUT AREA ===
        input_frame = ctk.CTkFrame(self.root, height=50, fg_color=COLORS["bg_primary"], corner_radius=0)
        input_frame.pack(fill=tk.X, padx=12, pady=(5, 12))
        
        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Jarvis bilan gaplashing...",
            font=("Segoe UI", 13),
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=42
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.input_entry.bind("<Return>", self._on_send)
        
        self.send_btn = ctk.CTkButton(
            input_frame, text=">>>", width=60, height=42,
            font=("Consolas", 14, "bold"),
            fg_color=COLORS["accent"], text_color="#000",
            hover_color=COLORS["accent_hover"],
            corner_radius=8,
            command=self._on_send
        )
        self.send_btn.pack(side=tk.RIGHT)
        
        # Welcome message
        self._add_msg("Jarvis tayyor. Sozlamalar panelidan API kalit kiriting va boshlang.", "system")
    
    def _on_send(self, event=None):
        """Foydalanuvchi xabarini jo'natish."""
        cmd = self.input_entry.get().strip()
        if cmd:
            self.input_entry.delete(0, tk.END)
            self.engine.command_queue.put(cmd)
    
    def _open_settings(self):
        """Sozlamalar oynasini ochish."""
        if not self.settings_open:
            self.settings_open = True
            SettingsPanel(
                self.root,
                self.engine.config,
                on_close_callback=self._on_settings_close
            )
    
    def _on_settings_close(self):
        self.settings_open = False
    
    # === OVERLAY ===
    def minimize_to_overlay(self):
        self.root.withdraw()
        self._create_overlay()
        self.is_minimized = True
    
    def _create_overlay(self):
        size = 68
        self.overlay_win = tk.Toplevel(self.root)
        self.overlay_win.overrideredirect(True)
        self.overlay_win.attributes("-topmost", True)
        self.overlay_win.attributes("-alpha", 0.92)
        self.overlay_win.configure(bg="black")
        try:
            self.overlay_win.attributes("-transparentcolor", "black")
        except:
            pass
        
        scr_w = self.overlay_win.winfo_screenwidth()
        self.overlay_win.geometry(f"{size}x{size}+{scr_w - size - 25}+25")
        
        self.ov_canvas = Canvas(self.overlay_win, width=size, height=size, bg="black", highlightthickness=0)
        self.ov_canvas.pack()
        
        st_color = STATUS_MAP.get(self.status, STATUS_MAP["idle"])["color"]
        self.ov_ring = self.ov_canvas.create_oval(3, 3, size-3, size-3, fill=COLORS["bg_primary"], outline=st_color, width=3)
        self.ov_canvas.create_text(size//2, size//2, text="J", fill=COLORS["accent"], font=("Segoe UI", 22, "bold"))
        
        self._ov_dx, self._ov_dy = 0, 0
        self.ov_canvas.bind("<Button-1>", lambda e: setattr(self, '_ov_dx', e.x) or setattr(self, '_ov_dy', e.y))
        self.ov_canvas.bind("<B1-Motion>", self._ov_drag)
        self.ov_canvas.bind("<Double-Button-1>", self._restore)
    
    def _ov_drag(self, e):
        x = self.overlay_win.winfo_x() + (e.x - self._ov_dx)
        y = self.overlay_win.winfo_y() + (e.y - self._ov_dy)
        self.overlay_win.geometry(f"+{x}+{y}")
    
    def _restore(self, e=None):
        if self.overlay_win:
            self.overlay_win.destroy()
            self.overlay_win = None
        self.root.deiconify()
        self.is_minimized = False
    
    # === STATUS UPDATE ===
    def set_status(self, status: str):
        self.status = status
        info = STATUS_MAP.get(status, STATUS_MAP["idle"])
        try:
            self.root.after(0, lambda: self.status_dot.configure(text_color=info["color"]))
            self.root.after(0, lambda: self.status_label.configure(text=info["text"], text_color=info["color"]))
            if self.is_minimized and self.overlay_win:
                self.ov_canvas.itemconfig(self.ov_ring, outline=info["color"])
        except:
            pass
    
    def set_category(self, category: str):
        info = MODEL_CATEGORIES.get(category, {})
        name = info.get("name", "")
        try:
            self.root.after(0, lambda: self.category_label.configure(text=name))
        except:
            pass
    
    # === CHAT LOG ===
    def _add_msg(self, text: str, role: str):
        """Xabarni chat log ga qo'shish (thread-safe)."""
        def _insert():
            self.chat_log.configure(state="normal")
            
            if role == "user":
                prefix = "SIZ"
                color = COLORS["user_msg"]
            elif role == "jarvis":
                prefix = "JARVIS"
                color = COLORS["jarvis_msg"]
            else:
                prefix = "TIZIM"
                color = COLORS["system_msg"]
            
            self.chat_log.insert(tk.END, f"[{prefix}] {text}\n\n")
            self.chat_log.configure(state="disabled")
            self.chat_log.see(tk.END)
        
        try:
            self.root.after(0, _insert)
        except:
            pass
    
    def add_msg(self, text: str, role: str):
        self._add_msg(text, role)
    
    def run(self):
        self.root.after(500, self.engine.start)
        self.root.mainloop()


# ===================================================================
# JARVIS ENGINE - Core Logic
# ===================================================================
class JarvisEngine:
    """
    Jarvis yadrolasi - barcha komponentlarni birlashtirib,
    0-delay multithread logika bilan boshqaradi.
    """
    
    def __init__(self):
        self.config = ConfigManager()
        self.brain = Brain(self.config)
        self.voice = Voice(self.config)
        self.actions = ActionHandler()
        self.ui = JarvisUI(self)
        
        self.running = True
        self.active_mode = False
        self.command_queue = queue.Queue()
    
    def start(self):
        """Asosiy mantiq threadlarini ishga tushirish."""
        self.ui.add_msg("Ovoz tizimi yoqilmoqda...", "system")
        
        # FastAPI
        try:
            from server import run_server
            run_server(self, host="127.0.0.1", port=8765)
            self.ui.add_msg("API Server faol (Port: 8765)", "system")
        except Exception as e:
            self.ui.add_msg(f"API Server xatosi: {e}", "system")
            
        # Listener thread
        t1 = threading.Thread(target=self._listen_loop, daemon=True)
        # Processor thread
        t2 = threading.Thread(target=self._process_loop, daemon=True)
        
        t1.start()
        t2.start()
        
        # API kalit borligini tekshirish
        keys = self.config.get_api_keys()
        if keys:
            self.ui.add_msg(f"{len(keys)} ta API kalit topildi. Jarvis tayyor.", "system")
        else:
            self.ui.add_msg("API kalit topilmadi. Sozlamalar -> API kalit kiriting.", "system")
    
    def _listen_loop(self):
        """Doimiy tinglash sikli."""
        while self.running:
            try:
                if not self.active_mode:
                    self.ui.set_status("idle")
                    if self.voice.detect_wake():
                        self.active_mode = True
                        self.ui.set_status("listening")
                        self.voice.speak("Tinglayapman", emotion="excited")
                        self.ui.add_msg("Jarvis faollashdi - gapiring.", "system")
                    continue
                
                self.ui.set_status("listening")
                cmd = self.voice.listen(timeout=5, phrase_limit=6)
                
                if cmd:
                    # Kutish buyruqlari
                    cmd_lower = cmd.lower()
                    if any(w in cmd_lower for w in ["uxla", "sleep", "tinch", "jim"]):
                        self.active_mode = False
                        self.voice.speak("Jim rejim.", emotion="calm")
                        self.ui.add_msg("Kutish rejimiga qaytdi.", "system")
                    else:
                        self.command_queue.put(cmd)
            except Exception as e:
                logger.error(f"Listen loop: {e}")
                time.sleep(1)
    
    def _process_loop(self):
        """Buyruqlarni qayta ishlash sikli."""
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            
            try:
                self.ui.add_msg(cmd, "user")
                
                # 1. Lokal harakatlar tekshiruvi
                local_result = self.actions.handle(cmd)
                if local_result:
                    self.ui.set_status("action")
                    self.voice.speak(local_result, emotion="excited")
                    self.ui.add_msg(local_result, "jarvis")
                    continue
                
                # 2. AI Brain
                self.ui.set_status("thinking")
                result = self.brain.think(cmd)
                
                answer = result["answer"]
                category = result["category"]
                status = result["status"]
                model = result["model"]
                
                # Kategoriyani ko'rsatish
                self.ui.set_category(category)
                
                # Javobni ko'rsatish
                self.ui.add_msg(answer, "jarvis")
                
                # Gapirish
                self.ui.set_status("speaking")
                emotion = "normal"
                if status in ["no_key", "auth_error", "no_internet"]:
                    emotion = "sad"
                elif "!" in answer:
                    emotion = "excited"
                
                self.voice.speak(answer, emotion=emotion, blocking=True)
                
            except Exception as e:
                logger.error(f"Process loop: {e}")
                self.ui.add_msg(f"Ichki xato: {e}", "system")


# ===================================================================
# ENTRY POINT
# ===================================================================
if __name__ == "__main__":
    app = JarvisEngine()
    app.ui.run()
