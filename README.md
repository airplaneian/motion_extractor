## Motion Extraction Experiments in Python
This is a lightweight Python experiment exploring a couple of different ways to visualize motion in live video. It's a fun sandbox built with OpenCV to play around with live RTSP streams, NDI virtual cameras, or just a standard webcam to see what happens when you mess with time delays and frame differencing.

## What It Does
Stream Handling: Accepts integer inputs for local webcams (e.g., 0) or network IP streams (rtsp://...). It automatically caches your last used stream on launch so you don't have to keep pasting it.

Threaded GUI: Video capture and frame buffering run on a background thread to ensure the Tkinter interface doesn't lock up or stutter while you are adjusting settings.

Resolution Management: The mathematical processing and video writing occur at the stream's uncompressed native resolution, while the live preview window is dynamically scaled down to fit your monitor.

Recording: Includes a basic cv2.VideoWriter setup to trigger local MP4 saves of the processed feed directly from the UI.

## The Two Modes
You can toggle between two different visual effects in real-time:

Classic Motion Extraction: This replicates a fascinating visual technique demonstrated by the YouTube channel Posy. The script maintains a rolling buffer of frames, takes a delayed frame, inverts its colors, and blends it with the live feed at 50% opacity. Because the static background pixels are exact opposites, they cancel each other out into a neutral gray. As a result, any object that has moved between the two frames suddenly pops out. Sliders allow you to adjust the time delay to target fast or slow motion.

Polarity Frame Differencing (Event Camera Mimic): A software approximation of how neuromorphic "event cameras" work. It compares the current frame to the previous one to isolate brightness changes. If a pixel gets brighter, it paints it pure Red. If it gets darker, it paints it pure Blue. Everything else stays Black. It's fast, high-contrast, and you can tweak the noise threshold to filter out standard camera grain.

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
