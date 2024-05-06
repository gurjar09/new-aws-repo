import qrcode

# Define the data you want to encode in the QR code
data = "http://3.25.106.135:8000/candidateform/?ref=EMTA2803"

# Create QR code instance
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)

# Add data to the QR code
qr.add_data(data)
qr.make(fit=True)

# Create an image from the QR code
img = qr.make_image(fill_color="skyblue", back_color="black")

# Save the image
img.save("qrcode.png")

# Display the image
img.show()
