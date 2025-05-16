# market_research/voice.py
import os
import uuid
import logging
import tempfile
from typing import Optional, Dict, Any

import speech_recognition as sr
from gtts import gTTS

logger = logging.getLogger(__name__)

try:
    # Optional imports for enhanced capabilities
    import pygame
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("pygame or pydub not available. Using simpler audio playback.")

class VoiceProcessor:
    """Handles speech-to-text and text-to-speech functionality"""
    
    def __init__(self, config):
        """
        Initialize voice processor
        
        Args:
            config: AppConfig object containing voice settings
        """
        self.config = config
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300  # Adjust sensitivity
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # Time of silence to consider the end of a phrase
        
        # Initialize audio playback if pygame is available
        if PYGAME_AVAILABLE:
            pygame.mixer.init()
    
    def listen(self, timeout: int = 5, phrase_time_limit: int = 15) -> Optional[str]:
        """
        Record audio from microphone and convert to text
        
        Args:
            timeout: Maximum time to wait for speech to start
            phrase_time_limit: Maximum time to allow for a single phrase
            
        Returns:
            Recognized text or None if recognition failed
        """
        try:
            with sr.Microphone() as source:
                logger.info("Listening for speech input...")
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Record audio
                try:
                    audio = self.recognizer.listen(
                        source, 
                        timeout=timeout, 
                        phrase_time_limit=phrase_time_limit
                    )
                except sr.WaitTimeoutError:
                    logger.info("No speech detected within timeout period")
                    return None
                
                logger.info("Audio captured, transcribing...")
                
                # Attempt speech recognition
                if self.config.stt_provider == "google":
                    text = self.recognizer.recognize_google(audio)
                elif self.config.stt_provider == "whisper":
                    try:
                        from openai import OpenAI
                        client = OpenAI(api_key=self.config.openai_api_key)
                        
                        # Save audio to temporary file
                        temp_dir = tempfile.gettempdir()
                        temp_file = os.path.join(temp_dir, f"speech_{uuid.uuid4()}.wav")
                        
                        with open(temp_file, "wb") as f:
                            f.write(audio.get_wav_data())
                        
                        # Transcribe with Whisper
                        with open(temp_file, "rb") as f:
                            transcription = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=f
                            )
                        
                        # Clean up temp file
                        os.remove(temp_file)
                        
                        text = transcription.text
                    except ImportError:
                        logger.warning("OpenAI package not installed. Falling back to Google STT.")
                        text = self.recognizer.recognize_google(audio)
                    except Exception as e:
                        logger.error(f"Error with Whisper transcription: {str(e)}")
                        text = self.recognizer.recognize_google(audio)
                else:
                    # Default to Google if no valid provider specified
                    text = self.recognizer.recognize_google(audio)
                
                logger.info(f"Transcription result: {text}")
                return text
                
        except sr.UnknownValueError:
            logger.warning("Speech recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from speech recognition service: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}")
            return None
    
    def speak(self, text: str) -> bool:
        """
        Convert text to speech and play it
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Success flag
        """
        if not text:
            logger.warning("Empty text provided to speech synthesis")
            return False
            
        try:
            # Create temp file for audio
            temp_dir = tempfile.gettempdir()
            audio_file = os.path.join(temp_dir, f"tts_{uuid.uuid4()}.mp3")
            
            if self.config.tts_provider == "elevenlabs" and self.config.elevenlabs_api_key:
                try:
                    from elevenlabs import generate, save
                    
                    # Generate audio with ElevenLabs
                    audio = generate(
                        text=text,
                        voice="Daniel",  # Default voice, could be configurable
                        model="eleven_monolingual_v1",
                        api_key=self.config.elevenlabs_api_key
                    )
                    
                    # Save audio to temp file
                    save(audio, audio_file)
                    logger.info(f"Generated speech with ElevenLabs: {len(text)} chars")
                    
                except ImportError:
                    logger.warning("ElevenLabs package not installed. Falling back to gTTS.")
                    self._generate_with_gtts(text, audio_file)
                except Exception as e:
                    logger.error(f"Error with ElevenLabs synthesis: {str(e)}")
                    self._generate_with_gtts(text, audio_file)
            else:
                # Fallback to gTTS
                self._generate_with_gtts(text, audio_file)
                
            # Play the audio
            self._play_audio(audio_file)
            
            # Clean up temp file
            try:
                os.remove(audio_file)
            except:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return False
    
    def _generate_with_gtts(self, text: str, output_file: str) -> None:
        """Generate speech using Google Text-to-Speech"""
        try:
            # For very long text, we need to chunk it to avoid gTTS limits
            if len(text) > 500:
                # Split by sentences or paragraphs
                chunks = []
                current_chunk = ""
                
                # Split by sentences (simple approach)
                sentences = text.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < 500:
                        current_chunk += sentence + " "
                    else:
                        chunks.append(current_chunk)
                        current_chunk = sentence + " "
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Generate speech for each chunk and concatenate
                temp_files = []
                for i, chunk in enumerate(chunks):
                    temp_file = output_file + f".part{i}.mp3"
                    tts = gTTS(text=chunk, lang='en', slow=False)
                    tts.save(temp_file)
                    temp_files.append(temp_file)
                
                # Concatenate audio files if pydub is available
                if PYGAME_AVAILABLE:
                    combined = AudioSegment.empty()
                    for temp_file in temp_files:
                        segment = AudioSegment.from_mp3(temp_file)
                        combined += segment
                    combined.export(output_file, format="mp3")
                    
                    # Clean up temp files
                    for temp_file in temp_files:
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                else:
                    # If pydub not available, just use the first chunk
                    if temp_files:
                        os.replace(temp_files[0], output_file)
            else:
                # For shorter text, just use gTTS directly
                tts = gTTS(text=text, lang='en', slow=False)
                tts.save(output_file)
                
            logger.info(f"Generated speech with gTTS: {len(text)} chars")
                
        except Exception as e:
            logger.error(f"Error generating speech with gTTS: {e}")
            raise
    
    def _play_audio(self, audio_file: str) -> None:
        """Play audio file using the best available method"""
        if not os.path.exists(audio_file):
            logger.error(f"Audio file not found: {audio_file}")
            return
            
        try:
            if PYGAME_AVAILABLE:
                # Use pygame for better audio playback
                try:
                    pygame.mixer.music.load(audio_file)
                    pygame.mixer.music.play()
                    # Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                except Exception as e:
                    logger.error(f"Error playing audio with pygame: {e}")
                    # Fallback to pydub
                    try:
                        sound = AudioSegment.from_mp3(audio_file)
                        pydub_play(sound)
                    except Exception as e2:
                        logger.error(f"Error playing audio with pydub: {e2}")
            else:
                # Use platform-specific commands as fallback
                import platform
                system = platform.system()
                
                if system == 'Darwin':  # macOS
                    os.system(f"afplay {audio_file}")
                elif system == 'Linux':
                    os.system(f"mpg123 {audio_file}")
                elif system == 'Windows':
                    os.system(f"start {audio_file}")
                else:
                    logger.warning(f"Unsupported platform for audio playback: {system}")
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
