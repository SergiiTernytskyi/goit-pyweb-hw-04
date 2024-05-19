import json
import logging
import mimetypes
import socket
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread


BASE_DIR = Path()
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8080

SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 4000
BUFFER_SIZE = 1024


class HomeworkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)

        if parsed_url.path == "/":
            self.send_html_file("index.html")
        if parsed_url.path == "/message":
            self.send_html_file("message.html")
        else:
            file_path = BASE_DIR.joinpath(parsed_url.path[1:])

            if file_path.exists():
                self.send_assets_file(file_path)
            else:
                self.send_html_file("error.html", 404)

    def do_POST(self):
        size = self.headers.get("Content-length")
        data = self.rfile.read(int(size))

        socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_client.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        socket_client.close()

        self.send_response(302)
        self.send_header("Location", "/message")
        self.end_headers()

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())

    def send_assets_file(self, filename, status=200):
        self.send_response(status)
        file_mime_type, *_ = mimetypes.guess_type(filename)

        if file_mime_type:
            self.send_header("Content-type", file_mime_type)
        else:
            self.send_header("Content-type", "plain/text")

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
        with open("storage/data.json", "w", encoding="utf-8") as file:
            json.dump(dictionary_from_data, file, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)


def start_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, HomeworkHandler)
    logging.info("Starting HTTP server")

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")

    http_server = Thread(target=start_server, args=(HTTP_HOST, HTTP_PORT))
    http_server.start()

    socket_server = Thread(target=start_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    socket_server.start()
