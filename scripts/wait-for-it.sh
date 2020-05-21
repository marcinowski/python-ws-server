#!/bin/sh
# wait-for-it.sh

host="$1"
port="$2"

while ! nc -z "$host" "$port";
do
    echo "$host:$port is unavailable - sleeping"
    sleep 1
done;

echo "$host:$port is up - executing command"