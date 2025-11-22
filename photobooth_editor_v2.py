import cv2
import tkinter as tk
from tkinter.messagebox import showerror, askyesno

import ttkbootstrap as ttk
from PIL import Image, ImageOps, ImageTk
import time
from pathlib import Path
from typing import List, Tuple

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
WIDTH = 1000
HEIGHT = 1000

MAX_CAPTURED_IMAGES = 8   # how many photos you can take (fixed at 8)
MAX_FRAME_IMAGES = 4      # how many photos go into the final frame

BASE_DIR = Path(__file__).resolve().parent
BACKGROUND_DIR = BASE_DIR / "frame_designs"
GOOGLE_DRIVE_FOLDER = BASE_DIR / "photos"

SLOT_W = 354   # width of one white box (frame slot)
SLOT_H = 236   # height of one white box

# All other boxes keep the same aspect ratio as SLOT_W : SLOT_H
SLOT_RATIO = SLOT_W / SLOT_H

# Preview size (fixed; we center this in the preview canvas)
PREVIEW_W = 1300
PREVIEW_H = int(PREVIEW_W / SLOT_RATIO)

# Layout selector box size (page 2 top strip)
LAYOUT_BOX_W = 110
LAYOUT_BOX_H = int(LAYOUT_BOX_W / SLOT_RATIO)


# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
def resize_to_fit(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """Resize background to (almost) fit canvas while keeping aspect ratio,
    and rotate 90 degrees like your original code."""
    img_width, img_height = image.size
    img_aspect = img_width / img_height
    target_aspect = target_width / target_height

    if img_aspect > target_aspect:
        new_width = target_width
        new_height = int(target_width / img_aspect)
    else:
        new_height = target_height
        new_width = int(target_height * img_aspect)

    resized_image = image.resize((int(new_width * 0.9), int(new_height * 0.9)))
    resized_image = resized_image.rotate(90, expand=True)
    return resized_image


def create_photo_strip_positions_display() -> List[Tuple[int, int]]:
    """Positions used when DRAWING on the layout canvas (what the user sees)."""
    return [
        (177, 58),
        (537, 58),
        (177, 299),
        (537, 299),
    ]

def create_photo_strip_positions_save() -> List[Tuple[int, int]]:
    """Positions used when SAVING to the final image file."""
    return [
        (177, 256),
        (177 + 354 + 6, 256),
        (177, 256 + 236 + 7),
        (177 + 354 + 6, 256 + 236 + 7),
    ]


# -------------------------------------------------------------------
# MAIN APP
# -------------------------------------------------------------------
class PhotoboothApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photobooth Editor")
        self.root.geometry("1100x1000")
        self.root.resizable(True, True)

        # Camera
        self.cap = None
        self.camera_running = False
        self.current_preview_pil = None  # cropped to SLOT_RATIO
        self.current_preview_tk = None

        # Countdown / sequence
        self.is_counting_down = False       # used to lock the button
        self.sequence_running = False       # are we in the 8-photo sequence?
        self.sequence_index = 0             # which photo (0..7)
        self.sequence_delay_remaining = 0   # seconds until next photo

        # Global style tweaks
        style = ttk.Style()
        style.configure("TFrame", padding=10)
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=(10, 6))

        # Data: layout slots (final 4 photos)
        self.image_positions_display = create_photo_strip_positions_display()
        self.image_positions_save = create_photo_strip_positions_save()

        self.current_images = [None] * MAX_FRAME_IMAGES   # 4 images used in the frame
        self.image_widgets = [None] * MAX_FRAME_IMAGES    # keep PhotoImage refs per slot

        # Data: captured pool (8 photos from the sequence)
        self.captured_images = [None] * MAX_CAPTURED_IMAGES
        self.captured_thumbs = [None] * MAX_CAPTURED_IMAGES
        self.layout_slot_canvases: list[tk.Canvas] = []
        self.layout_thumbs = [None] * MAX_CAPTURED_IMAGES
        self.frame_selection_order: list[int] = []  # indices into captured_images

        # Backgrounds
        self.filtered_cache = {}
        self.background_images = []     # large ImageTk for display
        self.background_thumbs = []     # small ImageTk for bottom bar
        self.current_background_index = 0

        # Status bar
        self.status_var = tk.StringVar(value="Ready")

        # Pages: "landing", "capture", "layout"
        self.current_page = "landing"

        # UI
        self._build_ui()
        self.load_background_images()
        self.display_background()
        self._update_buttons()

        # Shortcuts
        self.root.bind("<space>", lambda e: self.start_sequence())
        self.root.bind("<Control-s>", lambda e: self.save_canvas())

    # ---------------------- UI LAYOUT --------------------------------
    def _build_ui(self):
        # Status bar at bottom
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            bootstyle="secondary-inverse",
        )
        status_bar.pack(side="bottom", fill="x")

        # Main frame holds all pages (no left control panel anymore)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side="top", fill="both", expand=True)

        self.page_landing = ttk.Frame(self.main_frame)
        self.page_capture = ttk.Frame(self.main_frame)
        self.page_layout = ttk.Frame(self.main_frame)

        self._build_landing_page()
        self._build_capture_page()
        self._build_layout_page()

        self.show_landing_page()

    # ---------------------- LANDING PAGE -----------------------------
    def _build_landing_page(self):
        """Simple landing screen shown when the app launches or after saving."""
        self.page_landing.rowconfigure(0, weight=1)
        self.page_landing.columnconfigure(0, weight=1)

        container = ttk.Frame(self.page_landing)
        container.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)

        title = ttk.Label(
            container,
            text="📸 Photobooth",
            style="Title.TLabel",
            anchor="center",
            justify="center",
        )
        title.pack(pady=(0, 20))

        subtitle = ttk.Label(
            container,
            text="Tap the button below to start a new photo session.",
            anchor="center",
            justify="center",
        )
        subtitle.pack(pady=(0, 20))

        start_btn = ttk.Button(
            container,
            text="Start Photobooth",
            bootstyle="primary",
            command=self.start_session,
        )
        start_btn.pack(pady=10)

    def show_landing_page(self):
        self.page_capture.pack_forget()
        self.page_layout.pack_forget()
        self.page_landing.pack(fill="both", expand=True)

        self.current_page = "landing"
        self.status_var.set("Welcome! Click 'Start Photobooth' to begin.")

    def start_session(self):
        """From landing → reset, go to camera page, start camera."""
        self._reset_images()
        self.sequence_running = False
        self.is_counting_down = False
        self.sequence_index = 0

        self.show_capture_page()
        self.start_camera()

    # ---------------------- CAPTURE PAGE -----------------------------
    def _build_capture_page(self):
        """Page: full camera preview with a single button at the bottom center."""
        self.page_capture.rowconfigure(0, weight=1)
        self.page_capture.rowconfigure(1, weight=0)
        self.page_capture.columnconfigure(0, weight=1)

        # Preview area
        preview_frame = ttk.Frame(self.page_capture)
        preview_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        # label = ttk.Label(
        #     preview_frame,
        #     text="Camera Preview",
        #     style="Section.TLabel",
        #     anchor="w",
        # )
        # label.grid(row=0, column=0, sticky="w", padx=10, pady=(0, 5))

        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.camera_preview_main = tk.Canvas(
            canvas_frame,
            width=PREVIEW_W,
            height=PREVIEW_H,
            bg="black",            # default background is black
            highlightthickness=0,
        )
        self.camera_preview_main.grid(row=0, column=0, sticky="nsew")

        # Bottom button area (single button in bottom middle)
        button_frame = ttk.Frame(self.page_capture)
        button_frame.grid(row=1, column=0, pady=(0, 20))

        self.capture_btn = ttk.Button(
            button_frame,
            text="Start Photo Session",
            bootstyle="success",
            command=self.start_sequence,
        )
        self.capture_btn.pack()

    def show_capture_page(self):
        self.page_landing.pack_forget()
        self.page_layout.pack_forget()
        self.page_capture.pack(fill="both", expand=True)

        self.current_page = "capture"
        self.status_var.set("Capture mode: press the button to start the 8-photo session.")
        self._update_buttons()

    # ---------------------- LAYOUT PAGE ------------------------------
    def _build_layout_page(self):
        """Page: top = 8-photo strip, middle = canvas, bottom = backgrounds + Save."""
        self.page_layout.rowconfigure(0, weight=0)   # thumbnails
        self.page_layout.rowconfigure(1, weight=1)   # canvas area
        self.page_layout.rowconfigure(2, weight=0)   # background bar
        self.page_layout.rowconfigure(3, weight=0)   # save button
        self.page_layout.columnconfigure(0, weight=1)

        # ---------- TOP STRIP ----------
        top_area = ttk.Frame(self.page_layout)
        top_area.grid(row=0, column=0, sticky="ew", pady=(12, 6))
        top_area.columnconfigure(0, weight=1)

        info_label = ttk.Label(
            top_area,
            text="Select up to 4 photos in order for the strip",
            style="Section.TLabel",
            anchor="center",
            justify="center",
        )
        info_label.grid(row=0, column=0, pady=(0, 6))

        self.selector_wrapper = ttk.Frame(top_area)
        self.selector_wrapper.grid(row=1, column=0)
        self.selector_wrapper.columnconfigure(0, weight=1)

        self.selector_bar = ttk.Frame(self.selector_wrapper)
        self.selector_bar.grid(row=0, column=0)

        # ---------- MIDDLE: CANVAS AREA ----------
        self.canvas_area = ttk.Frame(self.page_layout)
        self.canvas_area.grid(row=1, column=0, sticky="nsew")
        self.canvas_area.rowconfigure(0, weight=0)
        self.canvas_area.rowconfigure(1, weight=1)
        self.canvas_area.columnconfigure(0, weight=1)

        CANVAS_W = WIDTH
        CANVAS_H = HEIGHT

        self.canvas = tk.Canvas(
            self.canvas_area,
            width=CANVAS_W,
            height=CANVAS_H,
            bg="white",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, pady=(4, 0))

        # ---------- BOTTOM: BACKGROUND BAR ----------
        self.bg_bar = ttk.Frame(self.page_layout, height=120)
        self.bg_bar.grid(row=2, column=0, sticky="ew")
        self.bg_bar.grid_propagate(False)

        # ---------- SAVE BUTTON ----------
        save_frame = ttk.Frame(self.page_layout)
        save_frame.grid(row=3, column=0, pady=(10, 20))

        self.save_btn = ttk.Button(
            save_frame,
            text="💾 Save Strip",
            bootstyle="primary",
            command=self.save_canvas,
        )
        self.save_btn.pack()

    def show_layout_page(self):
        self.page_landing.pack_forget()
        self.page_capture.pack_forget()
        self.page_layout.pack(fill="both", expand=True)

        self.current_page = "layout"
        self.status_var.set("Layout mode: choose up to 4 photos and save your strip.")

        self._populate_layout_selector()
        self._highlight_selected_background()
        self._draw_photos_on_canvas()
        self.display_background()
        self._update_buttons()

    # ---------- layout selector strip ----------
    def _populate_layout_selector(self):
        for child in self.selector_bar.winfo_children():
            child.destroy()

        self.layout_slot_canvases = []
        self.layout_thumbs = [None] * MAX_CAPTURED_IMAGES

        for idx in range(MAX_CAPTURED_IMAGES):
            c = tk.Canvas(
                self.selector_bar,
                width=LAYOUT_BOX_W,
                height=LAYOUT_BOX_H,
                bg="#f0f0f0",
                highlightthickness=2,
                highlightbackground="#999",
            )
            c.pack(side="left", padx=6, pady=4)
            c.bind("<Button-1>", lambda e, i=idx: self.toggle_frame_selection(i))
            self.layout_slot_canvases.append(c)

        self._refresh_layout_selector()

    def _refresh_layout_selector(self):
        for idx in range(MAX_CAPTURED_IMAGES):
            if idx >= len(self.layout_slot_canvases):
                break

            canvas = self.layout_slot_canvases[idx]
            img = self.captured_images[idx]
            canvas.delete("all")

            selected = idx in self.frame_selection_order
            border_color = "dodgerblue" if selected else "#888"
            canvas.configure(highlightbackground=border_color)

            canvas.create_rectangle(
                2,
                2,
                LAYOUT_BOX_W - 2,
                LAYOUT_BOX_H - 2,
                outline=border_color,
                width=2,
            )

            if img is None:
                canvas.create_text(
                    LAYOUT_BOX_W // 2,
                    LAYOUT_BOX_H // 2,
                    text=f"{idx + 1}",
                    fill="#666",
                )
            else:
                thumb = img.resize(
                    (LAYOUT_BOX_W - 6, LAYOUT_BOX_H - 6),
                    Image.LANCZOS
                )
                tk_thumb = ImageTk.PhotoImage(thumb)
                self.layout_thumbs[idx] = tk_thumb
                canvas.create_image(
                    LAYOUT_BOX_W // 2,
                    LAYOUT_BOX_H // 2,
                    image=tk_thumb,
                )

                if selected:
                    order = self.frame_selection_order.index(idx) + 1
                    canvas.create_oval(
                        8, 8, 26, 26,
                        fill="dodgerblue",
                        outline="white",
                        width=1,
                    )
                    canvas.create_text(
                        17, 17,
                        text=str(order),
                        fill="white",
                        font=("TkDefaultFont", 9, "bold"),
                    )

    def toggle_frame_selection(self, index: int):
        if not (0 <= index < MAX_CAPTURED_IMAGES):
            return

        img = self.captured_images[index]
        if img is None:
            self.status_var.set("No image in that captured slot")
            return

        if index in self.frame_selection_order:
            self.frame_selection_order.remove(index)
            self.status_var.set(
                f"Removed captured photo #{index + 1} from frame selection"
            )
        else:
            if len(self.frame_selection_order) >= MAX_FRAME_IMAGES:
                self.status_var.set("You can only select up to 4 photos for the frame")
                return
            self.frame_selection_order.append(index)
            self.status_var.set(
                "Selected order: "
                + ", ".join(str(i + 1) for i in self.frame_selection_order)
            )

        self._apply_frame_selection_to_slots()
        self._refresh_layout_selector()
        self._draw_photos_on_canvas()
        self._update_buttons()

    def _apply_frame_selection_to_slots(self):
        self.current_images = [None] * MAX_FRAME_IMAGES
        for slot_idx, cap_idx in enumerate(self.frame_selection_order[:MAX_FRAME_IMAGES]):
            src = self.captured_images[cap_idx]
            if src is not None:
                self.current_images[slot_idx] = src.copy()

    # ---------------------- BACKGROUNDS -------------------------------
    def load_background_images(self):
        """Load full-size and thumbnail versions of each background."""
        try:
            self.background_images.clear()
            self.background_thumbs.clear()

            for i in range(7, 16):
                path = BACKGROUND_DIR / f"{i}.png"
                if not path.exists():
                    continue

                pil_img = Image.open(path).convert("RGBA")
                large = resize_to_fit(pil_img, WIDTH, HEIGHT)
                thumb = large.copy()
                thumb.thumbnail((120, 120))

                tk_large = ImageTk.PhotoImage(large)
                tk_thumb = ImageTk.PhotoImage(thumb)

                self.background_images.append(tk_large)
                self.background_thumbs.append(tk_thumb)

            self._populate_background_bar()
        except Exception as e:
            showerror("Error", f"Error loading background images: {e}")
            self.status_var.set("Error loading backgrounds")

    def _populate_background_bar(self):
        for child in self.bg_bar.winfo_children():
            child.destroy()

        strip = ttk.Frame(self.bg_bar)
        strip.pack(anchor="center", pady=4)

        for idx, thumb in enumerate(self.background_thumbs):
            frame = ttk.Frame(strip, padding=2)
            frame.pack(side="left", padx=4, pady=4)

            lbl = ttk.Label(frame, image=thumb)
            lbl.image = thumb
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, i=idx: self.set_background(i))

        self._highlight_selected_background()

    def _highlight_selected_background(self):
        for i, child in enumerate(self.bg_bar.winfo_children()):
            child.configure(bootstyle="")

    def set_background(self, index):
        self.current_background_index = index
        self.display_background()
        self._highlight_selected_background()
        self.status_var.set(f"Background set to #{index + 1}")

    def display_background(self):
        if not self.background_images or not hasattr(self, "canvas"):
            return

        self.canvas.delete("background")

        bg_image = self.background_images[self.current_background_index]
        canvas_w = int(self.canvas.cget("width"))
        canvas_h = int(self.canvas.cget("height"))

        # Center horizontally, but stick to TOP vertically
        x_offset = (canvas_w - bg_image.width()) // 2
        y_offset = 0

        bg_id = self.canvas.create_image(
            x_offset, y_offset, anchor="nw", image=bg_image, tags="background"
        )
        # If you want photos behind the frame:
        # self.canvas.tag_raise("background")
        self.root.update_idletasks()


    # ---------------------- CAMERA -----------------------------------
    def _crop_to_slot_ratio(self, img: Image.Image) -> Image.Image:
        """Center-crop the given image to the SLOT_W:SLOT_H aspect ratio."""
        w, h = img.size
        current_ratio = w / h

        if current_ratio > SLOT_RATIO:
            new_w = int(h * SLOT_RATIO)
            left = (w - new_w) // 2
            box = (left, 0, left + new_w, h)
        else:
            new_h = int(w / SLOT_RATIO)
            top = (h - new_h) // 2
            box = (0, top, w, top + new_h)

        return img.crop(box)

    def start_camera(self):
        if self.camera_running:
            return

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            showerror("Error", "Could not open camera. Check permissions.")
            self.status_var.set("Could not open camera")
            return

        self.camera_running = True
        self.status_var.set("Camera started")
        self._update_buttons()
        self.update_camera_frame()

    def update_camera_frame(self):
        if not self.camera_running or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.camera_running = False
            self.status_var.set("Camera stopped (no frame)")
            self._update_buttons()
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.flip(frame, 1)
        img = Image.fromarray(frame)

        cropped = self._crop_to_slot_ratio(img)
        self.current_preview_pil = cropped

        preview = cropped.resize((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
        self.current_preview_tk = ImageTk.PhotoImage(preview)

        # Center the preview in the canvas
        canvas_w = max(self.camera_preview_main.winfo_width(), PREVIEW_W)
        canvas_h = max(self.camera_preview_main.winfo_height(), PREVIEW_H)
        cx = canvas_w // 2
        cy = canvas_h // 2

        self.camera_preview_main.delete("preview")
        self.camera_preview_main.create_image(
            cx,
            cy,
            image=self.current_preview_tk,
            tags="preview",
        )
        self.camera_preview_main.image = self.current_preview_tk

        self.camera_preview_main.tag_raise("countdown")
        self.root.after(30, self.update_camera_frame)

    # ---------------------- 8-PHOTO SEQUENCE --------------------------
    def start_sequence(self):
        """Start the 8-photo timed sequence: 15s before first, 10s between others."""
        if self.current_page != "capture":
            return

        if self.sequence_running:
            self.status_var.set("Session already running...")
            return

        if not self.camera_running:
            self.start_camera()
            if not self.camera_running:
                return

        # Reset captured images for this new sequence
        self.captured_images = [None] * MAX_CAPTURED_IMAGES
        self.frame_selection_order.clear()
        self.current_images = [None] * MAX_FRAME_IMAGES

        self.sequence_running = True
        self.sequence_index = 0
        self.sequence_delay_remaining = 3  # first wait: 15 seconds
        self.is_counting_down = True

        self.status_var.set("Starting 8-photo session... first photo in 15 seconds.")
        self._update_buttons()
        self._sequence_countdown_tick()

    def _sequence_countdown_tick(self):
        if not self.sequence_running:
            # Clean up any leftover countdown graphics
            self.camera_preview_main.delete("countdown")
            self.is_counting_down = False
            self._update_buttons()
            return

        # Remove previous countdown drawing
        self.camera_preview_main.delete("countdown")

        # If we're done counting, take the photo
        if self.sequence_delay_remaining <= 0:
            self.camera_preview_main.delete("countdown")
            self._capture_one_in_sequence()
            return

        # --- Get canvas size safely ---
        canvas_w = self.camera_preview_main.winfo_width()
        canvas_h = self.camera_preview_main.winfo_height()

        # If canvas hasn't been laid out yet, try again shortly
        if canvas_w < 50 or canvas_h < 50:
            self.root.after(100, self._sequence_countdown_tick)
            return

        # Small countdown badge in the top-right corner
        margin = 20
        # Radius relative to screen size, but clamped so it doesn't get huge
        radius = int(min(canvas_w, canvas_h) * 0.05)
        radius = max(25, min(radius, 60))  # between 25 and 60 px

        cx = canvas_w - margin - radius
        cy = margin + radius

        # Draw circle
        self.camera_preview_main.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill="black",
            outline="white",
            width=3,
            tags="countdown",
        )

        # Draw seconds text
        font_size = int(radius * 0.9)
        self.camera_preview_main.create_text(
            cx,
            cy,
            text=str(self.sequence_delay_remaining),
            fill="white",
            font=("Segoe UI", font_size, "bold"),
            tags="countdown",
        )

        # Make sure countdown is above the video preview
        self.camera_preview_main.tag_raise("countdown")

        # Update status bar text
        self.status_var.set(
            f"Photo {self.sequence_index + 1} of {MAX_CAPTURED_IMAGES} in "
            f"{self.sequence_delay_remaining} seconds..."
        )

        # Schedule next tick
        self.sequence_delay_remaining -= 1
        self.root.after(1000, self._sequence_countdown_tick)


    def _capture_one_in_sequence(self):
        if self.current_preview_pil is None:
            showerror("Error", "No camera frame available to capture.")
            self.status_var.set("No camera frame to capture")
            self.sequence_running = False
            self.is_counting_down = False
            self._update_buttons()
            return

        if self.sequence_index >= MAX_CAPTURED_IMAGES:
            self.sequence_running = False
            self.is_counting_down = False
            self._update_buttons()
            return

        img = self.current_preview_pil.copy().convert("RGB")
        cropped = img.resize((SLOT_W, SLOT_H), Image.LANCZOS)
        slot_idx = self.sequence_index
        self.captured_images[slot_idx] = cropped
        self.sequence_index += 1

        self.status_var.set(f"Captured photo {slot_idx + 1} of {MAX_CAPTURED_IMAGES}")
        self._flash_preview()

        try:
            self.root.bell()
        except Exception:
            pass

        if self.sequence_index >= MAX_CAPTURED_IMAGES:
            self.sequence_running = False
            self.is_counting_down = False
            self.status_var.set("All 8 photos captured! Building layout...")
            self._update_buttons()
            self.show_layout_page()
        else:
            self.sequence_delay_remaining = 1  # 10 seconds between remaining photos
            self.is_counting_down = True
            self._update_buttons()
            self._sequence_countdown_tick()

    def _flash_preview(self):
        if not hasattr(self, "camera_preview_main"):
            return

        self.camera_preview_main.delete("flash")

        canvas_w = max(self.camera_preview_main.winfo_width(), PREVIEW_W)
        canvas_h = max(self.camera_preview_main.winfo_height(), PREVIEW_H)

        self.camera_preview_main.create_rectangle(
            0,
            0,
            canvas_w,
            canvas_h,
            fill="white",
            outline="",
            tags="flash",
        )
        self.camera_preview_main.tag_raise("flash")
        self.root.after(150, lambda: self.camera_preview_main.delete("flash"))

    # ---------------------- CLEAR / RESET -----------------------------
    def clear_photos(self):
        if not any(self.captured_images) and not any(self.current_images):
            self.status_var.set("No photos to clear")
            return

        if not askyesno("Clear Photos", "Are you sure you want to clear all photos?"):
            return

        self._reset_images()
        self.status_var.set("All photos cleared")

    def _reset_images(self):
        self.captured_images = [None] * MAX_CAPTURED_IMAGES
        self.captured_thumbs = [None] * MAX_CAPTURED_IMAGES
        self.current_images = [None] * MAX_FRAME_IMAGES
        self.filtered_cache.clear()
        self.frame_selection_order.clear()
        self.image_widgets = [None] * MAX_FRAME_IMAGES

        if hasattr(self, "canvas"):
            self.canvas.delete("photo")
            self.canvas.delete("delete_btn")
            self.canvas.delete("selection")

        if self.current_page == "layout":
            self._populate_layout_selector()
            self._draw_photos_on_canvas()

        self._update_buttons()

    def _reset_after_save(self):
        """Clear everything and return to landing page after saving."""
        self._reset_images()
        self.shutdown()
        self.show_landing_page()

    # ---------------------- DRAW PHOTOS ON CANVAS --------------------
    def _draw_photos_on_canvas(self):
        if not hasattr(self, "canvas"):
            return

        BORDER = 2
        self.canvas.delete("photo")
        self.canvas.delete("delete_btn")
        self.canvas.delete("selection")
        self.image_widgets = [None] * MAX_FRAME_IMAGES

        for idx in range(MAX_FRAME_IMAGES):
            img = self.current_images[idx]
            base_x, base_y = self.image_positions_display[idx]
            x = base_x - 2
            y = base_y

            # self.canvas.create_rectangle(
            #     x,
            #     y,
            #     x + SLOT_W,
            #     y + SLOT_H,
            #     outline="#dddddd" if img is None else "",
            #     width=1,
            #     tags=("photo", f"photo_{idx}"),
            # )

            if img is not None:
                bordered = ImageOps.expand(img, border=BORDER, fill="white")
                tk_img = ImageTk.PhotoImage(bordered)
                self.image_widgets[idx] = tk_img

                self.canvas.create_image(
                    x,
                    y,
                    anchor="nw",
                    image=tk_img,
                    tags=("photo", f"photo_{idx}")
                )

                x_btn = x + SLOT_W + BORDER - 10
                y_btn = y + 10
                btn_radius = 12

                self.canvas.create_oval(
                    x_btn - btn_radius,
                    y_btn - btn_radius,
                    x_btn + btn_radius,
                    y_btn + btn_radius,
                    fill="#f44336",
                    outline="white",
                    tags=("delete_btn", f"delete_{idx}")
                )
                self.canvas.create_text(
                    x_btn,
                    y_btn,
                    text="✕",
                    fill="white",
                    font=("TkDefaultFont", 10, "bold"),
                    tags=("delete_btn", f"delete_{idx}")
                )
                self.canvas.tag_bind(
                    f"delete_{idx}",
                    "<Button-1>",
                    lambda e, i=idx: self._delete_frame_slot(i)
                )
                
        self.canvas.tag_lower("photo", "background")

    def _delete_frame_slot(self, index: int):
        if 0 <= index < MAX_FRAME_IMAGES:
            if index < len(self.frame_selection_order):
                cap_idx = self.frame_selection_order[index]
                if cap_idx in self.frame_selection_order:
                    self.frame_selection_order.remove(cap_idx)

            self._apply_frame_selection_to_slots()
            self._refresh_layout_selector()
            self._draw_photos_on_canvas()
            self._update_buttons()
            self.status_var.set(f"Cleared frame slot {index + 1}")

    # ---------------------- SAVE OUTPUT -------------------------------
    def save_canvas(self):
        if not askyesno("Save Strip", "Are you sure you want to save this photo strip?"):
            self.status_var.set("Save canceled")
            return

        try:
            GOOGLE_DRIVE_FOLDER.mkdir(parents=True, exist_ok=True)

            fname = f"photo_strip_{time.strftime('%Y%m%d_%H%M%S')}.png"
            file_path = GOOGLE_DRIVE_FOLDER / fname

            canvas_image = Image.new("RGB", (WIDTH, HEIGHT), "white")

            crop_region = (0, 0, WIDTH, HEIGHT)
            if self.background_images:
                idx = self.current_background_index + 2  # file index (2.png, etc.)
                bg_path = BACKGROUND_DIR / f"{idx}.png"
                if bg_path.exists():
                    bg_pillow = Image.open(bg_path).convert("RGB")
                    bg_resized = resize_to_fit(bg_pillow, WIDTH, HEIGHT)
                    bg_width, bg_height = bg_resized.size
                    x_offset = (WIDTH - bg_width) // 2
                    y_offset = (HEIGHT - bg_height) // 2
                    canvas_image.paste(bg_resized, (x_offset, y_offset))
                    crop_region = (
                        x_offset,
                        y_offset,
                        x_offset + bg_width,
                        y_offset + bg_height,
                    )

            for idx, img in enumerate(self.current_images):
                if img is None:
                    continue
                if idx >= len(self.image_positions_save):
                    break

                img_x, img_y = self.image_positions_save[idx]

                aspect = img.width / img.height
                new_height = SLOT_H
                new_width = int(new_height * aspect)
                resized = img.resize((new_width, new_height), Image.LANCZOS)
                resized = ImageOps.expand(resized, border=2, fill="white")
                canvas_image.paste(resized, (img_x, img_y))

            cropped = canvas_image.crop(crop_region)
            cropped.save(file_path)

            self.status_var.set(f"Image saved to {file_path}. Ready for new photos.")
            print(f"Image saved to {file_path}")

            self._reset_after_save()

        except Exception as e:
            showerror("Error", f"Error saving image: {e}")
            self.status_var.set("Error saving image")

    # ---------------------- BUTTON STATE ------------------------------
    def _update_buttons(self):
        # capture page button
        if self.current_page == "capture":
            if self.is_counting_down or self.sequence_running or not self.camera_running:
                self.capture_btn.configure(state="disabled")
            else:
                self.capture_btn.configure(state="normal")

        # layout page save button
        any_layout = any(self.current_images)
        if hasattr(self, "save_btn"):
            self.save_btn.configure(state="normal" if any_layout else "disabled")

    # ---------------------- CLEANUP ----------------------------------
    def shutdown(self):
        self.camera_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None


# -------------------------------------------------------------------
# RUN
# -------------------------------------------------------------------
if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = PhotoboothApp(root)

    def on_close():
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
