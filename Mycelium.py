############## Mycelium Version 0.18.24 of 2024.05.05 ##############

import aio_pika
import base64
import copy
from datetime import datetime
import io
import json
import pika
from PIL import Image
import random
import re
import string
import sys
import threading
import uuid
import warnings
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
        self.send_datetime = send_datetime if send_datetime else datetime.now()
        self.diagnosticData = diagnosticData
        self.agentConfig = agentConfig
        self.unified_prompts = self.validate_unified_prompts(unified_prompts) if unified_prompts else []
        if billingData is None:
            billingData = []
        self.billingData = self.validate_billing_data(billingData)
        self.routingStrategy = routingStrategy
        self.myceliumVersion = myceliumVersion

    def __str__(self):
        if not self.unified_prompts or self.unified_prompts == []:
            return "Message is empty."
        messages_str_list = []
        for k, prompt in enumerate(self.unified_prompts, start=1):
            if prompt.content_type == "text":
                messages_str_list.append(f"Prompt {k}: content type: {prompt.content_type}, mime-type: {prompt.mime_type}, content: {prompt.content}")   
            else:
                messages_str_list.append(f"Prompt {k}: content type: {prompt.content_type}, mime-type: {prompt.mime_type}.")  
        return "\n".join(messages_str_list)
        
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
    def __init__(self, dialog_id = None, messages=None, context=None, reply_to = None, lastMessageDiagnosticData = None, requestAgentConfig = None,
                 lastMessageBillingData = None, endUserCommunicationID = None, lastMessageRoutingStrategy = RoutingStrategy(), myceliumVersion = "0.18"):
        self.dialog_id = dialog_id if dialog_id is not None else str(uuid.uuid4())
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
        
    @classmethod
    def Create(self, textPrompt = None, imagePrompt = None, audioPrompt = None, audioMimeType = None, 
               documentPrompt = None, documentMimeType = None, url = None, urlMimeType = None, agent=None):
        unifiedPrompts = []
        if textPrompt:
            if not isinstance(textPrompt, str) and not isinstance(textPrompt, list):
                raise TypeError ("textPrompt must be either a string or a list of strings")
            if isinstance(textPrompt, str):
                textPrompt = [textPrompt]
            if isinstance(textPrompt, list):
                for text in textPrompt:
                    if isinstance(text, str):
                        unifiedPrompts.append(UnifiedPrompt(content_type="text", content=text, mime_type="text/plain"))
                    else:
                        raise TypeError ("textPrompt must be either a string or a list of strings")
        if imagePrompt:
            if not isinstance(imagePrompt, Image.Image) and not isinstance(imagePrompt, list):
                #TODO. Process the file path(s) to load image
                raise TypeError ("imagePrompt must be either a Pillow Image or a list of Pillow Images")
            if isinstance(imagePrompt, Image.Image):
                imagePrompt = [imagePrompt]
            if isinstance(imagePrompt, list):
                for img in imagePrompt:
                    if isinstance(img, Image.Image):
                        unifiedPrompts.append(UnifiedPrompt(content_type="image", content=img, mime_type=f"image/{imagePrompt.format.lower()}"))
                    else:
                        raise TypeError ("imagePrompt must be either a Pillow Image or a list of Pillow Images")
        if audioPrompt and audioMimeType:
            if not isinstance(audioPrompt, bytes) and not isinstance(audioPrompt, list):
                #TODO. Process the file path(s) to load audio file
                raise TypeError("audioPrompt must be either a Byte array or a list of byte arrays")
            if not isinstance(audioMimeType, str) and not isinstance(audioMimeType, list):
                raise TypeError("audioMimeType must be either a string starting with audio/ or a list of strings where each starts with audio/")
            if isinstance(audioPrompt, bytes):
                audioPrompt = [audioPrompt]
            if isinstance(audioMimeType, str):
                audioMimeType = [audioMimeType]
            for i, audio in enumerate(audioPrompt):
                if i < len(audioMimeType):
                    mimeType = audioMimeType[i]
                else:
                    mimeType = audioMimeType[0]
                if isinstance(audio, bytes) and mimeType.startswith("audio/"):
                    unifiedPrompts.append(UnifiedPrompt(content_type="audio", content=audioPrompt[i], mime_type=mimeType))
                else:
                    raise TypeError("audioMimeType must be either a string starting with audio/ or a list of strings where each starts with audio/")
        if documentPrompt and documentMimeType:
            print("Not implemented...")
            #TODO. Finish for 3 document types (XLSXm DOCX, XML???)
            #TODO. Process the file path(s) to load document

        message = Message(role="user", unified_prompts=unifiedPrompts, sender_info="ComradeAI Client", send_datetime=datetime.now())
        resultDialog = Dialog(messages=[message])
        resultDialog._update_totals()
        if agent != None:
            resultDialog = agent.Invoke(resultDialog)
            resultDialog._update_totals()
        return (resultDialog)

    def __add__(self, other):
        if not isinstance(other, Dialog) and not isinstance(other, str) and not isinstance(other, list):
            raise ValueError("Can only add Dialog and string or [string] instances together")
        if isinstance(other, str):
            combined_messages = self.messages + [Message(role="user", unified_prompts=[UnifiedPrompt(content=other, content_type="text", mime_type="text/plain")],  send_datetime=datetime.now())]
            newDialog = Dialog(messages=combined_messages, dialog_id=self.dialog_id, reply_to=self.reply_to, requestAgentConfig=self.requestAgentConfig, endUserCommunicationID=self.endUserCommunicationID)
        elif isinstance(other, list):
            combined_messages = self.messages
            for strvalue in other:
                combined_messages.append(Message(role="user", unified_prompts=[UnifiedPrompt(content=strvalue, content_type="text", mime_type="text/plain")],  send_datetime=datetime.now()))
            newDialog = Dialog(messages=combined_messages, dialog_id=self.dialog_id, reply_to=self.reply_to, requestAgentConfig=self.requestAgentConfig, endUserCommunicationID=self.endUserCommunicationID)
        elif isinstance(other, Dialog):
            combined_messages = self.messages + other.messages
            newDialog = Dialog(messages=combined_messages, dialog_id=self.dialog_id, reply_to=self.reply_to, requestAgentConfig=self.requestAgentConfig, endUserCommunicationID=self.endUserCommunicationID)
        return newDialog
    
    def __radd__(self, other):
        if not isinstance(other, Dialog) and not isinstance(other, str) and not isinstance(other, list):
            raise ValueError("Can only add Dialog and string or [string] instances together")
        if isinstance(other, str):
            combined_messages = [Message(role="user", unified_prompts=[UnifiedPrompt(content=other, content_type="text", mime_type="text/plain")],  send_datetime=datetime.now())] + self.messages
            newDialog = Dialog(messages=combined_messages, dialog_id=self.dialog_id, reply_to=self.reply_to, requestAgentConfig=self.requestAgentConfig, endUserCommunicationID=self.endUserCommunicationID)
        elif isinstance(other, list):
            combined_messages = []
            for strvalue in other:
                combined_messages.append(Message(role="user", unified_prompts=[UnifiedPrompt(content=strvalue, content_type="text", mime_type="text/plain")],  send_datetime=datetime.now()))
            combined_messages.extend(self.messages)
            newDialog = Dialog(messages=combined_messages, dialog_id=self.dialog_id, reply_to=self.reply_to, requestAgentConfig=self.requestAgentConfig, endUserCommunicationID=self.endUserCommunicationID)
        elif isinstance(other, Dialog):
            combined_messages = self.messages + other.messages
            newDialog = Dialog(messages=combined_messages, dialog_id=other.dialog_id, reply_to=other.reply_to, requestAgentConfig=other.requestAgentConfig, endUserCommunicationID=other.endUserCommunicationID)
        return newDialog
    
    def __mul__(self, other):
        if not isinstance(other, Dialog) and not isinstance(other, str) and not isinstance(other, list):
            raise ValueError("Can only intersect Dialog and string or [string] instances together")
        if len(self.messages)<1:
            raise IndexError("Your dialog must have at least one message.")
        if isinstance(other, str):
            newDialog = copy.deepcopy(self)
            newDialog.messages[-1].unified_prompts = newDialog.messages[-1].unified_prompts + [UnifiedPrompt(content=other, content_type="text", mime_type="text/plain")]
            resut = newDialog
        elif isinstance(other, list):
            resultDialogs = []
            for strvalue in other:
                if not isinstance(strvalue, str):
                    raise ValueError("The intersected list must contain strings only")
                newDialog = copy.deepcopy(self)
                newDialog.messages[-1].unified_prompts = self.messages[-1].unified_prompts + [UnifiedPrompt(content=strvalue, content_type="text", mime_type="text/plain")]
                resultDialogs.append(newDialog)
            resut = resultDialogs
        elif isinstance(other, Dialog):
            if len(other.messages) < 1:
                raise IndexError("Both dialogs must have at least one message.")
            result = copy.deepcopy(self)
            result.messages[-1].unified_prompts = result.messages[-1].unified_prompts + other.messages[-1].unified_prompts
            resut = result
        return resut
    
    def __rmul__(self, other):
        if not isinstance(other, Dialog) and not isinstance(other, str) and not isinstance(other, list):
            raise ValueError("Can only intersect Dialog and string or [string] instances together")
        if len(self.messages)<1:
            raise IndexError("Your dialog must have at least one message.")
        if isinstance(other, str):
            newDialog = copy.deepcopy(self)
            newDialog.messages[-1].unified_prompts = [UnifiedPrompt(content=other, content_type="text", mime_type="text/plain")] + newDialog.messages[-1].unified_prompts
            resut = newDialog
        elif isinstance(other, list):
            resultDialogs = []
            for strvalue in other:
                if not isinstance(strvalue, str):
                    raise ValueError("The intersected list must contain strings only")
                newDialog = copy.deepcopy(self)
                newDialog.messages[-1].unified_prompts = [UnifiedPrompt(content=strvalue, content_type="text", mime_type="text/plain")] + newDialog.messages[-1].unified_prompts
                resultDialogs.append(newDialog)
            resut = resultDialogs
        elif isinstance(other, Dialog):
            if len(other.messages) < 1:
                raise IndexError("Both dialogs must have at least one message.")
            result = copy.deepcopy(self)
            result.messages[-1].unified_prompts = other.messages[-1].unified_prompts + result.messages[-1].unified_prompts
            resut = result
        return resut
    
    def __str__(self):
        if not self.messages or self.messages == []:
            return "Dialog is empty."
        messages_str_list = []
        for i, message in enumerate(self.messages, start=1):
            message_str = f"Message {i}: {message.role}"
            messages_str_list.append(message_str)
            for k, prompt in enumerate(message.unified_prompts, start=1):
                if prompt.content_type == "text":
                    messages_str_list.append(f"Prompt {k}: content type: {prompt.content_type}, mime-type: {prompt.mime_type}, content: {prompt.content}")   
                else:
                    messages_str_list.append(f"Prompt {k}: content type: {prompt.content_type}, mime-type: {prompt.mime_type}.")  
        return "\n".join(messages_str_list)

    @classmethod
    def FromTemplate(self, template, valueDictionary):
        # Осталось сделать перемножение... но, [Dialog] * [DialogTemplate], по ходу, не сделаю. 
        # Такое перемножение зарулим примером, где диалоги перебираются и множатся на массивы словарей с сохарнением в общий лист.

        def find_unique_placeholders(dialogTemplate):
            if not isinstance(dialogTemplate, DialogTemplate):
                raise TypeError ("dialogTemplate must be of type DialogTemplate")
            pattern = r"\{(\w+)\}"  # Matches placeholders in the format {placeholder}
            placeholders = set()
            for message in dialogTemplate.messages:
                for prompt in message.unified_prompts:
                    if prompt.content_type == "text":
                            matches = re.findall(pattern, prompt.content)
                            placeholders.update(matches)
            if len(placeholders) == 0:
                raise TypeError ("dialogTemplate is not a proper DialogTemplate as there is no prompt with content_type text containing any placeholders like {placeholder_name}")
            return placeholders

        if not isinstance(template, DialogTemplate) and not isinstance(valueDictionary, dict):
            raise TypeError ("template must be a DialogTemplate object and valueDictionary must be a dictionary of {placeholderName : value}")
        
        placeholders = find_unique_placeholders(template)
        missing_placeholders = placeholders - valueDictionary.keys()
        if missing_placeholders:
            raise ValueError(f"Missing replacement for placeholders: {', '.join(missing_placeholders)}")
        
        result = Dialog(dialog_id = template.dialog_id, messages = copy.deepcopy(template.messages), reply_to = template.reply_to,
                        lastMessageDiagnosticData = template.lastMessageDiagnosticData, requestAgentConfig = template.requestAgentConfig,
                        lastMessageBillingData = template.lastMessageBillingData, endUserCommunicationID = template.endUserCommunicationID,
                        lastMessageRoutingStrategy= template.lastMessageRoutingStrategy)        
        
        for msg in result.messages:
            for prmpt in msg.unified_prompts:
                if prmpt.content_type == "text":
                    try:
                        prmpt.content = prmpt.content.format(**valueDictionary)
                    except KeyError as e:
                        raise ValueError(f"Missing replacement for placeholder: {e}")
        return result

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
        return json.dumps(dialog_data, ensure_ascii=False)

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
                send_datetime=datetime.fromisoformat(data['send_datetime'])
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
        
    async def generate_error_message(self, errorMessage, billingData=None, sender_info=None, diagnosticData=None, 
                                     subAccount = None):
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
            send_datetime=datetime.now(), 
            agentConfig=self.requestAgentConfig, 
            billingData=billingData,
            diagnosticData = diagnosticData,
            subAccount = subAccount,
            routingStrategy=RoutingStrategy("direct", self.reply_to)
        )
        self.messages.append(error_message)
        self._update_totals()
        
    def SaveToFile(self, filename, use_zip=False):
        """
        Serialize the dialog, optionally compress it, and save it to a specified file.
        :param filename: The name of the file where the dialog should be saved.
        :param use_zip: Boolean flag indicating whether to compress the data before saving.
        """
        with open(filename, 'wb' if use_zip else 'w') as file:
            data_to_save = self.serialize_and_compress() if use_zip else self.serialize()
            if use_zip:
                # When using binary mode ('wb'), ensure data is in bytes
                file.write(data_to_save)
            else:
                # When not using zip, data is saved as a string
                file.write(data_to_save)
                
    @classmethod
    def CreateFromFile(cls, filename):
        """
        Create a Dialog instance from a file, automatically detecting if the data is compressed.
        :param filename: The name of the file to load the dialog from.
        :return: A Dialog instance.
        """
        with open(filename, 'rb') as file:  # Always read in binary mode
            data_to_load = file.read()
            try:
                # Try decompressing, assuming the data might be compressed
                decompressed_data = zlib.decompress(data_to_load)
                dialog_instance = cls()
                # If decompression was successful, deserialize the decompressed data
                dialog_instance.deserialize(decompressed_data.decode())
            except zlib.error:
                # If decompression fails, assume the data was not compressed and is in plain text format
                dialog_instance = cls()
                dialog_instance.deserialize(data_to_load.decode())  # Decode since we read in binary mode
            return dialog_instance

# Mycelium class
class Mycelium:
    def __init__(self, host="65.109.141.56", vhost="myceliumVersion018", username=None, password=None, input_chanel=None, output_chanel=None, ComradeAIToken=None, dialogs=None, message_received_callback=None, lastReceivedMessageBillingData = {}, serverAsyncModeThreads = 10, multiClientInstance = False, tempQueueTTL = 30 * 60 * 1000, myceliumVersion = "0.18"):
        #TODO. Don't forget to switch to 020 after testing is done.
        #TODO. I must allow to use different Mycelium hosts. In order to do it, I have to lauch one in Russia, like in the Office on Pushkina 38 :)
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
        self.message_received_callback = message_received_callback #Only used in a server mode when start_server is awaited.
        self.serverAsyncModeThreads = serverAsyncModeThreads
        # In case a client instance serves may users like visual designer, this thing must be True. If so, each request will create a separate random queue to 
        # reseive responce, and this queue will live for tempQueueTTL (default 30*60*1000) miliseconds
        self.multiClientInstance = multiClientInstance 
        self.tempQueueTTL = tempQueueTTL

    def dialog_count(self):
        return len(self.dialogs)
    
    def Merge(self, dialogs):
        #TODO. Make a proper merge. Requires uuuid for messages or manual checksum calculation for each message
        if isinstance(dialogs, Dialog):
            dialogs = [dialogs]
        for dialog in dialogs:
            if isinstance(dialog, Dialog):
                self.dialogs[dialog.dialog_id] = dialog
            else:
                raise TypeError("You can only merge a Dialog object or a list of Dialog objects")
    
    # Must NEVER EVER be used from here
    def Dialog(self, textPrompt = None, imagePrompt = None, audioPrompt = None, audioMimeType = None, documentPrompt = None, documentMimeType = None, url = None, urlMimeType = None, agent = None):
        newDialog = Dialog.Create(mycelium = self, textPrompt = textPrompt, imagePrompt = imagePrompt, audioPrompt = audioPrompt, audioMimeType = audioMimeType, documentPrompt = documentPrompt, documentMimeType = documentMimeType, url = url, urlMimeType = urlMimeType)
        newDialog._update_totals()
        self.dialogs[newDialog.dialog_id] = newDialog
        if agent is not None:
            newDialog = agent.Invoke(newDialog)
            newDialog._update_totals()
        return newDialog
    
    # Must NEVER EVER be used from here
    async def DialogAsync(self, textPrompt = None, imagePrompt = None, audioPrompt = None, audioMimeType = None, documentPrompt = None, documentMimeType = None, url = None, urlMimeType = None, agent = None):
        newDialog = Dialog.Create(mycelium = self, textPrompt = textPrompt, imagePrompt = imagePrompt, audioPrompt = audioPrompt, audioMimeType = audioMimeType, documentPrompt = documentPrompt, documentMimeType = documentMimeType, url = url, urlMimeType = urlMimeType)
        newDialog._update_totals()
        self.dialogs[newDialog.dialog_id] = newDialog
        if agent is not None:
            newDialog = await agent.InvokeAsync(newDialog)
            newDialog._update_totals()
        return newDialog
    
    async def connectAsync(self):
        self.connection = await aio_pika.connect_robust(
            host=self.rabbitmq_host,
            login=self.rabbitmq_username,
            password=self.rabbitmq_password,
            virtualhost=self.rabbitmq_vhost
        )
        self.chanel = await self.connection.channel()
        await self.chanel.set_qos(prefetch_count=self.serverAsyncModeThreads)

    async def connect_to_mycelium(self): 
        #Will be deprecated in further releases. 
        warnings.warn("connect_to_mycelium() is deprecated and will be removed in a future versions. Use connect() or await connectAsync() instead.", DeprecationWarning, stacklevel=2)
        self.connection = await aio_pika.connect_robust(
            host=self.rabbitmq_host,
            login=self.rabbitmq_username,
            password=self.rabbitmq_password,
            virtualhost=self.rabbitmq_vhost
        )
        self.chanel = await self.connection.channel()
        await self.chanel.set_qos(prefetch_count=self.serverAsyncModeThreads)

    def connect(self):      
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rabbitmq_host,
                virtual_host=self.rabbitmq_vhost,  # Include the virtual host here
                credentials=pika.PlainCredentials(
                    self.rabbitmq_username, self.rabbitmq_password
                )
            )
        )
        self.chanel = self.connection.channel()
        # Declare the reply_to queue if it doesn't exist
        if self.multiClientInstance:
            self.input_chanel = self._generate_random_sequence(8) + "@" + self.input_chanel
        self.chanel.queue_declare(queue=self.input_chanel, durable=False, arguments={'x-expires': self.tempQueueTTL})
            
    async def start_server(self, allowNewDialogs = False):
        try:
            await self.connect_to_mycelium()
            queue = await self.chanel.declare_queue(self.input_chanel)
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await message.ack()
                    try:                        
                        headers = message.headers
                        dialog = Dialog(reply_to=message.reply_to, dialog_id=message.correlation_id)
                        dialog_id = dialog.dialog_id #We use it further to find the dialog after adding to self.dialogs.
                        if dialog_id in self.dialogs:
                            dialog.decompress_and_deserialize(message.body)
                            self.dialogs[dialog_id].messages += dialog.messages
                            self.dialogs[dialog_id].requestAgentConfig = dialog.requestAgentConfig
                        elif dialog_id not in self.dialogs and allowNewDialogs:
                            dialog.decompress_and_deserialize(message.body)
                            self.dialogs[dialog_id] = dialog
                        else:
                            continue
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
                            if await self.message_received_callback(dialog):
                                self.dialogs[dialog_id]._update_totals() #We call it for the 2nd time to update after possible manipulations in message_received_callback()
                            else:
                                self.dialogs = {}
                    except Exception as process_ex:
                        print(f"Error processing message: {process_ex}")
        except Exception as ex:
            print("Failed to start server. Error: " + str(ex))
            
    async def ensure_connected(self):
        if not self.connection or self.connection.is_closed:
            await self.connectAsync()  # Assumes connectAsync() is your method to asynchronously connect

    async def send_to_mycelium(self, dialog_id, isReply = False, newestMessagesToSend = 1, autogenerateRoutingStrategies = False):          
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
        
        # print(str(datetime.now()) + " Sending message with headers: " + str(message.headers))
        # sys.stdout.flush() # This is how we sorted out 4 month flaky error with type2 MQ headers

        try:
            await self.ensure_connected()
            await self.chanel.default_exchange.publish(message, routing_key=routing_key)
        except aio_pika.exceptions.AMQPConnectionError as e:
            print(f"Connection error detected: {e}. Attempting to reconnect...")
            await self.connect_to_mycelium()
            await self.chanel.default_exchange.publish(message, routing_key=routing_key)  # Retry publishing
        except Exception as e:
            print(f"Failed to sort connection problem by reconnecting: {e}")
    
    async def close(self):
        await self.connection.close()
        
    def _generate_random_sequence(self, length):
        characters = string.ascii_lowercase + string.digits
        random_sequence = ''.join(random.choice(characters) for _ in range(length))
        return random_sequence

class Agent:
    def __init__(self, mycelium, service, serviceParams = "", timeoutOfSyncRequest = 600):
        self.mycelium = mycelium
        self.service = service
        self.serviceParams = serviceParams
        # In case Agent has timeoutOfSyncRequest defined, we ignore (replace) tempQueueTTL. But if tempQueueTTL < timeoutOfSyncRequest we raise and exception.
        self.timeoutOfSyncRequest = timeoutOfSyncRequest
        if self.timeoutOfSyncRequest > self.mycelium.tempQueueTTL/1000:
            raise ValueError(f"The timeoutOfSyncRequest value of {self.timeoutOfSyncRequest} seconds is higher than the expected maximum of {self.mycelium.tempQueueTTL} miliseconds defined in tempQueueTTL of Mycelium class object which will make your application wait for responce into auto-deleted queue. You should either decrease timeoutOfSyncRequest of this Agent class object or increase tempQueueTTL of the Mycelium class object.")
        
    def __rrshift__(self, other):
        return self.Invoke(other)

    def PurgeAwaitingIncomeMessages(self):     
        if not self.mycelium.connection:         
            self.mycelium.connect()     
            try:         # Check if the queue exists         
                self.mycelium.channel.queue_declare(queue=self.mycelium.input_channel, passive=True)       
                self.mycelium.channel.queue_purge(queue=self.mycelium.input_channel)     
            except pika.exceptions.ChannelClosedByBroker as e: 
                print(str(datetime.now()) + " Queue does not exist: " + str(e))     
            except pika.exceptions.NotFound as e:       
                print(str(datetime.now()) + " Queue does not exist: " + str(e))     
            except Exception as ex:       
                print(str(datetime.now()) + " Error during purging awaiting messages: " + str(ex)) 
 
    def Invoke(self, dialogs):
        dialogs = copy.deepcopy(dialogs)
        # Conceptual point. If the imput type is Dialog, we return a Dialog
        # But if it's a list of dialogs, we retrun a list of Dialog
        errorMessage = "Only a Dialog object, a string or a list of dialog objects/strings can be processed"
        result = None
        if not isinstance(dialogs, Dialog) and not isinstance(dialogs, str) and not isinstance(dialogs, list):
            raise TypeError (errorMessage)
        if isinstance(dialogs, Dialog):
            result = self.__Process(dialogs)
        if isinstance(dialogs, str):
            result = self.__Process(Dialog.Create(dialogs))
        if isinstance (dialogs, list):
            resultDialogs = []
            for dialog in dialogs:
                if isinstance(dialog, Dialog):
                    resultDialogs.append(self.__Process(dialog))
                elif isinstance(dialog, str):
                    resultDialogs.append(self.__Process(Dialog.Create(dialog)))
                else:
                    raise TypeError(errorMessage)
            result = resultDialogs
        return result
    
    def __Process(self, dialog) -> Dialog:     
        errorMessage = "Only a Dialog object or a list of dialog class objects can be processed"
        if not isinstance(dialog, Dialog):
            raise TypeError (errorMessage)
        
        if self.timeoutOfSyncRequest > self.mycelium.tempQueueTTL/1000:
            raise ValueError(f"The timeoutOfSyncRequest value of {self.timeoutOfSyncRequest} seconds is higher than the expected maximum of {self.mycelium.tempQueueTTL} miliseconds defined in tempQueueTTL of Mycelium class object which will make your application wait for responce into auto-deleted queue. You should either decrease timeoutOfSyncRequest of this Agent class object or increase tempQueueTTL of the Mycelium class object.")

        if not self.mycelium.connection or not self.mycelium.connection.is_open:
            self.mycelium.connect()

        self.PurgeAwaitingIncomeMessages()

        # Define headers
        headers = {
            'billingData': json.dumps([]),
            'routingStrategy': RoutingStrategy(strategy="direct", params=self.service).to_json(),
        }
        dialog.lastMessageRoutingStrategy = RoutingStrategy(strategy="direct", params=self.service)
        
        if self.serviceParams != "" and self.serviceParams is not None:
            dialog.requestAgentConfig = self.serviceParams
            headers['requestAgentConfig'] = json.dumps(self.serviceParams)

        # Put the dialog into Mycelium and add relevant reply_to
        dialog.reply_to = self.mycelium.input_chanel
        self.mycelium.dialogs[dialog.dialog_id] = dialog
        
        # Place message
        properties = pika.BasicProperties(
            reply_to=self.mycelium.input_chanel,
            correlation_id=str(dialog.dialog_id),
            headers=headers
        )
        def TryPublish(self, dialog, properties):
            
            self.mycelium.chanel.basic_publish(
                exchange='',
                routing_key=self.mycelium.output_chanel,
                body=dialog.serialize_and_compress(),
                properties=properties
            )
        def TryConsume():
            def stop_consuming():
                self.mycelium.chanel.stop_consuming()
                raise TimeoutError(f"Agent did not respond in {self.timeoutOfSyncRequest} seconds defined by timeoutOfSyncRequest probperty for this Agent class object.")

            self.mycelium.connection.call_later(self.timeoutOfSyncRequest, stop_consuming)
            self.mycelium.chanel.basic_consume(queue=self.mycelium.input_chanel, on_message_callback=callback, auto_ack=False)
            self.mycelium.chanel.start_consuming()

        try:
            TryPublish(self, dialog, properties)
        except aio_pika.exceptions.AMQPError as e:
            self.mycelium.connect()
            TryPublish(self, dialog, properties)
        except Exception as e:
            print(f"{str(datetime.now())} Error during PUBLISH stage connection check: {e}")

        def callback(ch, method, properties, body):
            new_dialog = Dialog(reply_to=properties.reply_to, dialog_id=properties.correlation_id)
            dialog_id = new_dialog.dialog_id
            if dialog_id in self.mycelium.dialogs:
                new_dialog.decompress_and_deserialize(body)
                self.mycelium.dialogs[dialog_id].messages += new_dialog.messages
                self.mycelium.dialogs[dialog_id].requestAgentConfig = new_dialog.requestAgentConfig
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.mycelium.chanel.stop_consuming()

        try:
            TryConsume()
        except aio_pika.exceptions.AMQPError as e:
            self.mycelium.connect()
            TryConsume()
        except Exception as e:
            print(f"{str(datetime.now())} Error during responce awaiting or receiving: {e}. In case queue was not found, try increasing timeoutOfSyncRequest for the Agent to have enough time to generate response.")
        
        return self.mycelium.dialogs.get(dialog.dialog_id)
    
    async def StreamAsync(self, dialogs):
        return False

class DialogTemplate():
    def __init__(self, messages=None, context=None, reply_to = None, lastMessageDiagnosticData = None, requestAgentConfig = None,
                 lastMessageBillingData = None, endUserCommunicationID = None, lastMessageRoutingStrategy = RoutingStrategy()):
        self.dialog_id = None
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
    
    def _update_totals(self):
        self.message_count = len(self.messages)
        if self.message_count > 0:
            self.lastMessageBillingData = self.messages[-1].billingData
            self.lastMessageDiagnosticData = self.messages[-1].diagnosticData
            self.lastMessageRoutingStrategy = self.messages[-1].routingStrategy
    
    def __mul__(self, other):
        return self.__Process(other)
    
    def __rmul__(self, other):
        return self.__Process(other)
    
    def __Process(self, other):
        if not isinstance(other, dict) and not isinstance(other, list):
            raise ValueError("Can only create Dialog(s) from DialogTemplate and dict or [dict]")
        if len(self.messages)<1:
            raise IndexError("DialogTemplate must have at least one message.")
        if isinstance(other, dict):
            result = Dialog.FromTemplate(self, other)
        elif isinstance(other, list):
            resultDialogs = []
            for item in other:
                if not isinstance(item, dict):
                    raise ValueError("Can only create Dialog(s) from DialogTemplate and dict or [dict]")
                newDialog = Dialog.FromTemplate(self, item)
                resultDialogs.append(newDialog)
            result = resultDialogs
        return result

    @classmethod
    def Create(self, textPrompt = None, imagePrompt = None, audioPrompt = None, audioMimeType = None, 
               documentPrompt = None, documentMimeType = None, url = None, urlMimeType = None):
        unifiedPrompts = []
        if textPrompt:
            if not isinstance(textPrompt, str) and not isinstance(textPrompt, list):
                raise TypeError ("textPrompt must be either a string or a list of strings")
            if isinstance(textPrompt, str):
                textPrompt = [textPrompt]
            if isinstance(textPrompt, list):
                for text in textPrompt:
                    if isinstance(text, str):
                        unifiedPrompts.append(UnifiedPrompt(content_type="text", content=text, mime_type="text/plain"))
                    else:
                        raise TypeError ("textPrompt must be either a string or a list of strings")
        if imagePrompt:
            if not isinstance(imagePrompt, Image.Image) and not isinstance(imagePrompt, list):
                raise TypeError ("imagePrompt must be either a Pillow Image or a list of Pillow Images")
            if isinstance(imagePrompt, Image.Image):
                imagePrompt = [imagePrompt]
            if isinstance(imagePrompt, list):
                for img in imagePrompt:
                    if isinstance(img, Image.Image):
                        unifiedPrompts.append(UnifiedPrompt(content_type="image", content=img, mime_type=f"image/{imagePrompt.format.lower()}"))
                    else:
                        raise TypeError ("imagePrompt must be either a Pillow Image or a list of Pillow Images")
        if audioPrompt and audioMimeType:
            if not isinstance(audioPrompt, bytes) and not isinstance(audioPrompt, list):
                raise TypeError("audioPrompt must be either a Byte array or a list of byte arrays")
            if not isinstance(audioMimeType, str) and not isinstance(audioMimeType, list):
                raise TypeError("audioMimeType must be either a string starting with audio/ or a list of strings where each starts with audio/")
            if isinstance(audioPrompt, bytes):
                audioPrompt = [audioPrompt]
            if isinstance(audioMimeType, str):
                audioMimeType = [audioMimeType]
            i = 0
            for audio in audioPrompt:
                if i < len(audioMimeType):
                    mimeType = audioMimeType[i]
                else:
                    mimeType = audioMimeType[0]
                if isinstance(audio, bytes) and mimeType.startswith("audio/"):
                    unifiedPrompts.append(UnifiedPrompt(content_type="audio", content=audioPrompt, mime_type=mimeType))
                else:
                    raise TypeError("audioMimeType must be either a string starting with audio/ or a list of strings where each starts with audio/")
                i += 1
        if documentPrompt and documentMimeType:
            print("Not implemented...")
            #TODO. Finish for 3 document types (XLSXm DOCX, XML???)
            #Missed in both Dialog and DialogTemplate. Pythom OOP sucks.
        message = Message(role="user", unified_prompts=unifiedPrompts, sender_info="ComradeAI Client", send_datetime=datetime.now())
        resultDialogTemplate = DialogTemplate(messages=[message])
        resultDialogTemplate._update_totals()
        return (resultDialogTemplate)