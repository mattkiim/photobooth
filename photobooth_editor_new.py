import ttkbootstrap as ttk
from tkinter import filedialog, colorchooser
from tkinter.messagebox import showerror, askyesno
from PIL import Image, ImageOps, ImageTk, ImageFilter, ImageGrab

# Window setup
root = ttk.Window(themename='cosmo')
root.title('Photobooth Editor')
root.geometry("900x800+300+210")
root.resizable(0, 0)

# Constants
WIDTH = 750
HEIGHT = 560
pen_size = 3
pen_color = "black"

# Globals for current image
current_image = None
display_image = None

# Left frame for tools
left_frame = ttk.Frame(root, width=200, height=600)
left_frame.pack(side="left", fill="y")

canvas = ttk.Canvas(root, width=WIDTH, height=HEIGHT)
canvas.pack()

# Filter dropdown
filter_label = ttk.Label(left_frame, text="Select Filter:", background="white")
filter_label.pack(padx=0, pady=2)

image_filters = ["Contour", "Black and White", "Blur", "Detail", "Emboss", "Edge Enhance", "Sharpen", "Smooth"]
filter_combobox = ttk.Combobox(left_frame, values=image_filters, width=15)
filter_combobox.pack(padx=10, pady=5)

# Icons for buttons
try:
    image_icon = ttk.PhotoImage(file='add.png').subsample(12, 12)
    color_icon = ttk.PhotoImage(file='color.png').subsample(12, 12)
    save_icon = ttk.PhotoImage(file='saved.png').subsample(12, 12)
except Exception as e:
    showerror("Error", f"Error loading icons: {e}")

# Helper to display the image on the canvas
def display_on_canvas(image):
    global display_image
    canvas.delete("all")
    resized_image = image.copy()
    aspect_ratio = image.width / image.height
    new_height = HEIGHT
    new_width = int(HEIGHT * aspect_ratio)
    if new_width > WIDTH:
        new_width = WIDTH
        new_height = int(WIDTH / aspect_ratio)
    resized_image = resized_image.resize((new_width, new_height), Image.LANCZOS)
    display_image = ImageTk.PhotoImage(resized_image)
    canvas.create_image(WIDTH // 2, HEIGHT // 2, anchor="center", image=display_image)

# Open image
def open_image():
    global current_image
    file_path = filedialog.askopenfilename(
        title="Open Image File",
        filetypes=[
            ("All Image Files", "*.jpg;*.jpeg;*.png;*.gif;*.bmp"),  # Group of all supported formats
            ("JPEG Files", "*.jpg;*.jpeg"),  
            ("JPEG Files", "*.jpeg"),                        # Explicitly list JPEG
            ("PNG Files", "*.png"),                                # Explicitly list PNG
            ("GIF Files", "*.gif"),                                # Explicitly list GIF
            ("Bitmap Files", "*.bmp"),                             # Explicitly list BMP
            ("All Files", "*.*")                                  # Allow all file types
        ]
    )
    if file_path:
        try:
            current_image = Image.open(file_path)
            display_on_canvas(current_image)
        except Exception as e:
            showerror("Error", f"Error opening image: {e}")

# Apply filter
def apply_filter(filter_name):
    global current_image
    if not current_image:
        showerror("Error", "No image loaded!")
        return
    try:
        filtered_image = current_image.copy()
        if filter_name == "Black and White":
            filtered_image = ImageOps.grayscale(filtered_image)
        elif filter_name == "Blur":
            filtered_image = filtered_image.filter(ImageFilter.BLUR)
        elif filter_name == "Sharpen":
            filtered_image = filtered_image.filter(ImageFilter.SHARPEN)
        elif filter_name == "Smooth":
            filtered_image = filtered_image.filter(ImageFilter.SMOOTH)
        elif filter_name == "Emboss":
            filtered_image = filtered_image.filter(ImageFilter.EMBOSS)
        elif filter_name == "Detail":
            filtered_image = filtered_image.filter(ImageFilter.DETAIL)
        elif filter_name == "Edge Enhance":
            filtered_image = filtered_image.filter(ImageFilter.EDGE_ENHANCE)
        elif filter_name == "Contour":
            filtered_image = filtered_image.filter(ImageFilter.CONTOUR)
        display_on_canvas(filtered_image)
    except Exception as e:
        showerror("Error", f"Error applying filter: {e}")

filter_combobox.bind("<<ComboboxSelected>>", lambda event: apply_filter(filter_combobox.get()))

# Save image
def save_image():
    global current_image
    if not current_image:
        showerror("Error", "No image to save!")
        return
    try:
        save_path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if save_path:
            if askyesno(title='Save Image', message='Do you want to save this image?'):
                current_image.save(save_path)
    except Exception as e:
        showerror("Error", f"Error saving image: {e}")

# Buttons for operations
image_button = ttk.Button(left_frame, image=image_icon, bootstyle="light", command=open_image)
image_button.pack(pady=5)

color_button = ttk.Button(left_frame, image=color_icon, bootstyle="light")
color_button.pack(pady=5)

save_button = ttk.Button(left_frame, image=save_icon, bootstyle="light", command=save_image)
save_button.pack(pady=5)

root.mainloop()
