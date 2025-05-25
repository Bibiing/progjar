#!/usr/bin/env python3
import os
import socket
import json
import base64
import logging
import argparse
import time
import csv
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def send_command(server_ip, server_port, command_str):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_ip, server_port))
        sock.sendall((command_str + "\r\n\r\n").encode())
        # Read header
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(1024)
            if not chunk:
                break
            data += chunk
        header, rest = data.split(b"\r\n\r\n", 1)
        parts = header.decode().split()
        status = parts[0]
        if status != "OK":
            raise Exception(" ".join(parts[1:]))
        size = int(parts[1])
        # Receive file data
        received = len(rest)
        file_data = [rest]
        while received < size:
            chunk = sock.recv(min(65536, size - received))
            if not chunk:
                break
            file_data.append(chunk)
            received += len(chunk)
        return b"".join(file_data)


def download_once(server_ip, server_port, filename, download_folder):
    start = time.time()
    try:
        data = send_command(server_ip, server_port, f"GET {filename}")
        os.makedirs(download_folder, exist_ok=True)
        outpath = os.path.join(download_folder, filename)

        if os.path.exists(outpath):
            name, ext = os.path.splitext(filename)
            outpath = os.path.join(
                download_folder,
                f"{name}_{int(time.time()*1000)}{ext}"
            )
        
        with open(outpath, 'wb') as f:
            f.write(data)
        duration = time.time() - start
        return True, duration, len(data), None

    except Exception as e:
        duration = time.time() - start
        return False, duration, 0, str(e)

def stress_test(server_ip, server_port, filename, volume,
                pool_mode, pool_size, server_workers,
                nomor, output_csv):
    executor_cls = ThreadPoolExecutor if pool_mode=="thread" else ProcessPoolExecutor
    download_folder = "downloaded_files"
    os.makedirs(download_folder, exist_ok=True)

    header = [
        "Nomor","Operasi","Volume","Jumlah client worker pool","Jumlah server worker pool",
        "Waktu total per client","Throughput per client","Jumlah sukses","Jumlah gagal","Error Message"
    ]
    write_header = not os.path.exists(output_csv)

    # default jika crash
    success = fail = 0
    avg_time = throughput = 0
    err_msg = ""

    try:
        start_all = time.time()
        results = []
        with executor_cls(max_workers=pool_size) as ex:
            futures = [ ex.submit(download_once, server_ip, server_port, filename, download_folder)
                        for _ in range(pool_size) ]
            for f in futures:
                results.append(f.result())
        total_all = time.time() - start_all

        success = sum(1 for ok,_,_,_ in results if ok)
        fail    = pool_size - success
        total_bytes = sum(size for _,_,size,_ in results)
        throughput = (total_bytes / total_all) if total_all>0 else 0
        avg_time   = (total_all / pool_size) if pool_size>0 else 0

    except Exception as e:
        # crash global
        success = 0
        fail    = pool_size
        err_msg = f"Stress crash: {e}"

    finally:
        # tulis CSV
        row = [
            nomor, "download", volume, pool_size, server_workers,
            round(avg_time,3), round(throughput/pool_size if pool_size>0 else 0,3),
            success, fail, err_msg
        ]
        with open(output_csv, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(header)
            writer.writerow(row)
        print(f"Hasil download stress test disimpan ke {output_csv}")
        print("Data:", row)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--server", required=True)
    p.add_argument("--port", type=int, default=8889)
    p.add_argument("--mode", choices=["upload","download","stress"], required=True)
    p.add_argument("--filename", help="File to download")
    p.add_argument("--volume", help="Label file size (e.g., 100MB)")
    p.add_argument("--pool_mode", choices=["thread","process"], default="thread")
    p.add_argument("--pool_size", type=int, default=1)
    p.add_argument("--server_workers", type=int, default=1)
    p.add_argument("--nomor", type=int, required=True)
    p.add_argument("--output", default="report.csv")
    args = p.parse_args()

    if args.mode == "stress":
        stress_test(
            args.server, args.port, args.filename, args.volume,
            args.pool_mode, args.pool_size, args.server_workers,
            args.nomor, args.output
        )
    else:
        print("Mode tidak dikenali untuk download.py; gunakan --mode stress")

if __name__=="__main__":
    main()
