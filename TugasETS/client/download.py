import os
import socket
import logging
import argparse
import time
import csv
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(processName)s:%(threadName)s] - %(message)s"
)

CHUNK_SIZE = 8192  # Ukuran chunk untuk menerima data
SOCKET_TIMEOUT = 60.0 # Timeout untuk operasi socket dalam detik

def download_once(server_ip, server_port, filename, download_folder):
    """
    Menangani proses download satu file dari server.
    """
    start_time = time.time()
    sock = None
    downloaded_bytes = 0
    error_message = None
    success = False

    try:
        os.makedirs(download_folder, exist_ok=True)
        
        base_filename, ext = os.path.splitext(filename)
        output_filepath = os.path.join(download_folder, filename)
        counter = 1
        while os.path.exists(output_filepath):
            output_filepath = os.path.join(download_folder, f"{base_filename}_{counter}{ext}")
            counter += 1

        logging.info(f"Mencoba mengunduh '{filename}' ke '{output_filepath}' dari {server_ip}:{server_port}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((server_ip, server_port))

        command_str = f"GET {filename}\r\n\r\n"
        logging.debug(f"Mengirim perintah: {command_str.strip()}")
        sock.sendall(command_str.encode())

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = sock.recv(CHUNK_SIZE) # Baca per chunk kecil untuk header
            if not chunk:
                raise ConnectionError("Koneksi ditutup server saat membaca header.")
            header_data += chunk
            if len(header_data) > CHUNK_SIZE * 2: # Batas wajar untuk header
                 raise ConnectionError("Header terlalu besar atau tidak valid.")


        header_str, initial_payload = header_data.split(b"\r\n\r\n", 1)
        header_parts = header_str.decode().split()
        logging.debug(f"Header diterima: {header_parts}")

        if header_parts[0] == "OK" and len(header_parts) > 1:
            try:
                expected_size = int(header_parts[1])
                logging.info(f"Server merespons OK. Ukuran file diharapkan: {expected_size} bytes.")
            except ValueError:
                raise ValueError(f"Format ukuran file di header tidak valid: {header_parts[1]}")

            # 3. Terima data file
            with open(output_filepath, 'wb') as f:
                # Tulis payload awal jika ada
                if initial_payload:
                    f.write(initial_payload)
                    downloaded_bytes += len(initial_payload)
                
                while downloaded_bytes < expected_size:
                    bytes_to_receive = min(CHUNK_SIZE, expected_size - downloaded_bytes)
                    chunk = sock.recv(bytes_to_receive)
                    if not chunk:
                        logging.warning(f"Koneksi terputus saat mengunduh. Diterima {downloaded_bytes}/{expected_size} bytes.")
                        break 
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
            
            if downloaded_bytes == expected_size:
                logging.info(f"File '{filename}' berhasil diunduh ({downloaded_bytes} bytes).")
                success = True
            else:
                error_message = f"Ukuran file tidak sesuai. Diharapkan {expected_size}, diterima {downloaded_bytes}."
                logging.error(error_message)
                if os.path.exists(output_filepath): # Hapus file parsial
                    os.remove(output_filepath)

        elif header_parts[0] == "ERROR":
            error_message = " ".join(header_parts[1:])
            logging.error(f"Server mengembalikan error: {error_message}")
        else:
            error_message = f"Format respons server tidak dikenal: {header_str.decode()}"
            logging.error(error_message)

    except socket.timeout:
        error_message = "Socket timeout saat operasi download."
        logging.error(error_message)
    except ConnectionError as ce:
        error_message = f"Kesalahan koneksi: {ce}"
        logging.error(error_message)
    except Exception as e:
        error_message = f"Terjadi kesalahan: {e}"
        logging.error(error_message, exc_info=True)
        if 'output_filepath' in locals() and os.path.exists(output_filepath) and not success:
            try:
                os.remove(output_filepath) # Hapus file parsial jika ada error tak terduga
            except OSError:
                pass 
    finally:
        if sock:
            sock.close()
        duration = time.time() - start_time
        logging.debug(f"Operasi download_once untuk '{filename}' selesai dalam {duration:.3f}s. Sukses: {success}")

    return success, duration, downloaded_bytes, error_message

def stress_test(server_ip, server_port, filename_to_download, volume_label,
                  client_pool_mode, num_client_workers, num_server_workers_reported,
                  test_case_num, output_csv_file):
    """
    Menjalankan stress test download dan menyimpan hasilnya ke file CSV.
    """
    executor_cls = ThreadPoolExecutor if client_pool_mode == "thread" else ProcessPoolExecutor
    download_target_folder = "downloaded_files_stress"

    logging.info(f"--- Memulai Tes Download #{test_case_num} ---")
    logging.info(f"Mode Pool Klien: {client_pool_mode}, Jumlah Worker Klien: {num_client_workers}, File: {filename_to_download}, Volume: {volume_label}")

   
    results = []
    
    with executor_cls(max_workers=num_client_workers) as executor:
        futures = [executor.submit(download_once, server_ip, server_port, filename_to_download, download_target_folder)
                   for _ in range(num_client_workers)]
        for i, f in enumerate(futures):
            try:
                logging.debug(f"Menunggu hasil dari tugas klien #{i+1}/{num_client_workers}")
                results.append(f.result(timeout=300)) # Timeout 5 menit per tugas download
            except Exception as e:
                logging.error(f"Sebuah tugas klien gagal dengan exception: {e}")
                results.append((False, 300.0, 0, str(e))) # Catat sebagai gagal dengan durasi timeout

    successful_tasks = sum(1 for r in results if r[0])
    failed_tasks = num_client_workers - successful_tasks
    
    sum_of_durations = sum(r[1] for r in results)
    avg_time_per_worker = sum_of_durations / num_client_workers if num_client_workers > 0 else 0
    
    total_bytes_successful = sum(r[2] for r in results if r[0])
    total_duration_successful_tasks = sum(r[1] for r in results if r[0]) # Hanya durasi dari tugas sukses
    avg_throughput_per_successful_worker_kbs = (total_bytes_successful / total_duration_successful_tasks / 1024) if total_duration_successful_tasks > 0 else 0

    first_error_message = next((r[3] for r in results if not r[0] and r[3]), "")

    # --- Penulisan Laporan CSV ---
    header = [
        "Nomor", "Operasi (Client Pool Mode)", "Volume (Label)", "Jumlah client worker pool", 
        "Jumlah server worker pool (Reported)", "Waktu rata-rata per tugas klien (s)", 
        "Throughput rata-rata per tugas klien sukses (KB/s)", 
        "Jumlah worker client sukses", "Jumlah worker client gagal", 
        "Pesan Error Pertama (jika ada)"
    ]
    
    row_data = [
        test_case_num,
        client_pool_mode,
        volume_label,
        num_client_workers,
        num_server_workers_reported,
        f"{avg_time_per_worker:.3f}", # Diformat sebagai string dengan 3 desimal
        f"{avg_throughput_per_successful_worker_kbs:.2f}", # Diformat sebagai string dengan 2 desimal
        successful_tasks,
        failed_tasks,
        first_error_message
    ]
    
    # Tulis ke file CSV
    write_header = not os.path.exists(output_csv_file) or os.path.getsize(output_csv_file) == 0
    with open(output_csv_file, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(header)
        writer.writerow(row_data)

    logging.info(f"--- Laporan Tes Download #{test_case_num} disimpan ke {output_csv_file} ---")
    logging.debug(f"Data baris CSV: {row_data}")


def main():
    parser = argparse.ArgumentParser(description="Klien untuk download file dan stress testing.")
    parser.add_argument("--server", required=True, help="Alamat IP server.")
    parser.add_argument("--port", type=int, default=8889, help="Port server (default: 8889).")
    parser.add_argument("--mode", choices=["download", "stress"], required=True, help="Mode operasi: 'download' untuk satu file, 'stress' untuk stress test.")
    parser.add_argument("--filename", help="Nama file yang akan diunduh (diperlukan untuk mode 'download' dan 'stress').")
    # Argumen khusus stress test
    parser.add_argument("--volume", help="Label ukuran file untuk laporan CSV (misal: '10MB', '100MB'). Diperlukan untuk mode 'stress'.")
    parser.add_argument("--pool_mode", choices=["thread", "process"], default="thread", help="Mode pool worker klien untuk stress test (default: thread).")
    parser.add_argument("--pool_size", type=int, default=1, help="Jumlah worker klien konkuren untuk stress test (default: 1).")
    parser.add_argument("--server_workers", type=int, default=1, help="Jumlah worker server (hanya untuk tujuan pelaporan di CSV).")
    parser.add_argument("--nomor", type=int, help="Nomor urut tes untuk laporan CSV (diperlukan untuk mode 'stress').")
    parser.add_argument("--output", default="download_stress_report.csv", help="Nama file output CSV untuk hasil stress test (default: download_stress_report.csv).")
    
    args = parser.parse_args()

    if args.mode == "download":
        if not args.filename:
            print("Error: Argumen --filename diperlukan untuk mode 'download'.")
            logging.error("Mode download dipanggil tanpa --filename.")
            return
        
        download_folder = "downloaded_files_single" # Folder terpisah untuk download tunggal
        success, duration, bytes_downloaded, error_msg = download_once(args.server, args.port, args.filename, download_folder)
        
        if success:
            print(f"File '{args.filename}' berhasil diunduh ({bytes_downloaded} bytes) dalam {duration:.3f} detik.")
            logging.info(f"Download tunggal '{args.filename}' sukses.")
        else:
            print(f"Gagal mengunduh file '{args.filename}'. Error: {error_msg}")
            logging.error(f"Download tunggal '{args.filename}' gagal. Error: {error_msg}")

    elif args.mode == "stress":
        if not args.filename:
            print("Error: Argumen --filename diperlukan untuk mode 'stress'.")
            logging.error("Mode stress dipanggil tanpa --filename.")
            return
        if not args.volume:
            print("Error: Argumen --volume diperlukan untuk mode 'stress' (untuk label laporan).")
            logging.error("Mode stress dipanggil tanpa --volume.")
            return
        if args.nomor is None: # --nomor sekarang wajib untuk mode stress
            print("Error: Argumen --nomor diperlukan untuk mode 'stress'.")
            logging.error("Mode stress dipanggil tanpa --nomor.")
            return

        stress_test(
            args.server, args.port, args.filename, args.volume,
            args.pool_mode, args.pool_size, args.server_workers,
            args.nomor, args.output
        )
    else:
        print(f"Mode tidak dikenal: {args.mode}")
        logging.error(f"Mode operasi tidak dikenal: {args.mode}")

if __name__ == "__main__":
    main()
