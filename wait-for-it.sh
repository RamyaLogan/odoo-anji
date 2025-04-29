#!/usr/bin/env bash
# wait-for-it.sh

set -e

host="$1"
shift
port="$2"
shift

while nc -z "$host" "$port"; do
  echo "Waiting for $host:$port..."
  sleep 2
done

exec "$@"
