from Mycelium_v01 import Mycelium, Dialog, Message
import datetime
from PIL import Image

# Connection parameters
host = ''
vhost = ''
username = ''
password = ''
queue_name = ''

# Function to create a sample image
def create_sample_image():
    img = Image.new('RGB', (1024, 1024), color = (73, 109, 137))
    img.format = 'JPEG'  # Example format
    return img

def server_logic(dialog):
    # Create a response message with specified attributes
    response_message = Message(
        textPrompts=[{"role": "assistant", "content": "I am Groot."},{"role": "assistant", "content": "I am GROOT!"}],
        urlPrompts=[{"url": "http://www.spellsystems.com", "mime_type" : "image/jpeg"},{"url": "https://www.cx.technology", "mime_type" : "video/mp4"}],
        imagePrompts=[create_sample_image(), create_sample_image()],  # Two violet images
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )


    # Add the response message to the dialog
    dialog = Dialog(messages=[response_message])
    return dialog

if __name__ == "__main__":
    mycelium_server = Mycelium(host=host, vhost=vhost, username=username, password=password, queue_name=queue_name)
    mycelium_server.start_server(server_logic)