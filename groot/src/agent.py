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

channel.queue_declare(queue='groot')

def Reply(body):
    #We ignore the body for now. Soon we'll apply agent responce protocol. Als we'll be more careful processing byte strings
    return "I am Groot!"

def on_request(ch, method, props, body):
    response = Reply(body)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='groot', on_message_callback=on_request)

channel.start_consuming()