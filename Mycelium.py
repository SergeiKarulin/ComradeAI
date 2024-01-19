############## Mycelium Version 0.18 of 2024.01.18 ##############

import aio_pika
import base64
import copy
import datetime
import io
import json
import os
from PIL import Image
import threading
import uuid
import zlib

class InvalidPromptException(Exception):
    pass

class InvalidRoutingStrategyException(Exception):
    def __init__(self, message="Invalid routing strategy format"):
        self.message = message
        super().__init__(self.message)
        
class InvalidBillingDataException(Exception):
    """Exception raised for errors in the billing data format."""
    def __init__(self, message="Invalid billing data format"):
        self.message = message
        super().__init__(self.message)

class DialogDoesNotSupportReplies(Exception):
    """Exception raised for dialogs that don't have reply_to property, but called to reply."""
    def __init__(self, message="The dialog does not support replies as it doesn't have reply_to property value"):
        self.message = message
        super().__init__(self.message)
        
class DialogHasNoMessages(Exception):
    """Exception raised when trying to process a dialog with no messages in it."""
    def __init__(self, message="The dialog has no message to process"):
        self.message = message
        super().__init__(self.message)
        
#Unified Prompt class
class UnifiedPrompt:
    def __init__(self, content_type, content, mime_type=None):
        self.content_type = content_type
        self.content = content
        self.mime_type = mime_type
        
#Routing Strategy class with validator        
class RoutingStrategy:
    _rules = None
    _rules_lock = threading.Lock()
    _rules_loaded = False
    _file_tried_loading = False
    _file_load_successful = False

    def __init__(self, strategy = "auto", params = "text-to-text.en.global"):
        self.strategy = strategy
        self.params = params
        self.validate()
        
    def validate(self):
        required_keys = {'strategy', 'params'}
        # Check if all required keys are present and there are no extra keys
        if set(self.__dict__.keys()) != required_keys:
            raise InvalidRoutingStrategyException("Routing strategy must only have keys 'strategy' and 'params'. Strategy set to default {'strategy' : 'auto', 'params' : 'text-to-text.en.global'}")
        # Check if the values are of expected types
        if not isinstance(self.strategy, str):
            raise InvalidRoutingStrategyException("The value for 'strategy' must be a string. Strategy set to default {'strategy' : 'auto', 'params' : 'text-to-text.en.global'}")
        if not isinstance(self.params, str):
            raise InvalidRoutingStrategyException("The value for 'params' must be a string. Strategy set to default {'strategy' : 'auto', 'params' : 'text-to-text.en.global'}")
        pass
    
    def to_json(self):
        """Converts the RoutingStrategy object to a JSON string."""
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        """Creates a RoutingStrategy instance from a JSON string."""
        data = json.loads(json_str)
        return cls(**data)
    
# Message class
class Message:
    def __init__(self, role, unified_prompts, sender_info="", subAccount = "", send_datetime=None, diagnosticData=None, agentConfig = None,
                 billingData = None, routingStrategy = RoutingStrategy(), myceliumVersion = "0.18"):
        self.sender_info = sender_info
        self.subAccount = subAccount
        self.role = self.validate_role(role)
        self.send_datetime = send_datetime if send_datetime else datetime.datetime.now()
        self.diagnosticData = diagnosticData
        self.agentConfig = agentConfig
        self.unified_prompts = self.validate_unified_prompts(unified_prompts) if unified_prompts else []
        if billingData is None:
            billingData = []
        self.billingData = self.validate_billing_data(billingData)
        self.routingStrategy = routingStrategy
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

    def validate_billing_data(self, billing_data):
        if not isinstance(billing_data, list):
            raise InvalidBillingDataException("Billing data should be a list.")
        for item in billing_data:
            if not isinstance(item, dict):
                raise InvalidBillingDataException("Each item in billing data should be a dictionary.")
            if 'agent' not in item or not isinstance(item['agent'], str):
                raise InvalidBillingDataException("Each billing item must have a string 'agent' key.")
            if 'cost' not in item or not isinstance(item['cost'], (float, int)):
                raise InvalidBillingDataException("Each billing item must have a numeric 'cost' key.")
            if 'currency' not in item or not isinstance(item['currency'], str):
                raise InvalidBillingDataException("Each billing item must have a string 'currency' key.")
            if len(item['agent']) > 64:
                raise InvalidBillingDataException("'agent' string should not be more than 64 symbols.")
            if len(item['currency']) > 6:
                raise InvalidBillingDataException("'currency' string should not be longer than 6 characters.")
        return billing_data

# Dialog class
class Dialog:
    def __init__(self, dialog_id = str(uuid.uuid4()), messages=None, context=None, reply_to = None, lastMessageDiagnosticData = None, requestAgentConfig = None,
                 lastMessageBillingData = None, endUserCommunicationID = None, lastMessageRoutingStrategy = RoutingStrategy(), myceliumVersion = "0.18"):
        self.dialog_id = dialog_id
        self.reply_to = reply_to
        self.messages = context if context else []
        if lastMessageBillingData is None:
            lastMessageBillingData = []
        self.lastMessageBillingData = lastMessageBillingData
        if messages:
            self.messages.extend(messages)
        self._update_totals()
        self.lastMessageDiagnosticData = lastMessageDiagnosticData
        self.requestAgentConfig = requestAgentConfig
        self.endUserCommunicationID = endUserCommunicationID
        self.lastMessageRoutingStrategy = lastMessageRoutingStrategy
        self.myceliumVersion = myceliumVersion

    def _update_totals(self):
        self.message_count = len(self.messages)
        if self.message_count > 0:
            self.lastMessageBillingData = self.messages[-1].billingData
            self.lastMessageDiagnosticData = self.messages[-1].diagnosticData
            self.lastMessageRoutingStrategy = self.messages[-1].routingStrategy

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
                'billingData' : message.billingData,
                'diagnosticData' : message.diagnosticData,
                'routingStrategy' : message.routingStrategy.to_json(),
                'subAccount' : message.subAccount,
                'myceliumVersion' : message.myceliumVersion
            }
            serialized_messages.append(serialized_message)
        dialog_data = {
            'dialog_id': str(self.dialog_id),
            'reply_to': self.reply_to,
            'messages': serialized_messages,
            'lastMessageDiagnosticData': self.lastMessageDiagnosticData,
            'lastMessageBillingData' : self.lastMessageBillingData,
            'requestAgentConfig' : self.requestAgentConfig,
            'endUserCommunicationID' : self.endUserCommunicationID,
            'lastMessageRoutingStrategy' : self.lastMessageRoutingStrategy.to_json(),
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
        self.lastMessageBillingData = dialog_data['lastMessageBillingData']
        self.endUserCommunicationID = dialog_data['endUserCommunicationID']
        self.lastMessageRoutingStrategy = RoutingStrategy.from_json(dialog_data['lastMessageRoutingStrategy'])
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
                billingData=data['billingData'],
                diagnosticData=data['diagnosticData'],
                sender_info=data['sender_info'],
                subAccount=data['subAccount'],
                routingStrategy = RoutingStrategy.from_json(data['routingStrategy']),
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
        
    async def generate_error_message(self, errorMessage, billingData=None, sender_info=None, diagnosticData=None, subAccount = None):
        if not isinstance(errorMessage, str):
            errorMessage = str(errorMessage)
        if billingData is None:
            billingData = []
        if sender_info is None:
            sender_info = "ComradeAI"
        if diagnosticData is None:
            diagnosticData = ""
        if subAccount is None:
            subAccount = ""
        error_prompt = UnifiedPrompt(content_type="text", content=errorMessage, mime_type="text/plain")
        error_message = Message(
            role="assistant", 
            unified_prompts=[error_prompt], 
            sender_info=sender_info, 
            send_datetime=datetime.datetime.now(), 
            agentConfig=self.requestAgentConfig, 
            billingData=billingData,
            diagnosticData = diagnosticData,
            subAccount = subAccount,
            routingStrategy=RoutingStrategy("direct", self.reply_to)
        )
        self.messages.append(error_message)
        self._update_totals()

# Mycelium class
class Mycelium:
    def __init__(self, host="65.109.141.56", vhost="myceliumVersion018", username=None, password=None, input_chanel=None, output_chanel=None, ComradeAIToken=None, dialogs=None, message_received_callback=None, lastReceivedMessageBillingData = {}, myceliumVersion = "0.18"):
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
        self.lastReceivedMessageBillingData = lastReceivedMessageBillingData
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
            
    async def start_server(self, allowNewDialogs = False):
        try:
            await self.connect_to_mycelium()
            queue = await self.chanel.declare_queue(self.input_chanel)
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        headers = message.headers
                        dialog = Dialog(reply_to=message.reply_to, dialog_id=message.correlation_id)
                        dialog_id = dialog.dialog_id #We use it further to find the dialog after adding to self.dialogs.
                        if dialog_id in self.dialogs:
                            self.dialogs[dialog_id].messages += dialog.messages
                            self.dialogs[dialog_id].requestAgentConfig = dialog.requestAgentConfig
                        elif dialog_id not in self.dialogs and allowNewDialogs:
                            self.dialogs[dialog_id] = dialog
                        else:
                            continue
                        self.dialogs[dialog_id].decompress_and_deserialize(message.body)
                        # Updating billing data to apply new bills from Router
                        lastMessageBillingData = json.loads(message.headers.get("billingData", []))
                        self.lastReceivedMessageBillingData[dialog_id] = lastMessageBillingData
                        if self.dialogs[dialog_id].messages:
                            self.dialogs[dialog_id].messages[-1].billingData = lastMessageBillingData
                            diagnosticData = headers.get('diagnosticData', None)
                            if diagnosticData:
                                self.dialogs[dialog_id].messages[-1].diagnosticData = diagnosticData
                        self.dialogs[dialog_id]._update_totals()
                        if self.message_received_callback:
                            if await self.message_received_callback(self.dialogs[dialog_id]):
                                self.dialogs[dialog_id]._update_totals() #We call it for the 2nd time to update after possible manipulations in message_received_callback()
                            else:
                                self.dialogs = {}
        except Exception as ex:
            print("Failed to start server. Error: " + str(ex))

    async def send_to_mycelium(self, dialog_id, isReply = False, newestMessagesToSend = 1, autogenerateRoutingStrategies = False):
        #autogenerateRoutingStrategies applies dialog.reply_to as direct parameter to all messages being sent
        #newestMessagesToSend and autogenerateRoutingStrategies applicable only when isReply == True
        if not self.chanel:
            await self.connect_to_mycelium()
        
        if len(self.dialogs[dialog_id].messages) == 0:
            raise DialogHasNoMessages()
        
        last_message = self.dialogs[dialog_id].messages[-1]
        self.dialogs[dialog_id]._update_totals()
        routingStrategy = RoutingStrategy()
        if isReply:
            if self.dialogs[dialog_id].reply_to == None:
                raise DialogDoesNotSupportReplies()
            routingStrategy = RoutingStrategy("direct", self.dialogs[dialog_id].reply_to)
            temp_dialog = copy.deepcopy(self.dialogs[dialog_id])
            if newestMessagesToSend > len(temp_dialog.messages) - 1:
                #We can't send more messages than we have - the one we received to reply to
                newestMessagesToSend = len(temp_dialog.messages) - 1
            
            if autogenerateRoutingStrategies:
                temp_dialog.messages = temp_dialog.messages[-newestMessagesToSend:]
                for msg in temp_dialog.messages:
                    msg.routingStrategy = RoutingStrategy("direct", temp_dialog.reply_to)
            tmpBillingData = tmpBillingData = self.lastReceivedMessageBillingData.get(dialog_id, [])
            tmpBillingData.extend(temp_dialog.messages[-1].billingData)
            temp_dialog.messages[-1].billingData = tmpBillingData
            last_message.billingData = tmpBillingData
            compressed_dialog = temp_dialog.serialize_and_compress()
        else:
            if self.dialogs[dialog_id].reply_to == None:
                self.dialogs[dialog_id].reply_to = self.input_chanel
            routingStrategy = last_message.routingStrategy
            compressed_dialog = self.dialogs[dialog_id].serialize_and_compress()
        headers = {
            'billingData' : json.dumps(last_message.billingData),
            'routingStrategy' : routingStrategy.to_json(),
            'endUserCommunicationID' : self.dialogs[dialog_id].endUserCommunicationID,
            'subAccount' : last_message.subAccount
        }
        if last_message.diagnosticData is not None:
            headers['diagnosticData'] = last_message.diagnosticData
        if self.dialogs[dialog_id].requestAgentConfig is not None:
            headers['requestAgentConfig'] = json.dumps(self.dialogs[dialog_id].requestAgentConfig)
        
        message = aio_pika.Message(body=compressed_dialog, correlation_id=str(dialog_id), headers=headers, reply_to=self.dialogs[dialog_id].reply_to)
        routing_key = self.output_chanel
        await self.chanel.default_exchange.publish(message, routing_key=routing_key)
    
    async def close(self):
        await self.connection.close()