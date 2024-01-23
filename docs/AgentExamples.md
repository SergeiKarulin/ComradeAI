# Agent Examples in ComradeAI

Welcome to `AGENTEXAMPLES.md`! This document provides practical examples for each of the AI agents available within the ComradeAI framework. Each section is dedicated to a specific agent and includes a detailed example showcasing how to interact with that agent using ComradeAI. The examples are designed to be informative and easy to follow, providing insights into the capabilities of each agent and explaining key concepts in their usage.

Whether you are looking to generate images, process text, or engage in multimodal AI tasks, these examples will guide you through the functionalities of each agent. You'll find explanations accompanying the code to clarify the processes and configurations involved, making it easier for you to adapt these examples to your specific needs.

Feel free to navigate through the sections to explore the diverse range of AI agents and learn how to effectively utilize them in your projects with ComradeAI.

## OpenAI DALL-e 3 Agent Usage Example

This section demonstrates how to use the OpenAI DALL-e 3 agent in the ComradeAI framework to generate images based on textual descriptions. The example covers the process from setting up the request to handling and displaying the generated image.

### Prerequisites
- PIL (Python Imaging Library) installed: pip install Pillow
- Python's json and asyncio modules
- ComradeAI

### Important notes
- The OpenAI DALL-e 3 agent returns a PIL image object.
- The requestAgentConfig must be a JSON-formatted string.

### Script Example

```python
import asyncio
import io
import uuid
from PIL import Image
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy

# Function to display the image using PIL
def display_image(image_data):
    image = Image.open(io.BytesIO(image_data))
    image.show()

# Handler to process the response from Mycelium
async def message_received_handler(dialog):
    for message in dialog.messages:
        for prompt in message.unified_prompts:
            if prompt.content_type == 'image':
                # Convert the PIL Image object to bytes if necessary
                if isinstance(prompt.content, bytes):
                    image_data = prompt.content
                else:
                    image_bytes_io = io.BytesIO()
                    prompt.content.save(image_bytes_io, format='PNG')
                    image_data = image_bytes_io.getvalue()
                display_image(image_data)

async def send_request_to_dalle(comradeai_token, myceliumRouter):
    # Set the Agent Variable and RoutingStrategy
    agent = "OpenAI_DALLE3"
    routing_strategy = RoutingStrategy("direct", agent)

    # Configure the RequestAgentConfig as a JSON string
    requestAgentConfig = {
        "size": "1024x1024",
        "style": "vivid",
        "n": 1,
        "quality": "standard"
    }

    # Create a Dialog instance with a unique ID and configure it
    dialog_id = str(uuid.uuid4())
    dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
    description_prompt = UnifiedPrompt(content_type="text", content="Create an image of a futuristic city at sunset", mime_type="text/plain")
    hello_message = Message(role="user", unified_prompts=[description_prompt], routingStrategy=routing_strategy)

    myceliumRouter.dialogs[dialog_id] = dialog
    myceliumRouter.dialogs[dialog_id].requestAgentConfig = requestAgentConfig
    myceliumRouter.dialogs[dialog_id].messages.append(hello_message)

    # Send the dialog to Mycelium with the specified routing strategy
    await myceliumRouter.send_to_mycelium(dialog_id, isReply=False)

async def main():
    # Initialize Mycelium with your ComradeAI token
    comradeai_token = 'your_ComradeAI_token'  # Replace with your actual token
    myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler, dialogs={})

    # Send request and start server
    await send_request_to_dalle(comradeai_token, myceliumRouter)   
    await myceliumRouter.start_server(allowNewDialogs=False)


if __name__ == "__main__":
    asyncio.run(main())
```

### Explanation

The script initializes the ComradeAI Mycelium router and sets up a dialog with a textual description for image generation.
The message_received_handler handles the response from DALL-e 3. If the response contains an image, it is displayed using the PIL library. This script can handle both bytes and PIL Image objects.

## Google/VertexAI Gemini Pro Vision Agent Usage Example

This section demonstrates how to use the Gemini Pro Vision agent in the ComradeAI framework for multimodal tasks including text generation, image analysis, and video processing. The example covers setting up the request and handling the response.

We request Google Gemini Pro Vision to convert an image to an XML-file, structuring items appearing on this image.

### Prerequisites
- Python's json and asyncio modules
- ComradeAI

### Important notes
- The Gemini Pro Vision agent can handle text, images, and videos for generating responses.
- The requestAgentConfig must be a JSON-formatted string.

### Script Example

```python
import asyncio
import uuid
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt,RoutingStrategy

# Handler to process the response from Mycelium
async def message_received_handler(dialog):
    for message in dialog.messages:
        for prompt in message.unified_prompts:
            # Handle the response here
            # Example: Print the text content
            if prompt.content_type == 'text':
                print(prompt.content)

async def send_request_to_gemini_pro(comradeai_token, myceliumRouter):
    # Set the Agent Variable and RoutingStrategy
    agent = "Google_GeminiProVision"
    routingStrategy = RoutingStrategy("direct", agent)

    # Configure the RequestAgentConfig as a JSON string
    requestAgentConfig = {
        "model": "gemini-pro-vision",
        "max_output_tokens": 1024,
        "temperature": 0.7,
        "top_p": 1.0,
        "top_k": 40
        # Add other parameters as needed
    }

    # Create a Dialog instance with a unique ID and configure it
    dialog_id = str(uuid.uuid4())
    dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
    
    # Text and Image Prompt
    text_prompt = UnifiedPrompt(content_type="text", content="Provide an XML-code listing and describing every item on the picture.", mime_type="text/plain")
    image_url = "https://images.freeimages.com/image/previews/cb3/travel-elements-map-5692424.jpg"
    image_prompt = UnifiedPrompt(content_type="url", content=image_url, mime_type="image/jpeg")
    hello_message = Message(role="user", unified_prompts=[text_prompt, image_prompt], routingStrategy=routingStrategy)

    myceliumRouter.dialogs[dialog_id] =  dialog
    myceliumRouter.dialogs[dialog_id].requestAgentConfig = requestAgentConfig

    myceliumRouter.dialogs[dialog_id].messages.append(hello_message)

    # Send the dialog to Mycelium with the specified routing strategy
    await myceliumRouter.send_to_mycelium(dialog_id, isReply=False)

async def main():
    # Initialize Mycelium with your ComradeAI token
    comradeai_token = '0xADeCEfdF7409B87969EEC0cacf6B7575c27aA05e.864960034558443590'  # Replace with your actual token
    myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler, dialogs={})

    # Send request and start server
    await send_request_to_gemini_pro(comradeai_token, myceliumRouter)
    await myceliumRouter.start_server(allowNewDialogs=False)

if __name__ == "__main__":
    asyncio.run(main())
```

### Explanation
- The script initializes the ComradeAI Mycelium router and sets up a dialog with a text prompt for processing.
- The message_received_handler handles the response from the Gemini Pro Vision agent. In this example, it simply prints the text content of the response, but it can be modified to handle images or videos.

# Anthropic CLAUDE 2.1 Agent Usage Example
This section demonstrates how to use the Anthropic CLAUDE 2.1 agent in the ComradeAI framework for creative and generative text tasks. The example includes setting up a request to generate novel and engaging names for a hypothetical product, in this case, a flying car, along with creative idea notes for each name.

## Prerequisites
- Python's asyncio and uuid modules
- ComradeAI

## Important notes
- The Anthropic CLAUDE 2.1 agent specializes in generating creative and contextually relevant text, it is an extremely friendly service.
- The response is purely text-based.

## Script Example
```python
import asyncio
import uuid
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy

# Handler to process the response from Mycelium
async def message_received_handler(dialog):
    for message in dialog.messages:
        for prompt in message.unified_prompts:
            # Handle the text response here
            if prompt.content_type == 'text':
                print(prompt.content)

async def send_request_to_claude(comradeai_token, myceliumRouter):
    # Set the Agent Variable and RoutingStrategy
    agent = "Anthropic_CLAUDE2.1"
    routingStrategy = RoutingStrategy("direct", agent)

    # Create a Dialog instance with a unique ID and configure it
    dialog_id = str(uuid.uuid4())
    dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
    
    # Text Prompt for generating flying car names and ideas
    text_prompt = UnifiedPrompt(content_type="text", content="Generate 50 engaging names for new flying car. Add an idea note for each of them.", mime_type="text/plain")
    hello_message = Message(role="user", unified_prompts=[text_prompt], routingStrategy=routingStrategy)

    myceliumRouter.dialogs[dialog_id] = dialog
    myceliumRouter.dialogs[dialog_id].messages.append(hello_message)

    # Send the dialog to Mycelium with the specified routing strategy
    await myceliumRouter.send_to_mycelium(dialog_id, isReply=False)

async def main():
    # Initialize Mycelium with your ComradeAI token
    comradeai_token = 'your_ComradeAI_token'  # Replace with your actual token
    myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler, dialogs={})

    # Send request and start server
    await send_request_to_claude(comradeai_token, myceliumRouter)
    await myceliumRouter.start_server(allowNewDialogs=False)

if __name__ == "__main__":
    asyncio.run(main())
```
## Explanation
- The script demonstrates the use of the Anthropic CLAUDE 2.1 agent for creative text generation.
- Upon receiving a response, the message_received_handler function prints the generated names and ideas for the flying car.
- The example highlights the agent's ability to creatively interpret and execute text-based prompts, making it suitable for innovative and imaginative tasks.