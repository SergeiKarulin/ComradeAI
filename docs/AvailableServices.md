# Available Services and their paramenters
You can utilize any available Service using its name in the following manner:
```python

import asyncio
from ComradeAI.Mycelium import Mycelium, Agent

AI = Mycelium(ComradeAIToken=YOUR_COMRADEAI_TOKEN)
AI.connect()

llama2 = Agent(AI, "Meta_LLaMa2")

dialog = AI.Dialog(textPrompt=["Hello! How are you?"], agent=llama2)
print(dialog)

AI.connection.close()

```
Async calls are under development and expected in the nearest versions. Meanwhile you can implement async calls manually.

If you want to pass model parameteres to customize the Service behaviour, you may pass serviceParams dicto to Agent constructor. For example:

```python
    creative_params = {"temperature": 0.9}
    conservative_params = {"temperature": 0.5}
    llama2_creative = Agent(AI, "Meta_LLaMa2", creative_params)
    llama2_concervative = Agent(AI, "Meta_LLaMa2", conservative_params)
```

Agents llama2_creative and llama2_concervative based on the same Service "Meta_LLaMa2" will have different behaviour and respond differently, because the hihter the temperature the more artistic and creative the model is.

Each service has it's onn name and available parameters to adjust.

## Services and their available parameters
This reference is dated 2024.02.11. Since that new Services/models might be supported.

### Meta LLaMa 2
Service name: Meta_LLaMa2
Params template: {"temperature" : temperature, "max_tokens" : max_tokens, "max_responce_words" : max_responce_words}

Where:
- temperature is not required float, between 0.0 and 0.1, default is 0.7
- max_tokens is not required int, between 0 and 4096, default is 4096
- max_responce_words is not required int, default is 100.

### OpenAI DALL-e 3
Service name: OpenAI_DALLE3
Params template: {"size" : size, "style" : style, "n" : n, "quality": quality}

Where:

- size is not required string, choices are "1024x1024", "1792x1024", "1024x1792"
- style is not required string, choices are "vivid", "natural"
- n is not required int, default is 1
- quality is not required string, choices are "standard", "hd"

### MindSimulation Steos Voice
Service name: MindSimulation_SteosVoice
Params template: {"voice_id" : voice_id, "file_format" : file_format}

Where:

- voice_id is not required int, with predefined choices for voice identities. There is 500+  voices, for example:   "Stanislav Kontsevich": 198, "Maria Voice of radio host Maria Zagumyonnova": 18, "The voice of professional announcer Ilya Rogovin": 19, "Olaf": 413, "Anna Omutkova Professional Russian dubbing actor": 360, "Alpatkin Alexander Professional Russian dubbing actor": 359, "Han Solo style": 408, "Bart Simpson style": 232, "Homer Simpson style": 229, "Thrall": 260, "Acolyte": 263, "A female voice with a pleasant timbre": 72, "A male voice with a pleasant timbre": 64, "A male voice with a pleasant timbre (2)": 63, "A female voice with a pleasant tone": 35, "A voice of an elder narrator character": 23
- file_format is not required string, choices are "mp3", "ogg", "wav"

### Stable Diffusion Text-to-Image
Service name: StabeDiffusion_Text2Image
Params template: {"negative_prompt" : negative_prompt, "n_steps" : n_steps, "high_noise_frac": high_noise_frac}

Where:

- negative_prompt is not required string
- n_steps is not required int, default is 100
- high_noise_frac is not required float, default is 0.8

### Meta MBART
Service name: Meta_MBART
Params template: {"src_lang" : source_language, "target_lang" : target_language}

Where:

- source_language is required string, with predefined choices for languages
- target_language is required string, with predefined choices for languages

Language code examples: "Russian": "ru_RU", "English": "en_XX", "Chinese": "zh_CN", "Arabic": "ar_AR", "Bengali": "bn_IN", "French": "fr_XX", "German": "de_DE", "Greek": "el_GR", "Hebrew": "he_IL", "Hindi": "hi_IN", "Indonesian": "id_ID", "Italian": "it_IT", "Japanese": "ja_XX", "Korean": "ko_KR", "Malay": "ms_MY", "Polish": "pl_PL", "Portuguese": "pt_XX", "Romanian": "ro_RO", "Spanish": "es_XX", "Swedish": "sv_SE", "Thai": "th_TH", "Turkish": "tr_TR", "Vietnamese": "vi_VN", "Urdu" : "ur_PK"

### OpenAI Whisper Large v3
Service name: Whisper_v3_Large
Params template: {"language" : language}

Where:
- language is not required string, with predefined choices for languages
Language code examples: "Russian": "ru", "English": "en", "Chinese": "zh", "Arabic": "ar", "French": "fr",  "Indonesian": "id", "Italian": "it", "Korean": "ko", "Portuguese": "pt", "Spanish": "es", "Thai": "th", "Turkish": "tr", "Urdu" : "ur"

### Gemini Pro Vision from Vertex AI/Google
Service name: Google_GeminiProVision
Params template: {"model" : model, "max_output_tokens": max_output_tokens, "temperature" : temperature, "top_p" : top_p, "top_k" : top_k, "stopSequences" : stop_sequences}

Where:

- model is not required string, choices are "gemini-pro", "gemini-pro-vision", default is "gemini-pro-vision"
- max_output_tokens is not required int
- temperature is not required float, between 0.1 and 1.0
- top_p is not required float, between 0.1 and 1.0
- top_k is not required int, between 1 and 40
- stop_sequences is not required string

### Anthropic CLAUDE 2.1
Service name: Anthropic_CLAUDE2.1
Params template: {"temperature" : temperature, "top_k" : top_k, "stop_sequences" : stop_sequences}

Where:

- temperature is not required float, between 0.1 and 1.0, default is 1
- top_k is not required int, default is 50
- stop_sequences is not required string

### OpenAI GPT Completions
Service name: OpenAI_GPT_Completions
Params template: {"model" : model, "max_tokens" : max_tokens, "frequency_penalty" : frequency_penalty, "top_p": top_p, "temperature": temperature, "response_format": response_format, "seed": seed, "stop": stop}

Where:

- model is not required string, with predefined choices for models "gpt-3.5-turbo-1106", "gpt-4-1106-preview", "gpt-4-vision-preview" default is "gpt-4-1106-preview"
- max_tokens is not required int
- frequency_penalty is not required float, between 0.0 and 1.0
- top_p is not required float, between 0.1 and 1.0
- temperature is not required float, between 0.0 and 2.0
- response_format is not required string, for JSON output
- seed is not required int
- stop is not required string

### Yandex GPT Full
Service name: YandexGPT2-FULL
Params template: {"temperature" : temperature, "maxTokens" : maxtokens}

Where:

- temperature is not required float, between 0.0 and 1.0, default is 0.2
- maxTokens is not required int, between 0 and 8000, default is 8000