# Meeting Recorder

A lightweight macOS application that allows you to record any meeting on your laptop, transcribe the audio, and save it to disk. This application works regardless of what video conferencing tool you are using and can operate discreetly in the background.

## Features

- **Universal Recording**: Works with any application or meeting software
- **Multiple Audio Source Support**: Configure to use any connected audio input device
- **Transcription**: Automatically transcribe recordings using OpenAI's Whisper API
- **Discreet Interface**: Simple menu bar icon with minimal UI
- **Timestamps**: Transcripts include timestamps for easy navigation
- **Configurable Storage**: Save transcripts where you want them

## Requirements

- macOS
- Python 3.7 or higher
- OpenAI API key (for transcription)
- PyAudio
- rumps (for menu bar interface)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/forayconsulting/meeting-recorder.git
cd meeting-recorder
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the sample configuration file and add your OpenAI API key:
```bash
cp config.sample.json config.json
# Edit config.json with your preferred editor and add your API key
```

## Usage

### Running the Application

```bash
python simplified_tray_app.py
```

This will launch the application and add a microphone icon (🎙️) to your menu bar.

### Recording a Meeting

1. Click on the microphone icon in the menu bar
2. Select "Start Recording"
3. The icon will change to a red dot (🔴) to indicate active recording
4. When finished, click the icon again and select "Stop Recording"
5. The recording will be transcribed and saved to your configured transcript directory

### Selecting Audio Input Device

1. Click on the microphone icon in the menu bar
2. Select "Audio Device"
3. Choose from the list of available audio input devices
4. The selected device will be remembered for future recordings

### Viewing Transcripts

Transcripts are saved to the directory configured in `config.json` (default: `~/Documents/Transcriptions`).
The most recent transcript will automatically open after processing is complete.

## Configuration

Edit `config.json` to customize the application:

```json
{
    "api_key": "YOUR_OPENAI_API_KEY_HERE",
    "transcript_dir": "~/Documents/Transcriptions",
    "show_visual_indicator": true,
    "indicator_opacity": 0.3,
    "audio": {
        "device_id": null,
        "device_name": "System Default",
        "channels": 1,
        "sample_rate": 44100
    }
}
```

- **api_key**: Your OpenAI API key for transcription
- **transcript_dir**: Directory where transcripts will be saved
- **show_visual_indicator**: Enable/disable visual recording indicator
- **indicator_opacity**: Opacity of the visual indicator if enabled
- **audio**: Configuration for audio recording
  - **device_id**: ID of the audio device to use (null for system default)
  - **device_name**: Name of the audio device (for display purposes)
  - **channels**: Number of audio channels to capture
  - **sample_rate**: Sample rate for recording in Hz

## Utility Scripts

- **list_inputs.py**: List all available audio input devices
- **test_webcam_mic.py**: Test recording specifically with a webcam microphone
- **debug_recorder.py**: More detailed recording script with verbose logging

## License

MIT License