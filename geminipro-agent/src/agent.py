import pika
import os
from dotenv import load_dotenv
import requests
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Image, Part

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_AGENT')
agnetRMQPass = os.getenv('RABBITMQ_DEFAULT_AGENT_PASS')
agentGCloudServer = os.getenv('GOOGLE_CLOUD_SERVER')
agentGCloudJSON = os.getenv('GOOGLE_CLOUD_JSON')
agentGCloudProjectID = os.getenv('GOOGLE_CLOUD_PROJECT')


def generate_text(prompt) -> str:
    playLoad = [
            prompt,
        ]
    project_id = "fair-catbird-407919"
    location = "us-central1"
    vertexai.init(project=project_id, location=location)
    multimodal_model = GenerativeModel("gemini-pro-vision")
    response = multimodal_model.generate_content(playLoad)
    return response.text

credentials = pika.PlainCredentials(agentRMQLogin, agnetRMQPass)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='65.109.141.56', credentials = credentials, virtual_host = 'demoAccess'))

channel = connection.channel()
channel.queue_declare(queue='gemini-pro') #ToDo. Define queue once after testing everything

def Reply(body):
    #We ignore the body for now. Soon we'll apply agent responce protocol.
    return generate_text(str(body.decode('utf-8')))

def on_request(ch, method, props, body):
    response = Reply(body)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='gemini-pro', on_message_callback=on_request)

channel.start_consuming()