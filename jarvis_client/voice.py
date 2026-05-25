"""
JARVIS AI - Voice Engine
Edge-TTS neyron ovozi + Google STT orqali 0-delay ovoz tizimi.
"""

import os
import asyncio
import threading
import logging
import time
import speech_recognition as sr
import edge_tts
import pygame

from config import ConfigManager

logger = logging.getLogger("JARVIS.Voice")


class Voice:
    """Jarvis ovoz tizimi - tinglash va gapirish."""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        
        # STT sozlamalari (tezkor aniqlash uchun optimizatsiya)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.5
        self.recognizer.non_speaking_duration = 0.3
        
        # Wake words
        self.WAKE_WORDS = ["jarvis", "djarvis", "yarvis", "jervis", "jarwis"]
        
        # TTS ovoz nomi (config dan)
        voice_settings = self.config.get_voice_settings()
        self.voice_name = voice_settings.get("voice_name", "uz-UZ-SardorNeural")
        self.language = voice_settings.get("language", "uz-UZ")
        
        # Pygame audio init
        try:
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
        except:
            try:
                pygame.mixer.init()
            except Exception as e:
                logger.error(f"Audio tizim ishga tushmadi: {e}")
        
        self._tts_lock = threading.Lock()
        self._speaking = False
    
    @property
    def is_speaking(self) -> bool:
        return self._speaking
    
    def speak(self, text: str, emotion: str = "normal", blocking: bool = False):
        """
        Edge-TTS orqali tabiiy ovozda gapirish.
        blocking=True bo'lsa, gapirish tugaguncha kutadi.
        blocking=False bo'lsa, alohida threadda ishlaydi.
        """
        if blocking:
            self._speak_internal(text, emotion)
        else:
            t = threading.Thread(target=self._speak_internal, args=(text, emotion), daemon=True)
            t.start()
    
    def _speak_internal(self, text: str, emotion: str):
        """TTS generatsiya va playback."""
        with self._tts_lock:
            self._speaking = True
            try:
                # Tezlik va pitch (emotsiya bo'yicha)
                rate, pitch = "+0%", "+0Hz"
                if emotion == "excited":
                    rate, pitch = "+12%", "+8Hz"
                elif emotion == "sad":
                    rate, pitch = "-8%", "-5Hz"
                elif emotion == "calm":
                    rate, pitch = "-5%", "+0Hz"
                
                # Vaqtinchalik fayl nomi
                tmp_file = os.path.join(os.path.expanduser("~"), f"jarvis_tts_{int(time.time()*1000)}.mp3")
                
                # Edge-TTS generatsiya
                async def _generate():
                    communicate = edge_tts.Communicate(text, self.voice_name, rate=rate, pitch=pitch)
                    await communicate.save(tmp_file)
                
                asyncio.run(_generate())
                
                # Pygame orqali ijro
                if os.path.exists(tmp_file):
                    pygame.mixer.music.load(tmp_file)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.02)
                    
                    pygame.mixer.music.unload()
                    
                    # Tozalash
                    try:
                        os.remove(tmp_file)
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"TTS xatosi: {e}")
            finally:
                self._speaking = False
    
    def listen(self, timeout: int = 5, phrase_limit: int = 6) -> str:
        """
        Mikrofondan tinglash va matnni aniqlash.
        Google STT - O'zbek tili.
        """
        try:
            with sr.Microphone() as mic:
                audio = self.recognizer.listen(
                    mic,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
                text = self.recognizer.recognize_google(audio, language=self.language)
                return text.strip()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.error(f"Google STT xatosi: {e}")
            return None
        except Exception as e:
            logger.error(f"Tinglash xatosi: {e}")
            return None
    
    def detect_wake(self) -> bool:
        """Wake word tekshiruvi."""
        text = self.listen(timeout=2, phrase_limit=2)
        if text:
            text_lower = text.lower()
            return any(w in text_lower for w in self.WAKE_WORDS)
        return False
