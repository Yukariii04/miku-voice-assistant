import tkinter as tk
from tkinter import PhotoImage, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageSequence
import threading
import speech_recognition as sr
from gtts import gTTS
import os
import pygame
import tempfile
import google.generativeai as genai
from dotenv import load_dotenv
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class AssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Miku Assistant 🎤")
        self.root.geometry("450x700")
        self.root.configure(bg='#1a1a2e')
        self.root.resizable(True, True)
        
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize OpenAI client: {e}")
            return
        
        try:
            pygame.mixer.init()
        except Exception as e:
            logger.warning(f"Could not initialize pygame mixer: {e}")

        self.is_listening = False
        self.conversation_history = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
    
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        title_label = tk.Label(main_frame, text="🎤 Miku Voice Assistant", 
                              font=("Arial", 18, "bold"), 
                              bg='#1a1a2e', fg='#00d4ff')
        title_label.pack(pady=(0, 10))
        
        self.setup_animation(main_frame)
        
        self.setup_chat_display(main_frame)
        
        self.setup_controls(main_frame)
    
        self.setup_status_bar()
        
    def setup_animation(self, parent):
        """Setup the animated GIF display"""
        animation_frame = tk.Frame(parent, bg='#1a1a2e')
        animation_frame.pack(pady=10)
        
        try:
            self.label = tk.Label(animation_frame, bg='#1a1a2e')
            self.label.pack()
            
            if os.path.exists("assets/miku.gif"):
                self.sequence = [ImageTk.PhotoImage(img) for img in ImageSequence.Iterator(Image.open("assets/miku.gif"))]
                self.animate(0)
            else:
                self.label.configure(text="🎵 Miku 🎵", font=("Arial", 24), 
                                   fg='#00d4ff', bg='#1a1a2e')
                logger.info("GIF not found, using text fallback")
        except Exception as e:
            self.label = tk.Label(animation_frame, text="🎵 Miku 🎵", 
                                font=("Arial", 24), fg='#00d4ff', bg='#1a1a2e')
            self.label.pack()
            logger.warning(f"Could not load animation: {e}")

    def animate(self, counter):
        """Animate the GIF"""
        if hasattr(self, 'sequence') and self.sequence:
            self.label.configure(image=self.sequence[counter])
            self.root.after(100, self.animate, (counter + 1) % len(self.sequence))

    def setup_chat_display(self, parent):
        """Setup the chat display area"""
        chat_frame = tk.Frame(parent, bg='#1a1a2e')
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        chat_label = tk.Label(chat_frame, text="💬 Conversation", 
                             font=("Arial", 12, "bold"), 
                             bg='#1a1a2e', fg='#ffffff')
        chat_label.pack(anchor='w')
        
        self.text_display = scrolledtext.ScrolledText(
            chat_frame, 
            height=15, 
            bg='#2d2d44', 
            fg='#ffffff',
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            insertbackground='#00d4ff'
        )
        self.text_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_controls(self, parent):
        """Setup control buttons"""
        control_frame = tk.Frame(parent, bg='#1a1a2e')
        control_frame.pack(fill=tk.X, pady=10)
        
        self.listen_btn = tk.Button(
            control_frame, 
            text="🎙️ Start Listening",
            command=self.toggle_listening,
            font=("Arial", 14, "bold"), 
            bg="#00d4ff", 
            fg="white",
            activebackground="#0099cc",
            relief=tk.RAISED,
            bd=3,
            pady=10
        )
        self.listen_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        test_btn = tk.Button(
            control_frame,
            text="🔧 Test Mic",
            command=self.test_microphone,
            font=("Arial", 10),
            bg="#2ed573",
            fg="white",
            activebackground="#26c565",
            relief=tk.RAISED,
            bd=2,
            pady=8
        )
        test_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        clear_btn = tk.Button(
            control_frame,
            text="🗑️ Clear",
            command=self.clear_chat,
            font=("Arial", 10),
            bg="#ff4757",
            fg="white",
            activebackground="#cc3a47",
            relief=tk.RAISED,
            bd=2,
            pady=8
        )
        clear_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready to listen...")
        
        status_bar = tk.Label(
            self.root, 
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg='#2d2d44',
            fg='#ffffff',
            font=("Arial", 9)
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def append_to_chat(self, message, is_user=True):
        """Safely append message to chat display"""
        self.text_display.config(state=tk.NORMAL)
        
        if is_user:
            self.text_display.insert(tk.END, f"👤 You: {message}\n", "user")
        else:
            self.text_display.insert(tk.END, f"🎵 Miku: {message}\n", "assistant")
        
        self.text_display.config(state=tk.DISABLED)
        self.text_display.see(tk.END)
        
        self.text_display.tag_config("user", foreground="#00d4ff")
        self.text_display.tag_config("assistant", foreground="#ff6b9d")

    def toggle_listening(self):
        """Toggle listening state"""
        if not self.is_listening:
            self.start_listening()
        else:
            self.stop_listening()

    def start_listening(self):
        """Start voice recognition"""
        self.is_listening = True
        self.listen_btn.configure(text="⏹️ Stop Listening", bg="#ff4757")
        threading.Thread(target=self.handle_voice, daemon=True).start()

    def stop_listening(self):
        """Stop voice recognition"""
        self.is_listening = False
        self.listen_btn.configure(text="🎙️ Start Listening", bg="#00d4ff")
        self.update_status("Stopped listening")

    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(f"{time.strftime('%H:%M:%S')} - {message}")

    def clear_chat(self):
        """Clear the chat display and conversation history"""
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete(1.0, tk.END)
        self.text_display.config(state=tk.DISABLED)
        self.conversation_history = []
        self.update_status("Chat cleared")

    def test_microphone(self):
        """Test microphone availability and permissions"""
        try:
            recognizer = sr.Recognizer()
            mic_list = sr.Microphone.list_microphone_names()
            self.append_to_chat(f"🎤 Available microphones: {len(mic_list)}", is_user=False)
            
            for i, name in enumerate(mic_list[:3]):
                self.append_to_chat(f"  {i}: {name}", is_user=False)
    
            with sr.Microphone() as source:
                self.append_to_chat("🎤 Testing microphone access...", is_user=False)
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.append_to_chat("✅ Microphone access successful!", is_user=False)
                
        except Exception as e:
            self.append_to_chat(f"❌ Microphone test failed: {e}", is_user=False)
            self.append_to_chat("💡 Try: Check microphone permissions, restart app as admin, or install PyAudio", is_user=False)

    def handle_voice(self):
        """Handle voice recognition and response"""
        recognizer = sr.Recognizer()
        
        try:
            mic_list = sr.Microphone.list_microphone_names()
            logger.info(f"Available microphones: {mic_list}")
        
            try:
                with sr.Microphone() as source:
                    self.append_to_chat("🎤 Microphone connected successfully", is_user=False)
                    self.update_status("🎧 Adjusting for ambient noise...")
                    
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    self.append_to_chat("🔊 Ambient noise adjustment complete", is_user=False)
                    
                    self.update_status("🎧 Listening... (Speak now!)")
                    self.append_to_chat("🎧 Listening for your voice... Please speak!", is_user=False)
                    self.play_sound_effect("start")
                    
                    recognizer.energy_threshold = 300  
                    recognizer.dynamic_energy_threshold = True
                    recognizer.pause_threshold = 0.8 
                    
                    audio = recognizer.listen(source, timeout=15, phrase_time_limit=8)
                    self.append_to_chat("🎵 Audio captured! Processing...", is_user=False)
                    
            except OSError as e:
                self.append_to_chat(f"❌ Microphone access error: {e}", is_user=False)
                self.append_to_chat("💡 Solutions: Check microphone permissions, ensure mic is not used by other apps", is_user=False)
                return
            except Exception as e:
                self.append_to_chat(f"❌ Microphone setup error: {e}", is_user=False)
                return

            if not self.is_listening:
                return

            self.update_status("🗣️ Processing speech...")
            
            recognition_attempts = [
                ("en-US", "English"),
                ("ja-JP", "Japanese"),
                ("en-GB", "English (UK)"),
                ("es-ES", "Spanish"),
                ("fr-FR", "French"),
                ("de-DE", "German")
            ]
            
            text = None
            used_language = None
            
            for lang_code, lang_name in recognition_attempts:
                try:
                    self.update_status(f"🗣️ Trying {lang_name} recognition...")
                    text = recognizer.recognize_google(audio, language=lang_code)
                    used_language = lang_name
                    break
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    self.append_to_chat(f"❌ Google Speech API error for {lang_name}: {e}", is_user=False)
                    continue
            
            if not text:
                try:
                    self.update_status("🗣️ Trying default recognition...")
                    text = recognizer.recognize_google(audio)
                    used_language = "Auto-detected"
                except:
                    pass
            
            if not text:
                self.append_to_chat("❗ Could not understand audio in any language", is_user=False)
                self.append_to_chat("💡 Try: Speak more clearly, check internet connection, reduce background noise", is_user=False)
                return
            
            logger.info(f"User said ({used_language}): {text}")
            self.append_to_chat(f"[{used_language}] {text}", is_user=True)
            
            self.update_status("🤖 Getting AI response...")
            response = self.get_gpt_response(text)
            
            if response:
                logger.info(f"Miku: {response}")
                self.append_to_chat(response, is_user=False)
            
                self.update_status("🎵 Speaking response...")
                self.speak_response(response)
            
            self.update_status("Ready to listen...")
            
        except sr.WaitTimeoutError:
            self.append_to_chat("❗ Listening timeout - no speech detected within 15 seconds", is_user=False)
            self.append_to_chat("💡 Try: Speak louder, check microphone, reduce timeout", is_user=False)
            self.update_status("Timeout - no speech detected")
        except sr.UnknownValueError:
            self.append_to_chat("❗ Could not understand the audio", is_user=False)
            self.append_to_chat("💡 Try: Speak more clearly, reduce background noise, check internet", is_user=False)
            self.update_status("Could not understand audio")
        except sr.RequestError as e:
            error_msg = f"❗ Speech recognition service error: {e}"
            self.append_to_chat(error_msg, is_user=False)
            self.append_to_chat("💡 Check internet connection and try again", is_user=False)
            self.update_status("Speech recognition service error")
        except Exception as e:
            error_msg = f"❗ Unexpected error: {e}"
            self.append_to_chat(error_msg, is_user=False)
            self.update_status("Unexpected error occurred")
            logger.error(f"Unexpected error in handle_voice: {e}", exc_info=True)
        
        finally:
            self.stop_listening()

    def get_gpt_response(self, prompt):
        """Get response from Gemini"""
        try:
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            history = "\n".join(
                [f"You: {msg['content']}" if msg['role'] == "user" else f"Miku: {msg['content']}"
                 for msg in self.conversation_history]
            )

            prompt_text = f"""You are Miku, a cheerful and helpful voice assistant who loves music and technology.
            Keep your answers conversational and concise.

{history}
You: {prompt}
Miku:"""

            model = genai.GenerativeModel("gemini-1.5-flash")
            chat = model.start_chat(history=[])
            response = chat.send_message(prompt_text)


            reply = response.text.strip()
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
        
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def speak_response(self, text):
        """Convert text to speech and play it"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                temp_filename = tmp_file.name
            
            tts = gTTS(text=text, lang='ja', slow=False)
            tts.save(temp_filename)
            
            if pygame.mixer.get_init():
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
            
            try:
                os.unlink(temp_filename)
            except:
                pass
                
        except Exception as e:
            logger.error(f"TTS error: {e}")
            self.append_to_chat("❗ Could not generate speech", is_user=False)

    def play_sound_effect(self, effect_type):
        """Play sound effects"""
        try:
            sound_files = {
                "start": "assets/voice_start.mp3",
                "end": "assets/voice_end.mp3"
            }
            
            if effect_type in sound_files and os.path.exists(sound_files[effect_type]):
                if pygame.mixer.get_init():
                    sound = pygame.mixer.Sound(sound_files[effect_type])
                    sound.play()
        except Exception as e:
            logger.warning(f"Could not play sound effect: {e}")

    def on_closing(self):
        """Handle application closing"""
        try:
            pygame.mixer.quit()
        except:
            pass
        self.root.destroy()

def main():
    """Main application entry point"""
    if not os.getenv("GEMINI_API_KEY"):
        tk.messagebox.showerror(
            "Error", 
            "Gemini API key not found!\n\nPlease set GEMINI_API_KEY in your .env file"
        )
        return

    
    root = tk.Tk()
    app = AssistantGUI(root)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()

if __name__ == "__main__":
    main()