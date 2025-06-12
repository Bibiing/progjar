from socket import *
import socket
import time
import sys
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from http import HttpServer

httpserver = HttpServer()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

#untuk menggunakan processpoolexecutor, karena tidak mendukung subclassing pada process,
#maka class ProcessTheClient dirubah dulu menjadi function, tanpda memodifikasi behaviour didalamnya

def ProcessTheClient(connection, address):
    logging.info(f"[Connection] Diterima dari {address}")
    try:
        # Baca seluruh payload dari client 
        data = connection.recv(65536)
        if not data:
            logging.warning(f"[Connection] Tidak ada data yang diterima dari {address}")
            return
        text = data.decode('utf-8', errors='ignore')
        # Pisahkan baris pertama dan sisanya
        lines = text.split('\n', 1)
        cmd_line = lines[0].strip()
        rest = lines[1] if len(lines) > 1 else ''

        parts = cmd_line.split()
        if len(parts) < 2:
            response = httpserver.response(400, 'Bad Request', 'Format: COMMAND filename')
        else:
            cmd, filename = parts[0].upper(), parts[1]
            if cmd == 'GET':
                # Panggil langsung http_get
                response = httpserver.http_get(f'/{filename}', [])
            elif cmd == 'POST':
                # Siapkan header Content-Disposition
                hdr = f'Content-Disposition: form-data; name="file"; filename="{filename}"'
                # body adalah sisa data setelah newline
                body = rest.rstrip('\r\n')
                response = httpserver.http_post('/upload', [hdr], body)
            elif cmd == 'DELETE':
                response = httpserver.http_delete(f'/{filename}', [])
            else:
                response = httpserver.response(400, 'Bad Request', f'Unknown command: {cmd}')

        connection.sendall(response)
    except Exception as e:
        # Jika terjadi exception, kirim 500
        err = f'Internal server error: {e}'
        connection.sendall(httpserver.response(500, 'Internal Server Error', err))
    finally:
        connection.close()
        logging.info(f"[Connection] Closed {address}")

def Server(host='0.0.0.0', port=8889, pool_size=20):
    logging.info(f"[Startup] Binding to {host}:{port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as my_socket:
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        my_socket.bind((host, port))
        my_socket.listen(5)
        
        with ProcessPoolExecutor(pool_size) as executor:
            try:
                while True:
                    connection, client_address = my_socket.accept()
                    print(f"Koneksi diterima dari {client_address}")
                    # Kirim tugas ke process pool
                    executor.submit(ProcessTheClient, connection, client_address)
                
            except KeyboardInterrupt:
                logging.info("[Shutdown] Server dihentikan oleh user")
            except Exception as e:
                logging.exception(f"[Error] Terjadi error: {e}")
    logging.info("[Shutdown] Server socket closed")

def main():
	Server()

if __name__=="__main__":
	main()
