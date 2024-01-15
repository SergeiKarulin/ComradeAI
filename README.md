# ComradeAI
Comrade AI is an open source framework that connects various AI services, such as Gemini Pro Vision, Claude, GPT-3/4, Meta LLaMa2, and Yandex GPT 2, into one unified system. It allows you to build automated workflows and create specialized bots for specific tasks like scheduling or customer service. With Comrade AI, you can enable seamless communication across different platforms, including chat, email, and calls.

What sets Comrade AI apart is its ability to use both open source and commercial AI models. This means you have the freedom to choose the tools that best suit your needs and budget. Additionally, Comrade AI comes with a centralized balance feature. This unique system allows you to manage your resources more efficiently by enabling one-time top-ups for all connected services, saving you the hassle of dealing with multiple payments and accounts.

By linking different AI agents into a collaborative network, Comrade AI enhances their collective effectiveness. This interconnectedness allows for more sophisticated and coordinated activities, tapping into the full potential of AI to support and streamline your operations.

In short, Comrade AI delivers a unified, efficient, and hassle-free way to integrate and manage multiple AI services, catering to your specific requirements and simplifying the process of harnessing the power of AI.

As for January 13, 2024 framework supports OpenAI DALLE-3, OpenAI GPT3.5 Turbo, GPT4/Vision, Vertex AI/Google Gemini Pro/Pro Vision, Yandex GPT v2 in asynchomnic mode, Meta LLaMa v2. We are working on getting access to Claude API. 

## Table of Contents
- [Introduction](README.md)
- [Availabe AI Agents](docs/Agents.md)
- [Agent Usage Examples](docs/AgentExamples.md)
- [Document Routines](docs/DocumentRoutines.md)
- [Agent-Agent Interaction Example](docs/AgentAgentInteractions.md)


## Getting Started with ComradeAI

### Hierarchical Structure
The ComradeAI framework consists of the following components:

#### Mycelium
Acts as the central network, managing the flow of information and routing messages to appropriate AI agents.

#### Dialog
Represents a conversation thread between the user and AI agents, containing a series of Messages.

#### Message
Encapsulates the user's input or AI's response within a Dialog.

#### Unified Prompts
Elements within a Message that contain the actual content, specified by type, content, and MIME type.

### Handling Responses: `message_received_handler` Function
This function is crucial for processing responses from AI agents. It is called every time Mycelium receives a response, adding it to the corresponding Dialog.

### Groot Agent: Testing Connectivity to Mycelium
The Groot agent is utilized primarily for testing and confirming a successful connection to the Mycelium network. When you send a message to the Groot agent, it always responds with "I am Groot!" This consistent response is an easy and reliable way to verify that your setup is correctly configured and that you are successfully communicating with Mycelium. If you receive this response, you can be confident that your environment is ready for more advanced interactions with other AI agents.

### Example: Sending a "Hello" Message to Groot Agent

This guide demonstrates how to check ComradeAI connectivity and token validity using Groot.

#### Prerequisites

- Python environment

#### ComradeAI Installation
Before you begin, make sure you have the ComradeAI package installed:

```bash
pip install ComradeAI

```

#### Step 1: Importing Modules
```python
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt
import uuid
import asyncio
```

#### Step 2: Defining the Message Handler
```python
async def message_received_handler(dialog):
    for message in dialog.messages:
        for prompt in message.unified_prompts:
            print(f"Received message: {prompt.content}")
```

#### Step 3: Initializing Mycelium
```python
comradeai_token = 'your_comradeai_token'  # Replace with your actual token
myceliumRouter = Mycelium(ComradeAIToken=comradeai_token, message_received_callback=message_received_handler)
```

#### Step 4: Sending a Message
```python
async def hello_world():
    dialog_id = str(uuid.uuid4())
    dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
    hello_prompt = UnifiedPrompt(content_type="text", content="Hi there!", mime_type="text/plain")
    hello_message = Message(role="user", unified_prompts=[hello_prompt])
    dialog.messages.append(hello_message)
    routing_strategy = {'strategy': 'auto', 'params': 'groot'}
    await myceliumRouter.send_to_mycelium(dialog, routing_strategy)
```

#### Step 5: Running the Script
```python
asyncio.run(hello_world())
asyncio.run(myceliumRouter.start_server(allowNewDialogs=True))
```

##### Expected Behavior
Sending the "Hello" Message: When you run hello_world(), it sends a message to the Groot agent.

Starting the Mycelium Server: By running myceliumRouter.start_server(allowNewDialogs=True), you start the Mycelium server with the capability to allow new dialogs.

###### What to Look For
Once the script is executed, you should see the response "I am Groot!" printed in your console. This confirms that the message has been successfully sent and received by the Groot agent.
The printed response indicates a successful connection to the Mycelium network and proper functioning of the message handling setup in your script.
If you receive this response, you can be confident that your system is correctly set up and ready for more complex interactions with other AI agents.
Remember, the Groot agent is always free of charge, making it an ideal choice for initial testing and connectivity verification.

#### Summary
This guide introduces the core concepts of the ComradeAI package and demonstrates how to send a message to an AI agent and process the response. It provides a foundational understanding for new users, guiding them through the initial steps of using ComradeAI for AI interactions.