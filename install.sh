#!/bin/bash
# Meeting Recorder Installation Script

echo "======================================"
echo "   Meeting Recorder Setup Script"
echo "======================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is required but not installed. Please install pip3 and try again."
    exit 1
fi

# Creating Transcriptions directory
echo "Creating Transcriptions directory..."
mkdir -p ~/Documents/Transcriptions

# Install PortAudio (required for PyAudio)
echo "Checking for PortAudio (required for PyAudio)..."
if ! command -v brew &> /dev/null; then
    echo "Homebrew is not installed. It's recommended for installing PortAudio."
    echo "Visit https://brew.sh to install Homebrew, then run this script again."
    echo ""
    echo "Alternatively, you can install PortAudio manually."
    READ_VAR=""
    read -p "Press Enter to continue anyway, or Ctrl+C to cancel..." READ_VAR
else
    echo "Installing PortAudio using Homebrew..."
    brew install portaudio
fi

# Set up Python virtual environment (optional but recommended)
echo "Would you like to set up a Python virtual environment for the recorder? (Recommended)"
echo "This isolates the dependencies from your system Python. (y/n)"
read -p "> " SETUP_VENV

if [[ $SETUP_VENV == "y" || $SETUP_VENV == "Y" ]]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install requirements
    echo "Installing required packages..."
    pip3 install -r requirements.txt
    
    echo ""
    echo "Virtual environment created and activated."
    echo "To run the app from the virtual environment in the future, first run:"
    echo "source $(pwd)/venv/bin/activate"
else
    # Install requirements globally
    echo "Installing required packages globally..."
    pip3 install -r requirements.txt
fi

echo ""
echo "======================================"
echo "   Installation Complete!"
echo "======================================"
echo ""
echo "To run Meeting Recorder, use:"
echo "python3 $(pwd)/meeting_recorder.py"
echo ""
echo "Important Notes:"
echo "1. The first time you run the app, you'll need to enter your OpenAI API key in settings"
echo "2. The app will create a system tray icon when running"
echo "3. Use Command+Shift+R to start/stop recording from anywhere"
echo "4. Transcripts will be saved to ~/Documents/Transcriptions"
echo ""

# Ask if user wants to create a launch agent (run at login)
echo "Would you like to set up the app to run at login? (y/n)"
read -p "> " RUN_AT_LOGIN

if [[ $RUN_AT_LOGIN == "y" || $RUN_AT_LOGIN == "Y" ]]; then
    LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
    LAUNCH_AGENT_FILE="$LAUNCH_AGENT_DIR/com.user.meetingrecorder.plist"
    
    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$LAUNCH_AGENT_DIR"
    
    # Create the launch agent plist file
    echo "Creating launch agent..."
    
    if [[ $SETUP_VENV == "y" || $SETUP_VENV == "Y" ]]; then
        # With virtual environment
        PYTHON_PATH="$(pwd)/venv/bin/python3"
    else
        # System Python
        PYTHON_PATH=$(which python3)
    fi
    
    # Create plist file
    cat > "$LAUNCH_AGENT_FILE" << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.meetingrecorder</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>$(pwd)/meeting_recorder.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>$(pwd)/error.log</string>
    <key>StandardOutPath</key>
    <string>$(pwd)/output.log</string>
</dict>
</plist>
EOL
    
    # Load the launch agent
    launchctl load "$LAUNCH_AGENT_FILE"
    
    echo "Launch agent created. The app will start automatically at login."
    echo "To manually start the app now, run:"
    echo "launchctl start com.user.meetingrecorder"
fi

echo ""
echo "Thank you for installing Meeting Recorder!"