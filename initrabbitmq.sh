#!/bin/bash

# Function to wait for RabbitMQ server to start
wait_for_rabbitmq() {
    echo "Waiting for RabbitMQ to start..."
    while ! rabbitmqctl status >/dev/null 2>&1; do
        sleep 1
    done
}

# Wait for RabbitMQ server to start
wait_for_rabbitmq

# Add vhost, user, and set permissions
rabbitmqctl add_vhost demoAccess
rabbitmqctl add_user remoteClient01 remoteClient01Pass
rabbitmqctl set_permissions -p demoAccess remoteClient01 ".*" ".*" ".*"
