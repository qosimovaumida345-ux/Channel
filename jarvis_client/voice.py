import os
import asyncio
import threading
import logging
import time
import speech_recognition as sr
import edge_tts
import pygame

logger = logging.getLogger("JARVIS.Voice")

class Voice:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Optimize for 0-delay listening
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.4 # Very quick pause detection (10ms-like feel)
        self.recognizer.non_speaking_duration = 0.3
        
        self.WAKE_WORDS = ["jarvis", "djarvis", "yarvis", "jervis"]
        
        # Super natural TTS setup (Sardor - Uzbek Male Voice for Grok/Jarvis feel)
        self.VOICE_NAME = "uz-UZ-SardorNeural"
        
        # Init audio playback
        pygame.mixer.init()
        self._tts_lock = threading.Lock()

    def speak(self, text: str, emotion: str = "normal"):
        """
        Non-blocking exactly 0-delay feel TTS using edge-tts.
        Runs in a separate thread so the main brain/UI doesn't freeze.
        """
        def _speak_task():
            with self._tts_lock:
                try:
                    # Generate TTS
                    filename = f"out_{int(time.time()*100)}.mp3"
                    
                    # Pitch/Rate adjustments for emotion
                    rate = "+0%"
                    pitch = "+0Hz"
                    if emotion == "excited":
                        rate = "+15%"
                        pitch = "+10Hz"
                    elif emotion == "sad":
                        rate = "-10%"
                        pitch = "-10Hz"
                    elif emotion == "calm":
                        rate = "-5%"
                        
                    async def _gen():
                        communicate = edge_tts.Communicate(text, self.VOICE_NAME, rate=rate, pitch=pitch)
                        await communicate.save(filename)
                        
                    asyncio.run(_gen())
                    
                    # Play the generated audio
                    pygame.mixer.music.load(filename)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.01)
                        
                    pygame.mixer.music.unload()
                    os.remove(filename)
                except Exception as e:
                    logger.error(f"TTS Xatosi: {e}")

        t = threading.Thread(target=_speak_task, daemon=True)
        t.start()

    def listen(self, timeout: int = 5, phrase_limit: int = 5) -> str:
        """
        Zero-delay listener optimized for Uzbek.
        """
        try:
            with sr.Microphone() as mic:
                audio = self.recognizer.listen(mic, timeout=timeout, phrase_time_limit=phrase_limit)
                # Google STT configured strictly for Uzbek
                text = self.recognizer.recognize_google(audio, language="uz-UZ")
                return text.lower().strip()
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            return None

    def detect_wake(self) -> bool:
        """
        Listens constantly for the wake word in the background.
        """
        text = self.listen(timeout=2, phrase_limit=2)
        if text:
            # Check for any soundalikes
            if any(w in text for w in self.WAKE_WORDS):
                return True
        return False
