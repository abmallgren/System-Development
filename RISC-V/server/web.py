from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

# --- CONFIGURE THE DIRECTORIES ---
TAP0_IP = "192.168.1.100"      # Your Windows tap0 interface static IP
TFTP_ROOT = r"..\Web" 

class CustomFileHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Force Python to map all incoming web requests straight to your tftp folder
        return os.path.join(TFTP_ROOT, os.path.basename(path))

if __name__ == '__main__':
    
    server = HTTPServer((TAP0_IP, 80), CustomFileHandler)
    print(f"Python HTTP Server listening on {TAP0_IP}:80 (Serving files from {TFTP_ROOT})...")
    server.serve_forever()
