import ttkbootstrap as ttk
from tkinter import filedialog
from tkinter.messagebox import showerror, askyesno
from tkinter import colorchooser
from PIL import Image, ImageOps, ImageTk, ImageFilter, ImageGrab

#window code
root = ttk.Window(themename = 'cosmo')
root.title('Photobooth Editor')
root.geometry("900x800+300+210")
root.resizable(0, 0)

#global variables - ** DO NOT MODIFY!**
WIDTH = 750
HEIGHT = 560
file_path = ""
pen_size = 3
pen_color = "black"

left_frame = ttk.Frame(root, width=200, height=600)
left_frame.pack(side="left", fill="y")

canvas = ttk.Canvas(root, width=WIDTH, height=HEIGHT)
canvas.pack()

filter_label = ttk.Label(left_frame, text="Select Filter:", background="white")
filter_label.pack(padx=0, pady=2)

image_filters = ["Contour", "Black and White", "Blur", "Detail", "Emboss", "Edge Enhance", "Sharpen", "Smooth"]

filter_combobox = ttk.Combobox(left_frame, values=image_filters, width=15)
filter_combobox.pack(padx=10, pady=5)\

image_icon = ttk.PhotoImage(file = 'add.png').subsample(12, 12)
color_icon = ttk.PhotoImage(file = 'color.png').subsample(12, 12)
save_icon = ttk.PhotoImage(file = 'saved.png').subsample(12, 12)

def open_image():
    global file_path
    file_path = filedialog.askopenfilename(title="Open Image File", filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.gif;*.bmp")])
    if file_path:
        global image, photo_image
        image = Image.open(file_path)
        new_width = int((WIDTH / 2))
        image = image.resize((new_width, HEIGHT), Image.LANCZOS)
            
        image = ImageTk.PhotoImage(image)
        canvas.create_image(0, 0, anchor="nw", image=image)

# function for applying filters to the opened image file
def apply_filter(filter):
    global image, photo_image
        # apply the filter to the original image
    image = Image.open(file_path)
    if filter == "Black and White":
            image = ImageOps.grayscale(image)
    elif filter == "Blur":
        image = image.filter(ImageFilter.BLUR)
    elif filter == "Sharpen":
        image = image.filter(ImageFilter.SHARPEN)
    elif filter == "Smooth":
        image = image.filter(ImageFilter.SMOOTH)
    elif filter == "Emboss":
        image = image.filter(ImageFilter.EMBOSS)
    elif filter == "Detail":
        image = image.filter(ImageFilter.DETAIL)
    elif filter == "Edge Enhance":
        image = image.filter(ImageFilter.EDGE_ENHANCE)
    elif filter == "Contour":
        image = image.filter(ImageFilter.CONTOUR)

        new_width = int((WIDTH / 2))
        rotated_image = rotated_image.resize((new_width, HEIGHT), Image.LANCZOS)

        photo_image = ImageTk.PhotoImage(rotated_image)
        canvas.create_image(0, 0, anchor="nw", image=photo_image)

filter_combobox.bind("<<ComboboxSelected>>", lambda event: apply_filter(filter_combobox.get()))

# the function for saving an image
def save_image():
    global file_path, is_flipped, rotation_angle
    if file_path:
        # create a new PIL Image object from the canvas
        image = ImageGrab.grab(bbox=(canvas.winfo_rootx(), canvas.winfo_rooty(), canvas.winfo_rootx() + canvas.winfo_width(), canvas.winfo_rooty() + canvas.winfo_height()))
        # check if the image has been flipped or rotated
        if is_flipped or rotation_angle % 360 != 0:
            # Resize and rotate the image
            new_width = int((WIDTH / 2))
            image = image.resize((new_width, HEIGHT), Image.LANCZOS)
            if is_flipped:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
            if rotation_angle % 360 != 0:
                image = image.rotate(rotation_angle)
            # update the file path to include the modifications in the file name
            file_path = file_path.split(".")[0] + "_mod.jpg"
        # apply any filters to the image before saving
        filter = filter_combobox.get()
        if filter:
            if filter == "Black and White":
                image = ImageOps.grayscale(image)
            elif filter == "Blur":
                image = image.filter(ImageFilter.BLUR)
            elif filter == "Sharpen":
                image = image.filter(ImageFilter.SHARPEN)
            elif filter == "Smooth":
                image = image.filter(ImageFilter.SMOOTH)
            elif filter == "Emboss":
                image = image.filter(ImageFilter.EMBOSS)
            elif filter == "Detail":
                image = image.filter(ImageFilter.DETAIL)
            elif filter == "Edge Enhance":
                image = image.filter(ImageFilter.EDGE_ENHANCE)
            elif filter == "Contour":
                image = image.filter(ImageFilter.CONTOUR)
            # update the file path to include the filter in the file name
            file_path = file_path.split(".")[0] + "_" + filter.lower().replace(" ", "_") + ".jpg"
        # open file dialog to select save location and file type
        file_path = filedialog.asksaveasfilename(defaultextension=".jpg")
        if file_path:
            if askyesno(title='Save Image', message='Do you want to save this image?'):
                # save the image to a file
                image.save(f"~/Downloads/{file_path}")


image_button = ttk.Button(left_frame, image=image_icon, bootstyle="light", command=open_image)
image_button.pack(pady=5)

color_button = ttk.Button(left_frame, image=color_icon, bootstyle="light")
color_button.pack(pady=5)

save_button = ttk.Button(left_frame, image=save_icon, bootstyle="light", command=save_image)
save_button.pack(pady=5)

root.mainloop()

