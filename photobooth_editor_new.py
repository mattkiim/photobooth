import ttkbootstrap as ttk
from tkinter import filedialog
from tkinter.messagebox import showerror
from PIL import Image, ImageOps, ImageTk, ImageFilter
import os
import threading

# Window setup
root = ttk.Window(themename='cosmo')
root.title('Photobooth Editor')
root.geometry("1100x1000")
root.resizable(True, True)
placeholder = ttk.Label(root, text="Photobooth Editor", font=("Helvetica", 16))
placeholder.pack(fill="both", expand=True)

# Constants
WIDTH = 1000
HEIGHT = 1000
MAX_IMAGES = 4

# Globals
current_images = []  # List to store selected images
image_positions = [(177, 256), (177 + 354 + 6, 256), (177, 256 + 236 + 7), (177 + 354 + 6, 256 + 236 + 7)]
image_widgets = []  # List to store canvas image objects
filtered_cache = {}  # Cache for filtered images
background_images = []  # Pre-loaded background images
current_background_index = 0  # Current background index

# Directory for background images
BACKGROUND_DIR = "frame_designs/"  # Replace with your directory path

# Left frame for tools
left_frame = ttk.Frame(root, width=200, height=600)
left_frame.pack(side="left", fill="y")

canvas = ttk.Canvas(root, width=WIDTH, height=HEIGHT, bg="white")
canvas.pack()
canvas.update_idletasks()



def load_background_images():
    global background_images, BACKGROUND_DIR
    try:
        files = [os.path.join(BACKGROUND_DIR, f"{i}.png") for i in range(2, 10)]
        for file in files:
            with Image.open(file) as img:
                img = resize_to_fit(img, WIDTH, HEIGHT)
                background_images.append(ImageTk.PhotoImage(img))
                root.update_idletasks()
                root.update()
    except Exception as e:
        showerror("Error", f"Error loading background images: {e}")



# Resize background image to fit the canvas while maintaining aspect ratio
def resize_to_fit(image, target_width, target_height):
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


# Display background on canvas
def display_background():
    global current_background_index, background_images
    if not background_images:
        load_background_images()

    canvas.delete("background")
    bg_image = background_images[current_background_index]
    x_offset = (WIDTH - bg_image.width()) // 2
    y_offset = (HEIGHT - bg_image.height()) // 2
    background_id = canvas.create_image(x_offset, y_offset, anchor="nw", image=bg_image, tags="background")
    canvas.tag_lower(background_id)
    root.update_idletasks()
    root.update()



# Cycle background images only if the click is not on an image
def cycle_background(event=None):
    print("working")
    item = canvas.find_withtag("current")
    if "image_item" in canvas.gettags(item):
        return  # Don't change the background if clicking on an image
    global current_background_index
    if not background_images:
        return
    current_background_index = (current_background_index + 1) % len(background_images)
    display_background()


# Open images with threading
def open_images():
    threading.Thread(target=_open_images_worker).start()


def _open_images_worker():
    global current_images, current_filters, image_widgets, filtered_cache
    try:
        file_paths = filedialog.askopenfilenames(
            title="Select Up to 4 Images",
            filetypes=[
                ("JPG Files", "*.jpg"),
                ("JPEG Files", "*.jpeg"),
                ("PNG Files", "*.png"),
            ]
        )
        if len(file_paths) > MAX_IMAGES:
            showerror("Error", f"Please select up to {MAX_IMAGES} images.")
            return

        current_images.clear()
        image_widgets.clear()
        filtered_cache.clear()

        for i, file_path in enumerate(file_paths):
            img = Image.open(file_path).convert("RGB")
            img.thumbnail((300, 300), Image.LANCZOS)
            current_images.append(img)
            filtered_cache[i] = {"None": img}

            img_display, x, y = display_image_on_canvas(img, *image_positions[i])
            image_widget = canvas.create_image(x, y, anchor="nw", image=img_display, tags="image_item")
            image_widgets.append((image_widget, img_display))
    except Exception as e:
        showerror("Error", f"Error opening images: {e}")



# Helper function to display image
def display_image_on_canvas(image, x, y):
    aspect_ratio = image.width / image.height
    new_height = 236
    new_width = int(new_height * aspect_ratio)
    resized_image = image.resize((new_width, new_height))
    resized_image = ImageOps.expand(resized_image, border=2, fill="white")

    root.update_idletasks()
    root.update()
    return ImageTk.PhotoImage(resized_image), x, y


# Load backgrounds and display the first one
# load_background_images()
display_background()

canvas.bind("<Button-1>", cycle_background)

# Buttons
open_button = ttk.Button(left_frame, text="Open Images", bootstyle="primary", command=open_images)
open_button.pack(pady=5)

root.mainloop()
