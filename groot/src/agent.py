from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_AGENT')
agentRMQPass = os.getenv('RABBITMQ_DEFAULT_AGENT_PASS')
agentRMQHost = os.getenv('RABBITMQ_DEFAULT_HOST')
agentRMQvHost = os.getenv('RABBITMQ_DEFAULT_VHOST')
agentRMQQueueName = os.getenv('QUEUE')

async def server_logic(dialog):
    subAccount = ""
    if len(dialog.messages)>0:
        subAccount = dialog.messages[-1].subAccount
    prompts = [UnifiedPrompt(content_type="text", content="I am Groot!", mime_type="text/plain")]
    message = Message(role="assistant", unified_prompts = prompts, sender_info="Groot", costData={'agentCost' : 0.0, 'networkComission' : 0.0, 'currency' : 'USD'}, subAccount=subAccount)
    new_dialog = Dialog(dialog_id=dialog.dialog_id, endUserCommunicationID=dialog.endUserCommunicationID, requestAgentConfig=dialog.requestAgentConfig, messages=[message])
    await myceliumRouter.send_to_mycelium(new_dialog, routingStrategy = {'strategy' : 'direct', 'params' : dialog.reply_to})

myceliumRouter = Mycelium(host=agentRMQHost, vhost=agentRMQvHost, username=agentRMQLogin, password=agentRMQPass, input_chanel=agentRMQQueueName, message_received_callback=server_logic)

async def main():
    await myceliumRouter.start_server()

if __name__ == "__main__":
    asyncio.run(main())