import pika
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_AGENT')
agnetRMQPass = os.getenv('RABBITMQ_DEFAULT_AGENT_PASS')
yandexCloudAPIKey = os.getenv('YANDEXCLOUD_API_KEY')

credentials = pika.PlainCredentials(agentRMQLogin, agnetRMQPass)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='65.109.141.56', credentials = credentials, virtual_host = 'demoAccess'))

channel = connection.channel()

channel.queue_declare(queue='yandexGPT')

initialPrompt = {
    "modelUri": "gpt://b1g8p2irpvbrbqlcvbvi/yandexgpt-lite", #You'll need your own directory ID here. I'll get rid of it later (#ToDo)
    "completionOptions": {
        "stream": False,
        "temperature": 0.6,
        "maxTokens": "2000"
    },
    "messages": [
        {
        "role": "system",
        "text": "Ты искусственный интеллект, отвечающий на вопросы."
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
    result = response.text
    result_json = json.loads(result)
    print(result_json)
    return result_json['result']['alternatives'][0]['message']['text']
    

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