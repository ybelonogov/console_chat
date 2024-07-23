import socket
import threading
import json
import sys

config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
with open(config_file) as f:
    config = json.load(f)

HOST = config.get('host', '127.0.0.1')
PORT = config.get('port', 12345)
BUFFER_SIZE = config.get('buffer_size', 1024)

def receive_messages(client_socket):
    while True:
        try:
            msg = client_socket.recv(BUFFER_SIZE)
            if msg:
                print(msg.decode('utf-8'))
            else:
                print("Server disconnected.")
                break
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

if __name__ == '__main__':
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
    except Exception as e:
        print(f"Unable to connect to server: {e}")
        sys.exit()

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.start()

    print("Connected to the chat server. Please register with /register <nickname>")

    while True:
        try:
            msg = input()
            client_socket.sendall(msg.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
            break
