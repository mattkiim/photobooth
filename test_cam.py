import cv2

# Open the camera (usually index 0 for the first connected device)
cap = cv2.VideoCapture(0)  # Replace 0 with the correct device index if needed

if not cap.isOpened():
    print("Unable to access the camera. Check your connection.")
    exit()

print("Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame. Exiting.")
        break

    # Display the frame
    cv2.imshow('Sony Camera Live View', frame)

    # Exit loop on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
