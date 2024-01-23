# Available Agents in ComradeAI

This document details the AI agents available in the ComradeAI Discord interface, emphasizing their functionalities, strengths, and specific parameters.

## Configuring and Using Agents in ComradeAI

In ComradeAI, the choice and configuration of an AI agent are crucial. This is managed through the `agent` variable, which are then used as part of the `routingStrategy`, and `requestAgentConfig` dictionary.

### Agent Variable
The `agent` variable specifies which AI agent you intend to use. This should be set to the agent's identifier within the ComradeAI framework.

### RoutingStrategy
The `routingStrategy` is a crucial component in directing your requests to the correct AI agent. It includes the `agent` variable as part of its configuration, especially for 'auto' and 'direct' strategies.

### Example of Setting Up and Using an Agent

1. **Set the Agent Variable:**
   Define which AI agent you want to use. For example, for GPT 3.5 Turbo:
   ```python
   agent = "gpt-3.5-turbo-1106"
   ```

2. **Define RoutingStrategy:**
    Incorporate the agent variable into the routing strategy which is Mycelium.Message constructor (__init__) parameter.
   ```python
    routingStrategy = RoutingStrategy("direct", agent)
    # Means you know which agent you need and there is no need for Mycelium to auto-define it.
   ```

3. **Configure the RequestAgentConfig:**
    Set up the specific parameters for the chosen agent. This dictionary is a member of Mycelium.Dialog class.
   ```python
    requestAgentConfig = {
        "max_tokens": 100,
        "temperature": 0.7
        # Add other parameters as needed
    }
   ```

4. **Use in Mycelium:**
    When sending a message or initializing a dialog, include these configurations to ensure your request is processed by the specified agent.

## OpenAI DALL-e 3 (Artistic Image Generation)

### Agent Name
The service is incapsulated by "OpenAI_DALLE3" agent.

### Purpose
Generates high-quality, creative images from textual descriptions.

### Strengths
- Produces detailed, artistic images from descriptive prompts.
- Offers versatility in styles and resolutions.

### Parameters
- `size` (string): Image resolution, choices: "1024x1024", "1792x1024", "1024x1792".
- `style` (string): Image style, choices: "vivid", "natural".
- `n` (integer): Number of images to generate.
- `quality` (string): Image quality, choices: "standard", "hd".
- **Note**: The prompt of the etire dialog to pass to DALLE-e 3 is limited to 4000 characters.

## Gemini Pro Vision (Multimodal AI)

### Agent Name
The service is incapsulated by "Google_GeminiProVisoin" agent.

### Purpose
Handles multimodal tasks including text generation, image analysis, and video processing.

### Strengths
- Advanced in understanding and generating text based on diverse inputs.
- Skilled in analyzing and interpreting visual content.

### Parameters
- `model` (string): Specific model selection. Supports "gemini-pro" for text to text generation and "gemini-pro-vision" for text/image(s)/video(s) to text generation.
- `max_output_tokens` (integer): Limits response size, usually 10-1000.
- `temperature` (float): Controls the randomness in responses, with a range from 0.1 to 1.0.
- `top_p` (float): Influences the diversity of generated text, range: 0.1 - 1.0.
- `top_k` (integer): Narrows the set of tokens to be considered for responses, typically from 1 to 40.
- `stop_sequences` (string/array): Defines specific sequences where the model will stop generating further tokens.

## OpenAI GPT Models (Advanced Text Generation)

### Agent Name
The services are incapsulated by "OpenAI_GPT_Completions" agent.

The ComradeAI framework integrates three advanced models from OpenAI's GPT series, each designed for specific text generation tasks and offering unique capabilities.

### GPT 3.5 Turbo

#### Purpose
GPT 3.5 Turbo is designed for high-speed, cost-effective text generation, maintaining a balance between performance and accuracy.

#### Strengths
- Faster response times compared to other GPT models.
- Cost-effective for applications that require quick, coherent text generation.
- Suitable for chatbots, quick content creation, and real-time applications.

#### Parameters
- `model`: "gpt-3.5-turbo-1106".
- `max_tokens` (integer): Limits the output length, typically 10-4096 tokens.
- `temperature` (float): Controls randomness in output, range: 0.0 - 1.0.
- `top_p` (float): Influences diversity, range: 0.1 - 1.0.
- `frequency_penalty` (float): Reduces repetition, range: 0.0 - 2.0.
- `presence_penalty` (float): Encourages new concepts, range: 0.0 - 2.0.
- `stop` (string/array): Specifies tokens at which the model should stop generating further content.
- **Note**: The prompt pass (the context window) to the model is limited to 16,385 tokens.

### GPT 4 (Text and Code)

#### Purpose
GPT 4 excels in understanding and generating both human language and code, making it versatile for a wide range of applications.

#### Strengths
- Advanced comprehension and generation of complex text.
- Capable of understanding and generating code in various programming languages.
- Ideal for detailed content creation, technical documentation, and programming-related tasks.

#### Parameters
- `model` (string): "gpt-4-1106-preview".
- `max_tokens` (integer): Limits output length, up to 4096 tokens.
- `temperature` (float): Adjusts creativity, range: 0.0 - 1.0.
- `top_p` (float): Controls diversity, range: 0.1 - 1.0.
- `frequency_penalty` (float): Decreases repetition, range: 0.0 - 2.0.
- `presence_penalty` (float): Encourages novelty, range: 0.0 - 2.0.
- `stop` (string/array): Specifies tokens at which the model should stop generating further content.
- **Note**: The prompt pass (the context window) to the model is limited to 128,000 tokens.

### GPT 4 Vision (Multimodal)

#### Purpose
GPT 4 Vision is a multimodal model capable of processing and generating both text and images, bridging the gap between visual and textual data.

#### Strengths
- Interprets and generates text based on visual inputs.
- Capable of creating content that combines visual and textual elements.
- Suitable for applications requiring integration of text and images, such as graphic design suggestions, visual storytelling, and educational content.

#### Parameters
- `model` (string): "gpt-4-vision-preview".
- `max_tokens` (integer): Limits output length, up to 4096 tokens.
- `temperature` (float): Adjusts creativity, range: 0.0 - 1.0.
- `top_p` (float): Controls diversity, range: 0.1 - 1.0.
- `frequency_penalty` (float): Decreases repetition, range: 0.0 - 2.0.
- `presence_penalty` (float): Encourages novelty, range: 0.0 - 2.0.
- `stop` (string/array): Specifies tokens at which the model should stop generating further content.
- **Note**: The prompt pass (the context window) to the model is limited to 128,000 tokens.

## Meta LLaMa 2 (Versatile Text Processor)

### Agent Name
The service is incapsulated by "Meta_LLaMa2" agent.

### Purpose
Efficient in diverse text processing tasks, offering unique capabilities.

### Strengths
- Excels in translation, summarization, and question-answering.
- Offers a distinct style compared to GPT models.
- Sensitive to context; setting up a system message (role="system") is recommended for appropriate results.

### Parameters
- `temperature` (float): Adjusts creativity level, range: 0.0 - 1.0.
- `max_tokens` (integer): Total token count limit, typically up to 4096.
- `max_response_words` (integer): Maximum word count for responses. Default is 100 words.

## YandexGPT v2 (Russian Language Text Generation)

### Agent Name
The service is incapsulated by "YandexGPT2-FULL" agent.

### Purpose
Specialized in generating and processing text in Russian, with a nuanced understanding of the language.

### Strengths
- Creates coherent, contextually relevant Russian text.
- Particularly effective for high-quality Russian language output.
- Context-sensitive; setting up a system message (role="system") is recommended for accurate results.

### Parameters
- `temperature` (float): Controls creativity and style, range: 0.0 - 1.0.
- `maxtokens` (integer): Total token count limit, usually up to 8000.

## Groot (Connectivity Verification)

### Agent Name
The service is incapsulated by "groot" agent.

### Purpose
Used to verify successful connectivity to the Mycelium network.

### Strengths
- Provides a consistent "I am Groot!" response for connection testing.
- Free of charge, ideal for initial setup and connectivity checks.

### Parameters
- No parameters are required. The primary function is to confirm system connectivity.