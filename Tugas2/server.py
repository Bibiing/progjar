from socket import *
import socket
import threading
import logging
import time
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        buffer = b''
        while True:
            try:
                data = self.connection.recv(32)
                if data:
                    buffer += data

                    # CRLF (13 DAN 10)
                    while b'\r\n' in buffer:
                        line, buffer = buffer.split(b'\r\n', 1)

                        if line == b'TIME':
                            now = datetime.now()
                            time_str = now.strftime("%H:%M:%S")
                            response = f"JAM {time_str}\r\n".encode('utf-8')
                            self.connection.sendall(response)
                            logging.info(f"Sent time {time_str} to {self.address}")

                        elif line == b'QUIT':
                            logging.info(f"Client {self.address} requested to quit")
                            return 

                        else:
                            logging.warning(f"Unknown request from {self.address}: {line}")
                else:
                    break 

            except Exception as e:
                logging.error(f"Error processing client request: {str(e)}")
                break

        logging.info(f"Closing connection with {self.address}")
        self.connection.close()

class Server(threading.Thread):
    def __init__(self):
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.my_socket.bind(('0.0.0.0', 45000))
            self.my_socket.listen(5)
            logging.info(f"Time server started on port 45000")

            while True:
                self.connection, self.client_address = self.my_socket.accept()
                logging.info(f"Connection from {self.client_address}")
                clt = ProcessTheClient(self.connection, self.client_address)
                clt.start()
                self.the_clients.append(clt)
                self.the_clients = [c for c in self.the_clients if c.is_alive()]

        except KeyboardInterrupt:
            logging.info("Server shutting down...")
        except Exception as e:
            logging.error(f"Server error: {str(e)}")
        finally:
            if hasattr(self, 'my_socket'):
                self.my_socket.close()

def main():
    svr = Server()
    svr.start()

if __name__ == "__main__":
    main()
