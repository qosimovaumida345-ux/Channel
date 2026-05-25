"""
JARVIS AI - ASGI Backend Server (FastAPI)
=========================================
Jarvis uchun mahalliy REST API server. 
Telefon ilovasi yoki boshqa devayslar LAN (Wi-Fi) orqali
Ushbu kompyuterdagi ASOSIY Jarvis aqli bilan bevosita ulanib ishlay olishi uchun yaratildi.

Xususiyatlar:
- GET /status - Jarvisning joriy holati
- POST /chat - Masofaviy matnli so'rov yuborish
- POST /command - Masofadan turib command (macro) yuborish
"""

import logging
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import threading

logger = logging.getLogger("JARVIS.FastAPI")

app = FastAPI(title="Jarvis AI Local API", version="2.0")

# CORS ruxtasnomalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Reference to the running engine (injected from main.py)
jarvis_engine_ref = None

class ChatRequest(BaseModel):
    message: str
    client_id: str = "mobile_app"

class CommandRequest(BaseModel):
    command: str

@app.get("/")
def read_root():
    return {"status": "Jarvis API is running."}

@app.get("/status")
def get_status():
    if not jarvis_engine_ref:
        return {"status": "backend_offline", "listening": False}
    return {
        "status": jarvis_engine_ref.ui.status if hasattr(jarvis_engine_ref, 'ui') else "unknown",
        "listening": jarvis_engine_ref.active_mode
    }

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not jarvis_engine_ref:
        raise HTTPException(status_code=503, detail="Jarvis is not initialized")
    
    # Push into the queue exactly like voice
    jarvis_engine_ref.command_queue.put(req.message)
    return {"status": "Message queued", "message": req.message}

@app.post("/command")
def execute_command(req: CommandRequest):
    if not jarvis_engine_ref:
        raise HTTPException(status_code=503, detail="Jarvis is not initialized")
    
    # Try local actions immediately via API
    res = jarvis_engine_ref.actions.handle(req.command)
    if res:
        return {"local_action": True, "result": res}
    else:
        # Pass to brain queue
        jarvis_engine_ref.command_queue.put(req.command)
        return {"local_action": False, "queued": True}

def run_server(engine_reference, host="0.0.0.0", port=8765):
    """Starts the FastAPI Uvicorn server in a separate thread."""
    global jarvis_engine_ref
    jarvis_engine_ref = engine_reference
    
    def _run():
        logger.info(f"FastAPI Server ishga tushirilyapti... (http://{host}:{port})")
        uvicorn.run(app, host=host, port=port, log_level="error")
        
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
