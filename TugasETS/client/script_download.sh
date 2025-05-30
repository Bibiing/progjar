#!/usr/bin/env bash

SERVER_IP="172.16.16.101"
PORT=8889
FILENAME="file_100mb.txt" 
VOLUME="100MB"          
OUTPUT_CSV="report_thread.csv" 
POOL_MODE="thread" 

TEST_NUM=1

CLIENT_WORKERS="1 5 50" # Jumlah worker klien yang akan diuji
SERVER_WORKERS_REPORTED="50" # Jumlah worker server (hanya untuk label di laporan)

for sw in $SERVER_WORKERS_REPORTED; do
  for c_workers in $CLIENT_WORKERS; do
    echo "Menjalankan download stress test: Clients=$c_workers, ServerWorkers (Reported)=$sw, File=$FILENAME"
    
    python3 download.py \
      --server "$SERVER_IP" \
      --port "$PORT" \
      --mode stress \
      --filename "$FILENAME" \
      --volume "$VOLUME" \
      --pool_mode "$POOL_MODE" \
      --pool_size "$c_workers" \
      --server_workers "$sw" \
      --nomor "$TEST_NUM" \
      --output "$OUTPUT_CSV"

    TEST_NUM=$(( TEST_NUM + 1 ))
  done
done

echo "Download stress test selesai. Lihat hasil di $OUTPUT_CSV"