import pyttsx3
import speech_recognition as sr
import threading
import logging

logger = logging.getLogger("JARVIS.Voice")

class Voice:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        self.WAKE_WORDS = ["jarvis", "hey jarvis", "yordam", "tuzat"]
        self._engine_lock = threading.Lock()
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            with self._engine_lock:
                if self._engine is None:
                    engine = pyttsx3.init()
                    for v in engine.getProperty("voices"):
                        if "david" in v.id.lower() or "zira" in v.id.lower():
                            engine.setProperty("voice", v.id)
                            break
                    engine.setProperty("rate", 160) # Natural speaking rate
                    engine.setProperty("volume", 1.0)
                    self._engine = engine
        return self._engine

    def speak(self, text: str, emotion: str = "normal"):
        """
        Speak out loud with simulated emotion by changing speech parameters.
        """
        try:
            engine = self._get_engine()
            
            # Simple emotion modulation
            if emotion == "excited":
                engine.setProperty("rate", 190)
            elif emotion == "sad":
                engine.setProperty("rate", 130)
            elif emotion == "calm":
                engine.setProperty("rate", 150)
            else:
                engine.setProperty("rate", 165)

            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS Xatosi: {e}")
            # Reinit
            with self._engine_lock:
                self._engine = None

    def listen(self, timeout: int = 5, phrase_limit: int = 8) -> str:
        try:
            with sr.Microphone() as mic:
                audio = self.recognizer.listen(mic, timeout=timeout, phrase_time_limit=phrase_limit)
                text = self.recognizer.recognize_google(audio, language="en-US") # or uz-UZ if natively supported by google
                return text.lower().strip()
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            return None

    def detect_wake(self) -> bool:
        text = self.listen(timeout=3, phrase_limit=3)
        if text:
            return any(w in text for w in self.WAKE_WORDS)
        return False
