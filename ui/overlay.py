import socket
import struct
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np

HOST = 'localhost'
PORT = 9999

# Connect to server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
print("Connected to webcam server")

root = tk.Tk()
root.title("Webcam Stream (Client)")

label = tk.Label(root)
label.pack()

def update_frame():
    # Receive frame length
    length_bytes = s.recv(4)
    if not length_bytes:
        root.after(10, update_frame)
        return
    length = struct.unpack('!I', length_bytes)[0]

    # Receive frame
    data = b''
    while len(data) < length:
        packet = s.recv(length - len(data))
        if not packet:
            break
        data += packet

    if data:
        # Decode JPEG
        nparr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Display in Tkinter
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(img)
        label.imgtk = imgtk
        label.configure(image=imgtk)

    # Repeat after 30ms
    root.after(30, update_frame)

update_frame()
root.mainloop()