# Advanced Motion Extractor Tool

A high-performance, real-time computer vision application written in Python. It is designed to extract movement and analyze motion from live video streams via RTSP, NDI Virtual Cameras, or local webcams, without deadlocking or lagging the user interface.

## Core Features
- **Persistent Connection UI**: Connect seamlessly to local cameras (e.g., `0`, `1`) or remote IP streams (e.g., `rtsp://...`). The app automatically remembers your last successfully used stream for quick access.
- **Multithreaded Architecture**: Video capture, frame buffering, and algorithmic calculations all run on background threads. Output is piped to a robust Tkinter queue for a perfectly fluid GUI.
- **Dynamic Resolution Handling**: Streams are processed internally at uncompressed full native resolutions (720p, 1080p, 4K), but scaled dynamically so the preview fits comfortably on modern monitor screens.
- **MP4 Local Recording**: Records the resulting mathematical extraction stream natively without GUI compression constraints. Output runs at native framerate seamlessly.

## Available Algorithms
The engine can be toggled in real-time between processing modes seamlessly:
1. **Classic Motion Extraction**: Inverts a delayed frame in a rolling temporal buffer and combines it dynamically with the active frame. The sliders enable tuning for both `Delay (sec)` and `Blend %`, pushing out stationary pixels while tracking movement trails.
2. **Polarity Frame Differencing (Neuromorphic Mimic)**: Ultra-fast grayscale variance tracking using structural matrices. Frame divergence is flagged if it out-paces the user-set `Noise Threshold`. Darkening pixels are painted Pure Blue, whilst brightening pixels fire as Pure Red. Emulates Event-based vision sensor polarity models at fractions of normal loop overhead. 

## Installation

### Prerequisites
It's strongly recommended to use a virtual environment so as not to clutter system packages or run afoul of OS limits (such as macOS `EXTERNALLY-MANAGED` errors).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install opencv-python pillow
```
*(Note for macOS Users: If your `tkinter` headers fail because Homebrew's python separated the bindings, simply run `brew install python-tk@3.14` or equivalent Python version before executing).*

## Running the Application
Ensure your virtual environment is activated, then run:

```bash
python motion_extractor.py
```

The application will prompt you for an address. Enter `0` for the laptop webcam or an `rtsp://` link for a remote network source, and click Connect!
