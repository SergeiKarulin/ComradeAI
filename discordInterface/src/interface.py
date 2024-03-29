#----------------------------------------------------ToDo----------------------------------------------------#
# 1. Documented example of how to save dialog to file and load it. Everything is ready for that.
#------------------------------------------------------------------------------------------------------------#

from ComradeAI.DocumentRoutines import DocxToPromptsConverter, XlsxToPromptsConverter
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy
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

# Message received handler function
async def message_received_handler(dialog):
    for message in dialog.messages:
        if dialog.endUserCommunicationID.startswith("channel.id:"):
            endUserCommunicationID = dialog.endUserCommunicationID[len("channel.id:"):]
            try:
                channel = bot.get_channel(int(endUserCommunicationID))
            except Exception as ex:
                print ("Error: broken dialog.endUserCommunicationID returned: channel.id is not integer. The message is passed.")
                return False
        elif dialog.endUserCommunicationID.startswith("user.id:"):
            endUserCommunicationID = dialog.endUserCommunicationID[len("user.id:"):]
            try:
                user = await bot.fetch_user(int(endUserCommunicationID))
            except Exception as ex:
                print ("Error: broken dialog.endUserCommunicationID returned: user.id is not integer. The message is passed.")
                return False
            channel = await user.create_dm()
        else:
            print ("Error: broken dialog.endUserCommunicationID returned. The message is passed.")
            return False
        for prompt in message.unified_prompts:
            if prompt.content_type == 'text':
                await send_long_message(channel, prompt.content)
            elif prompt.content_type == 'image':                  
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                    prompt.content.save(tmp_file, 'PNG')
                    tmp_file_path = tmp_file.name
                await channel.send(file=nextcord.File(fp=tmp_file_path, filename='tmpImage.png'))
                os.remove(tmp_file_path)
    return True

dialog_configurations = {}
myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler, dialogs={})

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
    elif mime_type in ["audio/mpeg", "audio/ogg", "audio/wav"]:
        return [UnifiedPrompt(content_type="audio", content=content, mime_type=mime_type)]
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
    global myceliumRouter
    dialog_id = str(message.author.id)
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
        myceliumRouter.dialogs[dialog_id]=dialog
        dialog_configurations[dialog_id] = {"agent": "groot", "requestAgentConfig": ""}
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
        new_message = Message(role="user", unified_prompts=prompts, sender_info="Discord User", subAccount=str(message.author.id), routingStrategy=RoutingStrategy("direct", dialog_configurations[dialog_id]['agent']))
        if message.guild is not None:
            endUserCommunicationID = "channel.id:" + str(message.channel.id)
        else:
            endUserCommunicationID = "user.id:" + str(message.author.id)
        myceliumRouter.dialogs[dialog_id].messages.append(new_message)
        myceliumRouter.dialogs[dialog_id].endUserCommunicationID = endUserCommunicationID
        myceliumRouter.dialogs[dialog_id].requestAgentConfig = dialog_configurations[dialog_id]['requestAgentConfig']
        await myceliumRouter.send_to_mycelium(dialog_id, isReply=False)

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
    requestAgentConfig = None
    tmpConfig = None
    if size is not None or style is not None or n is not None or quality is not None :
        tmpConfig = {"size" : size, "style" : style, "n" : n, "quality": quality}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "OpenAI_DALLE3"
    dialog_id = str(interaction.user.id)
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set OpenAI DALL-e 3, config: " + str(tmpConfig))


@bot.slash_command(name="mindsimulation_steos_voice", description="An amazing Text to Speech model for Russian and English")
async def mindsimulation_steos_voice(
        interaction: Interaction,
        voice_id: int = SlashOption(
            name="voice_id",
            description="Choose a voice. There are 500+ of them, here are some examples",
            required=False,
            choices={
                "Stanislav Kontsevich": 198,
                "Maria Voice of radio host Maria Zagumyonnova": 18,
                "The voice of professional announcer Ilya Rogovin": 19,
                "Olaf Character voice from Disney Infinity": 413,
                "Anna Omutkova Professional Russian dubbing actor": 360,
                "Alpatkin Alexander Professional Russian dubbing actor": 359,
                "Han Solo": 408,
                "Bart Simpson": 232,
                "Homer Simpson": 229,
                "Thrall from Warcraft": 260,
                "Acolyte from Warcraft": 263,
                "A female voice with a pleasant timbre": 72,
                "A male voice with a pleasant timbre": 64,
                "A male voice with a pleasant timbre (2)": 63,
                "A female voice with a pleasant tone": 35,
                "A voice of an elder narrator character": 23
            },
        ),
        file_format: str = SlashOption(
            name="file_format",
            description="Output file format",
            required=False, 
            choices={
                "mp3": "mp3",
                "ogg": "ogg",
                "wav": "wav"
            }
        ),
    ):
    requestAgentConfig = None
    tmpConfig = None
    if voice_id is not None or file_format is not None:
        tmpConfig = {"voice_id" : voice_id, "file_format" : file_format}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "MindSimulation_SteosVoice"
    dialog_id = str(interaction.user.id)
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
        myceliumRouter.dialogs[dialog_id]=dialog
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set Mind Simulation SteosVoice, config: " + str(tmpConfig))
    
@bot.slash_command(name="stable_diffusion_txt2img", description="Agent Stable Diffusion - realistic imaging")
async def stable_diffusion_txt2img(
        interaction: Interaction,
        negative_prompt: str = SlashOption(
            name="negative_prompt",
            description="Negative prompt. If not set up, default negative prompt will be used",
            required=False,
        ),
        n_steps : int = SlashOption(
            name="n_steps",
            description="Amount of iterations during generation and refinery. Defaults to 100",
            required=False, 
            min_value=1
        ),
        high_noise_frac: float = SlashOption(
            name="high_noise_frac",
            description="The fraction of highly noicy iterations. Defaults to 0.8.",
            required=False,
            min_value=0.1
        )
    ):
    requestAgentConfig = None
    tmpConfig = None
    if negative_prompt is not None or n_steps is not None or high_noise_frac is not None :
        tmpConfig = {"negative_prompt" : negative_prompt, "n_steps" : n_steps, "high_noise_frac": high_noise_frac}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "StabeDiffusion_Text2Image"
    dialog_id = str(interaction.user.id)
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
        myceliumRouter.dialogs[dialog_id]=dialog
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set Stabe Diffusion XL Text-to-Image, config: " + str(tmpConfig))


@bot.slash_command(name="mbart", description="Agent Meta MBART to translate between 50 languages.")
async def mbart(
        interaction: Interaction,
        source_language: str = SlashOption(
            name="source_language",
            description="The language of your original text",
            required=True,
            choices={
                "Russian": "ru_RU",
                "English": "en_XX",
                "Chinese": "zh_CN",
                "Arabic": "ar_AR",
                "Bengali": "bn_IN",
                "French": "fr_XX",
                "German": "de_DE",
                "Greek": "el_GR",
                "Hebrew": "he_IL",
                "Hindi": "hi_IN",
                "Indonesian": "id_ID",
                "Italian": "it_IT",
                "Japanese": "ja_XX",
                "Korean": "ko_KR",
                "Malay": "ms_MY",
                "Polish": "pl_PL",
                "Portuguese": "pt_XX",
                "Romanian": "ro_RO",
                "Spanish": "es_XX",
                "Swedish": "sv_SE",
                "Thai": "th_TH",
                "Turkish": "tr_TR",
                "Vietnamese": "vi_VN",
                "Urdu" : "ur_PK"
            },
        ),
        target_language: str = SlashOption(
            name="target_language",
            description="The language you want to translate to",
            required=True, 
            choices={
                "Russian": "ru_RU",
                "English": "en_XX",
                "Chinese": "zh_CN",
                "Arabic": "ar_AR",
                "Bengali": "bn_IN",
                "French": "fr_XX",
                "German": "de_DE",
                "Greek": "el_GR",
                "Hebrew": "he_IL",
                "Hindi": "hi_IN",
                "Indonesian": "id_ID",
                "Italian": "it_IT",
                "Japanese": "ja_XX",
                "Korean": "ko_KR",
                "Malay": "ms_MY",
                "Polish": "pl_PL",
                "Portuguese": "pt_XX",
                "Romanian": "ro_RO",
                "Spanish": "es_XX",
                "Swedish": "sv_SE",
                "Thai": "th_TH",
                "Turkish": "tr_TR",
                "Vietnamese": "vi_VN",
                "Urdu" : "ur_PK"
            }
        )
    ):
    requestAgentConfig = None
    tmpConfig = None
    if source_language is not None or target_language is not None:
        tmpConfig = {"src_lang" : source_language, "target_lang" : target_language}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "Meta_MBART"
    dialog_id = str(interaction.user.id)
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
        myceliumRouter.dialogs[dialog_id]=dialog
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set Meta MBART, config: " + str(tmpConfig))
    
@bot.slash_command(name="whisper_v3", description="OpenAI Whisper Large v3 - Speech to Text in multiple languages")
async def whisper_v3(interaction: Interaction,
        language: str = SlashOption(
            name="language",
            description="Target text language",
            required=False,
            choices={
                "Russian": "ru",
                "English": "en",
                "Chinese": "zh",
                "Arabic": "ar",
                "French": "fr",
                "Indonesian": "id",
                "Italian": "it",
                "Korean": "ko",
                "Portuguese": "pt",
                "Spanish": "es",
                "Thai": "th",
                "Turkish": "tr",
                "Urdu" : "ur"
            }
        )):
    requestAgentConfig = None
    tmpConfig = None
    if language is not None:
        tmpConfig = {"language" : language}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "Whisper_v3_Large"
    dialog_id = str(interaction.user.id)
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
        myceliumRouter.dialogs[dialog_id]=dialog
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set OpenAI Whisper Large v3, config: " + str(tmpConfig))

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
    requestAgentConfig = None
    tmpConfig = None
    if sub_model is not None or max_output_tokens is not None or temperature is not None or top_p is not None or top_k is not None or stop_sequences is not None:
        tmpConfig = {"model" : sub_model, "max_output_tokens": max_output_tokens, "temperature" : temperature, "top_p" : top_p, "top_k" : top_k, "stopSequences" : stop_sequences}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "Google_GeminiProVision"
    dialog_id = str(interaction.user.id)
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set Gemini Pro/Pro Vision, config: " + str(tmpConfig))

@bot.slash_command(name="claude", description="Anthropic CLAUDE text/image-2-text model. Great creativity perfomance.")
async def claude(interaction: Interaction,
        temperature: float = SlashOption(
            name="temperature",
            description="The lower the more more deterministic response is. 0.1 to 1, default 1.",
            required=False, 
            min_value=0.1,
            max_value=1.0
        ),
        top_k : int = SlashOption(
            name="top_k",
            description="Narrows the set of tokens to select. To highter the more variation. Default 50",
            required=False, 
            min_value=1,
            max_value=200
        ),
        stop_sequences: str = SlashOption(
            name="stop_sequences",
            description="A sequence where the API will stop generating further tokens.",
            required=False
        )):
    requestAgentConfig = None
    tmpConfig = None
    if temperature is not None or top_k is not None or stop_sequences is not None:
        tmpConfig = {"temperature" : temperature, "top_k" : top_k, "stop_sequences" : stop_sequences}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "Anthropic_CLAUDE3"
    dialog_id = str(interaction.user.id)
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set Anthropic CLAUDE, config: " + str(tmpConfig))
    
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
    requestAgentConfig = None
    tmpConfig = None
    if sub_model is not None or max_tokens is not None or frequency_penalty is not None or top_p is not None or temperature is not None or response_format is not None or seed is not None or stop is not None:
        tmpConfig = {"model" : sub_model, "max_tokens" : max_tokens, "frequency_penalty" : frequency_penalty, "top_p": top_p, "temperature": temperature, "response_format": response_format, "seed": seed, "stop": stop}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "OpenAI_GPT_Completions"
    dialog_id = str(interaction.user.id)
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
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
    requestAgentConfig = None
    tmpConfig = None
    if temperature is not None or max_tokens is not None or max_responce_words is not None:
        tmpConfig = {"temperature" : temperature, "max_tokens" : max_tokens, "max_responce_words" : max_responce_words }
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "Meta_LLaMa2"
    dialog_id = str(interaction.user.id)
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
    await interaction.response.send_message(f"Agent set LLaMa 2, config: " + str(tmpConfig) + ". It is highly recommended to set up context for LLaMa 2 using the /restart command.")
    
@bot.slash_command(name="groot", description="Testing connection to Mycelium")
async def groot(interaction: Interaction):
    agent = "groot"
    dialog_id = str(interaction.user.id)
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": ""}
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
    requestAgentConfig = None
    tmpConfig = None
    if temperature is not None or maxtokens is not None:
        tmpConfig = {"temperature" : temperature, "maxTokens" : maxtokens}
        requestAgentConfig = json.dumps(tmpConfig)
    agent = "YandexGPT2-FULL"
    dialog_id = str(interaction.user.id)
    dialog_configurations[dialog_id] = {"agent": agent, "requestAgentConfig": requestAgentConfig}
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
    dialog_id = str(interaction.user.id)
    dialog_ids = list(myceliumRouter.dialogs.keys())
    if not dialog_id in dialog_ids:
        dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
        myceliumRouter.dialogs[dialog_id]=dialog
        if dialog_id not in dialog_configurations or dialog_configurations[dialog_id] is None:
            dialog_configurations[dialog_id] = {"agent": "groot", "requestAgentConfig": ""}
        else:
            dialog_configurations[dialog_id]['requestAgentConfig'] = ""
    if context:
        myceliumRouter.dialogs[dialog_id] = Dialog(messages=[Message(role="system", unified_prompts = [UnifiedPrompt(content_type = 'text', content = context, mime_type = 'text/plain')], sender_info="system")], dialog_id=dialog_id, reply_to = comradeai_token)
    else:
        myceliumRouter.dialogs[dialog_id] = Dialog(messages=[], dialog_id=dialog_id, reply_to = comradeai_token)
    await interaction.response.send_message("Let's start again! The Agent: " + dialog_configurations[dialog_id]['agent'] + ". The context: " + str(context))

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await myceliumRouter.start_server(allowNewDialogs = False)

bot.run(discord_token)