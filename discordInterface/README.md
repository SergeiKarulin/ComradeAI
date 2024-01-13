# ComradeAI Discord Bot

## Overview
This Discord bot integrates with various AI agents available through ComradeAI, offering multimodal interactions including text and image processing. It allows users to interact with different AI models like OpenAI's DALL-e 3, Google's Gemini Pro, Meta's LLaMa 2, and others.

## Features
- Support for multiple AI agents including OpenAI, Google, Meta, and Yandex.
- Multimodal interactions: text and image processing.
- Customizable agent settings via slash commands.
- Dynamic context handling for conversations.
- Ability to handle and process different file formats and URLs.

## Installation
1. Clone the repository: git clone <repository_url>

2. Install required dependencies: pip install -r requirements.txt

## Configuration
- Set up your environment variables in a `.env` file:
- `DISCORD_TOKEN`: Your Discord bot token.
- `COMRADEAI_TOKEN`: Your ComradeAI access token.
- Configure bot intents in Discord Developer Portal to enable `messages` and `message_content`.

## Usage
1. Run the bot: interfgace.py
2. Use the bot in Discord through the following slash commands:
- `/dall-e_3`: Interact with OpenAI DALL-e 3 for image generation.
- `/gemini_pro`: Use Gemini Pro Vision from Vertex AI/Google for text, images, and video processing.
- `/chat_gpt_completions`: Access various GPT models for text generation.
- `/llama_2`: Interact with Meta LLaMa 2 for text-to-text processing.
- `/yandex_gpt_full`: Utilize YandexGPT v2 for larger text generation with good Russian support.
- `/restart`: Restart the conversation and redefine the context.
- `/groot`: Test connection to Mycelium.

## Developer Notes
- The bot's architecture leverages `Mycelium` for handling dialogues and routing to appropriate AI agents.
- Each user can have a unique dialogue and context.
- Dialogues are identifiable by unique IDs and can be dynamically managed.

### Saving and Loading Dialogues
- Dialogues can be saved to a file and loaded using the provided methods in `ComradeAI.DocumentRoutines`.

## Contributing
Contributions to the bot are welcome. Please follow the standard fork-and-pull request workflow.

## License
MIT License

