from ComradeAI.Mycelium import Agent, Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy

import base64
from datetime import datetime
from dotenv import load_dotenv
from enum import Enum
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
import io
from io import BytesIO
import json
import os
from PIL import Image
from pydantic import BaseModel, validator
from typing import Annotated, Dict, List, Optional, Union
from tempfile import NamedTemporaryFile

app = FastAPI(title="ComradeAI REST-API", version="0.18.19")
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
static_dir = BASE_DIR + "/static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

load_dotenv()
comradeai_token = os.getenv('COMRADEAI_TOKEN')

class PromptAppendRule(Enum):
    APPEND_TO_LAST = "APPEND_TO_LAST" # appends propmts to the last message of the serialized_request dialog
    PREPEND_TO_LAST = "PREPEND_TO_LAST" # puts prompts to the last message of the serialized_request dialog before its existing prompts
    ADD_FIRST = "ADD_FIRST" # puts prompts together as the first message for the serialized_request dialog
    ADD_LAST = "ADD_LAST" # puts prompts together as the last message for the serialized_request dialog
    ADD_PENULT = "ADD_PENULT" # puts prompts together as the penult message for the serialized_request dialog    

class FileObject(BaseModel):
    content: str  # Base64 encoded file content
    filename: str  # Original file name

    @validator('content')
    def validate_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except ValueError:
            raise ValueError("File content must be a valid base64 encoded string. The FileObject must be of {\"content\": base_64_string:str, \"filename\": original_file_name:str}")

class MultiformatRequest(BaseModel):
    agentAddress: str
    text: Optional[str] = None
    comradeAIToken: Optional[str] = None
    requestAgentConfig: Optional[dict] = {}
    request_dialog: Union[Dict, str] = None
    prompt_append_rule: Optional[str] = PromptAppendRule.APPEND_TO_LAST
    files: Optional[List[FileObject]] = []  

class StringRequest(BaseModel):
    agentAddress: str
    text: str
    comradeAIToken: str = ""
    requestAgentConfig: dict = {}

image_mime_types = {
    "bmp": "image/bmp",
    "gif": "image/gif",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "webp": "image/webp"
}

def unifiedPromptToJSON(unified_prompt: UnifiedPrompt):
    return {"content_type": unified_prompt.content_type, "content": content_to_base64(unified_prompt.content) if unified_prompt.content_type in ['image', 'document', 'audio'] else unified_prompt.content, "mime_type": unified_prompt.mime_type}

@app.post("/get_agent_response/")
async def get_agent_response(request: MultiformatRequest):
    global comradeai_token
    # Self-expanatory result format
    result = {
        "result" : None, # Success when result is 200 OK. In case of error server returns 400 with error message.
        "content": {    # Each output looks like {"content_type": "", "content": "", "mime_type: ""}
            "last_text_output": None,
            "last_image_output": None,
            "last_audio_output": None,
            "last_video_output": None,
            "last_document_output" : None,
            "raw_response": None
        }
    }
    
    # Validate that at least one type of content is present
    if not request.text and not request.files and (not request.request_dialog or len(request.request_dialog)) == 0:
        raise HTTPException(status_code=400, detail="At least one of text, audio, image, video or Mycelium Dialog object must be present")
    
    # Validate that the instance has the ComradeAI token to operate
    if not request.comradeAIToken or len(request.comradeAIToken) == 0:
        if comradeai_token and len(comradeai_token)>0:
            local_comradeai_token = comradeai_token
        else:
            raise HTTPException(status_code=400, detail="Comrade AI token is not set")
    else:
        local_comradeai_token = request.comradeAIToken

    # Process files if present
    added_prompts = []
    if request.text:
        added_prompts.append(UnifiedPrompt(content_type="text", content=request.text, mime_type="text/plain"))
               
    agentConfig = None
    if request.requestAgentConfig != {}:
        agentConfig = request.requestAgentConfig

    files = []

    for file_obj in request.files:
        file_content = base64.b64decode(file_obj.content)
        file_extension = file_obj.filename.split(".")[-1].lower()
        print(f"{str(datetime.now())} Processing file of type {file_obj.filename}", flush=True)
        if file_extension in ["mp3", "wav", "ogg"]:
            # Handle audio file
            if file_extension in ["wav", "ogg"]: mime_type = "audio/" + file_extension 
            else: mime_type = "audio/mpeg"
            added_prompts.append(UnifiedPrompt(content_type="audio", content=file_content, mime_type=mime_type))
        elif file_extension in ["bmp", "gif", "png", "jpg", "jpeg", "tif", "tiff", "webp"]:
            # Handle image file
            image_file = BytesIO(file_content)
            image = Image.open(image_file)
            mime_type = image_mime_types.get(file_extension, "application/octet-stream")
            added_prompts.append(UnifiedPrompt(content_type="image", content=image, mime_type=mime_type))
        # elif content_type.startswith("video"):
        #     # Handle video file
        #     added_prompts.append(UnifiedPrompt(content_type="video", content=await file_obj.read(), mime_type=content_type))
        
        else:
            # Unsupported file type
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
   
    sourceDialog = None
    if request.request_dialog and len(request.request_dialog) > 0:
        sourceDialog = Dialog()
        if isinstance(request.request_dialog, Dict):
            request_dialog = json.dumps(request.request_dialog)
        else:
            request_dialog = request.request_dialog
        sourceDialog.deserialize(request_dialog)

    # Shape as Mycelium Message and send to Mycelium
    request_message = Message(role="user", unified_prompts=added_prompts, sender_info="REST-API User", subAccount="", routingStrategy=RoutingStrategy("direct", request.agentAddress))
    request_dialog = None
    if sourceDialog:
        sourceDialog.requestAgentConfig = agentConfig
        #sourceDialog.messages.append(request_message)
        if request.prompt_append_rule == PromptAppendRule.APPEND_TO_LAST:
            sourceDialog.messages[-1].unified_prompts.extend(added_prompts)
        elif request.prompt_append_rule == PromptAppendRule.PREPEND_TO_LAST:
            added_prompts.extend(sourceDialog.messages[-1].unified_prompts)
            sourceDialog.messages[-1].unified_prompts = added_prompts
        elif request.prompt_append_rule == PromptAppendRule.ADD_FIRST:
            sourceDialog.messages.insert(0, request_message)
        elif request.prompt_append_rule == PromptAppendRule.ADD_LAST:
            sourceDialog.messages.append(request_message)
        elif request.prompt_append_rule == PromptAppendRule.ADD_PENULT:
            sourceDialog.messages.insert(-1, request_message)
        request_dialog = sourceDialog
    else:
        request_dialog = Dialog(requestAgentConfig=agentConfig)
        request_dialog.messages.append(request_message)
    try:
        AI = Mycelium(ComradeAIToken=local_comradeai_token)
        AI.connect()
    except Exception as ex:
        print(f"{str(datetime.now())} Error: {str(ex)}", flush=True)
        return {"result": "error", "content": str(ex)}

    agent = Agent(AI, request.agentAddress)
    # TODO. To make it work properly, each oepration must create an own temprorary queue, which requires Router changes
    
    resultDialog = request_dialog >> agent
    
    result["content"]["raw_response"] = json.loads(resultDialog.serialize())
    
    for unified_prompt in resultDialog.messages[-1].unified_prompts:
        if unified_prompt.content_type == 'text':
            result["content"]["last_text_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'image':
            # Original architecture mistake - the lib uses pillow images instead of binaries.
            result["content"]["last_image_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'audio':
            result["content"]["last_audio_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'video':
            result["content"]["last_video_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'document':
            result["content"]["last_document_output"] = unifiedPromptToJSON(unified_prompt)
    
    result["result"] = "success"
    result = jsonable_encoder(result)
    return result 

@app.post("/get_agent_response_webform/")
async def get_agent_response_webform(
    agentAddress: str = Form(...),
    text: Optional[str] = Form(None),
    comradeAIToken: Optional[str] = Form(None),
    requestAgentConfig: Optional[str] = Form("{}"),
    audio_file: Annotated[UploadFile, File(description="Audio file: mp3, wav, or ogg")] = None,
    image_file: Annotated[UploadFile, File(description="Image file: bmp, gif, png, jpg, jpeg, tif, tiff, or webp")] = None):

    global comradeai_token

    # Convert JSON string back to dictionary
    try:
        agent_config_dict = json.loads(requestAgentConfig)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for agent config.")


    # Self-expanatory result format
    result = {
        "result" : None, # Success when result is 200 OK. In case of error server returns 400 with error message.
        "content": {    # Each output looks like {"content_type": "", "content": "", "mime_type: ""}
            "last_text_output": None,
            "last_image_output": None,
            "last_audio_output": None
        }
    }
    
    # Validate that at least one type of content is present
    if not text and not audio_file and not image_file:
        raise HTTPException(status_code=400, detail="At least one of text, audio, image must be present")
    
    # Validate that the instance has the ComradeAI token to operate
    if not comradeAIToken or len(comradeAIToken) == 0:
        if comradeai_token and len(comradeai_token)>0:
            local_comradeai_token = comradeai_token
        else:
            raise HTTPException(status_code=400, detail="Comrade AI token is not set")
    else:
        local_comradeai_token = comradeAIToken

    # Process files if present
    added_prompts = []
    if text:
        added_prompts.append(UnifiedPrompt(content_type="text", content=text, mime_type="text/plain"))
               
    agentConfig = None
    if requestAgentConfig != {}:
        agentConfig = requestAgentConfig

    # Preparing prompt of audio_file
    if audio_file:
        audio_file_content = await audio_file.read()
        audio_file_extension = audio_file.filename.split(".")[-1].lower()
        print(f"{str(datetime.now())} Processing file of type {audio_file.filename}", flush=True)
        if audio_file_extension in ["mp3", "wav", "ogg"]:
            if audio_file_extension in ["wav", "ogg"]: mime_type = "audio/" + audio_file_extension 
            else: mime_type = "audio/mpeg"
            added_prompts.append(UnifiedPrompt(content_type="audio", content=audio_file_content, mime_type=mime_type))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type for audio file: {audio_file_extension}")
        
    # Preparing prompt of image_file
    if image_file:
        image_file_content = await image_file.read()
        image_file_extension = image_file.filename.split(".")[-1].lower()
        if image_file_extension in ["bmp", "gif", "png", "jpg", "jpeg", "tif", "tiff", "webp"]:
            image_binary = BytesIO(image_file_content)
            image = Image.open(image_binary)
            mime_type = image_mime_types.get(image_file_extension, "application/octet-stream")
            added_prompts.append(UnifiedPrompt(content_type="image", content=image, mime_type=mime_type))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type for image file: {image_file_extension}")
   
    # Shape as Mycelium Message and send to Mycelium
    request_message = Message(role="user", unified_prompts=added_prompts, sender_info="REST-API User", subAccount="", routingStrategy=RoutingStrategy("direct", agentAddress))
    request_dialog = None
    request_dialog = Dialog(requestAgentConfig=agentConfig)
    request_dialog.messages.append(request_message)
    try:
        AI = Mycelium(ComradeAIToken=local_comradeai_token, multiClientInstance = True, tempQueueTTL=60*60*1000)
        AI.connect()
    except Exception as ex:
        print(f"{str(datetime.now())} Error: {str(ex)}", flush=True)
        return {"result": "error", "content": str(ex)}

    agent = Agent(AI, agentAddress, timeoutOfSyncRequest=60*60)
    resultDialog = request_dialog >> agent
    
    # result["content"]["raw_response"] = json.loads(resultDialog.serialize())
    # User's don't need huge binary files they saw here during tests, they wanted only responces. Thus, commented.
    
    for unified_prompt in resultDialog.messages[-1].unified_prompts:
        if unified_prompt.content_type == 'text':
            result["content"]["last_text_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'image':
            # Original architecture mistake - the lib uses pillow images instead of binaries.
            result["content"]["last_image_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'audio':
            result["content"]["last_audio_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'video':
            result["content"]["last_video_output"] = unifiedPromptToJSON(unified_prompt)
        if unified_prompt.content_type == 'document':
            result["content"]["last_document_output"] = unifiedPromptToJSON(unified_prompt)

    result["result"] = "success"
    result = jsonable_encoder(result)
    return result 

@app.post("/text_to_text/")
async def text_to_text(request: StringRequest):
    global comradeai_token
    
    # Validate that at least one type of content is present
    if not request.text:
        raise HTTPException(status_code=400, detail="Request text is required")
    
    # Validate that the instance has the ComradeAI token to operate 
    if not request.comradeAIToken or len(request.comradeAIToken) == 0:
        if comradeai_token and len(comradeai_token)>0:
            local_comradeai_token = comradeai_token
        else:
            raise HTTPException(status_code=400, detail="Comrade AI token is not set")
    else:
        local_comradeai_token = request.comradeAIToken  
    
    # Process files if present
    unified_prompts = []
    if request.text:
        unified_prompts.append(UnifiedPrompt(content_type="text", content=request.text, mime_type="text/plain"))
        
    agentConfig = None
    if request.requestAgentConfig != {}:
        agentConfig = request.requestAgentConfig
        
    # Shape as Mycelium Message and send to Mycelium
    request_message = Message(role="user", unified_prompts=unified_prompts, sender_info="REST-API User", subAccount="", routingStrategy=RoutingStrategy("direct", request.agentAddress))
    request_dialog = Dialog(requestAgentConfig=agentConfig)
    request_dialog.messages.append(request_message)
      
    AI = Mycelium(ComradeAIToken=local_comradeai_token)
    AI.connect()

    agent = Agent(AI, request.agentAddress)
    resultDialog = request_dialog >> agent
    
    result = None
    try:
        result = resultDialog.messages[-1].unified_prompts[-1].content
    except Exception as ex:
        result = "Error"
    return result
    
@app.get("/status")
async def get_status():
    return {"status": "online"}

@app.get("/version")
async def get_version():
    return {"version": "0.18.xx"}

def content_to_base64(content):
    if isinstance(content, Image.Image):
        buffered = io.BytesIO()
        content.save(buffered, format='PNG')
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    elif isinstance(content, bytes):
        return base64.b64encode(content).decode()
    else:
        return content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)