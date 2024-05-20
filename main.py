import json
import logging
import mimetypes
import socket
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread

BASE_DIR = Path(__file__).parent
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 3000

SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 5000
BUFFER_SIZE = 1024


class HomeworkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        file_path = BASE_DIR.joinpath(parsed_url.path.lstrip("/"))

        if parsed_url.path == "/":
            self.send_html_file("index.html")
        elif parsed_url.path == "/message":
            self.send_html_file("message.html")
        else:
            if file_path.exists():
                self.send_assets_file(file_path)
            else:
                self.send_html_file("error.html", 404)

    def do_POST(self):
        size = int(self.headers.get("Content-Length"))
        data = self.rfile.read(size)

        socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_client.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        socket_client.close()

        self.send_response(302)
        self.send_header("Location", "/message")
        self.end_headers()

    def send_html_file(self, filename, status=200):
        file_path = BASE_DIR / filename
        if file_path.exists():
            self.send_response(status)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open(file_path, "rb") as file:
                self.wfile.write(file.read())
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def send_assets_file(self, filename, status=200):
        self.send_response(status)
        file_mime_type, _ = mimetypes.guess_type(filename)

        if file_mime_type:
            self.send_header("Content-type", file_mime_type)
        else:
            self.send_header("Content-type", "text/plain")

        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())


def save_data(data):
    parsed_data = urllib.parse.unquote_plus(data.decode())

    try:
        dictionary_from_data = {
            datetime.now().isoformat(" ", "auto"): {
                key: value
                for key, value in [
                    element.split("=") for element in parsed_data.split("&")
                ]
            }
        }

        logging.info(dictionary_from_data)

        data_file = BASE_DIR / "storage" / "data.json"
        if data_file.exists():
            with open("storage/data.json", "r", encoding="utf-8") as file:
                try:
                    existed_data = json.load(file)
                except json.JSONDecodeError:
                    existed_data = {}
        else:
            existed_data = {}
        existed_data.update(dictionary_from_data)

        with open("storage/data.json", "w", encoding="utf-8") as file:
            json.dump(existed_data, file, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(f"ValueError: {err}")
    except OSError as err:
        logging.error(f"OSError: {err}")


def start_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, HomeworkHandler)
    logging.info("Starting HTTP server")

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
        logging.info("HTTP server stopped")


def start_socket_server(host, port):
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_server.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            message, _ = socket_server.recvfrom(BUFFER_SIZE)
            save_data(message)
    except KeyboardInterrupt:
        socket_server.close()
        logging.info("Socket server stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")

    http_server = Thread(target=start_server, args=(HTTP_HOST, HTTP_PORT), daemon=True)
    http_server.start()

    socket_server = Thread(
        target=start_socket_server, args=(SOCKET_HOST, SOCKET_PORT), daemon=True
    )
    socket_server.start()

    http_server.join()
    socket_server.join()
