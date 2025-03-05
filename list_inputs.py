#!/usr/bin/env python3
"""
Simple utility to list all audio input devices
"""

import pyaudio
import sys

def main():
    print("\n=== Available Audio Input Devices ===\n")

    try:
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        print(f"Total audio devices: {device_count}")
        
        for i in range(device_count):
            try:
                info = p.get_device_info_by_index(i)
                
                # Only show devices with input channels
                if info.get('maxInputChannels', 0) > 0:
                    name = info.get('name', 'Unknown')
                    channels = info.get('maxInputChannels', 0)
                    sample_rate = int(info.get('defaultSampleRate', 0))
                    
                    # Show device info
                    print(f"\nDevice ID: {i}")
                    print(f"  Name: {name}")
                    print(f"  Input Channels: {channels}")
                    print(f"  Sample Rate: {sample_rate} Hz")
                    
                    # Try to get more info about the device
                    host_api = info.get('hostApi', 0)
                    host_api_info = p.get_host_api_info_by_index(host_api)
                    print(f"  Host API: {host_api_info.get('name', 'Unknown')}")
                    
                    # Check if this is the default input device
                    try:
                        default_info = p.get_default_input_device_info()
                        if default_info['index'] == i:
                            print("  *** DEFAULT INPUT DEVICE ***")
                    except:
                        pass
            except Exception as e:
                print(f"Error getting info for device {i}: {e}")
                continue
        
        # Try to get and print default device info
        try:
            default = p.get_default_input_device_info()
            print(f"\nDefault Input Device: {default['name']} (ID: {default['index']})")
        except Exception as e:
            print(f"\nCould not determine default input device: {e}")
        
        p.terminate()
        
    except Exception as e:
        print(f"Error initializing PyAudio: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())