import socket
import threading
# library for serialization of objects in python
import pickle
import io

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 4444  # Port to listen on (non-privileged ports are > 1023)

is_running = True
BUFFER_SIZE = 8

class Response:
  def __init__(self, payload):
    self.payload = payload

class Request:
  def __init__(self, command, key, post = None):
    self.command = command
    self.key = key
    self.post = post


CLIENTS_SOCKETS_LIST = []


class ClientManager:
  def __init__(self):
    self.clients = {}
    self.lock = threading.Lock()

  def add(self, port):
    self.lock.acquire()
    self.clients[port] = []
    self.lock.release()

  def add_key(self, port, key):
    self.lock.acquire()
    self.clients.get(port).append(key)
    self.lock.release()


  def get_client_by_key(self, key):
    for client in list(self.clients.keys()):
      key_list = self.clients[client]
      if key in key_list:
        return client # port
      
  def remove_key_from_client(self, port, key):
     if key in list(self.clients[port]):
       self.clients[port].remove(key)
       return 0
     else:
       return 1

  def get_client_keys(self, port):
    return self.clients[port]
  
# operatiune cu succes = return code 0, altfel 1
class ObjectManager:
  def __init__(self, client_manager):
    self.objects = {}
    self.client_manager = client_manager
    self.lock = threading.Lock()

  def add(self, key, post, port):
    self.lock.acquire()

    if key in list(self.objects.keys()):
        self.lock.release()
        return 1
    
    self.objects[key] = post
    self.client_manager.add_key(port, key)
    self.lock.release()

    return 0
  
  def remove(self, key):
    self.lock.acquire()

    if key in self.objects:
        self.lock.release()
        return 1
    
    self.objects.pop(key, None)
    self.lock.release()
    return 0

  def get(self, key, port):
    self.lock.acquire()

    if key not in self.objects:
        self.lock.release()
        return f"Key: {key} not found!"
    
    client_vechi = self.client_manager.get_client_by_key(key)
    client_nou = port

    self.client_manager.remove_key_from_client(client_vechi, key)
    self.client_manager.add_key(client_nou, key)

    self.lock.release()
    return  f"Key: {key}, content: {self.objects[key]} belonged to {str(client_vechi)}!\n{key} is now yours!"

  def get_all_keys(self):
    message = "Existing keys: "
    for key in list(self.objects.keys()):
      message += key + " | "

    return message
  
  def search(self, key):
    self.lock.acquire()

    if key not in self.objects:
        self.lock.release()
        return f"Key: {key} not found!"
    
    self.lock.release()
    return  f"Key: {key}, content: {self.objects[key]} belongs to {str(self.client_manager.get_client_by_key(key))}!"

  def remove(self, port, key):
    self.lock.acquire()

    if key not in self.objects:
        self.lock.release()
        return 1, f"Key {key} not found!"
    
    if self.client_manager.remove_key_from_client(port, key) == 0:
      self.lock.release()
      self.objects.pop(key)
      return 0, f"Key: {key} has been removed, client: {port}!"
    else:
      self.lock.release()
      return 1, f"Key: {key} is not yours, you cannot remove it!"
    

  def list_client_objects(self, port):
    message = ''
    key_list = self.client_manager.get_client_keys(port)

    for key in key_list:
      message += f"Key {key} - post {self.objects[key]}\n"

    return message
    

client_manager = ClientManager()
object_manager = ObjectManager(client_manager=client_manager)


def compute_payload(payload):
  stream = io.BytesIO()
  # converting to bytes, serializing
  pickle.dump(Response(payload), stream)
  serialized_payload = stream.getvalue()
  # one extra byte for the length
  payload_length = len(serialized_payload) + 1
  return payload_length.to_bytes(1, byteorder='big') + serialized_payload


def process_command(data, addr):
  # first byte is the length
  payload = data[1:]
  # in-memory binary stream - produces bytes objects
  stream = io.BytesIO(payload)
  # deserialize object (according to structure defined) 
  request = pickle.load(stream)
  payload = '[ERROR] Command not recognized, doing nothing!' # error message
  port = addr[1]

  status_code = None
  
  if request.command == 'add':
    if object_manager.add(request.key, request.post, port) == 1:
      status_code = 1
      payload = f"Key: {request.key} already exists!"
    else:
      status_code = 0
      payload = f"Key: {request.key} has been inserted by {port}!"

  elif request.command == 'search':
    payload = object_manager.search(request.key)

  elif request.command == 'remove':
    status_code, payload = object_manager.remove(port=port, key=request.key)

  elif request.command == 'listmyposts':
    payload = object_manager.list_client_objects(port=port)
    if payload == '':
      payload = f"No posts for client {port}!"
    else:
      payload = "\n" + payload
  elif request.command == 'get':
    payload = object_manager.get(request.key, port)
  elif request.command == 'exit':
    payload="Disconnected!"
    print(f"Client {addr} has disconnected!")

  if (request.command == 'remove' or request.command == 'add') and status_code == 0:
    return compute_payload(payload="[SERVER] " + payload), True, compute_payload(payload="[NOTIFICATION] " + payload)
  else:
    return compute_payload(payload="[SERVER] " + payload), False, None 

def handle_client(client, addr):
  with client:
    while True:
      if client == None:
        break
      data = client.recv(BUFFER_SIZE)
      if not data:
        break
      binary_data = data
      full_data = binary_data
      message_length = binary_data[0]
      # message might be bigger than buffer size
      remaining = message_length - BUFFER_SIZE
      while remaining > 0:
        # we keep on receiving in another buffer and concatenating until there's no data to get full message
        data = client.recv(BUFFER_SIZE)
        binary_data = data
        full_data = full_data + binary_data
        remaining = remaining - len(binary_data)
      response, should_send_to_all, response_for_all = process_command(full_data, addr)

      client.send(response)

      if should_send_to_all:
        for client_from_list in CLIENTS_SOCKETS_LIST:
            if client_from_list != client:
              client_from_list.sendall(response_for_all)


def accept(server):
  while is_running:
    client, addr = server.accept()
    port = addr[1]

    client_manager.add(port)
    CLIENTS_SOCKETS_LIST.append(client)

    client.send(compute_payload("Run [cmdlist] to see all available commands! \n" + object_manager.get_all_keys()))
    print(f"Client {addr} has connected!")
    client_thread = threading.Thread(target=handle_client, args=(client, addr))
    client_thread.start()

def main():
  try:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    accept_thread = threading.Thread(target=accept, args=(server,))
    accept_thread.start()
    accept_thread.join()
  except BaseException as err:
    print(err)
  finally:
    if server:
      server.close()

if __name__ == '__main__':
  main()
