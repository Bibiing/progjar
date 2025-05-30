import socket
import os
import argparse
import logging
import sys
import threading
import base64
import binascii
from concurrent.futures import ThreadPoolExecutor

MAX_HEADER_SIZE = 8192
CHUNK_SIZE = 8192 

def parse_args():
    parser = argparse.ArgumentParser(description="Scalable multithreaded file server with Streaming Decode")
    parser.add_argument('--host', default='0.0.0.0', help='Host IP to bind the server (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8889, help='TCP port to listen on (default: 8889)')
    parser.add_argument('--workers', type=int, default=1, help='Number of worker threads (default: 1)') 
    parser.add_argument('--storage', default='files', help='Directory to store uploaded files (default: files)')
    parser.add_argument('--log', default='server_streaming.log', help='Log file path (default: server_streaming.log)')
    return parser.parse_args()

def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)]
    )

def handle_upload_streaming(conn, addr, parts, filepath, initial_payload):
    if len(parts) < 3:
        logging.warning(f"UPLOAD command from {addr} is missing the data size.")
        conn.sendall(b"ERROR No size provided for UPLOAD\r\n\r\n")
        return
    try:
        expected_size = int(parts[2])
    except ValueError:
        logging.warning(f"Invalid size format in UPLOAD from {addr}: {parts[2]}")
        conn.sendall(b"ERROR Invalid size format\r\n\r\n")
        return

    conn.sendall(b"OK Ready to receive\r\n\r\n")
    
    bytes_received = len(initial_payload)
    # Buffer untuk menampung sisa data yang belum kelipatan 4
    decode_buffer = initial_payload 
    
    try:
        with open(filepath, 'wb') as f:
            # menerima dan langsung memproses data
            while bytes_received < expected_size:
                # 1. Pastikan buffer bisa di-decode (panjangnya kelipatan 4)
                len_to_decode = (len(decode_buffer) // 4) * 4
                
                if len_to_decode > 0:
                    # Ambil bagian yang akan di-decode
                    chunk_to_decode = decode_buffer[:len_to_decode]
                    
                    # Simpan sisa datanya di buffer untuk digabung dengan data berikutnya
                    decode_buffer = decode_buffer[len_to_decode:]
                    
                    # 2. Decode dan langsung tulis ke disk
                    try:
                        decoded_data = base64.b64decode(chunk_to_decode)
                        f.write(decoded_data)
                    except binascii.Error as e:
                        logging.error(f"Streaming Base64 decode error from {addr}: {e}")
                        conn.sendall(b"ERROR Invalid Base64 data stream\r\n\r\n")
                        # Hapus file parsial jika terjadi error
                        f.close()
                        os.remove(filepath)
                        return

                # 3. Terima data berikutnya dari klien
                chunk = conn.recv(CHUNK_SIZE)
                if not chunk:
                    logging.warning(f"Connection lost during UPLOAD of {os.path.basename(filepath)} from {addr}.")
                    return
                decode_buffer += chunk
                bytes_received += len(chunk)

            # proses sisa data terakhir di buffer
            if decode_buffer:
                try:
                    decoded_data = base64.b64decode(decode_buffer)
                    f.write(decoded_data)
                except binascii.Error as e:
                    logging.error(f"Final Base64 decode error from {addr}: {e}")
                    f.close()
                    os.remove(filepath)
                    return
            
        logging.info(f"OK: Stream-decoded and saved {os.path.basename(filepath)} from {addr}")
        conn.sendall(b"OK Upload complete\r\n\r\n")

    except IOError as e:
        logging.error(f"File write error during streaming upload from {addr}: {e}")
        conn.sendall(b"ERROR Server file error\r\n\r\n")
    except Exception as e:
        logging.error(f"Unhandled exception during streaming upload: {e}", exc_info=True)

def handle_get(conn, addr, filepath):
    if not os.path.exists(filepath):
        conn.sendall(b"ERROR File not found\r\n\r\n")
        return
    try:
        file_size = os.path.getsize(filepath)
        conn.sendall(f"OK {file_size}\r\n\r\n".encode('utf-8'))
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk: break
                conn.sendall(chunk)
    except Exception as e:
        logging.error(f"Error sending file {os.path.basename(filepath)} to {addr}: {e}")


def handle_client(conn, addr, storage_dir):
    logging.info(f"Connection from {addr} assigned to thread {threading.current_thread().name}")
    try:
        header_data = b""
        while b"\r\n\r\n" not in header_data:
            if len(header_data) > MAX_HEADER_SIZE:
                logging.error(f"Header from {addr} exceeds max size.")
                conn.sendall(b"ERROR Header too large\r\n\r\n")
                return
            chunk = conn.recv(CHUNK_SIZE)
            if not chunk:
                return
            header_data += chunk

        header_bytes, initial_payload = header_data.split(b"\r\n\r\n", 1)
        header_str = header_bytes.decode('utf-8')
        parts = header_str.strip().split()
        
        if len(parts) < 2:
            return

        command = parts[0].upper()
        filename = os.path.basename(parts[1])
        filepath = os.path.join(storage_dir, filename)

        if command == "UPLOAD":
            handle_upload_streaming(conn, addr, parts, filepath, initial_payload)
        elif command == "GET":
            handle_get(conn, addr, filepath)
        else:
            logging.warning(f"Unknown command '{command}' from {addr}.")
            conn.sendall(b"ERROR Unknown command\r\n\r\n")

    except Exception as e:
        logging.error(f"Exception in handle_client for {addr}: {e}", exc_info=False)
    finally:
        try:
            conn.close()
            logging.info(f"Closed connection from {addr}")
        except: pass


def start_server(host, port, workers, storage_dir):
    os.makedirs(storage_dir, exist_ok=True)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='Worker') as executor:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind((host, port))
                server_socket.listen(100)
                logging.info(f"Scalable Server listening on {host}:{port} with {workers} workers")
                while True:
                    conn, addr = server_socket.accept()
                    executor.submit(handle_client, conn, addr, storage_dir)
        except KeyboardInterrupt:
            logging.info("Shutdown signal received.")
        except Exception as e:
            logging.error(f"Server main loop error: {e}", exc_info=True)
        finally:
            logging.info("Server has been shut down.")

def main():
    args = parse_args()
    setup_logging(args.log)
    start_server(args.host, args.port, args.workers, args.storage)

if __name__ == '__main__':
    main()