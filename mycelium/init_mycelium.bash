#ToDo. I'll automate this process based on data from Trainman agent
rabbitmqctl add_vhost demoAccess
rabbitmqctl add_user remoteClient01 ***
rabbitmqctl set_permissions -p demoAccess remoteClient01 ".*" ".*" ".*"
