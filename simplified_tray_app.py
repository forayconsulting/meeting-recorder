#!/usr/bin/env python3
"""
Simplified Meeting Recorder - System Tray App with basic functionality
"""

import os
import sys
import subprocess
import time
import json
import threading
import datetime
import rumps

# Configuration
CONFIG = {
    "api_key": "",
    "transcript_dir": os.path.expanduser("~/Documents/Transcriptions"),
    "show_visual_indicator": True
}

# Load configuration from file if it exists
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
if os.path.exists(config_path):
    try:
        with open(config_path, 'r') as f:
            loaded_config = json.load(f)
            for key, value in loaded_config.items():
                if key == "transcript_dir" and value.startswith("~"):
                    CONFIG[key] = os.path.expanduser(value)
                else:
                    CONFIG[key] = value
    except Exception as e:
        print(f"Error loading config: {e}")

# Ensure transcript directory exists
os.makedirs(CONFIG["transcript_dir"], exist_ok=True)

class RecorderTrayApp(rumps.App):
    def __init__(self):
        super(RecorderTrayApp, self).__init__(
            "🎙️",
            title="Meeting Recorder",
            icon=None,
            quit_button="Quit"
        )
        
        # Track recording process
        self.recorder_process = None
        self.recording = False
        
        # Menu setup
        self.menu = [
            rumps.MenuItem("Start Recording", callback=self.toggle_recording),
            rumps.MenuItem("Open Transcripts Folder", callback=self.open_transcripts),
            None,  # Separator
            rumps.MenuItem("Audio Device", callback=self.select_audio_device),
            rumps.MenuItem("Settings", callback=self.open_settings)
        ]
    
    def toggle_recording(self, sender):
        if not self.recording:
            # Start recording
            self.start_recording()
            sender.title = "Stop Recording"
            # Change the title instead of the icon
            self.title = "🔴 Recording..."
        else:
            # Stop recording
            self.stop_recording()
            sender.title = "Start Recording"
            # Reset the title
            self.title = "🎙️"
    
    def start_recording(self):
        """Start recording process"""
        self.recording = True
        
        # Launch debug recorder process for troubleshooting
        recorder_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_recorder.py")
        
        # Create recorder_process.py if it doesn't exist
        if not os.path.exists(recorder_script):
            self.create_recorder_process()
        
        # Start the process
        try:
            self.recorder_process = subprocess.Popen(
                [sys.executable, recorder_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            rumps.notification(
                "Meeting Recorder",
                "Recording Started",
                "Recording your meeting. Click the 🔴 icon to stop."
            )
        except Exception as e:
            self.recording = False
            rumps.notification(
                "Meeting Recorder",
                "Error",
                f"Failed to start recording: {str(e)}"
            )
    
    def stop_recording(self):
        """Stop recording process"""
        if self.recorder_process:
            # Display notification
            rumps.notification(
                "Meeting Recorder",
                "Processing Recording",
                "Transcribing audio. This may take a few minutes."
            )
            
            # Signal the process to stop recording, but let it complete transcription
            try:
                print("Sending signal to stop recording...")
                self.recorder_process.stdin.write("\n")
                self.recorder_process.stdin.flush()
                
                # Wait for transcription to complete (up to 2 minutes)
                print("Waiting for transcription to complete...")
                def wait_for_completion():
                    try:
                        # Wait for process to complete naturally
                        self.recorder_process.wait(timeout=120)
                        
                        # Process is done - check if successful
                        latest_files = self.get_latest_transcripts(1)
                        
                        if latest_files:
                            timestamp, filepath = latest_files[0]
                            # Check if it was created recently (within the last 2 minutes)
                            now = datetime.datetime.now()
                            if (now - timestamp).total_seconds() < 150:  # A bit more than 2 min
                                rumps.notification(
                                    "Meeting Recorder",
                                    "Transcription Complete",
                                    f"Transcript saved to: {os.path.basename(filepath)}"
                                )
                                # Open the transcript
                                subprocess.run(["open", filepath])
                        else:
                            rumps.notification(
                                "Meeting Recorder",
                                "Warning",
                                "No recent transcript was found. Transcription may have failed."
                            )
                    except subprocess.TimeoutExpired:
                        # If it's taking too long, terminate
                        print("Timeout waiting for transcription, terminating...")
                        self.recorder_process.terminate()
                        rumps.notification(
                            "Meeting Recorder",
                            "Transcription Timeout",
                            "Transcription took too long and was terminated."
                        )
                
                # Start wait in background thread to not block UI
                threading.Thread(target=wait_for_completion, daemon=True).start()
            except Exception as e:
                print(f"Error stopping recording: {e}")
                # If any error, fall back to terminate
                self.recorder_process.terminate()
                rumps.notification(
                    "Meeting Recorder",
                    "Error",
                    f"Failed to process recording: {str(e)}"
                )
            
            # Set to None - thread will handle the cleanup
            self.recorder_process = None
        
        self.recording = False
    
    def get_latest_transcripts(self, count=5):
        """Get the latest transcripts from the transcript directory"""
        try:
            transcript_files = []
            for filename in os.listdir(CONFIG["transcript_dir"]):
                if filename.endswith(".txt"):
                    filepath = os.path.join(CONFIG["transcript_dir"], filename)
                    mtime = os.path.getmtime(filepath)
                    timestamp = datetime.datetime.fromtimestamp(mtime)
                    transcript_files.append((timestamp, filepath))
            
            # Sort by timestamp, newest first
            transcript_files.sort(reverse=True)
            return transcript_files[:count]
        except Exception as e:
            print(f"Error getting latest transcripts: {e}")
            return []
    
    def open_transcripts(self, _):
        """Open transcripts folder in Finder"""
        subprocess.run(["open", CONFIG["transcript_dir"]])
    
    def select_audio_device(self, _):
        """Select audio input device"""
        # Get script path
        list_devices_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "list_inputs.py")
        
        # Check if script exists
        if not os.path.exists(list_devices_script):
            rumps.notification(
                "Meeting Recorder",
                "Error",
                "Device listing script not found."
            )
            return
        
        # Run the script to get devices
        try:
            result = subprocess.run(
                [sys.executable, list_devices_script],
                capture_output=True,
                text=True
            )
            
            # Process output to get device list
            lines = result.stdout.splitlines()
            devices = []
            current_device = None
            
            for line in lines:
                if line.startswith("Device ID:"):
                    current_device = {}
                    try:
                        current_device["id"] = int(line.split("Device ID:")[1].strip())
                    except:
                        continue
                elif current_device is not None and line.strip().startswith("Name:"):
                    current_device["name"] = line.split("Name:")[1].strip()
                    devices.append(current_device)
            
            # No devices found
            if not devices:
                rumps.notification(
                    "Meeting Recorder",
                    "No Devices Found",
                    "Could not detect any audio input devices."
                )
                return
            
            # Create menu for device selection
            device_window = rumps.Window(
                message="Select the audio input device you want to use:",
                title="Audio Device Selection",
                dimensions=(300, 100)
            )
            
            # Show device selection window
            device_window.default_text = "Select a device below:"
            device_options = []
            
            # Create options list
            for device in devices:
                label = f"{device['name']} (ID: {device['id']})"
                device_options.append(label)
            
            # Add default device option
            device_options.append("Use System Default")
            
            # Show dialog
            device_window.add_buttons(*device_options)
            response = device_window.run()
            
            if response.clicked < len(device_options):
                # User selected a device
                selected_option = response.clicked
                
                if selected_option < len(devices):
                    # Selected specific device
                    selected_device = devices[selected_option]
                    device_id = selected_device["id"]
                    device_name = selected_device["name"]
                    
                    # Gather device info (channels, rate)
                    # Get from PyAudio directly
                    import pyaudio
                    p = pyaudio.PyAudio()
                    device_info = p.get_device_info_by_index(device_id)
                    p.terminate()
                    
                    channels = int(device_info.get("maxInputChannels", 1))
                    sample_rate = int(device_info.get("defaultSampleRate", 44100))
                    
                    # Update config
                    CONFIG["audio"] = {
                        "device_id": device_id,
                        "device_name": device_name,
                        "channels": channels,
                        "sample_rate": sample_rate
                    }
                    
                    self.save_config()
                    
                    rumps.notification(
                        "Meeting Recorder",
                        "Device Changed",
                        f"Now using {device_name} for recording"
                    )
                else:
                    # Selected default device
                    CONFIG["audio"] = {
                        "device_id": None,
                        "device_name": "System Default",
                        "channels": 1,
                        "sample_rate": 44100
                    }
                    
                    self.save_config()
                    
                    rumps.notification(
                        "Meeting Recorder",
                        "Device Changed",
                        "Now using system default microphone"
                    )
        except Exception as e:
            rumps.notification(
                "Meeting Recorder",
                "Error",
                f"Could not select audio device: {str(e)}"
            )
    
    def open_settings(self, _):
        """Open settings dialog"""
        window = rumps.Window(
            message="Enter your OpenAI API Key:",
            title="Meeting Recorder Settings",
            default_text=CONFIG["api_key"],
            ok="Save",
            cancel="Cancel"
        )
        response = window.run()
        if response.clicked:
            CONFIG["api_key"] = response.text.strip()
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(config_path, 'w') as f:
                json.dump(CONFIG, f, indent=4)
        except Exception as e:
            rumps.notification(
                "Meeting Recorder",
                "Error",
                f"Failed to save settings: {str(e)}"
            )
    
    def create_recorder_process(self):
        """Create the recorder process script if it doesn't exist"""
        recorder_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recorder_process.py")
        
        with open(recorder_script, 'w') as f:
            f.write('''#!/usr/bin/env python3
import os
import sys
import time
import datetime
import json
import threading
import tempfile
import pyaudio
import wave
from openai import OpenAI

# Configuration
CONFIG = {
    "api_key": "",
    "transcript_dir": os.path.expanduser("~/Documents/Transcriptions"),
    "audio": {
        "device_id": None,
        "device_name": "System Default",
        "channels": 1,
        "sample_rate": 44100
    }
}

# Load configuration from file
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
if os.path.exists(config_path):
    try:
        with open(config_path, 'r') as f:
            loaded_config = json.load(f)
            for key, value in loaded_config.items():
                if key == "transcript_dir" and value.startswith("~"):
                    CONFIG[key] = os.path.expanduser(value)
                else:
                    CONFIG[key] = value
    except Exception as e:
        print(f"Error loading config: {e}")

# Create the transcript directory if it doesn't exist
os.makedirs(CONFIG["transcript_dir"], exist_ok=True)

def record_audio():
    """Record audio from microphone and save to temp file"""
    # Get audio settings from config
    device_id = CONFIG.get("audio", {}).get("device_id")
    device_name = CONFIG.get("audio", {}).get("device_name", "System Default")
    channels = CONFIG.get("audio", {}).get("channels", 1)
    rate = CONFIG.get("audio", {}).get("sample_rate", 44100)
    
    print(f"Audio device: {device_name} (ID: {device_id if device_id is not None else 'Default'})")
    print(f"Audio settings: {channels} channels, {rate} Hz")
    
    # PyAudio setup
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    print(f"Temporary file: {temp_file.name}")
    
    p = pyaudio.PyAudio()
    
    # Open stream with configured device if available
    stream_kwargs = {
        "format": FORMAT,
        "channels": channels,
        "rate": rate,
        "input": True,
        "frames_per_buffer": CHUNK
    }
    
    # Add input device if specified
    if device_id is not None:
        stream_kwargs["input_device_index"] = device_id
    
    # Open stream
    stream = p.open(**stream_kwargs)
    print("Recording started. Press Enter to stop.")
    
    frames = []
    recording = True
    
    # Start a thread to wait for Enter key to stop recording
    stop_thread = threading.Thread(target=wait_for_stop, args=(lambda: recording,))
    stop_thread.daemon = True
    stop_thread.start()
    
    # Record until stopped
    while recording:
        data = stream.read(CHUNK)
        frames.append(data)
        
        # Check if stop_thread is still alive
        if not stop_thread.is_alive():
            recording = False
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save the recorded data as a WAV file
    wf = wave.open(temp_file.name, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"Recording saved with {channels} channels at {rate} Hz")
    
    return temp_file.name

def wait_for_stop(recording_flag):
    """Wait for input to stop recording"""
    input()  # Wait for any input
    return False

def transcribe_audio(audio_file):
    """Transcribe audio using Whisper API"""
    if not CONFIG["api_key"]:
        print("Error: No API key provided")
        return
    
    # Initialize OpenAI client
    client = OpenAI(api_key=CONFIG["api_key"])
    
    # Generate transcript filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    transcript_path = os.path.join(CONFIG["transcript_dir"], f"{timestamp}.txt")
    
    try:
        # Call Whisper API for transcription
        with open(audio_file, "rb") as audio_data:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_data,
                response_format="verbose_json"
            )
        
        # Format and save transcript with metadata
        with open(transcript_path, 'w') as f:
            # Write header with metadata
            f.write(f"MEETING RECORDING TRANSCRIPT\n")
            f.write(f"Recorded: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Device: {device_name}\n")
            f.write("=" * 50 + "\n\n")
            
            # Check for segments (speaker differentiation)
            if hasattr(response, 'segments') and response.segments:
                # Get total duration for progress indicator
                if hasattr(response, 'duration'):
                    total_duration = response.duration
                else:
                    total_duration = 0
                    if response.segments:
                        last_segment = response.segments[-1]
                        if hasattr(last_segment, 'end'):
                            total_duration = last_segment.end
                
                # Write segments with timestamps
                for segment in response.segments:
                    # Get the timestamp
                    start_time = getattr(segment, 'start', 0)
                    timestamp = format_timestamp(start_time)
                    
                    # Get text content
                    text = getattr(segment, 'text', '').strip()
                    
                    # Write the segment
                    f.write(f"[{timestamp}] {text}\n\n")
            else:
                # Fallback to simple transcript
                if hasattr(response, 'text'):
                    f.write(response.text)
                else:
                    f.write(str(response))
        
        return transcript_path
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return None
    
def format_timestamp(seconds):
    """Convert seconds to a readable timestamp format"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def main():
    """Main recording function"""
    # Record audio
    audio_file = record_audio()
    
    # Transcribe
    transcript_path = transcribe_audio(audio_file)
    
    # Clean up
    if audio_file and os.path.exists(audio_file):
        os.unlink(audio_file)

if __name__ == "__main__":
    main()''')
        
        # Make executable
        os.chmod(recorder_script, 0o755)

def main():
    app = RecorderTrayApp()
    app.run()

if __name__ == "__main__":
    main()