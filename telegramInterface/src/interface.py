from ComradeAI.DocumentRoutines import DocxToPromptsConverter, XlsxToPromptsConverter
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy

import asyncio
import os
import io
from dotenv import load_dotenv

from telebot.async_telebot import AsyncTeleBot
from telebot import types
import tempfile
import re

from PIL import Image
from io import BytesIO

import textwrap

load_dotenv()
bot = AsyncTeleBot(os.getenv('TELEGRAM_TOKEN'))
comradeai_token = os.getenv('COMRADEAI_TOKEN')
max_dialog_len = int(os.getenv('MAX_DIALOG_LEN'))
hello_messages = {
    "russian": os.getenv('HELLO_MESSAGE_RU'),
    "english": os.getenv('HELLO_MESSAGE_EN'),
    "arabic": os.getenv('HELLO_MESSAGE_AR')
}

async def init_modelgroup_for_user(command, dialog_id):
    global myceliumRouter
    global available_model_configs
    global dialog_configs
    global comradeai_token
    dialog_id = str(dialog_id)
    command_list = list(available_model_configs.keys())
    if not command in command_list:
        return False
    model_keys = available_model_configs[command].keys()
    if "inlineButtons" in model_keys:
        dialog_configs[dialog_id] = available_model_configs[command]
        return True
    else:
        return False

async def init_model_for_user(command, dialog_id):
    global myceliumRouter
    global available_model_configs
    global dialog_configs
    global comradeai_token
    
    dialog_id = str(dialog_id) 
    
    command_list = list(available_model_configs.keys())
    if not command in command_list:
        return False
    dialog_configs[dialog_id] = available_model_configs[command]
           
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token, requestAgentConfig=dialog_configs[dialog_id]['requestAgentConfig'])
        myceliumRouter.dialogs[dialog_id]=dialog
    else:
        myceliumRouter.dialogs[dialog_id].requestAgentConfig=dialog_configs[dialog_id]['requestAgentConfig']
    return True

async def send_long_message(chat_id, text, max_length=4096):
    parts = textwrap.wrap(text, max_length)
    for part in parts:
        await bot.send_message(chat_id, part)

@bot.message_handler(commands=['start'])
async def start(message):
    global hello_messages
    global dialog_configs
    global dialog_lockers
    global dialog_modes
    global available_model_configs
    global myceliumRouter
    chat_id = str(message.chat.id)
    await init_model_for_user("/groot", chat_id)
    dialog_lockers[chat_id] = False
    dialog_modes[chat_id] = "ctx_amnesia"
    dialog_ids = myceliumRouter.dialogs.keys()
    if chat_id in dialog_ids:
        myceliumRouter.dialogs[chat_id].messages = []
    for language, message in hello_messages.items():
        if message and len(message)>0: await bot.send_message(chat_id, message)

@bot.message_handler(commands=['album_send'])
async def start(message):
    global dialog_lockers
    global myceliumRouter
    dialog_id = str(message.chat.id)
    dialog_ids = dialog_configs.keys()
    if dialog_id in dialog_ids:
        if len(myceliumRouter.dialogs[dialog_id].messages) > 0:
            await myceliumRouter.send_to_mycelium(dialog_id, isReply=False)
            myceliumRouter.dialogs[dialog_id].messages = []
            dialog_lockers[dialog_id] = False
        else:
             await bot.send_message(message.chat.id, "There is no messages to send.")
    else:
        await bot.send_message(message.chat.id, "There is no album to send. Start with /album_compose command then send some messages and call /album_send afterwards.")
    return

@bot.message_handler(commands=['album_cancel'])
async def start(message):
    global dialog_lockers
    global myceliumRouter
    dialog_id = str(message.chat.id)
    dialog_ids = dialog_configs.keys()
    if dialog_id in dialog_ids:
        if dialog_modes[dialog_id] == "ctx_amnesia":
            myceliumRouter.dialogs[dialog_id].messages = []
        dialog_lockers[dialog_id] = False
        await bot.send_message(message.chat.id, "Album compose mode calnceled.")
    else:
        await bot.send_message(message.chat.id, "There is nothing to cancel. Start with /album_compose command.")
    return

@bot.message_handler(commands=['album_compose'])
async def start(message):
    global dialog_lockers
    dialog_lockers[str(message.chat.id)] = True
    await bot.send_message(message.chat.id, "Auto-sending is disabled. Use /album_send command after you post all the messages to send.")
    return

@bot.message_handler(commands=['ctx_dialog'])
async def start(message):
    global dialog_modes
    dialog_id = str(message.chat.id)
    dialog_modes[dialog_id] = "ctx_dialog"
    await bot.send_message(message.chat.id, "Bot will send to AI agents the entire conversation history staring from your next message (FYI, text-to-image and text-to-speech models don't appreciate it much). Use /ctx_amnesia to switch for sending the last message only.")
    return

@bot.message_handler(commands=['ctx_amnesia'])
async def start(message):
    global dialog_modes
    global myceliumRouter
    dialog_id = str(message.chat.id)
    dialog_ids = myceliumRouter.dialogs.keys()
    dialog_modes[dialog_id] = "ctx_amnesia"
    if dialog_id in dialog_ids:
        myceliumRouter.dialogs[dialog_id].messages = []
    await bot.send_message(message.chat.id, "Bot will send to AI agents your last message only. Use /ctx_dialog to switch for sending the entire conversation.")
    return

@bot.message_handler(func=lambda message: True == message.text.startswith("/"))
async def echo_message(message):
    global myceliumRouter
    global dialog_configs
    dialog_id=str(message.chat.id)
    command = re.split('[@ ]', message.text)[0]
    if await init_modelgroup_for_user(command, message.chat.id):
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        tmp = dialog_configs[dialog_id]['inlineButtons']
        for item in tmp:
            keyboard.add(*[types.InlineKeyboardButton(text = item["text"], callback_data = item["callback_data"])])
        await bot.send_message(message.chat.id, 'Есть варианты: ', reply_markup=keyboard)
    elif await init_model_for_user(command, message.chat.id):
        await bot.reply_to(message, "Enjoy conversation with " + dialog_configs[dialog_id]['agent'])
    else:
        await bot.reply_to(message, "Uknown command: " + message.text + ". Type / to get a list of available commands.")
        
@bot.callback_query_handler(func=lambda call: True)
async def query_handler(call):
    global myceliumRouter
    global dialog_configs
    dialog_id=str(call.message.chat.id)
    if await init_model_for_user(call.data, call.message.chat.id):
        await bot.reply_to(call.message, "Enjoy conversation with " + dialog_configs[dialog_id]['agent'])
    else:
        await bot.reply_to(call.message, "Uknown command: " + call.data + ". Type / to get a list of available commands.")
    return
      
@bot.message_handler(content_types=['document', 'photo', 'audio', 'video', 'voice', 'text', 'video_note', 'location', 'contact', 'sticker'])
async def echo_message(message):
    global myceliumRouter
    global dialog_lockers
    global dialog_configs
    global max_dialog_len
    dialog_config_keys = list(dialog_configs.keys())
    if str(message.chat.id) not in dialog_config_keys:
        await bot.reply_to(message, "Use / command or a menu to select an Agent to talk to before sending your first message")
        return
    
    chat_id_str = str(message.chat.id)
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if chat_id_str in dialog_ids:
        current_dialog_len = len(myceliumRouter.dialogs[chat_id_str].messages)
        if current_dialog_len >= max_dialog_len:
            myceliumRouter.dialogs[str(message.chat.id)].messages = myceliumRouter.dialogs[str(message.chat.id)].messages[current_dialog_len - max_dialog_len:]
    
    if message.media_group_id != None:
        dialog_lockers[str(message.chat.id)] = True
        await bot.reply_to(message, "Your message contains an album. You will have to use /album_send command after sending everything you need to process.")
    unifiedPrompts = []
    if message.content_type == 'voice':
        file_info = await bot.get_file(message.voice.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        unifiedPrompts.append(UnifiedPrompt(content_type='audio', content=downloaded_file, mime_type='audio/ogg'))
    if message.content_type == 'audio':
        if message.audio.mime_type in ["audio/mpeg", "audio/ogg", "audio/wav"]:
            file_info = await bot.get_file(message.audio.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            unifiedPrompts.append(UnifiedPrompt(content_type='audio', content=downloaded_file, mime_type=message.audio.mime_type))
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
        if dialog_modes[str(message.chat.id)] == "ctx_amnesia":
            myceliumRouter.dialogs[str(message.chat.id)].messages = [] 
    return True

async def message_received_handler(dialog):
    global dialog_modes
    for message in dialog.messages:
        for unified_prompt in message.unified_prompts:
            if unified_prompt.content_type == 'text':
                await send_long_message(int(dialog.dialog_id), unified_prompt.content)
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
    dialog_ids = list(dialog_modes.keys())
    chat_id = str(dialog.dialog_id)
    if not chat_id in dialog_ids:
        dialog_modes[chat_id] = "ctx_amnesia"
    if dialog_modes[chat_id] == "ctx_amnesia":
        myceliumRouter.dialogs[chat_id].messages = []
    return True

available_model_configs = {
    "/steosvoice" : {"agent": None, "inlineButtons": [{"text": "Голос Концевича", "callback_data": "/steosvoice_kontsevich"}, 
                                                      {"text": "Голос Загумённовой", "callback_data": "/steosvoice_zagumyonnova"}, 
                                                      {"text": "Голос Роговина", "callback_data": "/steosvoice_rogovin"}, 
                                                      {"text": "Голос Омутковой", "callback_data": "/steosvoice_omutkova"}, 
                                                      {"text": "Голос Хана Соло", "callback_data": "/steosvoice_han_solo"}, 
                                                      {"text": "Голос Алпаткина", "callback_data": "/steosvoice_alpatkin"}, 
                                                      {"text": "Голос Акколита из WC3", "callback_data": "/steosvoice_wc3_acolyte"}]},
    "/groot": {"agent": "groot", "requestAgentConfig": {}},
    "/mbart_ru_2_en": {"agent": "Meta_MBART", "requestAgentConfig": {"src_lang": "ru_RU", "target_lang": "en_XX"}},
    "/mbart_en_2_ru": {"agent": "Meta_MBART", "requestAgentConfig": {"src_lang": "en_XX", "target_lang": "ru_RU"}},
    "/dalle_3_1024x1024_vivid": {"agent": "OpenAI_DALLE3", "requestAgentConfig": {"size": "1024x1024", "style": "vivid"}},
    "/dalle_3_1024x1024_natural": {"agent": "OpenAI_DALLE3", "requestAgentConfig": {"size": "1024x1024", "style": "natural"}},
    "/steosvoice_kontsevich": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 198, "file_format": "ogg"}},
    "/steosvoice_zagumyonnova": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 18, "file_format": "ogg"}},
    "/steosvoice_rogovin": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 19, "file_format": "ogg"}},
    "/steosvoice_omutkova": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 360, "file_format": "ogg"}},
    "/steosvoice_han_solo": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 408, "file_format": "ogg"}},
    "/steosvoice_wc3_acolyte": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 263, "file_format": "ogg"}},
    "/steosvoice_alpatkin": {"agent": "MindSimulation_SteosVoice", "requestAgentConfig": {"voice_id": 359, "file_format": "ogg"}},
    "/stable_diffusion_txt2img": {"agent": "StabeDiffusion_Text2Image", "requestAgentConfig": {"n_steps": 40}},
    "/gemini_pro_vision_creative": {"agent": "Google_GeminiProVision", "requestAgentConfig": {"model": "gemini-pro-vision", "temperature": 1}},
    "/gemini_pro_creative": {"agent": "Google_GeminiProVision", "requestAgentConfig": {"model": "gemini-pro", "temperature": 0.8}},
    "/gemini_pro_vision_normal": {"agent": "Google_GeminiProVision", "requestAgentConfig": {"model": "gemini-pro-vision", "temperature": 0.8}},
    "/gemini_pro_normal" : {"agent": "Google_GeminiProVision", "requestAgentConfig": {"model": "gemini-pro", "temperature": 0.4}},
    "/claude" : {"agent": "Anthropic_CLAUDE3", "requestAgentConfig": {}},
    "/chat_gpt" : {"agent": None, "inlineButtons": [{"text": "GPT3.5", "callback_data": "/chat_gpt_3_5_normal"}, 
                                                      {"text": "GPT3.5 - буйная фантазия", "callback_data": "/chat_gpt_3_5_creative"}, 
                                                      {"text": "GPT4", "callback_data": "/chat_gpt_4_normal"}, 
                                                      {"text": "GPT4 - буйная фантазия", "callback_data": "/chat_gpt_4_creative"}, 
                                                      {"text": "GPT4 с распознаванием картинок", "callback_data": "/chat_gpt_4_vision_normal"}, 
                                                      {"text": "GPT4  с распознаванием картинок - буйная фантазия", "callback_data": "/chat_gpt_4_vision_creative"}]},   
    "/chat_gpt_3_5_creative": {"agent": "OpenAI_GPT_Completions", "requestAgentConfig": {"model": "gpt-3.5-turbo-1106", "temperature": 0.9}},
    "/chat_gpt_3_5_normal" : {"agent": "OpenAI_GPT_Completions", "requestAgentConfig": {"model": "gpt-3.5-turbo-1106", "temperature": 0.7}},
    "/chat_gpt_4_creative": {"agent": "OpenAI_GPT_Completions", "requestAgentConfig": {"model": "gpt-4-1106-preview", "temperature": 0.9}},
    "/chat_gpt_4_normal": {"agent": "OpenAI_GPT_Completions", "requestAgentConfig": {"model": "gpt-4-1106-preview", "temperature": 0.7}},
    "/chat_gpt_4_vision_creative": {"agent": "OpenAI_GPT_Completions", "requestAgentConfig": {"model": "gpt-4-vision-preview", "temperature": 0.9}},
    "/chat_gpt_4_vision_normal": {"agent": "OpenAI_GPT_Completions", "requestAgentConfig": {"model": "gpt-4-vision-preview", "temperature": 0.7}},
    "/llama2_creative": {"agent": "Meta_LLaMa2", "requestAgentConfig": {"temperature": 0.9}},
    "/llama2_normal": {"agent": "Meta_LLaMa2", "requestAgentConfig": {"temperature": 0.6}},
    "/yandex_gpt_2_creative": {"agent": "YandexGPT2-FULL", "requestAgentConfig": {"temperature": 0.2}},
    "/yandex_gpt_2_normal": {"agent": "YandexGPT2-FULL", "requestAgentConfig": {"temperature": 0.6}},
    "/whisper_large_v3": {"agent": "Whisper_v3_Large", "requestAgentConfig": {}},
    "/gemma": {"agent": "Google_Gemma_7b", "requestAgentConfig": {"temperature": 0.7}},
    "/bark": {"agent": "Suno_Bark", "requestAgentConfig": {}},
    "/xtts": {"agent": "Coqui_XTTS", "requestAgentConfig": {}},
    "/meta_mms": {"agent": "Meta_MMS", "requestAgentConfig": {}},
    "/google_docs_ai": {"agent": "Google_DocsAI", "requestAgentConfig": {}},
    "/paddle_ocr": {"agent": "Paddle_OCR", "requestAgentConfig": {}},
    "/microsoft_trocr": {"agent": "Microsoft_TrOCR", "requestAgentConfig": {}},
    "/mistralai" : {"agent": "MistralAI_Mixtral7b_Instruct", "requestAgentConfig": {"temperature": 0.4}}
}

dialog_configs = {}
dialog_lockers = {}
dialog_modes = {}

#dialog_configurations = {}
myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler, dialogs={})

async def main():
    server_task = myceliumRouter.start_server(allowNewDialogs=False)
    bot_task = bot.polling()
    await asyncio.gather(server_task, bot_task)

if __name__ == "__main__":
    asyncio.run(main())