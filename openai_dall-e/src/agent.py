from dotenv import load_dotenv

import openai
import os
import pika
import requests

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_AGENT')
agnetRMQPass = os.getenv('RABBITMQ_DEFAULT_AGENT_PASS')

openAIAPIKey = os.getenv('OPENAI_API_KEY')

credentials = pika.PlainCredentials(agentRMQLogin, agnetRMQPass)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='65.109.141.56', credentials = credentials, virtual_host = 'demoAccess'))
channel = connection.channel()
channel.queue_declare(queue='openai_dall-e')


def complete(prompt):
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
        )
    url = response.data[0].url
    response = requests.get(url)
    return response.content
    

def Reply(body):
    return complete(str(body.decode('utf-8')))

def on_request(ch, method, props, body):
    response = Reply(body)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='openai_dall-e', on_message_callback=on_request)

channel.start_consuming()