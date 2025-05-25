import socket
import os
import argparse
import logging
import sys
from concurrent.futures import ProcessPoolExecutor

# Server configuration
def parse_args():
    parser = argparse.ArgumentParser(
        description="Multiprocessing file server using ProcessPoolExecutor"
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
        help='Number of worker processes in pool (default: 4)'
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
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(processName)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def recv_until(sock, delimiter=b"\r\n\r\n", bufsize=1024):
    data = b""
    while delimiter not in data:
        chunk = sock.recv(bufsize)
        if not chunk:
            break
        data += chunk
    return data


def handle_client_fd(fd, addr, storage_dir):
    # Reconstruct socket from FD in worker process
    conn = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, fileno=fd)
    try:
        logging.info(f"Connection from {addr}")
        data = recv_until(conn)
        if not data:
            return
        header, rest = data.split(b"\r\n\r\n", 1)
        parts = header.decode(errors='ignore').strip().split()
        if len(parts) < 2:
            conn.sendall(b"ERROR Invalid command format\r\n\r\n")
            return

        command = parts[0].upper()
        filename = os.path.basename(parts[1])
        filepath = os.path.join(storage_dir, filename)

        if command == "UPLOAD":
            if len(parts) < 3 or not parts[2].isdigit():
                conn.sendall(b"ERROR No size provided\r\n\r\n")
                return
            size = int(parts[2])
            conn.sendall(b"OK Ready to receive\r\n\r\n")
            received = len(rest)
            with open(filepath, 'wb') as f:
                if rest:
                    f.write(rest)
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
            conn.sendall(f"OK {size}\r\n\r\n".encode())
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
        logging.exception(f"Error handling {addr}: {e}")
    finally:
        conn.close()
        logging.info(f"Closed connection from {addr}")


def start_server(host, port, workers, storage_dir):
    os.makedirs(storage_dir, exist_ok=True)
    # Create listening socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(100)
        logging.info(f"Server listening on {host}:{port} with {workers} worker processes")

        # Use ProcessPoolExecutor; children inherit the listening socket FD
        with ProcessPoolExecutor(max_workers=workers) as executor:
            try:
                while True:
                    conn, addr = server_socket.accept()
                    # Pass connection FD and address to worker, then close in parent
                    fd = conn.fileno()
                    executor.submit(handle_client_fd, fd, addr, storage_dir)
                    conn.close()
                    logging.info(f"Dispatched connection from {addr} to worker")
            except KeyboardInterrupt:
                logging.info("Server shutdown requested, exiting...")


def main():
    args = parse_args()
    setup_logging(args.log)
    start_server(args.host, args.port, args.workers, args.storage)


if __name__ == '__main__':
    main()
