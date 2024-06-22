import socket
import threading
import os
import sys
import gzip

class SimpleHTTPServer:
    def __init__(self, host='localhost', port=4221, base_dir='.'):
        self.host = host
        self.port = port
        self.base_dir = base_dir
        self.server_socket = socket.create_server((self.host, self.port), reuse_port=True)

    def start(self):
        print(f"Starting server on {self.host}:{self.port}")
        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"Accepted connection from {client_address}")
                threading.Thread(target=self.handle_request, args=(client_socket,)).start()
        except KeyboardInterrupt:
            print("Shutting down server.")
        finally:
            self.server_socket.close()

    def handle_request(self, client_socket):
        try:
            request = b""
            while True:
                data = client_socket.recv(1024)
                request += data
                if len(data) < 1024:
                    break

            if request:
                # Decode the request
                request_lines = request.decode('utf-8').split('\r\n')
                request_line = request_lines[0]
                headers = request_lines[1:]

                # Parse request line
                method, path, _ = request_line.split()
                print(f"Received request: {method} {path}")

                # Extract headers
                headers_dict = {}
                body_index = 0
                for i, header in enumerate(headers):
                    if header == "":
                        body_index = i + 1
                        break
                    if ': ' in header:
                        key, value = header.split(': ', 1)
                        headers_dict[key.lower()] = value

                content_length = int(headers_dict.get('content-length', 0))
                request_body = "\r\n".join(headers[body_index:]).encode('utf-8')

                while len(request_body) < content_length:
                    request_body += client_socket.recv(1024)

                print(f"Request body: {request_body}")

                response = b""

                if method == 'GET':
                    if path == '/':
                        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n"
                    elif path.startswith('/echo/'):
                        response_body = path[len('/echo/'):].encode('utf-8')
                        if 'accept-encoding' in headers_dict:
                            if 'gzip' in headers_dict['accept-encoding']:
                                response_body = gzip.compress(response_body)
                                response_header = (
                                    b"HTTP/1.1 200 OK\r\n"
                                    b"Content-Encoding: gzip\r\n"
                                    b"Content-Type: text/plain\r\n"
                                    b"Content-Length: " + str(len(response_body)).encode('utf-8') + b"\r\n\r\n"
                                )
                            else:
                                response_header = (
                                    b"HTTP/1.1 200 OK\r\n"
                                    b"Content-Type: text/plain\r\n"
                                    b"Content-Length: " + str(len(response_body)).encode('utf-8') + b"\r\n\r\n"
                                )
                        else:
                            response_header = (
                                b"HTTP/1.1 200 OK\r\n"
                                b"Content-Type: text/plain\r\n"
                                b"Content-Length: " + str(len(response_body)).encode('utf-8') + b"\r\n\r\n"
                            )
                        response = response_header + response_body
                    elif path == '/user-agent' and 'user-agent' in headers_dict:
                        response_body = headers_dict['user-agent'].encode('utf-8')
                        response_header = (
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: text/plain\r\n"
                            b"Content-Length: " + str(len(response_body)).encode('utf-8') + b"\r\n\r\n"
                        )
                        response = response_header + response_body
                    elif path.startswith('/files/'):
                        file_path = os.path.join(self.base_dir, path[len('/files/'):])
                        if os.path.isfile(file_path):
                            with open(file_path, 'rb') as f:
                                response_body = f.read()
                            response_header = (
                                b"HTTP/1.1 200 OK\r\n"
                                b"Content-Type: application/octet-stream\r\n"
                                b"Content-Length: " + str(len(response_body)).encode('utf-8') + b"\r\n\r\n"
                            )
                            response = response_header + response_body
                        else:
                            response = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n"
                    else:
                        response = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n"

                elif method == 'POST':
                    if path.startswith('/files/'):
                        file_name = path.split('/')[-1]
                        file_path = os.path.join(self.base_dir, file_name)
                        with open(file_path, 'wb') as f:
                            f.write(request_body)

                        response = (
                            b"HTTP/1.1 201 Created\r\n"
                            b"Content-Length: 0\r\n"
                            b"Content-Type: text/plain\r\n\r\n"
                        )

                    else:
                        response = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n"

                print(f"Sending response: {response}")
                client_socket.sendall(response)

        except Exception as e:
            print(f"Error handling request: {e}")
        finally:
            client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == '--directory':
        base_dir = sys.argv[2]
    else:
        base_dir = '.'

    server = SimpleHTTPServer(base_dir=base_dir)
    server.start()