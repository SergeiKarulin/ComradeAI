#----------------------------------------------------ToDo----------------------------------------------------#
# 1. Define if each user has his own dialog and context, or everyone work on the same task
# 2. Documented example of how to save dialog to file and load it. Everything is ready for that.
#------------------------------------------------------------------------------------------------------------#

#import debugpy
#debugpy.listen(('0.0.0.0', 5678))
#debugpy.wait_for_client()

from  ComradeAI.DocumentRoutines import DocxToPromptsConverter, XlsxToPromptsConverter
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt
from dotenv import load_dotenv
import io
from io import BytesIO
import json
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import os
from PIL import Image
import re
import requests
import tempfile
import textwrap
import uuid

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')
comradeai_token = os.getenv('COMRADEAI_TOKEN')

# Initialize the bot
intents = nextcord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Agent variable
agent = "groot"
requestAgentConfig  = None

# Message received handler function
async def message_received_handler(dialog):
    for message in dialog.messages:
        for prompt in message.unified_prompts:
            if prompt.content_type == 'text':
                channel = bot.get_channel(dialog.endUserCommunicationID)
                await send_long_message(channel, prompt.content)
            elif prompt.content_type == 'image':                  
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                    prompt.content.save(tmp_file, 'PNG')
                    tmp_file_path = tmp_file.name
                await channel.send(file=nextcord.File(fp=tmp_file_path, filename='tmpImage.png'))
                os.remove(tmp_file_path)


dialog_id = str(uuid.uuid4())
dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to = comradeai_token)
myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler, dialogs={})
myceliumRouter.dialogs[dialog_id]=dialog

def remove_mentions(text):
    pattern = r"<@\d+>"
    cleaned_text = re.sub(pattern, '', text)
    return cleaned_text.strip()

def download_file(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.content

def create_unified_prompt_from_url(url):
    mime_type = getMimeType(url)
    content = download_file(url)
    if mime_type.startswith('text/') or mime_type in ['application/xml', 'text/xml']:
        return [UnifiedPrompt(content_type="text", content=content.decode('utf-8'), mime_type=mime_type)]
    elif mime_type.startswith('image/'):
        return [UnifiedPrompt(content_type="image", content=Image.open(io.BytesIO(content)), mime_type=mime_type)]
    elif mime_type.startswith('application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
        converter = DocxToPromptsConverter(convert_urls=True)
        prompts = converter.convert(io.BytesIO(content))
        return prompts
    elif mime_type.startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
        converter = XlsxToPromptsConverter()
        prompts = converter.convert(io.BytesIO(content))
        return prompts
    return False

async def send_long_message(channel, text, max_length=2000):
    # Split the text into chunks of max_length characters
    for chunk in textwrap.wrap(text, max_length, replace_whitespace=False):
        await channel.send(chunk)

def getMimeType(url):
    try:
        response = requests.get(url)
        content_type = response.headers.get('Content-Type')
        return str(content_type)
    except requests.RequestException as e:
        return "unknown"
    
# Event listener for messages
@bot.event
async def on_message(message):
    global agent
    global myceliumRouter
    global requestAgentConfig
    if bot.user.mentioned_in(message) and bot.user != message.author:
        attachments = [attachment.url for attachment in message.attachments]
        prompts = [
            UnifiedPrompt(content_type="text", content=remove_mentions(message.content), mime_type="text/plain")
        ]
        #Discord provides URL access to all attachments, including large messages. We convert text attachements to text prompts and image attachments to images. All other mime_types are sent as URLs.
        if attachments:
            for url in attachments:
                prompt = create_unified_prompt_from_url(url)
                if prompt:
                    prompts.extend(prompt)
                else:
                    prompts.append(UnifiedPrompt(content_type="url", content=url, mime_type=getMimeType(url)))
        # Initialize Mycelium with user token. Everything else is default.
        new_message = Message(role="user", unified_prompts = prompts, sender_info="Discord User", subAccount=message.author.id)
        dialog_ids = list(myceliumRouter.dialogs.keys())
        myceliumRouter.dialogs[dialog_ids[0]].messages.append(new_message)
        myceliumRouter.dialogs[dialog_ids[0]].endUserCommunicationID = message.channel.id
        myceliumRouter.dialogs[dialog_ids[0]].requestAgentConfig = requestAgentConfig 
        await myceliumRouter.send_to_mycelium(myceliumRouter.dialogs[dialog_ids[0]], routingStrategy = {'strategy' : 'auto', 'params' : agent})

@bot.slash_command(name="dall-e_3", description="Agent OpenAI DALL-e 3 to generate images from text")
async def dall_e_3(
        interaction: Interaction,
        size: str = SlashOption(
            name="size",
            description="Image resolution",
            required=False,
            choices={
                "1024x1024": "1024x1024",
                "1792x1024": "1792x1024",
                "1024x1792": "1024x1792"
            },
        ),
        style: str = SlashOption(
            name="style",
            description="Vivid or natural. Vivid - hyper-real and dramatic. Natural - more natural. Defaults to ‘vivid’",
            required=False, 
            choices={
                "vivid": "vivid",
                "natural": "natural"
            }
        ),
        n : int = SlashOption(
            name="n",
            description="The number of images to generate. Defaults to 1.",
            required=False, 
            min_value=1
        ),
        quality: str = SlashOption(
            name="quality",
            description="The quality of the image. ‘hd’ - finer details and greater consistency. Defaults to ‘standard.",
            required=False, 
            choices={
                "standard": "standard",
                "hd": "hd"
            }
        )
    ):
    global agent
    global requestAgentConfig
    requestAgentConfig = None
    tmpConfig = None
    if size is not None or style is not None or n is not None or quality is not None :
        tmpConfig = {"size" : size, "style" : style, "n" : n, "quality": quality}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "OpenAI_DALLE3"
    await interaction.response.send_message(f"Agent set OpenAI DALL-e 3, config: " + str(tmpConfig))

@bot.slash_command(name="gemini_pro", description="Multimodal Gemini Pro Vision from Vertex AI/Google to generate text from text, images and video")
async def gemini_pro(interaction: Interaction,
        sub_model: str = SlashOption(
            name="model",
            description="Completion model. Default is gemini-pro-vision",
            required=False,
            choices={
                "gemini-pro": "gemini-pro",
                "gemini-pro-vision": "gemini-pro-vision"
            }
        ),
        max_output_tokens : int = SlashOption(
            name="max_output_tokens",
            description="Helps to limit responce size.",
            required=False, 
            min_value=10
        ),
        temperature: float = SlashOption(
            name="temperature",
            description="The lower the more more deterministic response is. 0.1 to 1, default 0.4 (Pro) or 0.9 (Pro Vision).",
            required=False, 
            min_value=0.1,
            max_value=1.0
        ),
        top_p: float = SlashOption(
            name="top_p",
            description="The lower the more probable tokens included into responce. 0.1 to 1, default 1.",
            required=False, 
            min_value=0.1,
            max_value=1.0
        ),
        top_k : int = SlashOption(
            name="top_k",
            description="Narrows the set of tokens to select. To highter the more variation. 1-40, default 32",
            required=False, 
            min_value=1,
            max_value=40
        ),
        stop_sequences: str = SlashOption(
            name="stop_sequences",
            description="A sequence where the API will stop generating further tokens.",
            required=False
        )):
    global agent
    global requestAgentConfig
    requestAgentConfig = None
    tmpConfig = None
    if sub_model is not None or max_output_tokens is not None or temperature is not None or top_p is not None or top_k is not None or stop_sequences is not None:
        tmpConfig = {"model" : sub_model, "max_output_tokens": max_output_tokens, "temperature" : temperature, "top_p" : top_p, "top_k" : top_k, "stopSequences" : stop_sequences}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "Google_GeminiProVisoin"
    await interaction.response.send_message(f"Agent set Gemini Pro/Pro Vision, config: " + str(tmpConfig))
    
@bot.slash_command(name="chat_gpt_completions", description="Agent OpenAI Completions: GPT3-Turbo, GPT4, GPT4 vision to generate text from text and images")
async def chat_gpt_completions(
        interaction: Interaction,
        sub_model: str = SlashOption(
            name="model",
            description="Completion model. Default is gpt-4-1106-preview",
            required=False,
            choices={
                "GPT 3.5 Turbo": "gpt-3.5-turbo-1106",
                "GPT 4 Turbo Preview": "gpt-4-1106-preview",
                "GPT 4 Vision Preview": "gpt-4-vision-preview"
            },
        ),
        max_tokens : int = SlashOption(
            name="max_tokens",
            description="Helps to limit responce size. Includes both input and output tokens.",
            required=False, 
            min_value=10
        ),
        frequency_penalty: float = SlashOption(
            name="frequency_penalty",
            description="Helps reduce repeats. Range from 0.1 to 1.0. Default is 0.0. Not used w Vision",
            required=False, 
            min_value=0.0,
            max_value=1.0
        ),
        top_p: float = SlashOption(
            name="top_p",
            description="The lower the more probable tokens included into responce. 0.1 to 1, default 1. Not used w Vision",
            required=False, 
            min_value=0.1,
            max_value=1.0
        ),
        temperature: float = SlashOption(
            name="temperature",
            description="Higher values like 0.8 will make the output more random. Between 0 and 2. Default 0.7.",
            required=False, 
            min_value=0.0,
            max_value=2.0
        ),
        response_format: str = SlashOption(
            name="response_format",
            description="JSON output required. PROMPT MUST CONTAIN WORD 'JSON'. Not used w Vision",
            required=False, 
            choices={
                "JSON": json.dumps({"type" : "json_object"})
            }
        ),
        seed : int = SlashOption(
            name="seed",
            description="Allows  to obtain consistent results for every input submitted to GPT. Not used w Vision",
            required=False
        ),
        stop: str = SlashOption(
            name="stop",
            description="A sequence where the API will stop generating further tokens. Not used w Vision",
            required=False, 
        ),
    ):
    global agent
    global requestAgentConfig
    requestAgentConfig = None
    tmpConfig = None
    if sub_model is not None or max_tokens is not None or frequency_penalty is not None or top_p is not None or temperature is not None or response_format is not None or seed is not None or stop is not None:
        tmpConfig = {"model" : sub_model, "max_tokens" : max_tokens, "frequency_penalty" : frequency_penalty, "top_p": top_p, "temperature": temperature, "response_format": response_format, "seed": seed, "stop": stop}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "OpenAI_GPT_Completions"
    await interaction.response.send_message(f"Agent set OpenAI GPT Completions, config: "  + str(tmpConfig))
    
@bot.slash_command(name="llama_2", description="Agent Meta LLaMa 2 - text-to-text like GPT3")
async def LLaMa2(
        interaction: Interaction,
        temperature: float = SlashOption(
            name="temperature",
            description="From 0.0 to 1.0. The higher the more creative the model is. Default is 0.7",
            required=False,
            min_value=0.0,
            max_value=1.0
        ),
        max_tokens: int = SlashOption(
            name="max_tokens",
            description="Sum of in and out tokes for the model. The less the faster. Max is 4096, defult is 4094.",
            required=False, 
            min_value=0, 
            max_value=4096 
        ),
        max_responce_words: int = SlashOption(
            name="max_responce_words",
            description="Max responce word count. The less the faster. Deafult 100.",
            required=False, 
            min_value=0
        ),
    ):
    global agent
    global requestAgentConfig
    requestAgentConfig = None
    tmpConfig = None
    if temperature is not None or max_tokens is not None or max_responce_words is not None:
        tmpConfig = {"temperature" : temperature, "max_tokens" : max_tokens, "max_responce_words" : max_responce_words }
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "Meta_LLaMa2"
    await interaction.response.send_message(f"Agent set LLaMa 2, config: " + str(tmpConfig) + ". It is highly recommended to set up context for LLaMa 2 using the /restart command.")
    
@bot.slash_command(name="groot", description="Testing connection to Mycelium")
async def groot(interaction: Interaction):
    global agent
    agent = "groot"
    await interaction.response.send_message(f"Agent configuired Groot")
    
@bot.slash_command(name="yandex_gpt_full", description="Agent YandexGPT v2 to generate larger text from text with good Russian")
async def yandex_gpt_full(
        interaction: Interaction,
        temperature: float = SlashOption(
            name="temperature",
            description="From 0.0 to 1.0. The higher the more creative the model is. Default is 0.2",
            required=False,
            min_value=0.0,
            max_value=1.0
        ),
        maxtokens: int = SlashOption(
            name="maxtokens",
            description="Sum of input and output tokes for the model. Max is 8000, defult is 8000.",
            required=False, 
            min_value=0, 
            max_value=8000 
        )
    ):
    global agent
    global requestAgentConfig
    requestAgentConfig = None
    tmpConfig = None
    if temperature is not None or maxtokens is not None:
        tmpConfig = {"temperature" : temperature, "maxTokens" : maxtokens}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "YandexGPT2-FULL"
    await interaction.response.send_message(f"Agent set YandexGPT v2, config: " + str(tmpConfig) + ". It is highly recommended to set up context for YandexGPT v2 using the /restart command.")
    
@bot.slash_command(name="restart", description="Restart the conversation, re-define context")
async def restart(
        interaction: Interaction,
        context: str = SlashOption(
            name="context",
            description="Tell the machine who it is today (used as a system message) for services that support it.",
            required=False  # This makes the parameter optional
        )
    ):
    global comradeai_token
    global agent
    if context:
        dialog_id = str(uuid.uuid4())
        dialog = Dialog(messages=[Message(role="system", unified_prompts = [UnifiedPrompt(content_type = 'text', content = context, mime_type = 'text/plain')], sender_info="system")], dialog_id=dialog_id, reply_to = comradeai_token)
    else:
        dialog_id = str(uuid.uuid4())
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to = comradeai_token)
    myceliumRouter.dialogs = {}
    myceliumRouter.dialogs[dialog.dialog_id] = dialog
    await interaction.response.send_message("Let's start again! The Agent: " + str(agent) + ". The context: " + str(context))

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await myceliumRouter.start_server(allowNewDialogs = False)

bot.run(discord_token)