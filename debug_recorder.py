#!/usr/bin/env python3
"""
Debug version of the recorder process with detailed logging
"""

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
import traceback

# Set up logging
DEBUG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")

def log(message):
    """Write a message to the debug log"""
    with open(DEBUG_LOG, "a") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

# Configuration
CONFIG = {
    "api_key": "",
    "transcript_dir": os.path.expanduser("~/Documents/Transcriptions"),
    "audio": {
        "device_id": None,
        "device_name": "",
        "channels": 1,
        "sample_rate": 44100
    }
}

log("Starting debug_recorder.py")

# Load configuration from file
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
log(f"Looking for config at: {config_path}")

if os.path.exists(config_path):
    try:
        with open(config_path, 'r') as f:
            loaded_config = json.load(f)
            log(f"Loaded config: {json.dumps(loaded_config, indent=2)}")
            
            for key, value in loaded_config.items():
                if key == "api_key":
                    # Mask API key in logs
                    log(f"Found API key: {'*' * 10}...{'*' * 5}")
                    CONFIG[key] = value
                elif key == "transcript_dir" and value.startswith("~"):
                    expanded_path = os.path.expanduser(value)
                    log(f"Expanded path '{value}' to '{expanded_path}'")
                    CONFIG[key] = expanded_path
                else:
                    CONFIG[key] = value
    except Exception as e:
        log(f"Error loading config: {str(e)}")
        log(traceback.format_exc())

# Create the transcript directory if it doesn't exist
os.makedirs(CONFIG["transcript_dir"], exist_ok=True)
log(f"Ensuring transcript directory exists: {CONFIG['transcript_dir']}")

def record_audio():
    """Record audio from microphone and save to temp file"""
    log("Starting audio recording")
    
    # Get audio settings from config
    device_id = CONFIG.get("audio", {}).get("device_id")
    device_name = CONFIG.get("audio", {}).get("device_name", "Default Device")
    channels = CONFIG.get("audio", {}).get("channels", 1)
    rate = CONFIG.get("audio", {}).get("sample_rate", 44100)
    
    log(f"Audio settings from config: device_id={device_id}, device_name='{device_name}', channels={channels}, rate={rate}")
    
    # PyAudio setup
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    log(f"Created temporary file: {temp_file.name}")
    
    p = pyaudio.PyAudio()
    
    # Log available input devices
    try:
        device_count = p.get_device_count()
        log(f"Found {device_count} audio devices")
        
        for i in range(device_count):
            try:
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    log(f"Input device {i}: {info.get('name')} (Channels: {info.get('maxInputChannels')}, Rate: {info.get('defaultSampleRate')})")
            except Exception as e:
                log(f"Error getting info for device {i}: {e}")
    except Exception as e:
        log(f"Error enumerating audio devices: {e}")
    
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
        log(f"Using specific input device: ID {device_id} ({device_name})")
        stream_kwargs["input_device_index"] = device_id
    
    try:
        stream = p.open(**stream_kwargs)
        log(f"Opened audio stream successfully (channels={channels}, rate={rate})")
    except Exception as e:
        log(f"Error opening audio stream: {str(e)}")
        log(traceback.format_exc())
        return None
    
    frames = []
    recording = True
    
    # Start a thread to wait for Enter key to stop recording
    stop_thread = threading.Thread(target=wait_for_stop, args=(lambda: recording,))
    stop_thread.daemon = True
    stop_thread.start()
    log("Started stop-detection thread")
    
    start_time = time.time()
    # Record until stopped
    while recording:
        try:
            data = stream.read(CHUNK)
            frames.append(data)
        except Exception as e:
            log(f"Error reading audio data: {str(e)}")
            log(traceback.format_exc())
            break
        
        # Check if stop_thread is still alive
        if not stop_thread.is_alive():
            log("Stop-detection thread ended, stopping recording")
            recording = False
    
    duration = time.time() - start_time
    log(f"Recording stopped after {duration:.2f} seconds")
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    log("Audio stream closed")
    
    # Save the recorded data as a WAV file
    try:
        wf = wave.open(temp_file.name, 'wb')
        wf.setnchannels(channels)  # Use configured channels
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(rate)      # Use configured sample rate
        wf.writeframes(b''.join(frames))
        wf.close()
        log(f"Saved WAV file ({len(frames)} frames, {channels} channels, {rate} Hz) to {temp_file.name}")
    except Exception as e:
        log(f"Error saving WAV file: {str(e)}")
        log(traceback.format_exc())
        return None
    
    return temp_file.name

def wait_for_stop(recording_flag):
    """Wait for input to stop recording"""
    log("Waiting for input to stop recording")
    input()  # Wait for any input
    log("Received input to stop recording")
    return False

def transcribe_audio(audio_file):
    """Transcribe audio using Whisper API"""
    log(f"Starting transcription of {audio_file}")
    
    if not audio_file or not os.path.exists(audio_file):
        log(f"Audio file does not exist: {audio_file}")
        return None
    
    if not CONFIG["api_key"]:
        log("Error: No API key provided")
        return None
    
    # Initialize OpenAI client
    client = OpenAI(api_key=CONFIG["api_key"])
    log("OpenAI client initialized")
    
    # Generate transcript filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    transcript_path = os.path.join(CONFIG["transcript_dir"], f"{timestamp}.txt")
    log(f"Will save transcript to: {transcript_path}")
    
    try:
        # Get file size for logging
        file_size = os.path.getsize(audio_file)
        log(f"Audio file size: {file_size} bytes")
        
        # Call Whisper API for transcription with new API
        log("Sending audio to Whisper API...")
        with open(audio_file, "rb") as audio_data:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_data,
                response_format="verbose_json"
            )
        log("Received response from Whisper API")
        
        # Log response structure
        if isinstance(response, dict):
            log(f"Response keys: {list(response.keys())}")
            if 'text' in response:
                text_sample = response['text'][:100] + "..." if len(response['text']) > 100 else response['text']
                log(f"Text sample: {text_sample}")
            if 'segments' in response:
                log(f"Number of segments: {len(response['segments'])}")
        else:
            log(f"Response type: {type(response)}")
        
        # Get device name for metadata
        device_name = CONFIG.get("audio", {}).get("device_name", "Default Device")
        
        # Format and save transcript with metadata
        log("Saving transcript with metadata")
        with open(transcript_path, 'w') as f:
            # Write header with metadata
            f.write(f"MEETING RECORDING TRANSCRIPT\n")
            f.write(f"Recorded: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Device: {device_name}\n")
            f.write("=" * 50 + "\n\n")
            
            # Check for segments (speaker differentiation)
            if hasattr(response, 'segments') and response.segments:
                log(f"Found {len(response.segments)} segments")
                # Get total duration for progress indicator
                total_duration = getattr(response, 'duration', 0)
                if total_duration == 0 and response.segments:
                    # Try to get duration from last segment
                    last_segment = response.segments[-1]
                    total_duration = getattr(last_segment, 'end', 0)
                
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
                log("No segments found, using plain text")
                # Fallback to simple transcript
                if hasattr(response, 'text'):
                    f.write(response.text)
                else:
                    f.write(str(response))
        
        log(f"Saved transcript to {transcript_path}")
        
        return transcript_path
    except Exception as e:
        log(f"Transcription error: {str(e)}")
        log(traceback.format_exc())
        return None
    
def format_timestamp(seconds):
    """Convert seconds to a readable timestamp format"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def main():
    """Main recording function"""
    log("=== Starting recording session ===")
    
    # Record audio
    audio_file = record_audio()
    if not audio_file:
        log("Failed to record audio, exiting")
        return
    
    # Transcribe
    transcript_path = transcribe_audio(audio_file)
    if transcript_path:
        log(f"Transcription completed successfully: {transcript_path}")
    else:
        log("Transcription failed")
    
    # Clean up
    if audio_file and os.path.exists(audio_file):
        os.unlink(audio_file)
        log(f"Cleaned up temporary audio file: {audio_file}")
    
    log("=== Recording session completed ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Unhandled exception: {str(e)}")
        log(traceback.format_exc())