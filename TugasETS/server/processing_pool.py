import socket
import os
import argparse
import logging
import base64
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process

# Nilai default, bisa diubah via argparse
HOST = '0.0.0.0'
PORT = 55555
BUFFER_SIZE = 1048576
STORAGE_DIR = 'storage'
LOG_FILE = 'server.log'

def setup_logging(log_file):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def server_worker_process(host, port, storage_dir):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            logging.warning("SO_REUSEPORT is not supported on this platform.")

        server_socket.bind((host, port))
        server_socket.listen(100)
        logging.info(f"[PID {os.getpid()}] Listening on {host}:{port}")

        while True:
            try:
                conn, addr = server_socket.accept()
                logging.info(f"[PID {os.getpid()}] Accepted connection from {addr}")
                handle_client(conn, addr, storage_dir)
            except Exception as e:
                logging.error(f"[PID {os.getpid()}] Error accepting connection: {e}")

def handle_client(conn, addr, storage_dir):
    thread_name = threading.current_thread().name
    try:
        logging.info(f"Connection from {addr}")

        data_received = ""
        while True:
            data = conn.recv(BUFFER_SIZE).decode()
            if not data:
                break
            data_received += data
            if "\r\n\r\n" in data_received:
                break
        logging.debug(f"Received data (truncated): {data_received[:100]}")

        parts = data_received.strip().split()
        if len(parts) < 2:
            resp = json.dumps({"status": "ERROR", "data": "Invalid command format"}) + "\r\n\r\n"
            conn.sendall(resp.encode())
            return

        command = parts[0].upper()
        filename = parts[1]
        filepath = os.path.join(storage_dir, filename)

        if command == "UPLOAD":
            if len(parts) < 3:
                resp = json.dumps({"status": "ERROR", "data": "No data to upload"}) + "\r\n\r\n"
                conn.sendall(resp.encode())
                return
            encoded_data = " ".join(parts[2:])
            try:
                file_data = base64.b64decode(encoded_data)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                logging.info(f"Saved file {filename} from {addr}")
                resp = json.dumps({"status": "OK", "data": f"Uploaded {filename}"}) + "\r\n\r\n"
                conn.sendall(resp.encode())
            except Exception as e:
                logging.error(f"Error decoding/saving file {filename}: {e}")
                resp = json.dumps({"status": "ERROR", "data": str(e)}) + "\r\n\r\n"
                conn.sendall(resp.encode())

        elif command == "GET":
            if not os.path.exists(filepath):
                resp = json.dumps({"status": "ERROR", "data": "File not found"}) + "\r\n\r\n"
                conn.sendall(resp.encode())
                return
            with open(filepath, 'rb') as f:
                file_data = f.read()
            encoded_data = base64.b64encode(file_data).decode()
            resp = json.dumps({
                "status": "OK",
                "data_namafile": filename,
                "data_file": encoded_data
            }) + "\r\n\r\n"
            conn.sendall(resp.encode())
            logging.info(f"Sent file {filename} to {addr}")

        else:
            resp = json.dumps({"status": "ERROR", "data": "Invalid command"}) + "\r\n\r\n"
            conn.sendall(resp.encode())

    except Exception as e:
        logging.error(f"Exception handling client {addr}: {e}")
        resp = json.dumps({"status": "ERROR", "data": str(e)}) + "\r\n\r\n"
        try:
            conn.sendall(resp.encode())
        except:
            pass
    finally:
        conn.close()
        logging.info(f"Closed connection from {addr}")

def start_server_single(host, port, storage_dir):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(100)
        logging.info(f"Single-threaded server started on {host}:{port}")

        while True:
            conn, addr = server_socket.accept()
            logging.info(f"Accepted connection from {addr}")
            handle_client(conn, addr, storage_dir)

def start_server_threaded(host, port, workers, storage_dir):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(100)
        logging.info(f"Thread-pool server started on {host}:{port} with {workers} workers")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            while True:
                conn, addr = server_socket.accept()
                logging.info(f"Accepted connection from {addr}")
                executor.submit(handle_client, conn, addr, storage_dir)

def start_server_process(host, port, workers, storage_dir):
    logging.info(f"Starting multiprocessing server with {workers} workers")
    processes = []
    for _ in range(workers):
        p = Process(target=server_worker_process, args=(host, port, storage_dir))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

def main():
    global HOST, PORT, STORAGE_DIR, LOG_FILE

    parser = argparse.ArgumentParser(description="File server with multiple concurrency modes.")
    parser.add_argument('--mode', choices=['single', 'thread', 'process'], default='single', help="Mode to run the server")
    parser.add_argument('--host', default='0.0.0.0', help="Host to bind the server")
    parser.add_argument('--port', type=int, default=55555, help="Port to bind the server")
    parser.add_argument('--workers', type=int, default=1, help="Number of worker threads or processes")
    parser.add_argument('--storage', default='storage', help="Directory to store files")
    parser.add_argument('--log', default='server.log', help="Path to the log file")
    args = parser.parse_args()

    # Set global vars
    HOST = args.host
    PORT = args.port
    STORAGE_DIR = args.storage
    LOG_FILE = args.log

    os.makedirs(STORAGE_DIR, exist_ok=True)
    setup_logging(LOG_FILE)

    if args.mode == 'single':
        start_server_single(HOST, PORT, STORAGE_DIR)
    elif args.mode == 'thread':
        start_server_threaded(HOST, PORT, args.workers, STORAGE_DIR)
    elif args.mode == 'process':
        start_server_process(HOST, PORT, args.workers, STORAGE_DIR)
    else:
        logging.error("Invalid mode selected.")

if __name__ == '__main__':
    main()
