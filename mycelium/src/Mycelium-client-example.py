from Mycelium_v01 import Mycelium, Dialog, Message
from PIL import Image
import datetime

# Connection parameters
host = ''
vhost = ''
username = ''
password = ''
queue_name = ''

# Function to create a sample image
def create_sample_image():
    img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
    img.format = 'PNG'  # Example format
    return img

if __name__ == "__main__":
    mycelium_client = Mycelium(host=host, vhost=vhost, username=username, password=password, queue_name=queue_name)

    message = Message(
        textPrompts=[{"role": "user", "content": "Tell me more about AI applications in healthcare, please."}],
        urlPrompts=[{"url": "http://www.telemed.technology", "mime_type" : "image/jpeg"},{"url": "https://www.comradeai.org", "mime_type" : "video/mp4"}],
        imagePrompts=[create_sample_image(), create_sample_image()],  # Two violet images
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )
        
    dialog = Dialog(messages=[message])
    mycelium_client.dialogs.append(dialog)
    mycelium_client.connect_to_mycelium()
    mycelium_client.init_mycelium_client()
    mycelium_client.send_to_mycelium(mycelium_client.dialogs[0])
    mycelium_client.print_dialogs()