import socket
import os
import argparse
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

# Server configuration
def parse_args():
    parser = argparse.ArgumentParser(
        description="Multithreaded file server using ThreadPoolExecutor"
    )
    parser.add_argument(
        '--host', default='0.0.0.0',
        help='Host IP to bind the server (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port', type=int, default=8889,
        help='TCP port to listen on (default: 8889)'
    )
    parser.add_argument(
        '--workers', type=int, default=4,
        help='Number of worker threads in pool (default: 4)'
    )
    parser.add_argument(
        '--storage', default='Temp',
        help='Directory to store uploaded files (default: Temp)'
    )
    parser.add_argument(
        '--log', default='server.log',
        help='Log file path (default: server.log)'
    )
    return parser.parse_args()


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def handle_client(conn, addr, storage_dir):
    try:
        logging.info(f"Connection from {addr}")

        # Read command header until delimiter
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(1024)
            if not chunk:
                return
            data += chunk
        header, _ = data.split(b"\r\n\r\n", 1)
        parts = header.decode().strip().split()
        if len(parts) < 2:
            conn.sendall(b"ERROR Invalid command format\r\n\r\n")
            return

        command = parts[0].upper()
        filename = parts[1]
        filepath = os.path.join(storage_dir, filename)

        if command == "UPLOAD":
            # Read size
            if len(parts) < 3:
                conn.sendall(b"ERROR No size provided\r\n\r\n")
                return
            size = int(parts[2])
            # Send ACK to start sending data
            conn.sendall(b"OK Ready to receive\r\n\r\n")
            received = 0
            with open(filepath, 'wb') as f:
                while received < size:
                    chunk = conn.recv(min(65536, size - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
            logging.info(f"Saved file {filename} ({received} bytes)")
            conn.sendall(b"OK Upload complete\r\n\r\n")

        elif command == "GET":
            if not os.path.exists(filepath):
                conn.sendall(b"ERROR File not found\r\n\r\n")
                return
            size = os.path.getsize(filepath)
            # Send header with size
            header = f"OK {size}\r\n\r\n".encode()
            conn.sendall(header)
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    conn.sendall(chunk)
            logging.info(f"Sent file {filename} ({size} bytes)")

        else:
            conn.sendall(b"ERROR Invalid command\r\n\r\n")

    except Exception as e:
        logging.error(f"Exception handling client {addr}: {e}")
    finally:
        conn.close()
        logging.info(f"Closed connection from {addr}")


def start_server(host, port, workers, storage_dir):
    os.makedirs(storage_dir, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(100)
        logging.info(f"Server listening on {host}:{port} with {workers} workers")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            while True:
                conn, addr = server_socket.accept()
                logging.info(f"Accepted connection from {addr}")
                executor.submit(handle_client, conn, addr, storage_dir)


def main():
    args = parse_args()
    setup_logging(args.log)
    start_server(args.host, args.port, args.workers, args.storage)


if __name__ == '__main__':
    main()
