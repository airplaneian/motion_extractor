# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "opencv-python",
#     "pillow",
#     "numpy",
# ]
# ///

import cv2
import threading
import time
import datetime
import os
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import queue
import numpy as np

class MotionExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Motion Extractor Tool")
        
        # State variables
        self.video_source = None
        self.cap = None
        self.running = False
        self.thread = None
        self.capture_thread = None
        self.recording = False
        self.writer = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # Delcarations of dynamically bound UI components to please strict type checkers
        self.setup_frame = None
        self.source_var = None
        self.source_entry = None
        self.main_frame = None
        self.effect_var = None
        self.class_delay_var = None
        self.class_blend_var = None
        self.pol_thresh_var = None
        self.pol_delay_var = None
        self.panels_container = None
        self.classic_panel = None
        self.polarity_panel = None
        self.video_label = None

        # Thread-safe parameter values for the background thread
        self.active_effect_val = "Classic Motion Extraction"
        self.class_delay_val = 1.0
        self.class_blend_val = 0.5
        self.pol_thresh_val = 20.0
        self.pol_delay_val = 1.0
        
        # Stream properties
        self.native_w = 640
        self.native_h = 480
        self.fps = 30.0
        
        # Buffer for delayed frames
        self.frame_buffer = deque()
        self.last_known_frame = None
        
        # Thread-safe queue for GUI updates
        self.gui_queue = queue.Queue(maxsize=10)
        
        self.build_setup_ui()
        
    def build_setup_ui(self):
        """Initial UI to ask for Stream URL or Device Index."""
        self.setup_frame = ttk.Frame(self.root, padding=20)
        self.setup_frame.pack(expand=True, fill='both')
        
        ttk.Label(self.setup_frame, text="Enter Stream URL or Camera Index (e.g., 0):").pack(pady=5)
        
        last_val = "0"
        if os.path.exists("last_stream.txt"):
            try:
                with open("last_stream.txt", "r") as f:
                    last_val = f.read().strip()
            except Exception:
                pass
                
        self.source_var = tk.StringVar(value=last_val)
        self.source_entry = ttk.Entry(self.setup_frame, textvariable=self.source_var, width=50)
        self.source_entry.pack(pady=5)
        
        ttk.Button(self.setup_frame, text="Connect", command=self.connect_stream).pack(pady=10)
        
    def connect_stream(self):
        """Initializes the stream, determines properties, and launches main UI/thread."""
        src = self.source_var.get().strip()
        
        if src.isdigit():
            src = int(src)
            
        self.cap = cv2.VideoCapture(src)
        if self.cap is None or not self.cap.isOpened():
            messagebox.showerror("Connection Error", f"Failed to open video source: {src}")
            return
            
        # Dynamically fetch stream resolution and FPS
        width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        self.native_w = int(width) if width > 0 else 640
        self.native_h = int(height) if height > 0 else 480
        
        # Fallback for FPS
        if not fps or fps <= 0 or np.isnan(fps):
            self.fps = 30.0
        else:
            self.fps = float(fps)
            
        print(f"Connected. Native Resolution: {self.native_w}x{self.native_h}, Detected FPS: {self.fps}")
        
        # Save successful connection URL for next time
        try:
            with open("last_stream.txt", "w") as f:
                f.write(str(src))
        except Exception:
            pass
            
        self.setup_frame.pack_forget()
        self.build_main_ui()
        
        # Start GUI updater loop
        self.root.after(30, self.process_gui_queue)
        
        # Launch dedicated reading thread
        self.running = True
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        
        # Launch dedicated processing thread
        self.thread = threading.Thread(target=self.process_loop, daemon=True)
        self.thread.start()
        
    def build_main_ui(self):
        """Constructs the main video display and dynamic live controls GUI."""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both')
        
        # Top controls container
        settings_frame = ttk.Frame(self.main_frame, padding=10)
        settings_frame.pack(fill='x', side='top')
        
        # 1) Effect Selector Dropdown
        ttk.Label(settings_frame, text="Active Effect:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.effect_var = tk.StringVar(value="Classic Motion Extraction")
        self.effect_cb = ttk.Combobox(settings_frame, textvariable=self.effect_var, 
            values=["Classic Motion Extraction", "Polarity Frame Differencing"], state='readonly', width=30)
        self.effect_cb.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.effect_cb.bind("<<ComboboxSelected>>", self.on_effect_change)
        
        # 2) Global Buttons
        self.reset_btn = ttk.Button(settings_frame, text="Reset Defaults", command=self.reset_defaults)
        self.reset_btn.grid(row=0, column=2, padx=10, pady=5)
        
        self.record_btn = ttk.Button(settings_frame, text="Start Recording", command=self.toggle_recording)
        self.record_btn.grid(row=0, column=3, padx=10, pady=5)
        
        # 3) Dynamic Control Panels Container
        self.panels_container = ttk.Frame(settings_frame)
        self.panels_container.grid(row=1, column=0, columnspan=4, sticky='ew', pady=5)
        self.panels_container.columnconfigure(0, weight=1)
        
        # -- Panel A: Classic Motion Extraction --
        self.classic_panel = ttk.Frame(self.panels_container)
        self.classic_panel.columnconfigure(1, weight=1)
        
        ttk.Label(self.classic_panel, text="Delay (sec):").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.class_delay_var = tk.DoubleVar(value=1.0)
        self.class_delay_scale = ttk.Scale(self.classic_panel, from_=0.1, to_=5.0, variable=self.class_delay_var, command=self.update_labels)
        self.class_delay_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.class_delay_lbl = ttk.Label(self.classic_panel, text="1.00s", width=8)
        self.class_delay_lbl.grid(row=0, column=2, sticky='w', padx=5, pady=5)
        
        ttk.Label(self.classic_panel, text="Blend %:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.class_blend_var = tk.DoubleVar(value=0.5)
        self.class_blend_scale = ttk.Scale(self.classic_panel, from_=0.0, to_=1.0, variable=self.class_blend_var, command=self.update_labels)
        self.class_blend_scale.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        self.class_blend_lbl = ttk.Label(self.classic_panel, text="50%", width=8)
        self.class_blend_lbl.grid(row=1, column=2, sticky='w', padx=5, pady=5)
        
        # -- Panel B: Polarity Frame Differencing --
        self.polarity_panel = ttk.Frame(self.panels_container)
        self.polarity_panel.columnconfigure(1, weight=1)
        
        ttk.Label(self.polarity_panel, text="Noise Threshold:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.pol_thresh_var = tk.DoubleVar(value=20.0)
        self.pol_thresh_scale = ttk.Scale(self.polarity_panel, from_=1.0, to_=150.0, variable=self.pol_thresh_var, command=self.update_labels)
        self.pol_thresh_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.pol_thresh_lbl = ttk.Label(self.polarity_panel, text="20", width=8)
        self.pol_thresh_lbl.grid(row=0, column=2, sticky='w', padx=5, pady=5)
        
        ttk.Label(self.polarity_panel, text="Frame Delay:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.pol_delay_var = tk.DoubleVar(value=1.0)
        self.pol_delay_scale = ttk.Scale(self.polarity_panel, from_=1.0, to_=60.0, variable=self.pol_delay_var, command=self.update_labels)
        self.pol_delay_scale.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        self.pol_delay_lbl = ttk.Label(self.polarity_panel, text="1 frame(s)", width=12)
        self.pol_delay_lbl.grid(row=1, column=2, sticky='w', padx=5, pady=5)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # 4) Video Display Label
        self.video_label = tk.Label(self.main_frame)
        self.video_label.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Init Dynamic UI mapping
        self.on_effect_change()
        
        # Cleanup properly when window closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_effect_change(self, event=None):
        """Hides/Shows the correct control panel based on effect dropdown."""
        effect = self.effect_var.get()
        if effect == "Classic Motion Extraction":
            self.polarity_panel.pack_forget()
            self.classic_panel.pack(fill='both', expand=True)
        else:
            self.classic_panel.pack_forget()
            self.polarity_panel.pack(fill='both', expand=True)
        self.update_labels()

    def update_labels(self, *args):
        """Formats and updates the exact textual value of all slider inputs dynamically."""
        if getattr(self, 'class_delay_lbl', None) is None:
            return  # Prevent execution during Tkinter's Scale constructor before labels exist
            
        self.active_effect_val = self.effect_var.get()
        self.class_delay_val = self.class_delay_var.get()
        self.class_blend_val = self.class_blend_var.get()
        self.pol_thresh_val = self.pol_thresh_var.get()
        self.pol_delay_val = self.pol_delay_var.get()
        
        # Classic Motion Extraction
        self.class_delay_lbl.config(text=f"{self.class_delay_val:.2f}s")
        self.class_blend_lbl.config(text=f"{int(self.class_blend_val * 100)}%")
        # Polarity Diff
        self.pol_thresh_lbl.config(text=f"{int(self.pol_thresh_val)}")
        self.pol_delay_lbl.config(text=f"{int(self.pol_delay_val)} frm")

    def reset_defaults(self):
        """Restores the optimal slider positions for the currently active effect."""
        effect = self.effect_var.get()
        if effect == "Classic Motion Extraction":
            self.class_delay_var.set(1.0)
            self.class_blend_var.set(0.5)
        else:
            self.pol_thresh_var.set(20.0)
            self.pol_delay_var.set(1.0)
        self.update_labels()

    def toggle_recording(self):
        """Starts or stops local MP4 recording at native resolution."""
        if self.recording:
            self.recording = False
            self.record_btn.config(text="Start Recording")
            if self.writer:
                self.writer.release()
                self.writer = None
            print("Recording stopped.")
        else:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"motion_ext_{timestamp}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            self.writer = cv2.VideoWriter(filename, fourcc, self.fps, (self.native_w, self.native_h))
            self.recording = True
            self.record_btn.config(text="Stop Recording")
            print(f"Recording started: {filename}")
            
    def process_gui_queue(self):
        """Pulls generated frame updates from the processing thread to update the UI safely."""
        if not self.running:
            return
            
        latest_img = None
        try:
            while True:
                latest_img = self.gui_queue.get_nowait()
        except queue.Empty:
            pass
            
        if latest_img:
            # Instantiate PhotoImage securely in the MAIN Tkinter thread 
            imgtk = ImageTk.PhotoImage(image=latest_img)
            if self.video_label:
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
            
        if self.running:
            self.root.after(30, self.process_gui_queue)
            
    def capture_loop(self):
        """Continuously pulls frames from the camera to avoid buffer overflows."""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.frame_lock:
                        self.latest_frame = frame
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(0.1)
                
    def process_loop(self):
        """Background thread executing intensive capture, buffering, math, and recording."""
        max_gui_w = self.root.winfo_screenwidth() * 0.8
        max_gui_h = self.root.winfo_screenheight() * 0.8
        
        while self.running:
            try:
                start_time = time.perf_counter()
                
                with self.frame_lock:
                    if self.latest_frame is None:
                        frame = None
                    else:
                        frame = self.latest_frame.copy()
                
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # The rolling queue must support the maximum possible frame lookup depth
                # Example: Max classic delay = 5.0 seconds. 
                required_capacity = max(int(5.0 * self.fps) + 1, 65)
                
                self.frame_buffer.append(frame.copy())
                while len(self.frame_buffer) > required_capacity:
                    self.frame_buffer.popleft()
                
                active_effect = self.active_effect_val
                processed_frame = frame  # Default pass-through
                
                if active_effect == "Classic Motion Extraction":
                    delay_sec = self.class_delay_val
                    blend_weight = self.class_blend_val
                    
                    delay_frames = max(1, int(delay_sec * self.fps))
                    
                    # -1 is current frame, -2 is one frame ago, etc...
                    idx = min(len(self.frame_buffer), delay_frames + 1)
                    delayed_frame = self.frame_buffer[-idx]
                    
                    # Classic inverted blending logic
                    inverted_delayed = cv2.bitwise_not(delayed_frame)
                    processed_frame = cv2.addWeighted(
                        src1=frame, alpha=blend_weight,
                        src2=inverted_delayed, beta=1.0 - blend_weight,
                        gamma=0
                    )
                    
                elif active_effect == "Polarity Frame Differencing":
                    threshold = int(self.pol_thresh_val)
                    delay_frames = int(self.pol_delay_val)
                    
                    # Same rolling mechanism
                    idx = min(len(self.frame_buffer), delay_frames + 1)
                    delayed_frame = self.frame_buffer[-idx]
                    
                    # Polarity logic: isolate brightness diff into Red (positive) and Blue (negative)
                    gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray_delayed = cv2.cvtColor(delayed_frame, cv2.COLOR_BGR2GRAY)
                    
                    # Positive Difference (Pixels got Brighter) -> mapped to Red
                    diff_pos = cv2.subtract(gray_curr, gray_delayed)
                    _, mask_pos = cv2.threshold(diff_pos, threshold, 255, cv2.THRESH_BINARY)
                    
                    # Negative Difference (Pixels got Darker) -> mapped to Blue
                    diff_neg = cv2.subtract(gray_delayed, gray_curr)
                    _, mask_neg = cv2.threshold(diff_neg, threshold, 255, cv2.THRESH_BINARY)
                    
                    # OpenCV standard processing occurs in BGR layout: index 0 is Blue, 1 is Green, 2 is Red
                    mask_green = np.zeros_like(mask_neg)
                    processed_frame = cv2.merge([mask_neg, mask_green, mask_pos])
                    
                # Full uncompressed Native scale recording support (ignoring UI resize constraints)
                if self.recording and self.writer:
                    self.writer.write(processed_frame)
                    
                # Apply high quality scale-down targeting optimal screen fit for GUI representation
                disp_w, disp_h = self.native_w, self.native_h
                if disp_w > max_gui_w or disp_h > max_gui_h:
                    scale = min(max_gui_w / float(disp_w), max_gui_h / float(disp_h))
                    disp_w = int(disp_w * scale)
                    disp_h = int(disp_h * scale)
                    
                display_frame = cv2.resize(processed_frame, (disp_w, disp_h))
                
                # Converting for Tkinter compatibility (BGR -> RGB)
                display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(display_frame)
                
                if self.gui_queue.full():
                    try:
                        self.gui_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.gui_queue.put(img)
                
                # Enforce native framerate to avoid runaway processing and duplicate timestamps
                elapsed = time.perf_counter() - start_time
                target_frame_time = 1.0 / self.fps
                if elapsed < target_frame_time:
                    time.sleep(target_frame_time - elapsed)
                
            except Exception as e:
                print(f"Exception in process loop: {e}")
                time.sleep(0.1)
                
    def on_closing(self):
        """Cleanup all resources cleanly upon window exit."""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.recording and self.writer:
            self.writer.release()
        if self.cap:
            self.cap.release()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = MotionExtractorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
