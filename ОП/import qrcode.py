import qrcode
qr = qrcode.make("Привет, мир!")
qr.save("my_qrcode.png")

print("QR-код сохранен как 'my_qrcode.png'")