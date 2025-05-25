#!/usr/bin/env bash

SERVER_IP="172.16.16.101"
PORT=8889
FILE_PATH="./doc/file_10mb.bin"
OUTPUT_CSV="report_processing.csv"
POOL_MODE="process"      

# rm -f "$OUTPUT_CSV"

TEST_NUM=1

for CLIENTS in 1 5 50; do
  for SERVER_WORKERS in 1; do
    echo "Menjalankan stress test: CLIENTS=$CLIENTS, SERVER_WORKERS=$SERVER_WORKERS"
    python3 upload.py \
      --server "$SERVER_IP" \
      --port "$PORT" \
      --mode stress \
      --file "$FILE_PATH" \
      --pool_mode "$POOL_MODE" \
      --pool_size "$CLIENTS" \
      --server_workers "$SERVER_WORKERS" \
      --nomor "$TEST_NUM" \
      --output "$OUTPUT_CSV"

    TEST_NUM=$(( TEST_NUM + 1 ))
  done
done

echo "Stress test selesai. Lihat hasil di $OUTPUT_CSV"
