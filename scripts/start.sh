#!/bin/bash

./wait-for-it.sh "$RABBITMQ_HOST" "$RABBITMQ_TCP_PORT"

cd ..
supervisord -n
