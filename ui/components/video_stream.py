import socket
import struct
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk


class VideoStream:
    def __init__(self, parent, host, port):
        self.parent = parent
        self.host = host
        self.port = port

        self.label = tk.Label(parent)
        self.label.pack()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))

    def start(self, root):
        self.root = root
        self.update_frame()

    def update_frame(self):
        try:
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                self.root.after(30, self.update_frame)
                return

            length = struct.unpack("!I", length_bytes)[0]

            data = b""
            while len(data) < length:
                packet = self.socket.recv(length - len(data))
                if not packet:
                    break
                data += packet

            if data:
                nparr = np.frombuffer(data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(img)

                self.label.imgtk = imgtk
                self.label.configure(image=imgtk)

        except Exception:
            pass

        self.root.after(30, self.update_frame)