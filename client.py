import socket
import pickle
import io
import threading

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 4444  # The port used by the server
BUFFER_SIZE = 8

CMDLIST = {
  "listmyposts": "list all current client posts",
  "add <key> <post_content>": "add a new post content for current client with specified key",
  "search <key>": "search a post by key",
  "remove <key>": "remove a post by key",
  "get <key>": "display the post for the specified key and transfer the key to yourself",
  "exit": "close the connection"
}

class Response:
  def __init__(self, payload):
    self.payload = payload

class Request:
  def __init__(self, command, key, post = None):
    self.command = command
    self.key = key
    self.post = post

def get_command(command):
    # remove spaces at the beginning and at the end of the string
    c = command.strip()
    items = c.split(' ')
    # the object we're sending to the server respects the class structure defined
    if len(items) == 1:
      request = Request(items[0], None, None)
    elif len(items) == 2: 
      request = Request(items[0], items[1], None)
    else:
      request = Request(items[0], items[1], ' '.join(items[2:]))
    # buffer needed for serialization
    stream = io.BytesIO()
    pickle.dump(request, stream)
    serialized_payload = stream.getvalue()
    # specify the length of the bytes stream (first byte has this info)
    payload_length = len(serialized_payload) + 1
    return payload_length.to_bytes(1, byteorder='big') + serialized_payload


def handle_response(data):
   full_data = data
   message_length = data[0]
   remaining = message_length - len(data)
   # make sure to get data even if it exceeds buffer size
   while remaining > 0:
      data = s.recv(BUFFER_SIZE)
      full_data = full_data + data
      remaining = remaining - len(data)
   stream = io.BytesIO(full_data[1:])  
   response = pickle.load(stream)
   print(response.payload) 


def input_handler(socket, command):
    while True:
        command = input()
        if command == 'cmdlist':
            for key, value in CMDLIST.items():
              print(f"{key} - {value}\n")
        else:
          socket.send(get_command(command))
          if command == 'exit':
             exit(0)

def response_handler(socket):
    while True:
        try:
          data = socket.recv(BUFFER_SIZE)
          if data:
            handle_response(data)
        except:
          None


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    handle_response(s.recv(BUFFER_SIZE))
    command = ''

    thread_input = threading.Thread(target=input_handler, args=(s, command))
    thread_response= threading.Thread(target=response_handler, args=(s,))

    thread_response.start()
    thread_input.start()

    thread_response.join()
    thread_input.join()




