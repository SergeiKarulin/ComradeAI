############## Mycelium Version 0.17 of 2024.01.13 ##############

import datetime
import uuid
import json
import base64
import io
import zlib
from PIL import Image
import aio_pika

class InvalidPromptException(Exception):
    pass

class InvalidRoutingStrategyException(Exception):
    def __init__(self, message="Invalid routing strategy format"):
        self.message = message
        super().__init__(self.message)

#Unified Prompt class
class UnifiedPrompt:
    def __init__(self, content_type, content, mime_type=None):
        self.content_type = content_type
        self.content = content
        self.mime_type = mime_type

# Message class
class Message:
    def __init__(self, role, unified_prompts, sender_info="", subAccount = "", send_datetime=None, diagnosticData=None, agentConfig = None,
                 costData = {'agentCost' : 0.0, 'networkComission' : 0.0, 'currency' : 'USD'},
                 myceliumVersion = "0.17"):
        self.sender_info = sender_info
        self.subAccount = subAccount
        self.role = self.validate_role(role)
        self.send_datetime = send_datetime if send_datetime else datetime.datetime.now()
        self.diagnosticData = diagnosticData
        self.agentConfig = agentConfig
        self.unified_prompts = self.validate_unified_prompts(unified_prompts) if unified_prompts else []
        self.costData = costData
        self.myceliumVersion = myceliumVersion
        
    def validate_role(self, role):
        valid_roles = {'system', 'user', 'assistant'}
        if role not in valid_roles:
            raise InvalidPromptException(f"Error: 'role' value in prompt is invalid. Must be one of {valid_roles}.")
        return role

    def validate_unified_prompts(self, unified_prompts):
        SUPPORTED_PROMPT_TYPES = {'text', 'url', 'image', 'document', 'audio', 'video', 'stream_of_bytes', 'stream_audio', 'stream_video'}
        for i, prompt in enumerate(unified_prompts):
            if not isinstance(prompt, UnifiedPrompt):
                raise InvalidPromptException(f"Error in unified prompt at index {i}: Not a UnifiedPrompt object.")
            if prompt.content_type not in SUPPORTED_PROMPT_TYPES:
                raise InvalidPromptException(f"Error at index {i}: Unsupported prompt content_type '{prompt.content_type}'. Must be one of: " + str(SUPPORTED_PROMPT_TYPES) + ".")
            if prompt.content_type == 'text':
                if not isinstance(prompt.content, str):
                    raise InvalidPromptException(f"Error in text prompt at index {i}: Content must be a string.")
            elif prompt.content_type == 'url':
                if not isinstance(prompt.content, str):
                    raise InvalidPromptException(f"Error in URL prompt at index {i}: Content must be a string.")
            elif prompt.content_type == 'image':
                if not isinstance(prompt.content, Image.Image):
                    raise InvalidPromptException(f"Error in image prompt at index {i}: Content must be a PIL Image object.")
            elif prompt.content_type == 'document':
                if not isinstance(prompt.content, bytes):
                    raise InvalidPromptException(f"Error in document prompt at index {i}: Content must be bytes.")
            elif prompt.content_type == 'audio':
                if not isinstance(prompt.content, bytes):
                    raise InvalidPromptException(f"Error in audio prompt at index {i}: Content must be bytes.")
            elif prompt.content_type == 'video':
                if not isinstance(prompt.content, bytes):
                    raise InvalidPromptException(f"Error in video prompt at index {i}: Content must be bytes.")
            else:
                raise InvalidPromptException(f"Error at index {i}: Unknown prompt content_type '{prompt.content_type}'.")
             # MIME type validation
            if prompt.content_type == 'text' and not prompt.mime_type.startswith('text/'):
                raise InvalidPromptException(f"Error in text prompt at index {i}: MIME type should start with 'text/'.")
            elif prompt.content_type == 'url' and not (prompt.mime_type.startswith('text/') or prompt.mime_type.startswith('application/') or prompt.mime_type.startswith('image/') or prompt.mime_type.startswith('video/') or prompt.mime_type.startswith('audio/')):
                raise InvalidPromptException(f"Error in URL prompt at index {i}: MIME type start witj 'text/' or 'image/' or 'video/' or 'audio/' or 'application/'.")
            elif prompt.content_type == 'image' and not prompt.mime_type.startswith('image/'):
                raise InvalidPromptException(f"Error in image prompt at index {i}: MIME type should start with 'image/'.")
            elif prompt.content_type == 'document' and not prompt.mime_type.startswith('application/'):
                raise InvalidPromptException(f"Error in document prompt at index {i}: MIME type should start with 'application/'.")
            elif prompt.content_type == 'audio' and not prompt.mime_type.startswith('audio/'):
                raise InvalidPromptException(f"Error in audio prompt at index {i}: MIME type should start with 'audio/'.")
            elif prompt.content_type == 'video' and not prompt.mime_type.startswith('video/'):
                raise InvalidPromptException(f"Error in video prompt at index {i}: MIME type should start with 'video/'.")
        return unified_prompts

# Dialog class
class Dialog:
    def __init__(self, dialog_id = str(uuid.uuid4()), messages=None, context=None, reply_to = None, lastMessageDiagnosticData = None, requestAgentConfig = None,
                 lastMessageCostData = {'agentCost' : 0.0, 'networkComission' : 0.0, 'currency' : 'USD'},
                 endUserCommunicationID = None, myceliumVersion = "0.17"):
        self.dialog_id = dialog_id
        self.reply_to = reply_to
        self.messages = context if context else []
        if messages:
            self.messages.extend(messages)
        self._update_totals()
        self.lastMessageDiagnosticData = lastMessageDiagnosticData
        self.requestAgentConfig = requestAgentConfig
        self.lastMessageCostData = lastMessageCostData
        self.endUserCommunicationID = endUserCommunicationID
        self.myceliumVersion = myceliumVersion

    def _update_totals(self):
        self.message_count = len(self.messages)
        if self.message_count > 0:
            self.lastMessageCostData = self.messages[-1].costData
            self.lastMessageDiagnosticData = self.messages[-1].diagnosticData

    def serialize(self):
        serialized_messages = []
        for message in self.messages:
            # Convert unified prompts to a serializable format
            serialized_unified_prompts = []
            for prompt in message.unified_prompts:
                serialized_prompt = {
                    'content_type': prompt.content_type,
                    'content': self._content_to_base64(prompt.content) if prompt.content_type in ['image', 'document', 'audio'] else prompt.content,
                    'mime_type': prompt.mime_type
                }
                serialized_unified_prompts.append(serialized_prompt)

            # Create the serialized message
            serialized_message = {
                'role': message.role,
                'unified_prompts': serialized_unified_prompts,
                'sender_info': message.sender_info,
                'send_datetime': message.send_datetime.isoformat(),
                'agentConfig' : message.agentConfig,
                'costData' : message.costData,
                'diagnosticData' : message.diagnosticData,
                'subAccount' : message.subAccount,
                'myceliumVersion' : message.myceliumVersion
            }
            serialized_messages.append(serialized_message)
        dialog_data = {
            'dialog_id': str(self.dialog_id),
            'reply_to': self.reply_to,
            'messages': serialized_messages,
            'lastMessageDiagnosticData': self.lastMessageDiagnosticData,
            'lastMessageCostData': self.lastMessageCostData,
            'requestAgentConfig' : self.requestAgentConfig,
            'endUserCommunicationID' : self.endUserCommunicationID,
            'myceliumVersion': self.myceliumVersion
        }
        return json.dumps(dialog_data)

    def _content_to_base64(self, content):
        if isinstance(content, Image.Image):
            buffered = io.BytesIO()
            content.save(buffered, format='PNG')
            return base64.b64encode(buffered.getvalue()).decode()
        elif isinstance(content, bytes):
            return base64.b64encode(content).decode()
        else:
            return content  # For non-binary content

    def deserialize(self, serialized_data):
        dialog_data = json.loads(serialized_data)
        self.dialog_id = dialog_data['dialog_id']
        self.reply_to = dialog_data['reply_to']
        self.lastMessageDiagnosticData = dialog_data['lastMessageDiagnosticData']
        self.requestAgentConfig = dialog_data['requestAgentConfig']
        self.lastMessageCostData = dialog_data['lastMessageCostData']
        self.endUserCommunicationID = dialog_data['endUserCommunicationID']
        self.myceliumVersion = dialog_data['myceliumVersion']    
        
        self.messages = []
        for data in dialog_data['messages']:
            # Reconstruct unified prompts from serialized data
            unified_prompts = []
            for serialized_prompt in data['unified_prompts']:
                content = self._base64_to_content(serialized_prompt['content'], serialized_prompt['content_type']) if serialized_prompt['content_type'] in ['image', 'document', 'audio'] else serialized_prompt['content']
                prompt = UnifiedPrompt(
                    content_type=serialized_prompt['content_type'],
                    content=content,
                    mime_type=serialized_prompt.get('mime_type')
                )
                unified_prompts.append(prompt)

            # Create the Message object
            message = Message(
                role=data['role'],
                unified_prompts=unified_prompts,
                agentConfig=data['agentConfig'],
                myceliumVersion=data['myceliumVersion'],
                costData=data['costData'],
                diagnosticData=data['diagnosticData'],
                sender_info=data['sender_info'],
                subAccount=data['subAccount'],
                send_datetime=datetime.datetime.fromisoformat(data['send_datetime'])
            )
            self.messages.append(message)
        self._update_totals()

    def _base64_to_content(self, base64_string, content_type):
        if content_type in ['image', 'document', 'audio']:
            byte_content = base64.b64decode(base64_string)
            if content_type == 'image':
                return Image.open(io.BytesIO(byte_content))
            else:
                return byte_content
        else:
            return base64_string  # For non-binary content

    def serialize_and_compress(self):
        serialized_data = self.serialize()
        return zlib.compress(serialized_data.encode())

    def decompress_and_deserialize(self, compressed_data):
        decompressed_data = zlib.decompress(compressed_data)
        self.deserialize(decompressed_data.decode())

# Mycelium class
class Mycelium:
    def __init__(self, host="65.109.141.56", vhost="myceliumVersion017", username=None, password=None, input_chanel=None, output_chanel=None, ComradeAIToken=None, dialogs=None, message_received_callback=None, myceliumVersion = "0.17"):
        self.myceliumVersion = myceliumVersion
        self.input_chanel = input_chanel if ComradeAIToken is None else ComradeAIToken
        self.output_chanel = output_chanel if output_chanel is not None else "myceliumRouter" + self.myceliumVersion
        self.dialogs = {} if dialogs is None else dialogs
        self.rabbitmq_host = host
        self.rabbitmq_username = username if ComradeAIToken is None else ComradeAIToken
        self.rabbitmq_password = password if ComradeAIToken is None else ComradeAIToken
        self.rabbitmq_vhost = vhost
        self.connection = None
        self.chanel = None
        self.message_received_callback = message_received_callback

    def dialog_count(self):
        return len(self.dialogs)

    async def connect_to_mycelium(self):      
        self.connection = await aio_pika.connect_robust(
            host=self.rabbitmq_host,
            login=self.rabbitmq_username,
            password=self.rabbitmq_password,
            virtualhost=self.rabbitmq_vhost
        )
        self.chanel = await self.connection.channel()
            
    async def start_server(self, allowNewDialogs = True):
        try:
            await self.connect_to_mycelium()
            queue = await self.chanel.declare_queue(self.input_chanel)
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        dialog = Dialog(reply_to=message.reply_to, dialog_id=message.correlation_id)
                        dialog_id = dialog.dialog_id
                        if dialog_id in self.dialogs:
                            self.dialogs[dialog_id].messages += dialog.messages
                            self.dialogs[dialog_id].requestAgentConfig = dialog.requestAgentConfig
                        elif dialog_id not in self.dialogs and allowNewDialogs:
                            self.dialogs[dialog_id] = dialog
                        else:
                            continue
                        dialog.decompress_and_deserialize(message.body)
                        cost_data = {
                            'agentCost': float(message.headers.get('costAgentCost', 0.0)),
                            'networkComission': float(message.headers.get('costNetworkComission', 0.0)),
                            'currency': message.headers.get('costCurrency', 'USD')
                        }
                        if dialog.messages:
                            dialog.messages[-1].costData = cost_data
                        self.dialogs[dialog_id]._update_totals()
                        if self.message_received_callback:
                            await self.message_received_callback(dialog)
                        self.dialogs[dialog_id]._update_totals() #We call it for the 2nd time to update after possible manipulations in message_received_callback()
        except Exception as ex:
            print("Failed to start server. Error: " + str(ex))

    async def send_to_mycelium(self, dialog, routingStrategy = {'strategy' : 'auto', 'params' : ''}):
        try:
            if not self.chanel:
                await self.connect_to_mycelium()
        except Exception as e:
            print(f"Error connecting to Mycelium. Error: {e}")
            return
        try:
            self.validate_routing_strategy(routingStrategy)
        except InvalidRoutingStrategyException as e:
            routingStrategy = {'strategy' : 'auto', 'params' : ''}
            print(f"Error: {e}")
        last_message = dialog.messages[-1]
        headers = {
            'costAgentCost': str(last_message.costData['agentCost']),
            'costNetworkComission': str(last_message.costData['networkComission']),
            'costCurrency': last_message.costData['currency'],
            'routingStrategy' : routingStrategy['strategy'],
            'routingParams' : routingStrategy['params'],
            'subAccount' : last_message.subAccount
        }
        if dialog.requestAgentConfig is not None:
            headers['requestAgentConfig'] = str(dialog.requestAgentConfig)
        if last_message.diagnosticData is not None:
            headers['diagnosticData'] = last_message.diagnosticData
        compressed_dialog = dialog.serialize_and_compress()
        message = aio_pika.Message(body=compressed_dialog, correlation_id=str(dialog.dialog_id), headers=headers, reply_to=dialog.reply_to)
        routing_key = self.output_chanel
        await self.chanel.default_exchange.publish(message, routing_key=routing_key)


    def validate_routing_strategy(self, routing_strategy):
        required_keys = {'strategy', 'params'}
        # Check if all required keys are present and there are no extra keys
        if set(routing_strategy.keys()) != required_keys:
            raise InvalidRoutingStrategyException("Routing strategy must only have keys 'strategy' and 'params'. Strategy set to default {'strategy' : 'auto', 'params' : ''}")
        # Check if the values are of expected types
        if not isinstance(routing_strategy['strategy'], str):
            raise InvalidRoutingStrategyException("The value for 'strategy' must be a string. Strategy set to default {'strategy' : 'auto', 'params' : ''}")
        if not isinstance(routing_strategy['params'], str):
            raise InvalidRoutingStrategyException("The value for 'params' must be a string. Strategy set to default {'strategy' : 'auto', 'params' : ''}")

    async def close(self):
        await self.connection.close()