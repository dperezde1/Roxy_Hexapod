from picamera2 import Picamera2
from http.server import HTTPServer, BaseHTTPRequestHandler
import io, threading

cam = Picamera2()
cam.configure(cam.create_video_configuration(main={"size": (640, 480)}))
cam.start()

class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        try:
            while True:
                buf = io.BytesIO()
                cam.capture_file(buf, format='jpeg')
                self.wfile.write(b'--frame\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                self.wfile.write(buf.getvalue())
                self.wfile.write(b'\r\n')
        except (BrokenPipeError, ConnectionResetError):
            pass

print("Camera streaming on http://0.0.0.0:8080")
HTTPServer(('0.0.0.0', 8080), MJPEGHandler).serve_forever()