from PIL import Image

# Open the images
image1 = Image.open("image1.jpg")
image2 = Image.open("image2.png")

# Create a new image with the same size as the base image
result_image = Image.new("RGBA", image1.size)

# Paste the base image
result_image.paste(image1, (0, 0))

# Paste the second image on top
result_image.paste(image2, (0, 0), image2)

# Save the result
result_image.save("stacked_image.png")