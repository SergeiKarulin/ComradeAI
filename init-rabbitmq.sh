#!/bin/bash

sleep 10
rabbitmqctl add_vhost demoAccess
rabbitmqctl add_user remoteClient01 remoteClient01Pass
rabbitmqctl set_permissions -p demoAccess remoteClient01 ".*" ".*" ".*"