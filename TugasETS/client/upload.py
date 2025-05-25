import os
import socket
import json
import base64
import logging
import argparse
import time
import csv
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_command(server_ip, server_port, command_str=""):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server_ip, server_port))
        sock.sendall((command_str + "\r\n\r\n").encode())
        data_received = ""
        while True:
            data = sock.recv(65536)
            if data:
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
        return json.loads(data_received.strip())
    except Exception as e:
        return {"status": "ERROR", "data": str(e)}
    finally:
        sock.close()

def remote_upload(server_ip, server_port, filepath=""):
    try:
        with open(filepath, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        filename = os.path.basename(filepath)
        command_str = f"upload {filename} {encoded}"
        return send_command(server_ip, server_port, command_str)
    except Exception as e:
        return {"status": "ERROR", "data": str(e)}

def worker_task(server_ip, server_port, operation, filepath):
    start_time = time.time()
    if operation == "upload":
        result = remote_upload(server_ip, server_port, filepath)
        byte_size = os.path.getsize(filepath) if result.get('status') == 'OK' else 0
    else:
        result = {"status": "ERROR", "data": "Unknown operation"}
        byte_size = 0
    duration = time.time() - start_time
    return (result.get('status') == 'OK', duration, byte_size)

def stress_test(server_ip, server_port, operation, file_path, pool_mode, pool_size, server_workers, nomor, output_csv):
    executor_cls = ThreadPoolExecutor if pool_mode == "thread" else ProcessPoolExecutor
    results = []
    start_all = time.time()

    with executor_cls(max_workers=pool_size) as executor:
        futures = [executor.submit(worker_task, server_ip, server_port, operation, file_path) for _ in range(pool_size)]
        for f in futures:
            results.append(f.result())

    total_time = time.time() - start_all
    success_count = sum(1 for r in results if r[0])
    fail_count = pool_size - success_count
    total_bytes = sum(r[2] for r in results)
    throughput = total_bytes / total_time if total_time > 0 else 0
    avg_time = total_time / pool_size if pool_size > 0 else 0

    # Menulis ke CSV
    file_volume = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    file_volume_str = f"{round(file_volume / 1024 / 1024)}MB"

    header = [
        "Nomor", "Operasi", "Volume", "Jumlah client worker pool", "Jumlah server worker pool",
        "Waktu total per client", "Throughput per client",
        "Jumlah worker client yang sukses dan gagal", "Jumlah worker server yang sukses dan gagal"
    ]
    row = [
        nomor, operation, file_volume_str, pool_size, server_workers,
        round(avg_time, 3), round(throughput / pool_size, 3),
        f"{success_count} sukses, {fail_count} gagal",
        f"{server_workers} server worker (manual input)"
    ]
    write_header = not os.path.exists(output_csv)

    with open(output_csv, mode="a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(header)
        writer.writerow(row)

    print(f"Hasil stress test disimpan ke {output_csv}")
    print("Data:", row)

def main():
    parser = argparse.ArgumentParser(description="File client CLI test and stress test")
    parser.add_argument("--server", default="172.16.16.101", help="Server IP address")
    parser.add_argument("--port", type=int, default=8889, help="Server port")
    parser.add_argument("--mode", choices=["upload", "download", "stress"], required=True, help="Operation mode")
    parser.add_argument("--file", help="File path for upload or filename for download")
    parser.add_argument("--pool_mode", choices=["thread", "process"], default="thread", help="Pool mode for stress test")
    parser.add_argument("--pool_size", type=int, default=1, help="Number of concurrent workers")
    parser.add_argument("--server_workers", type=int, default=1, help="Number of server workers (for logging only)")
    parser.add_argument("--nomor", type=int, default=1, help="Nomor test case untuk laporan")
    parser.add_argument("--output", default="stress_test_report.csv", help="Output CSV file name")
    args = parser.parse_args()

    if args.mode == "UPLOAD":
        if not args.file:
            print("Upload mode requires --file argument")
            return
        res = remote_upload(args.server, args.port, args.file)
        print(res)
    elif args.mode == "stress":
        if not args.file:
            print("Stress test requires --file argument")
            return
        stress_test(
            args.server, args.port, "upload", args.file,
            args.pool_mode, args.pool_size, args.server_workers,
            args.nomor, args.output
        )

if __name__ == "__main__":
    main()
