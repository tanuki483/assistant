import os
import time
import threading
import subprocess
import json

class TTSManager:
    def __init__(self, config_path, default_speak_dir, on_speak_callback, on_speak_done_callback=None):
        self.config_path = config_path
        self.load_config()
        self.speak_dir = self.config.get("speak_dir", default_speak_dir)
        self.config["speak_dir"] = self.speak_dir
        self.save_config()
        self.on_speak_callback = on_speak_callback
        self.on_speak_done_callback = on_speak_done_callback
        self.running = False
        self.thread = None
        self._ensure_dir()
        self.processed_files = set()

    def _ensure_dir(self):
        if self.speak_dir and not os.path.exists(self.speak_dir):
            try:
                os.makedirs(self.speak_dir)
            except Exception:
                pass

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "speech_speed": 0, # -10 to 10
                "max_speech_length": 100,
                "speech_volume": 100,
                "bubble_max_height": 100,
                "tts_enabled": True
            }
            self.save_config()

    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def _ensure_ps_proc(self):
        if not hasattr(self, 'ps_proc') or self.ps_proc is None or self.ps_proc.poll() is not None:
            self.ps_proc = subprocess.Popen(
                ["powershell", "-Command", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.ps_proc.stdin.write("Add-Type -AssemblyName System.speech\n")
            self.ps_proc.stdin.write("$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer\n")
            self.ps_proc.stdin.flush()

    def speak(self, text):
        if not self.config.get("tts_enabled", True):
            return
            
        max_len = self.config.get("max_speech_length", 100)
        if len(text) > max_len:
            text = text[:max_len] + "..."
            
        # Call the callback to display text in UI bubble
        if self.on_speak_callback:
            self.on_speak_callback(text)

        speed = self.config.get("speech_speed", 0)
        vol = self.config.get("speech_volume", 100)
        
        # Escape single quotes and newlines for PowerShell
        safe_text = text.replace("'", "''").replace("\n", " ").replace("\r", "")
        
        self._ensure_ps_proc()
        
        try:
            self.ps_proc.stdin.write(f"$speak.Rate = {speed}; $speak.Volume = {vol}; $speak.Speak('{safe_text}')\n")
            self.ps_proc.stdin.write("Write-Output 'DONE'\n")
            self.ps_proc.stdin.flush()
            
            while True:
                line = self.ps_proc.stdout.readline()
                if not line or line.strip() == 'DONE':
                    break
        except Exception:
            self.ps_proc = None
        
        if self.on_speak_done_callback:
            self.on_speak_done_callback()

    def abort_speech(self):
        if hasattr(self, 'ps_proc') and self.ps_proc:
            try:
                self.ps_proc.terminate()
            except Exception:
                pass
            self.ps_proc = None

    def _poll(self):
        while self.running:
            try:
                files = [f for f in os.listdir(self.speak_dir) if f.endswith('.txt')]
                for f in files:
                    if f not in self.processed_files:
                        file_path = os.path.join(self.speak_dir, f)
                        
                        try:
                            # ファイルが生成中・書き込み中である可能性を考慮して待機
                            # 1. 最後に更新されてから1.5秒経過しているか確認
                            mtime = os.path.getmtime(file_path)
                            if time.time() - mtime < 1.5:
                                continue
                            
                            # 2. ファイルがロックされていないか確認
                            os.rename(file_path, file_path)
                        except Exception:
                            # アクセス拒否やロック中の場合は次回のループに持ち越す
                            continue
                            
                        self.processed_files.add(f)
                        try:
                            with open(file_path, 'rb') as file:
                                raw_data = file.read()
                            
                            text = ""
                            for enc in ['utf-8-sig', 'utf-8', 'cp932', 'shift_jis', 'utf-16', 'euc_jp']:
                                try:
                                    text = raw_data.decode(enc).strip()
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if text:
                                self.speak(text)
                                
                            try:
                                os.remove(file_path)
                                self.processed_files.discard(f)
                            except Exception as rm_err:
                                print(f"Error deleting {file_path}: {rm_err}")
                                
                        except Exception as read_err:
                            print(f"Error reading {file_path}: {read_err}")
                        
            except Exception as e:
                print(f"Polling error: {e}")
                
            time.sleep(2)

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._poll, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
