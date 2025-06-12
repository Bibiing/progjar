#!/usr/bin/env bash

HOST="172.16.16.101"
PORT="8889"
NC_OPTS="-q 1"

CONCURRENCY=1
CMD="$1"
FILE="$2"

if [[ -z "$CMD" || -z "$FILE" ]]; then
  echo "Usage: $0 <get|delete|post> <filename> [concurrency]"
  exit 1
fi

if [[ -n "$3" ]]; then
  CONCURRENCY=$3
fi

echo "Running $CONCURRENCY concurrent '$CMD' requests for '$FILE'"

for i in $(seq 1 $CONCURRENCY); do
  (
    case "$CMD" in
      get)
        printf "GET %s\n" "$FILE" | nc $NC_OPTS "$HOST" "$PORT"
        ;;
      delete)
        printf "DELETE %s\n" "$FILE" | nc $NC_OPTS "$HOST" "$PORT"
        ;;
      post)
        if [[ ! -f "$FILE" ]]; then
          echo "Error: '$FILE' not found"
          exit 2
        fi
        {
          printf "POST %s\n" "$FILE"
          cat "$FILE"
        } | nc $NC_OPTS "$HOST" "$PORT"
        ;;
      *)
        echo "Unknown command: $CMD"
        exit 1
        ;;
    esac
  ) &
done

wait

echo "All requests completed."