import datetime
import uuid
import json
import base64
import io
import zlib
from PIL import Image
import pika

# Message class
class Message:
    def __init__(self, textPrompts=None, imagePrompts=None, urlPrompts=None, sender_id="", send_datetime=None, token_cost=0, cost=0):
        self.textPrompts = textPrompts if textPrompts else []
        self.imagePrompts = imagePrompts if imagePrompts else []
        self.urlPrompts = urlPrompts if urlPrompts else []
        self.sender_id = sender_id
        self.send_datetime = send_datetime if send_datetime else datetime.datetime.now()
        self.token_cost = token_cost
        self.cost = cost

# Dialog class
class Dialog:
    def __init__(self, messages=None, context=None):
        self.dialog_id = uuid.uuid4()
        self.messages = context if context else []
        if messages:
            self.messages.extend(messages)
        self._update_totals()

    def _update_totals(self):
        self.message_count = len(self.messages)
        self.total_token_cost = sum(message.token_cost for message in self.messages)
        self.total_cost = sum(message.cost for message in self.messages)

    def _image_to_base64(self, image):
        img_format = image.format if image.format else 'PNG'
        buffered = io.BytesIO()
        image.save(buffered, format=img_format)
        image_str = base64.b64encode(buffered.getvalue()).decode()
        return {'data': image_str, 'format': img_format}

    def _base64_to_image(self, image_dict):
        image_data = base64.b64decode(image_dict['data'])
        image = Image.open(io.BytesIO(image_data))
        return image

    def serialize(self):
        serialized_messages = []
        for message in self.messages:
            serialized_message = {
                'textPrompts': message.textPrompts,
                'imagePrompts': [self._image_to_base64(img) for img in message.imagePrompts],
                'urlPrompts': message.urlPrompts,
                'sender_id': message.sender_id,
                'send_datetime': message.send_datetime.isoformat(),
                'token_cost': message.token_cost,
                'cost': message.cost
            }
            serialized_messages.append(serialized_message)
        return json.dumps(serialized_messages)

    def deserialize(self, serialized_data):
        message_data = json.loads(serialized_data)
        self.messages = []
        for data in message_data:
            message = Message(
                textPrompts=data['textPrompts'],
                imagePrompts=[self._base64_to_image(img_dict) for img_dict in data['imagePrompts']],
                urlPrompts=data['urlPrompts'],
                sender_id=data['sender_id'],
                send_datetime=datetime.datetime.fromisoformat(data['send_datetime']),
                token_cost=data['token_cost'],
                cost=data['cost']
            )
            self.messages.append(message)
        self._update_totals()

    def serialize_and_compress(self):
        serialized_data = self.serialize()
        return zlib.compress(serialized_data.encode())

    def decompress_and_deserialize(self, compressed_data):
        decompressed_data = zlib.decompress(compressed_data)
        self.deserialize(decompressed_data.decode())

# Mycelium class
class Mycelium:
    def __init__(self, host, vhost, username, password, queue_name, dialogs=None):
        self.queue_name = queue_name
        self.dialogs = dialogs if dialogs else []
        self.rabbitmq_host = host
        self.rabbitmq_username = username
        self.rabbitmq_password = password
        self.rabbitmq_vhost = vhost
        self.connection = None
        self.channel = None

    def dialog_count(self):
        return len(self.dialogs)

    def add_dialog(self, dialog):
        self.dialogs.append(dialog)
            
    def connect_to_mycelium(self):
        credentials = pika.PlainCredentials(self.rabbitmq_username, self.rabbitmq_password)
        parameters = pika.ConnectionParameters(self.rabbitmq_host, virtual_host=self.rabbitmq_vhost, credentials=credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def disconnect_from_rabbitmq(self):
        if self.connection:
            self.connection.close()

    def start_server(self, server_logic_function):
        self.connect_to_mycelium()
        self.channel.queue_declare(queue=self.queue_name)

        def on_request(ch, method, properties, body):
            dialog = Dialog()
            dialog.decompress_and_deserialize(body)
            response_dialog = server_logic_function(dialog)
            
            compressed_response = response_dialog.serialize_and_compress()
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(correlation_id=properties.correlation_id),
                body=compressed_response
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=self.queue_name, on_message_callback=on_request)
        print("Mycelium Agent Server is waiting for requests...")
        self.channel.start_consuming()

    def init_mycelium_client(self):
        self.connect_to_mycelium()
        self.callback_queue = self.channel.queue_declare('', exclusive=True).method.queue
        self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.mycelium_client_on_response, auto_ack=True)
        self.response = None
        self.correlation_id = None

    def mycelium_client_on_response(self, ch, method, properties, body):
        if self.correlation_id == properties.correlation_id:
            response_dialog = Dialog()
            response_dialog.decompress_and_deserialize(body)
            self.dialogs[0].messages += response_dialog.messages

    def send_to_mycelium(self, dialog):
        self.response = None
        self.correlation_id = str(uuid.uuid4()) 
        compressed_dialog = dialog.serialize_and_compress()
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.correlation_id,
            ),
            body=compressed_dialog
        )
        print(f"Sent message to server with correlation_id: {self.correlation_id}")
        self.connection.process_data_events(time_limit=None)
        return self.dialogs[0]
                
    def print_dialogs(self):
        for dialog in self.dialogs:
            print(f"Dialog ID: {dialog.dialog_id}")
            for message in dialog.messages:
                print(f"Sender ID: {message.sender_id}")
                print(f"Sent at: {message.send_datetime}")
                for text in message.textPrompts:
                    print(f"Text: {text['content']}")
                for url in message.urlPrompts:
                    print(f"URL: {url['url']}")
                print(f"Images: {len(message.imagePrompts)}")
                print(f"Token Cost: {message.token_cost}")
                print(f"Cost: {message.cost}")
                print("---")