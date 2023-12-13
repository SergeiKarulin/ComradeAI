import pika
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_AGENT')
agnetRMQPass = os.getenv('RABBITMQ_DEFAULT_AGENT_PASS')
llama2Endpoint = os.getenv('LLAMA2_ENDPOINT')

credentials = pika.PlainCredentials(agentRMQLogin, agnetRMQPass)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='65.109.141.56', credentials = credentials, virtual_host = 'demoAccess'))

channel = connection.channel()

channel.queue_declare(queue='llama2')


def complete(prompt, model_url='http://127.0.0.1:5000/v1/completions', max_tokens=2000):
    payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "mode": "chat",
            "max_tokens": max_tokens
        }
    try:
        response = requests.post(model_url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get('choices')[0].get('content')
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"
    

def Reply(body):
    global initialPrompt
    #We ignore the body for now. Soon we'll apply agent responce protocol.
    return complete(initialPrompt, str(body.decode('utf-8')))

def on_request(ch, method, props, body):
    response = Reply(body)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='yandexGPT', on_message_callback=on_request)

channel.start_consuming()

#