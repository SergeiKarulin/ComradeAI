from ComradeAI.DocumentRoutines import DocxToPromptsConverter, XlsxToPromptsConverter
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy
import asyncio
import os
import io
from dotenv import load_dotenv

from telebot.async_telebot import AsyncTeleBot
import tempfile
import re

from PIL import Image
from io import BytesIO

load_dotenv()
bot = AsyncTeleBot(os.getenv('TELEGRAM_TOKEN'))
comradeai_token = os.getenv('COMRADEAI_TOKEN')

async def init_model_for_user(command, user_id):
    global myceliumRouter
    global available_model_configs
    global dialog_configs
    global comradeai_token
    
    command_list = list(available_model_configs.keys())
    if not command in command_list:
        return False
    
    dialog_id = str(user_id)
    dialog_configs[dialog_id] = available_model_configs[command]
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token, requestAgentConfig=dialog_configs[dialog_id]['requestAgentConfig'])
        myceliumRouter.dialogs[dialog_id]=dialog
    return True

@bot.message_handler(commands=['start'])
async def start(message):
    chat_id = message.chat.id
    await bot.send_message(chat_id, "Welcome!")

@bot.message_handler(commands=['album_send'])
async def start(message):
    global dialog_lockers
    global myceliumRouter
    await myceliumRouter.send_to_mycelium(str(message.chat.id), isReply=False)
    dialog_lockers[str(message.chat.id)] = False
    return

@bot.message_handler(commands=['album_compose'])
async def start(message):
    global dialog_lockers
    dialog_lockers[str(message.chat.id)] = True
    await bot.send_message(message.chat.id, "Auto-sending is disable. Use /album_send command after placing all the messages to send.")
    return

@bot.message_handler(commands=['amnesia'])
async def start(message):
    global dialog_lockers
    dialog_id = str(message.chat.id)
    dialog_lockers[dialog_id] = False
    dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
    myceliumRouter.dialogs[dialog_id]=dialog
    await bot.send_message(message.chat.id, "Starting dialog from scratch.")
    return

@bot.message_handler(func=lambda message: True == message.text.startswith("/"))
async def echo_message(message):
    global myceliumRouter
    global dialog_configs
    command = re.split('[@ ]', message.text)[0]
    if await init_model_for_user(command, message.chat.id):
        await bot.reply_to(message, "Enjoy conversation with " + dialog_configs[str(message.chat.id)]['agent'])
    else:
        await bot.reply_to(message, "Uknown command: " + message.text + ". Type / to get a list of available commands.")
      
@bot.message_handler(content_types=['document', 'photo', 'audio', 'video', 'voice', 'text', 'video_note', 'location', 'contact', 'sticker'])
async def echo_message(message):
    global myceliumRouter
    global dialog_lockers
    global dialog_configs
    dialog_config_keys = list(dialog_configs.keys())
    if str(message.chat.id) not in dialog_config_keys:
        await bot.reply_to(message, "Use / command to select an Agent to talk to before sending your first message")
        return
    if message.media_group_id != None:
        dialog_lockers[str(message.chat.id)] = True
        await bot.reply_to(message, "Your message contains an album. You will have to us /album_send command after everything you need is loaded.")
    unifiedPrompts = []
    if message.content_type == 'text':
        unifiedPrompts.append(UnifiedPrompt(content_type='text', content=message.text, mime_type='text/plain'))
    if message.content_type in ['document', 'photo', 'audio', 'video'] and message.caption != None:
        unifiedPrompts.append(UnifiedPrompt(content_type='text', content=message.caption, mime_type='text/plain'))
    if message.content_type == 'photo':
        fileID = message.photo[-1].file_id
        file_info = await bot.get_file(fileID)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_stream = BytesIO(downloaded_file)
        image = Image.open(image_stream)
        unifiedPrompts.append(UnifiedPrompt(content_type='image', content=image, mime_type='image/jpg'))
    if message.content_type == 'document':
        if message.document.mime_type in ["image/jpg", "image/png", "image/jpeg", "image/gif"]:
            fileID = message.document.file_id
            file_info = await bot.get_file(fileID)
            downloaded_file = await bot.download_file(file_info.file_path)
            image_stream = BytesIO(downloaded_file)
            image = Image.open(image_stream)
            unifiedPrompts.append(UnifiedPrompt(content_type='image', content=image, mime_type=message.document.mime_type))
        if message.document.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            fileID = message.document.file_id
            file_info = await bot.get_file(fileID)
            downloaded_file = await bot.download_file(file_info.file_path)
            xlsx_stream = BytesIO(downloaded_file)
            converter = XlsxToPromptsConverter()
            prompts = converter.convert(xlsx_stream)
            unifiedPrompts.extend(prompts)
        if message.document.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            fileID = message.document.file_id
            file_info = await bot.get_file(fileID)
            downloaded_file = await bot.download_file(file_info.file_path)
            script_directory = os.path.dirname(os.path.abspath(__file__))
            temp_directory = os.path.join(script_directory, 'temp')
            try:
                if not os.path.exists(temp_directory):
                    os.makedirs(temp_directory)
                file_path = os.path.join(temp_directory, str(fileID) + '.docx')
                with open(file_path, 'wb') as file:
                    file.write(downloaded_file)
                converter = DocxToPromptsConverter(convert_urls=True)
                prompts = converter.convert(file_path)
                unifiedPrompts.extend(prompts)
            except Exception as ex:
                await bot.reply_to(message, "Error creating temprorary docx file.")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        if message.document.mime_type == "text/plain":
            fileID = message.document.file_id
            file_info = await bot.get_file(fileID)
            downloaded_file = await bot.download_file(file_info.file_path)
            text_string = downloaded_file.decode('utf-8')
            unifiedPrompts.append(UnifiedPrompt(content_type='text', content=text_string, mime_type='text/plain'))

    new_message = Message(role="user", unified_prompts=unifiedPrompts, sender_info="Telegram User", subAccount=str(message.from_user.id), routingStrategy=RoutingStrategy("direct", dialog_configs[str(message.chat.id)]['agent']))
    myceliumRouter.dialogs[str(message.chat.id)].messages.append(new_message)
    if str(message.chat.id) not in dialog_lockers or dialog_lockers[str(message.chat.id)] != True:
        await myceliumRouter.send_to_mycelium(str(message.chat.id), isReply=False)
    return True

async def message_received_handler(dialog):
    for message in dialog.messages:
        for unified_prompt in message.unified_prompts:
            if unified_prompt.content_type == 'text':
                await bot.send_message(int(dialog.dialog_id), unified_prompt.content)
            if unified_prompt.content_type == 'image':
                with io.BytesIO() as output:
                    unified_prompt.content.save(output, format="JPEG")
                    jpeg_data = output.getvalue()  
                await bot.send_photo(int(dialog.dialog_id), photo=jpeg_data)
            if unified_prompt.content_type == 'audio':
                script_directory = os.path.dirname(os.path.abspath(__file__))
                temp_directory = os.path.join(script_directory, 'temp')
                os.makedirs(temp_directory, exist_ok=True)
                suffix = unified_prompt.mime_type.split("/")[1]
                temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_directory, suffix="."+suffix)
                with open(temp_file.name, 'wb') as file:
                    file.write(unified_prompt.content)
                temp_file.close()
                await bot.send_voice(int(dialog.dialog_id), voice=open(temp_file.name, "rb"))


    return True

available_model_configs = {
    "/groot": {"agent": "groot", "requestAgentConfig": ""},
    "/mbart_ru_2_en": {"agent": "Meta_MBART", "requestAgentConfig": {"source_language": "ru_RU", "target_language": "en_XX"}},
    "/mbart_en_2_ru": {"agent": "Meta_MBART", "requestAgentConfig": {"source_language": "en_XX", "target_language": "ru_RU"}},
    "/dalle_3_1024x1024_vivid": {"agent": "OpenAI_DALLE3", "requestAgentConfig": {"size": "1024x1024", "style": "vivid"}},
    "/dalle_3_1024x1024_natural": {"agent": "OpenAI_DALLE3", "requestAgentConfig": {"size": "1024x1024", "style": "natural"}},
    "/steosvoice_kontsevich": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 198, "file_format": "ogg"}},
    "/steosvoice_zagumyonnova": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 18, "file_format": "ogg"}},
    "/steosvoice_rogovin": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 19, "file_format": "ogg"}},
    "/steosvoice_omutkova": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 360, "file_format": "ogg"}},
    "/steosvoice_han_solo": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 408, "file_format": "ogg"}},
    "/steosvoice_wc3_acolyte": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 263, "file_format": "ogg"}},
    "/steosvoice_alpatkin": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 359, "file_format": "ogg"}},
    "/stable_diffusion_txt2img": {"agent": "StabeDiffusion_Text2Image", "requestAgentConfig": {"n_steps": "40"}},
    "/gemini_pro_vision_creative": {},
    "/gemini_pro_creative": {},
    "/gemini_pro_vision_normal": {},
    "/gemini_pro_normal" : {},
    "/claude" : {"agent": "Anthropic_CLAUDE2.1", "requestAgentConfig": ""},
    "/chat_gpt_3-5_creative": {},
    "/chat_gpt_3-5_normal" : {},
    "/chat_gpt_4_creative": {},
    "/chat_gpt_4_normal": {},
    "/chat_gpt_4_vision_creative": {},
    "/chat_gpt_4_vision_normal": {},
    "/llama2_creative": {"agent": "Meta_LLaMa2", "requestAgentConfig": {"temperature": "0.9"}},
    "/llama2_normal": {"agent": "Meta_LLaMa2", "requestAgentConfig": {"temperature": "0.6"}},
    "/yandex_gpt_2_creative": {},
    "/yandex_gpt_2_normal": {}
}

dialog_configs = {}
dialog_lockers = {}

#dialog_configurations = {}
myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler, dialogs={})

async def main():
    server_task = myceliumRouter.start_server(allowNewDialogs=False)
    bot_task = bot.polling()
    await asyncio.gather(server_task, bot_task)

if __name__ == "__main__":
    asyncio.run(main())