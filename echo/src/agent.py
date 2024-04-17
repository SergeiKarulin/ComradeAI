from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy
#from Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy
from datetime import datetime
from dotenv import load_dotenv
import os
import asyncio
from PIL import Image

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_AGENT')
agentRMQPass = os.getenv('RABBITMQ_DEFAULT_AGENT_PASS')
agentRMQHost = os.getenv('RABBITMQ_HOST')
agentRMQvHost = os.getenv('RABBITMQ_VHOST')
agentRMQQueueName = os.getenv('RABBITMQ_QUEUE')

async def server_logic(dialog):
    try:
        myceliumRouter.dialogs[dialog.dialog_id].messages[-1].role = "assistant"
        myceliumRouter.dialogs[dialog.dialog_id].messages[-1].sender_info = "echo"
        myceliumRouter.dialogs[dialog.dialog_id].messages[-1].send_datetime = datetime.now()
        
        await myceliumRouter.send_to_mycelium(dialog.dialog_id, isReply=True, newestMessagesToSend=1, autogenerateRoutingStrategies=True)
        #If we enable error message for testing, newestMessagesToSend must be set to 2
    except Exception as ex:
        print("Failed to send message. Error: " + str(ex))
    return False #When False we clean the dialogs dict in Mycelium, when True we recalculate all the total values for the current dialog.

myceliumRouter = Mycelium(host=agentRMQHost, vhost=agentRMQvHost, username=agentRMQLogin, password=agentRMQPass, input_chanel=agentRMQQueueName, message_received_callback=server_logic, serverAsyncModeThreads=1)

async def main():
    #Agents use allowNewDialogs=True as they receive them, clients use False as they generate dialogs, but don't receive new ones, unless there is logic to process them.
    await myceliumRouter.start_server(allowNewDialogs=True)

if __name__ == "__main__":
    asyncio.run(main())