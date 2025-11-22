import os
import cv2
import threading
import tkinter as tk
from tkinter import filedialog
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
MAX_IMAGES = 4

BASE_DIR = Path(__file__).resolve().parent
BACKGROUND_DIR = BASE_DIR / "frame_designs"      # folder containing 1.png, 2.png, ...
GOOGLE_DRIVE_FOLDER = BASE_DIR / "photos"

SLOT_W = 354   # width of one white box
SLOT_H = 236   # height of one white box


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


def create_photo_strip_positions() -> List[Tuple[int, int]]:
    """Fixed positions for up to 4 images on the background."""
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

        # Global style tweaks
        style = ttk.Style()
        style.configure("TFrame", padding=10)
        style.configure("Left.TFrame", padding=(12, 12))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=(8, 4))

        # Data
        self.image_positions = create_photo_strip_positions()
        self.current_images = [None] * MAX_IMAGES   # list of PIL images or None
        self.image_widgets = [None] * MAX_IMAGES    # keep PhotoImage refs per slot
        self.filtered_cache = {}
        self.background_images = []     # large ImageTk
        self.background_thumbs = []     # small ImageTk
        self.current_background_index = 0
        self.selected_slot = None       # which slot is selected for overwrite

        # Camera
        self.cap = None
        self.camera_running = False
        self.current_preview_pil = None
        self.current_preview_tk = None

        # Status
        self.status_var = tk.StringVar(value="Ready")

        # UI
        self._build_ui()
        self.load_background_images()
        self.display_background()
        self._update_buttons()

        # Shortcuts
        self.root.bind("<Control-s>", lambda e: self.save_canvas())
        self.root.bind("<space>", lambda e: self.capture_photo())

    # ---------------------- UI LAYOUT --------------------------------
    def _build_ui(self):
        # Left toolbar
        self.left_frame = ttk.Frame(self.root, style="Left.TFrame")
        self.left_frame.pack(side="left", fill="y")

        # Title bar in left sidebar
        title_label = ttk.Label(
            self.left_frame,
            text="📸 Photobooth",
            style="Title.TLabel",
        )
        title_label.pack(pady=(5, 15))

        # Camera preview section
        preview_label = ttk.Label(
            self.left_frame,
            text="Camera Preview",
            style="Section.TLabel",
        )
        preview_label.pack(pady=(0, 4))

        preview_border = ttk.Frame(self.left_frame, bootstyle="secondary")
        preview_border.pack(padx=5, pady=(0, 10), fill="x")

        self.camera_preview = ttk.Label(preview_border)
        self.camera_preview.pack(padx=4, pady=4)

        # Controls
        controls_frame = ttk.Labelframe(
            self.left_frame,
            text="Controls",
            bootstyle="info",
        )
        controls_frame.pack(padx=5, pady=10, fill="x")

        self.start_cam_btn = ttk.Button(
            controls_frame,
            text="▶ Start Camera",
            bootstyle="primary",
            command=self.start_camera,
        )
        self.start_cam_btn.pack(pady=3, fill="x")

        self.capture_btn = ttk.Button(
            controls_frame,
            text="📷 Capture Photo",
            bootstyle="success",
            command=self.capture_photo,
        )
        self.capture_btn.pack(pady=3, fill="x")

        self.clear_btn = ttk.Button(
            controls_frame,
            text="🧹 Clear Photos",
            bootstyle="secondary",
            command=self.clear_photos,
        )
        self.clear_btn.pack(pady=3, fill="x")

        self.save_btn = ttk.Button(
            controls_frame,
            text="💾 Save Strip",
            bootstyle="success-outline",
            command=self.save_canvas,
        )
        self.save_btn.pack(pady=(8, 3), fill="x")

        # Status bar
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            bootstyle="secondary-inverse",
        )
        status_bar.pack(side="bottom", fill="x")

        # Main frame (canvas + background bar)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side="right", fill="both", expand=True)

        # Use GRID inside main_frame so canvas and bar share vertical space
        self.main_frame.rowconfigure(0, weight=1)   # canvas row grows/shrinks
        self.main_frame.rowconfigure(1, weight=0)   # separator
        self.main_frame.rowconfigure(2, weight=0)   # bar row fixed
        self.main_frame.columnconfigure(0, weight=1)

        # Canvas for big background + photos
        self.canvas = tk.Canvas(self.main_frame, bg="white")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Separator above background bar
        sep = ttk.Separator(self.main_frame, orient="horizontal")
        sep.grid(row=1, column=0, sticky="ew")

        # Bottom bar for background thumbnails
        self.bg_bar = ttk.Frame(self.main_frame, height=140)
        self.bg_bar.grid(row=2, column=0, sticky="ew")
        self.bg_bar.grid_propagate(False)   # keep the 140px height

    # ---------------------- BACKGROUNDS -------------------------------
    def load_background_images(self):
        """Load full-size and thumbnail versions of each background."""
        try:
            self.background_images.clear()
            self.background_thumbs.clear()

            for i in range(1, 10):
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
        """Create clickable thumbnails at bottom."""
        # Clear old widgets
        for child in self.bg_bar.winfo_children():
            child.destroy()

        for idx, thumb in enumerate(self.background_thumbs):
            frame = ttk.Frame(self.bg_bar, padding=2)
            frame.pack(side="left", padx=4, pady=4)

            lbl = ttk.Label(frame, image=thumb)
            lbl.image = thumb  # keep ref
            lbl.pack()

            # Click selects background
            lbl.bind("<Button-1>", lambda e, i=idx: self.set_background(i))

            lbl.bind(
                "<Enter>",
                lambda e, f=frame: f.configure(bootstyle="info")
            )
            lbl.bind(
                "<Leave>",
                lambda e: self._highlight_selected_background()
            )

        # Apply initial selected highlight
        self._highlight_selected_background()


    def _highlight_selected_background(self):
        for i, child in enumerate(self.bg_bar.winfo_children()):
            bootstyle = "primary" if i == self.current_background_index else "secondary"
            child.configure(bootstyle=bootstyle)

    def set_background(self, index):
        self.current_background_index = index
        self.display_background()
        self._highlight_selected_background()
        self.status_var.set(f"Background set to #{index + 1}")

    def display_background(self):
        if not self.background_images:
            return

        self.canvas.delete("background")
        bg_image = self.background_images[self.current_background_index]
        x_offset = (WIDTH - bg_image.width()) // 2
        y_offset = (HEIGHT - bg_image.height()) // 2
        bg_id = self.canvas.create_image(
            x_offset, y_offset, anchor="nw", image=bg_image, tags="background"
        )
        self.canvas.tag_lower(bg_id)
        self.root.update_idletasks()

    # ---------------------- CAMERA -----------------------------------
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
        img.thumbnail((400, 300))
        self.current_preview_pil = img
        self.current_preview_tk = ImageTk.PhotoImage(img)

        self.camera_preview.configure(image=self.current_preview_tk)
        self.camera_preview.image = self.current_preview_tk

        self.root.after(30, self.update_camera_frame)

    def capture_photo(self):
        """Capture from live preview, crop to slot aspect ratio, and store."""
        if self.current_preview_pil is None:
            showerror("Error", "No camera frame available to capture.")
            self.status_var.set("No camera frame to capture")
            return

        # Work on a copy of the preview frame
        img = self.current_preview_pil.copy().convert("RGB")
        w, h = img.size

        slot_ratio = SLOT_W / SLOT_H
        preview_ratio = w / h

        # Center-crop to match slot aspect ratio
        if preview_ratio > slot_ratio:
            new_w = int(h * slot_ratio)
            left = (w - new_w) // 2
            box = (left, 0, left + new_w, h)
        else:
            new_h = int(w / slot_ratio)
            top = (h - new_h) // 2
            box = (0, top, w, top + new_h)

        cropped = img.crop(box)
        cropped = cropped.resize((SLOT_W, SLOT_H), Image.LANCZOS)

        # Decide which slot to use:
        # 1) If a slot is selected, overwrite it.
        # 2) Else, first empty slot.
        slot_idx = None
        if self.selected_slot is not None:
            slot_idx = self.selected_slot
        else:
            for i in range(MAX_IMAGES):
                if self.current_images[i] is None:
                    slot_idx = i
                    break

        if slot_idx is None:
            showerror(
                "Error",
                f"All {MAX_IMAGES} photo slots are full.\n"
                f"Click the ✕ on a photo or click a photo to select it, then capture to overwrite."
            )
            self.status_var.set("All slots full")
            return

        # Store already-cropped, slot-sized image
        self.current_images[slot_idx] = cropped
        self.filtered_cache[slot_idx] = {"None": cropped}
        self._draw_photos_on_canvas()
        self._update_buttons()
        self.status_var.set(f"Captured photo into slot {slot_idx + 1}")

    def clear_photos(self):
        if not any(self.current_images):
            self.status_var.set("No photos to clear")
            return

        if not askyesno("Clear Photos", "Are you sure you want to clear all photos?"):
            return

        self.current_images = [None] * MAX_IMAGES
        self.filtered_cache.clear()
        self.selected_slot = None
        self.canvas.delete("photo")
        self.canvas.delete("delete_btn")
        self.canvas.delete("selection")
        self.image_widgets = [None] * MAX_IMAGES
        self._update_buttons()
        self.status_var.set("All photos cleared")

    # ---------------------- SLOT HELPERS ------------------------------
    def delete_photo(self, index):
        """Clear a single slot."""
        if 0 <= index < MAX_IMAGES:
            self.current_images[index] = None
            self.filtered_cache.pop(index, None)
            if self.selected_slot == index:
                self.selected_slot = None
            self._draw_photos_on_canvas()
            self._update_buttons()
            self.status_var.set(f"Deleted photo from slot {index + 1}")

    def select_photo(self, index):
        """Select a slot for overwrite on next capture."""
        if 0 <= index < MAX_IMAGES and self.current_images[index] is not None:
            self.selected_slot = index
            self.status_var.set(f"Selected slot {index + 1} for overwrite")
        else:
            self.selected_slot = None
            self.status_var.set("Selection cleared")
        self._draw_photos_on_canvas()

    # ---------------------- DRAW PHOTOS -------------------------------
    def _draw_photos_on_canvas(self):
        BORDER = 2  # white border thickness

        # Remove old photo items and buttons & selection overlay
        self.canvas.delete("photo")
        self.canvas.delete("delete_btn")
        self.canvas.delete("selection")
        self.image_widgets = [None] * MAX_IMAGES

        for idx in range(MAX_IMAGES):
            img = self.current_images[idx]
            if img is None:
                continue

            bordered = ImageOps.expand(img, border=BORDER, fill="white")
            tk_img = ImageTk.PhotoImage(bordered)
            self.image_widgets[idx] = tk_img  # keep ref

            base_x, base_y = self.image_positions[idx]
            x = base_x - 2
            y = base_y

            # Draw the photo
            self.canvas.create_image(
                x,
                y,
                anchor="nw",
                image=tk_img,
                tags=("photo", f"photo_{idx}")
            )

            # Bind click on photo to select it for overwrite
            self.canvas.tag_bind(
                f"photo_{idx}",
                "<Button-1>",
                lambda e, i=idx: self.select_photo(i)
            )

            # Draw a small circular 'X' button in upper-right corner of the slot
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
                lambda e, i=idx: self.delete_photo(i)
            )

        # Draw selection highlight if any slot is selected
        if self.selected_slot is not None and self.current_images[self.selected_slot] is not None:
            base_x, base_y = self.image_positions[self.selected_slot]
            x = base_x - 2
            y = base_y

            # outer glow
            self.canvas.create_rectangle(
                x - 6,
                y - 6,
                x + SLOT_W + 6,
                y + SLOT_H + 6,
                outline="lightblue",
                width=5,
                tags="selection"
            )
            # inner border
            self.canvas.create_rectangle(
                x - 2,
                y - 2,
                x + SLOT_W + 2,
                y + SLOT_H + 2,
                outline="dodgerblue",
                width=2,
                tags="selection"
            )

    # ---------------------- SAVE OUTPUT -------------------------------
    def save_canvas(self):
        try:
            # Ensure the Google Drive folder exists
            GOOGLE_DRIVE_FOLDER.mkdir(parents=True, exist_ok=True)

            # Auto-generate a unique filename, e.g. photo_strip_20251117_142355.png
            fname = f"photo_strip_{time.strftime('%Y%m%d_%H%M%S')}.png"
            file_path = GOOGLE_DRIVE_FOLDER / fname

            canvas_image = Image.new("RGB", (WIDTH, HEIGHT), "white")

            # Background
            crop_region = (0, 0, WIDTH, HEIGHT)
            if self.background_images:
                idx = self.current_background_index + 2  # file index (2.png, etc.) – keep your original logic
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

            # Photos
            for idx, img in enumerate(self.current_images):
                if img is None:
                    continue
                if idx >= len(self.image_positions):
                    break
                img_x, img_y = self.image_positions[idx]
                aspect = img.width / img.height
                new_height = 236
                new_width = int(new_height * aspect)
                resized = img.resize((new_width, new_height), Image.LANCZOS)
                resized = ImageOps.expand(resized, border=2, fill="white")
                canvas_image.paste(resized, (img_x, img_y))

            cropped = canvas_image.crop(crop_region)
            cropped.save(file_path)
            self.status_var.set(f"Image saved to {file_path}")
            print(f"Image saved to {file_path}")  # optional console log

        except Exception as e:
            showerror("Error", f"Error saving image: {e}")
            self.status_var.set("Error saving image")

    # ---------------------- BUTTON STATE ------------------------------
    def _update_buttons(self):
        any_photo = any(self.current_images)
        self.clear_btn.configure(state="normal" if any_photo else "disabled")
        self.save_btn.configure(state="normal" if any_photo else "disabled")
        self.capture_btn.configure(state="normal" if self.camera_running else "disabled")

    # ---------------------- CLEANUP ----------------------------------
    def shutdown(self):
        self.camera_running = False
        if self.cap is not None:
            self.cap.release()


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
