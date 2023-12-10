import pika
import os
from dotenv import load_dotenv
import requests

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_USER')
agnetRMQPass = os.getenv('RABBITMQ_DEFAULT_PASS')
yandexCloudAPIKey = os.getenv('YANDEXCLOUD_API_KEY')

credentials = pika.PlainCredentials(agentRMQLogin, agnetRMQPass)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='65.109.141.56', credentials = credentials, virtual_host = 'demoAccess'))

channel = connection.channel()

channel.queue_declare(queue='yandexGPT')

initialPrompt = {
    "modelUri": "gpt://b1g8p2irpvbrbqlcvbvi/yandexgpt-lite",
    "completionOptions": {
        "stream": False,
        "temperature": 0.6,
        "maxTokens": "2000"
    },
    "messages": [
        {
        "role": "system",
        "text": "Ты умный ассистент, созданный, чтобы помогать людям."
        },
    ]
}

def complete(prompt, strInput):
    new_message = {"role": "user", "text": strInput}
    
    prompt['messages'].append(new_message)
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Api-Key " + yandexCloudAPIKey
    }
    response = requests.post(url, headers=headers, json=prompt)
    result = response.text['alternatives'][0]['message']['text']
    return result
    

def Reply(body):
    global initialPrompt
    #We ignore the body for now. Soon we'll apply agent responce protocol.
    return complete(initialPrompt, body)

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