#!/usr/bin/env bash

SERVER_IP="172.16.16.101"
PORT=8889
FILENAME="file_100mb.bin"
VOLUME="100MB"
OUTPUT_CSV="report.csv"
POOL_MODE="thread"

TEST_NUM=1

# Pastikan header CSV ada sekali
if ! grep -q "^Nomor,Operasi" "$OUTPUT_CSV" 2>/dev/null; then
  echo "Nomor,Operasi,Volume,Jumlah client worker pool,Jumlah server worker pool,Waktu total per client,Throughput per client,Jumlah sukses,Jumlah gagal,Error Message" > "$OUTPUT_CSV"
fi

# Daftar jumlah worker
CLIENT_WORKERS="1 5 50"
SERVER_WORKERS="50"

for sw in $SERVER_WORKERS; do
  for c in $CLIENT_WORKERS; do
    echo "Menjalankan download stress test: Clients=$c, ServerWorkers=$sw"
    python3 download.py \
      --server "$SERVER_IP" \
      --port "$PORT" \
      --mode stress \
      --filename "$FILENAME" \
      --volume "$VOLUME" \
      --pool_mode "$POOL_MODE" \
      --pool_size "$c" \
      --server_workers "$sw" \
      --nomor "$TEST_NUM" \
      --output "$OUTPUT_CSV"

    TEST_NUM=$(( TEST_NUM + 1 ))
  done
done

echo "Download stress test selesai. Lihat hasil di $OUTPUT_CSV"
