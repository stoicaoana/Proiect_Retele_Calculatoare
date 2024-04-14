
### Object Sharing in Memory:

- The client connects to the server and receives a list of keys, each key identifying an object published on the server by connected clients.
- A client can search for an object on the server based on its key.
- The server maintains a dictionary mapping keys to the client where the corresponding object is located.
- Upon receiving a request to retrieve an object by key, the server identifies the client where the object is located and requests the transfer of the object's content from that client.
- Upon receiving the object, the server delivers it to the requesting client.
- A client can publish a new object on the server by sending a key associated with the object.
- The server checks the uniqueness of the key to accept the object's registration in the dictionary, notifying all connected clients with the newly published key.
- A client can delete a key previously published on the server, in which case the server notifies all connected clients to remove that key from their lists.

