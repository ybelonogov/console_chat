import socket
import threading
import json
import sys


class ChatClient:
    def __init__(self, config_file):
        with open(config_file) as f:
            config = json.load(f)

        self.HOST = config.get('host', '127.0.0.1')
        self.PORT = config.get('port', 12345)
        self.SYSLOG_HOST = config.get('syslog_host', '127.0.0.1')
        self.SYSLOG_PORT = config.get('syslog_port', 514)
        self.BUFFER_SIZE = config.get('buffer_size', 1024)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.syslog_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def connect(self):
        try:
            self.client_socket.connect((self.HOST, self.PORT))
            print("Connected to the chat server. Please register with /register <nickname>")
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.start()
            self.send_messages()
        except Exception as e:
            print(f"Unable to connect to server: {e}")
            sys.exit()

    def receive_messages(self):
        while True:
            try:
                msg = self.client_socket.recv(self.BUFFER_SIZE)
                if msg:
                    print(msg.decode('utf-8'))
                else:
                    print("Server disconnected.")
                    break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def send_messages(self):
        while True:
            try:
                msg = input()
                self.client_socket.sendall(msg.encode('utf-8'))
                if msg.startswith('/register') or msg.startswith('/change_nick') or ' ' in msg:
                    confirmation = self.client_socket.recv(self.BUFFER_SIZE).decode('utf-8')
                    print(confirmation)
                self.send_to_syslog(msg)
                if msg == '/quit':
                    print("You have disconnected.")
                    break
            except Exception as e:
                print(f"Error sending message: {e}")
                break
        self.client_socket.close()

    def send_to_syslog(self, message):
        try:
            self.syslog_socket.sendto(message.encode('utf-8'), (self.SYSLOG_HOST, self.SYSLOG_PORT))
        except Exception as e:
            print(f"Error sending message to syslog server: {e}")


if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    client = ChatClient(config_file)
    client.connect()
