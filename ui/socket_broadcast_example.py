import socket
import cv2
import struct

HOST = 'localhost'  # broadcast locally
PORT = 9999

# Open the webcam
cap = cv2.VideoCapture(0)

# Set up socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
print(f"Waiting for client to connect at {HOST}:{PORT}...")
conn, addr = s.accept()
print(f"Client connected: {addr}")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Encode frame as JPEG
        _, jpeg = cv2.imencode('.jpg', frame)
        data = jpeg.tobytes()
        # Send frame length first
        conn.sendall(struct.pack('!I', len(data)))
        conn.sendall(data)
except KeyboardInterrupt:
    print("Closing...")
finally:
    cap.release()
    conn.close()
    s.close()