import pika
import os
from dotenv import load_dotenv

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_USER')
agnetRMQPass = os.getenv('RABBITMQ_DEFAULT_PASS')

credentials = pika.PlainCredentials(agentRMQLogin, agnetRMQPass)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='65.109.141.56', credentials = credentials, virtual_host = 'demoAccess'))

channel = connection.channel()

channel.queue_declare(queue='rpc_queue')

def Reply():
    return "I am Groot!"

def on_request(ch, method, props, body):
    response = Reply()

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='rpc_queue', on_message_callback=on_request)

channel.start_consuming()