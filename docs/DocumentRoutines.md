# Document Routines in ComradeAI

This guide demonstrates how to use DocxToPromptsConverter and XlsxToPromptsConverter in ComradeAI to process .docx and .xlsx files, respectively, and interact with AI agents. We will use two examples: a software development contract (DOCX) and WHO statistics (XLSX).

## Processing a DOCX File with LLaMa v2

### Objective

This guide provides instructions on how to use ComradeAI's DocxToPromptsConverter to process a DOCX file and analyze its contents using the Mycelium framework with the LLaMa v2 agent.

## Prerequisites

- ComradeAI package
- A DOCX file for analysis (you can find one in docx/examples directory)
- ComradeAI Token

## Installation

Before you start, make sure ComradeAI is installed in your environment:

```bash
pip install ComradeAI
```

## Step-by-Step Guide

### Step 1: Convert DOCX to Prompts

First, convert the DOCX file into prompts using the DocxToPromptsConverter:

```python
from ComradeAI.DocumentRoutines import DocxToPromptsConverter
import os

# Define the path to your DOCX file
script_dir = os.path.dirname(os.path.abspath(__file__))
docx_file_path = os.path.join(script_dir, 'docs/examples/contract.docx')

# Convert the DOCX file into prompts
converter = DocxToPromptsConverter(convert_urls=True)
prompts = converter.convert(docx_file_path)
```

### Step 2: Set Up Mycelium with ComradeAI

Initialize Mycelium with your ComradeAI token:

```python
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt
import asyncio
import uuid

# Replace 'your_comradeai_token' with your actual token
comradeai_token = 'your_comradeai_token'
myceliumRouter = Mycelium(ComradeAIToken=comradeai_token)
```

### Step 3: Process the Response from Mycelium

Create a handler function to process the response received from Mycelium:

```python
async def message_received_handler(dialog):
    for message in dialog.messages:
        for prompt in message.unified_prompts:
            print(f"Received message: {prompt.content}")

myceliumRouter.message_received_callback = message_received_handler
```

### Step 4: Analyze the Contract
Send the prompts to the LLaMa v2 agent and receive the analysis:

```python
async def analyze_contract():
    dialog_id = str(uuid.uuid4())
    dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
    
    # Create one message with all the prompts
    new_message = Message(role="user", unified_prompts=prompts)
    dialog.messages.append(new_message)
    
    # Specify the AI agent (LLaMa v2 in this case)
    routing_strategy = {'strategy': 'auto', 'params': 'Meta_LLaMa2'}
    await myceliumRouter.send_to_mycelium(dialog, routing_strategy)

# Run the analysis
asyncio.run(analyze_contract())
asyncio.run(myceliumRouter.start_server(allowNewDialogs=True))
```

Be ready for the request to take 30-60 seconds.

### Conclusion

This guide demonstrates how to convert a DOCX file into prompts and analyze it using the ComradeAI Mycelium framework. Replace the your_comradeai_token with your actual ComradeAI token and ensure the DOCX file path is correctly set.

## Processing an XLSX File with OpenAI Completions (GPT 4 Turbo Preview)

This guide will demonstrate how to process and analyze an XLSX file containing WHO statistics using the ComradeAI Mycelium framework.

### Important Note on XLSX File Processing
Before proceeding, please be aware of the following limitation in the current version of XlsxToPromptsConverter:

- Merged Cells: The XlsxToPromptsConverter does not currently support processing of merged cells in XLSX files. This means that if your XLSX document contains merged cells, they may not be correctly interpreted or converted into prompts.This functionality is planned for future versions of ComradeAI, aiming to enhance the converter's capabilities and provide more accurate processing of complex XLSX documents.

### Prerequisites
- ComradeAI package
- An XLSX file for analysis (you can find one in docx/examples directory)
- ComradeAI Token

### Installation
Ensure you have the ComradeAI package installed in your environment:

```bash
pip install ComradeAI
```

### Step 1: Convert XLSX to Prompts
Convert the XLSX file into prompts suitable for analysis:

```python
from ComradeAI.DocumentRoutines import XlsxToPromptsConverter
import os

# Locate and convert the XLSX file
script_dir = os.path.dirname(os.path.abspath(__file__))
xlsx_file_path = os.path.join(script_dir, 'docs/examples/who_stat_2023_annex1.xlsx')
converter = XlsxToPromptsConverter()
prompts = converter.convert(xlsx_file_path)
```

### Step 2: Setup Mycelium with ComradeAI Token

Initialize the Mycelium router with your ComradeAI token:

```python
from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt
import asyncio
import uuid

comradeai_token = 'comradeai_token'  # Replace with your actual token
myceliumRouter = Mycelium(ComradeAIToken=comradeai_token)
```

### Step 3: Define a Message Handler
Create a function to handle the responses received from Mycelium:

```python
async def message_received_handler(dialog):
    for message in dialog.messages:
        for prompt in message.unified_prompts:
            print(f"Received message: {prompt.content}")

myceliumRouter.message_received_callback = message_received_handler
```

### Step 4: Analyze Statistics from the XLSX file
Send a request to analyze the WHO statistics. Include a role-play instruction to guide the AI:

```python
async def analyze_who_stats():
    dialog_id = str(uuid.uuid4())
    dialog = Dialog(messages=[], dialog_id=dialog_id, reply_to=comradeai_token)
    
    # Define the role of the AI
    analysis_request = "Ты аналитик, который делает выводы из различных таблиц медицинской статистики."
    system_prompt = UnifiedPrompt(content_type="text", content=analysis_request, mime_type="text/plain")
    
    # Prepare the messages
    system_message = Message(role="system", unified_prompts=[system_prompt])
    new_message = Message(role="user", unified_prompts=prompts)
    dialog.messages.extend([system_message, new_message])

    # Specify the AI agent
    routing_strategy = {'strategy': 'auto', 'params': 'OpenAI_GPT_Completions'}
    await myceliumRouter.send_to_mycelium(dialog, routing_strategy)

# Execute the analysis
asyncio.run(analyze_who_stats())
asyncio.run(myceliumRouter.start_server(allowNewDialogs=True))
```

### Notes
- Make sure to replace 'comradeai_token' with your actual token.
- The analysis request sets the context for the AI, guiding it to analyze the data from a specific perspective.

### Conclusion

This guide walks you through the steps to analyze an XLSX file containing WHO statistics using ComradeAI. By setting the context and specifying the role of the AI, you can gain valuable insights from complex data sets.