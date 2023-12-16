from Mycelium_v0.1 import Mycelium, Dialog, Message
from PIL import Image
import datetime

# Function to create a sample image
def create_sample_image():
    img = Image.new('RGB', (100, 100), color = (73, 109, 137))
    img.format = 'JPEG'  # Example format
    return img

# Test script
def test_script():
    # Create Mycelium objects
    myc01 = Mycelium("host1", "vhost1", "user1", "pass1", "queue1")
    myc02 = Mycelium("host2", "vhost2", "user2", "pass2", "queue2")

    # Create sample messages
    message1 = Message(
        textPrompts=[{"role": "user", "content": "Hello, smart machine!"}],
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message2 = Message(
        textPrompts=[{"role": "user", "content": "How does AI impact our daily lives?"}],
        imagePrompts=[create_sample_image()],  # One violet image
        sender_id="SenderID2",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message3 = Message(
        textPrompts=[{"role": "user", "content": "Tell me more about AI applications in healthcare."}],
        urlPrompts=[{"url": "http://www.spellsystems.com", "mime_type" : "image/jpeg"},{"url": "https://www.cx.technology", "mime_type" : "video/mp4"}],
        imagePrompts=[create_sample_image(), create_sample_image()],  # Two violet images
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message4 = Message(
        textPrompts=[{"role": "user", "content": "What are the ethical concerns related to AI?"}, {"role": "user", "content": "I am the second message :)"}],
        sender_id="SenderID2",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message5 = Message(
        textPrompts=[{"role": "user", "content": "Tell me about AI in education."}],
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message6 = Message(
        textPrompts=[{"role": "user", "content": "What are the current AI trends?"}],
        sender_id="SenderID2",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message7 = Message(
        textPrompts=[{"role": "user", "content": "How can AI improve healthcare?"}],
        imagePrompts=[create_sample_image(), create_sample_image()],  # Two violet images
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message8 = Message(
        textPrompts=[{"role": "user", "content": "Tell me about AI ethics."}],
        sender_id="SenderID2",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message9 = Message(
        textPrompts=[{"role": "user", "content": "What is the future of AI?"}],
        imagePrompts=[create_sample_image()],  # One violet image
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message10 = Message(
        textPrompts=[{"role": "user", "content": "How can AI benefit businesses?"}],
        imagePrompts=[create_sample_image(), create_sample_image()],  # Two violet images
        sender_id="SenderID2",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message11 = Message(
        textPrompts=[{"role": "user", "content": "Tell me about AI in finance."}],
        sender_id="SenderID1",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )

    message12 = Message(
        textPrompts=[{"role": "user", "content": "What are the challenges of AI implementation?"}],
        sender_id="SenderID2",
        token_cost=50,
        cost=0.001,
        send_datetime=datetime.datetime.now()
    )


    # Create more messages as needed...

    # Create and add dialogs
    #dialog1 = Dialog(messages=[message1,message2,message3,message4,message5,message6])
    dialog1 = Dialog(messages=[message1])
    #dialog2 = Dialog(messages=[message7,message8,message9,message10,message11,message12])
    dialog2 = Dialog(messages=[message12])
    myc01.add_dialog(dialog1)
    myc01.add_dialog(dialog2)

    # Serialize and deserialize
    serialized_data = myc01.dialogs[0].serialize()
    serialized_and_compressed_data = myc01.dialogs[1].serialize_and_compress()
    new_dialog1 = Dialog()
    new_dialog1.deserialize(serialized_data)
    new_dialog2 = Dialog()
    new_dialog2.decompress_and_deserialize(serialized_and_compressed_data)
    myc02.add_dialog(new_dialog1)
    myc02.add_dialog(new_dialog2)

    # Print dialogs
    print("Mycelium 1 Dialogs:")
    myc01.print_dialogs()
    print("\nMycelium 2 Dialogs:")
    myc02.print_dialogs()

test_script()
