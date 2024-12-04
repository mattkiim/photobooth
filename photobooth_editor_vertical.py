import ttkbootstrap as ttk
from tkinter import filedialog
from tkinter.messagebox import showerror
from PIL import Image, ImageOps, ImageTk, ImageFilter, ImageDraw
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
image_positions = [(260, 177), (260 + 240 + 7 , 177), (260, 177 + 360), (260 + 240 + 7, 177 + 360)]

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
    # resized_image = resized_image.rotate(90, expand=True)
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

display_height = 236 # 354
rotate = True

# Helper function to display image
def display_image_on_canvas(image, x, y):
    aspect_ratio = image.width / image.height
    new_height = display_height
    new_width = int(new_height * aspect_ratio)
    resized_image = image.resize((new_width, new_height))
    resized_image = ImageOps.expand(resized_image, border=2, fill="white")
    
    if rotate:
        resized_image = resized_image.rotate(90, expand=True)


    root.update_idletasks()
    root.update()
    return ImageTk.PhotoImage(resized_image), x, y


def save_canvas():
    try:
        # Ask user for save location and filename
        file_path = filedialog.asksaveasfilename(
            title="Save Image",
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png"), ("JPEG Files", "*.jpeg"), ("All Files", "*.*")]
        )
        if not file_path:
            return  # User canceled save dialog

        # Create a blank image with the size of the canvas
        canvas_image = Image.new("RGB", (WIDTH, HEIGHT), "white")

        # Draw background if available
        if background_images:
            bg_image = background_images[current_background_index]
            bg_pillow = Image.open(f"{BACKGROUND_DIR}/{current_background_index + 2}.png")
            bg_resized = resize_to_fit(bg_pillow, WIDTH, HEIGHT)

            # Calculate offsets for centering the background
            bg_width, bg_height = bg_resized.size
            x_offset = (WIDTH - bg_width) // 2
            y_offset = (HEIGHT - bg_height) // 2

            # Paste the resized background
            canvas_image.paste(bg_resized, (x_offset, y_offset))

            # Crop region for final output
            crop_region = (x_offset, y_offset, x_offset + bg_width, y_offset + bg_height)

        # Draw each resized image onto the canvas
        for idx, (img_widget, img_display) in enumerate(image_widgets):
            img_x, img_y = image_positions[idx]

            # Resize the original image to match the displayed size
            aspect_ratio = current_images[idx].width / current_images[idx].height
            new_height = display_height
            new_width = int(new_height * aspect_ratio)
            resized_image = current_images[idx].resize((new_width, new_height), Image.LANCZOS)
            resized_image = ImageOps.expand(resized_image, border=2, fill="white") # toggle

            if rotate:
                resized_image = resized_image.rotate(90, expand=True) # Toggle


            # Paste the resized image onto the canvas
            canvas_image.paste(resized_image, (img_x, img_y))

        # Crop the final image to the background region
        cropped_image = canvas_image.crop(crop_region)

        # Save the cropped image
        cropped_image.save(file_path)
        print(f"Image saved to {file_path}")
    except Exception as e:
        showerror("Error", f"Error saving image: {e}")


# Load backgrounds and display the first one
# load_background_images()
display_background()

canvas.bind("<Button-1>", cycle_background)

# Buttons
open_button = ttk.Button(left_frame, text="Open Images", bootstyle="primary", command=open_images)
open_button.pack(pady=5)

save_button = ttk.Button(left_frame, text="Save Image", bootstyle="success", command=save_canvas)
save_button.pack(pady=5)

root.mainloop()
