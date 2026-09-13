import qrcode

# Paste your actual link inside the quotes below
project_url = "https://drive.google.com/drive/folders/1mDDL81CBMuGMxGRHBg0RU39VzpP8RCli?usp=drive_link"

qr_img = qrcode.make(project_url)
qr_img.save("project_repository_qr.png")
print("QR Code generated successfully!")