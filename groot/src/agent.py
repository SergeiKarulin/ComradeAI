from ComradeAI.Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy
#from Mycelium import Mycelium, Message, Dialog, UnifiedPrompt, RoutingStrategy
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()
agentRMQLogin = os.getenv('RABBITMQ_DEFAULT_AGENT')
agentRMQPass = os.getenv('RABBITMQ_DEFAULT_AGENT_PASS')
agentRMQHost = os.getenv('RABBITMQ_HOST')
agentRMQvHost = os.getenv('RABBITMQ_VHOST')
agentRMQQueueName = os.getenv('RABBITMQ_QUEUE')

async def server_logic(dialog):
    subAccount = ""
    if len(dialog.messages)>0:
        subAccount = dialog.messages[-1].subAccount
        
    prompts = [UnifiedPrompt(content_type="text", content="I am Groot!", mime_type="text/plain")]
    message = Message(role="assistant", unified_prompts=prompts, sender_info="Groot", subAccount=subAccount, diagnosticData={"AgentDiagnosticData" : "Non-eror test"}, billingData=[{"agent" : "groot", "currency" : "USD", "cost" : 0.0}])
    myceliumRouter.dialogs[dialog.dialog_id].messages.extend([message])
    #await myceliumRouter.dialogs[dialog.dialog_id].generate_error_message("I am Error!", sender_info="Groot", diagnosticData={"AgentDiagnosticData" : "Error Test"}, billingData = [])
    try:
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