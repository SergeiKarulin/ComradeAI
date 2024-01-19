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
import json
import uuid
from PIL import Image
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt

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
    routingStrategy = {
        'strategy': 'direct',
        'params': agent
    }

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
    hello_message = Message(role="user", unified_prompts=[description_prompt])
    dialog.messages.append(hello_message)
    dialog.requestAgentConfig = requestAgentConfig

    # Send the dialog to Mycelium with the specified routing strategy
    await myceliumRouter.send_to_mycelium(dialog, routingStrategy)

async def main():
    # Initialize Mycelium with your ComradeAI token
    comradeai_token = 'your_comradeai_token'  # Replace with your actual token
    myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler)

    # Send request and start server
    await send_request_to_dalle(comradeai_token, myceliumRouter)
    await myceliumRouter.start_server(allowNewDialogs=True)

if __name__ == "__main__":
    asyncio.run(main())
```

### Explanation

The script initializes the ComradeAI Mycelium router and sets up a dialog with a textual description for image generation.
The message_received_handler handles the response from DALL-e 3. If the response contains an image, it is displayed using the PIL library. This script can handle both bytes and PIL Image objects.

## Google/VertexAI Gemini Pro Vision Agent Usage Example

This section demonstrates how to use the Gemini Pro Vision agent in the ComradeAI framework for multimodal tasks including text generation, image analysis, and video processing. The example covers setting up the request and handling the response.

### Prerequisites
- Python's json and asyncio modules
- ComradeAI

### Important notes
- The Gemini Pro Vision agent can handle text, images, and videos for generating responses.
- The requestAgentConfig must be a JSON-formatted string.

### Script Example

```python
import asyncio
import json
import uuid
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt

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
    routingStrategy = {
        'strategy': 'direct',
        'params': agent
    }

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
    
    hello_message = Message(role="user", unified_prompts=[text_prompt, image_prompt])
    dialog.messages.append(hello_message)
    dialog.requestAgentConfig = requestAgentConfig

    # Send the dialog to Mycelium with the specified routing strategy
    await myceliumRouter.send_to_mycelium(dialog, routingStrategy)

async def main():
    # Initialize Mycelium with your ComradeAI token
    comradeai_token = 'your_comradeai_token'  # Replace with your actual token
    myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler)

    # Send request and start server
    await send_request_to_gemini_pro(comradeai_token, myceliumRouter)
    await myceliumRouter.start_server(allowNewDialogs=True)

if __name__ == "__main__":
    asyncio.run(main())
```

### Explanation
- The script initializes the ComradeAI Mycelium router and sets up a dialog with a text prompt for processing.
- The message_received_handler handles the response from the Gemini Pro Vision agent. In this example, it simply prints the text content of the response, but it can be modified to handle images or videos.