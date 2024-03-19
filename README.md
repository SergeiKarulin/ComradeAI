# ComradeAI
Comrade AI is an open source framework that connects various AI services into one unified system. It allows you to build automated workflows and create specialized bots for specific tasks like scheduling or customer service. With Comrade AI, you can enable seamless communication across different platforms, including chat, email, and calls.

What sets Comrade AI apart is its ability to use both open source and commercial AI models. This means you have the freedom to choose the tools that best suit your needs and budget. Additionally, Comrade AI comes with a centralized balance feature. This unique system allows you to manage your resources more efficiently by enabling one-time top-ups for all connected services, saving you the hassle of dealing with multiple payments and accounts.

By linking different AI agents into a collaborative network, Comrade AI enhances their collective effectiveness. This interconnectedness allows for more sophisticated and coordinated activities, tapping into the full potential of AI to support and streamline your operations.

In short, Comrade AI delivers a unified, efficient, and hassle-free way to integrate and manage multiple AI services, catering to your specific requirements and simplifying the process of harnessing the power of AI.

As for February 7, 2024 framework supports OpenAI DALLE-3, OpenAI GPT3.5 Turbo, GPT4/Vision, Vertex AI/Google Gemini Pro/Pro Vision, Yandex GPT v2 in asynchronous mode, Meta LLaMa v2 and wonderful Claude 2.1 from Anthropic, OpenAI Whisper Large v3, Stable Diffusion XL, Meta MBART.

The upcoming agents are Sber model Zoo and WaveNet or Mozilla TTS.

## Table of Contents
- [Introduction](README.md)
- [Agent-Agent Interaction Example](docs/AgentAgentInteractions.md)
- [Processors to Load/Transform/Download data](docs/Processors.md)
- [Agent Usage Examples](docs/ServiceExamples.md)
- [Availabe AI Services Configurations](docs/ServiceConfigurations.md)
- [Document Routines - deprecated](docs/DocumentRoutines.md)

## Getting Started with ComradeAI

### Hierarchical Structure
The ComradeAI framework consists of the following components:

#### Mycelium
Acts as the central network, managing the flow of information and routing messages to appropriate AI agents.

#### Dialog and DialogTemplate
Represents a conversation thread between the user and AI agents, containing a series of Messages. DialogTemplate allows to create multiple Dialogs of the same purpose but with variations to find the prompt delivering the best Agent output.

#### Message
Encapsulates the user's input or AI's response within a Dialog.

#### Unified Prompts
Elements within a Message that contain the actual content, specified by type, content, and MIME type.

### AI Service
A Mycelium server that processes requests using AI model(s) or third-party AI service API.

### Agent
Agent is an abstraction that incapsulates some AI Service plus its specific configuration. A list if available services and their configuration options available [here](docs/ServiceConfigurations.md)

#### Processors
Tools to load, transform and download data keeping it compatible with ComradeAI Agents. A list of processors is available (here)[docs/Processors.md].

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
from ComradeAI.Mycelium import Mycelium, Agent
```

#### Step 2: Connecting to Mycelium Network

```python
AI = Mycelium(ComradeAIToken="YOUR_COMRADEAI_TOKEN")
AI.connect()
```

#### Step 3: Creating the AI agent
The only thing you need is token. 
```python
groot = Agent(AI, "groot")
```

#### Step 4: Sending a Message
```python
resultDialog = "Yo! Wussup?" >> groot
```

#### Step 5: Printing the conversation
```python
print(resultDialog)
```

##### Expected Behavior
You will the the follwoing in the console:
```
Message 1: user
Prompt 1: content type: text, mime-type: text/plain, content: Yo! Wussup?
Message 2: assistant
Prompt 1: content type: text, mime-type: text/plain, content: I am Groot!
```

###### What to Look For
Once the script is executed, you should see the Dialog data ending with the Agent message "I am Groot!" printed in your console. This confirms that the message has been successfully sent and received by the Groot agent.
The printed response indicates a successful connection to the Mycelium network and proper functioning of the message handling setup in your script.
If you receive this response, you can be confident that your system is correctly set up and ready for more complex interactions with other AI agents.
Remember, the Groot agent is always free of charge, making it an ideal choice for initial testing and connectivity verification.


### Example: Agent-Agent Interaction and Using Processors
In this example, we demonstrate how to leverage processors—specifically loaders, splitters, and downloaders—to manage dialogs derived from various data sources, transform these dialogs, and save the associated media.


```python
# Considering you have already installed ComradeAI as described above.
from ComradeAI.Mycelium import Mycelium, Agent
from ComradeAI.Processors import TextListSplitter, DialogToFileDownloader, DialogCollapser

AI = Mycelium(ComradeAIToken=YOUR_COMRADE_AI_TOKEN)
AI.connect()

#Defining agents we need
llama2 = Agent(AI, "Meta_LLaMa2", {"temperature" : 0.5})
sdXL = Agent(AI, "StabeDiffusion_Text2Image")
dalle = Agent(AI, "OpenAI_DALLE3")

prompt = """
Generate 5 promts to create a logo for Robotic Process Automation SDK called Comrade AI. Logo must one or two colored, wired. Give prompts as a list with no extra comments or task confirmations.
"""
# We provide prompt to LLaMa v2, then split last assistant responce into separate commands and save them into a list named promptLits.
promptList = prompt >> llama2 >> TextListSplitter(1, ["assistant"])
# We process promptList with Stable Diffusion and with DALL-e 3, then we unite results into one list of dialogs, download them all, 
# and then concatenate in one dialog to print.
result = ((promptList >> sdXL) + (promptList >> dalle)) >> DialogToFileDownloader() >> DialogCollapser()

print(result)

AI.connection.close()

```
In this script, we utilize three services: Meta LLaMa v2, StableDiffusion, and DALL-E 3 from OpenAI. To manage the dialog flow, we employ three processors: TextListSplitter, DialogToFileDownloader, and DialogCollapser.

The process begins with the generation of prompts using Meta LLaMa v2, where it creates five distinct prompts for logo ideas. To ensure that each prompt is processed individually by the text-to-image models, we employ the TextListSplitter to separate them into individual dialogs. This step prevents the models from interpreting the prompts as a single, combined task. Subsequently, we forward the prompts to both Stable Diffusion and DALL-E 3, aggregating the outputs into a unified list of dialogs. The DialogToFileDownloader then saves the media from each dialog into the Downloads folder, organizing them into subdirectories named after the DialogID. Finally, the DialogCollapser merges all dialogs back into a single entity, enabling us to print the result, as the print function does not support lists of dialogs.

### Example: Using Dialog Templates
Dialog templates allow you to create dialog variations in order to cover multiple related tasks in on pipeline or optimize prompts to get the best outcomes from models used.

```python
# Considering you have already installed ComradeAI as described above.
Coming soon

```

#### Summary
This guide introduces the core concepts of the ComradeAI package and demonstrates how to send a message to an AI agent and process the response. It provides a foundational understanding for new users, guiding them through the initial steps of using ComradeAI for AI interactions.