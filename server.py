import socket
import threading
import syslog
import json
import sys


class ChatServer:
    def __init__(self, config_file):
        with open(config_file) as f:
            config = json.load(f)

        self.HOST = config.get('host', '127.0.0.1')
        self.PORT = config.get('port', 12345)
        self.MAX_USERS = config.get('max_users', 10)
        self.BUFFER_SIZE = config.get('buffer_size', 1024)
        self.LOG_LEVEL = config.get('log_level', 'INFO')

        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_USER)
        syslog.setlogmask(getattr(syslog, f'LOG_{self.LOG_LEVEL.upper()}'))

        self.users = {}
        self.shutdown_event = threading.Event()
        self.server_socket = None

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.HOST, self.PORT))
        self.server_socket.listen(self.MAX_USERS)
        syslog.syslog(syslog.LOG_INFO, f'Server started on {self.HOST}:{self.PORT}')

        while not self.shutdown_event.is_set():
            try:
                self.server_socket.settimeout(1)
                client_socket, addr = self.server_socket.accept()
                syslog.syslog(syslog.LOG_INFO, f'Connection accepted: {addr}')
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.start()
            except socket.timeout:
                continue

        self.server_socket.close()
        syslog.syslog(syslog.LOG_INFO, 'Server shut down')

    def handle_client(self, client_socket, addr):
        nickname = None
        registered = False
        try:
            client_socket.sendall(self.get_welcome_message().encode('utf-8'))
            while not self.shutdown_event.is_set():
                msg = client_socket.recv(self.BUFFER_SIZE)
                if not msg:
                    break
                msg = msg.decode('utf-8').strip()
                if msg.startswith('/register'):
                    if registered:
                        client_socket.sendall(
                            b'You are already registered. Use /change_nick <new_nickname> to change your nickname.\n')
                    else:
                        _, nickname = msg.split()
                        if nickname in self.users:
                            client_socket.sendall(b'This nickname is already taken. Please choose another one.\n')
                        else:
                            self.users[nickname] = client_socket
                            registered = True
                            syslog.syslog(syslog.LOG_INFO, f'User registered: {nickname}')
                            client_socket.sendall(f'You are registered as {nickname}\n'.encode('utf-8'))
                elif msg.startswith('/change_nick'):
                    if not registered:
                        client_socket.sendall(b'You need to register first using /register <nickname>\n')
                    else:
                        _, new_nickname = msg.split()
                        if new_nickname in self.users:
                            client_socket.sendall(b'This nickname is already taken.\n')
                        else:
                            del self.users[nickname]
                            nickname = new_nickname
                            self.users[nickname] = client_socket
                            syslog.syslog(syslog.LOG_INFO, f'User changed nickname to: {nickname}')
                            client_socket.sendall(f'You changed your nickname to {nickname}\n'.encode('utf-8'))
                elif msg == '/quit':
                    client_socket.sendall(b'Goodbye!\n')
                    break
                elif msg == '/shutdown':
                    if nickname == 'admin':
                        client_socket.sendall(b'Shutting down server...\n')
                        self.shutdown_event.set()
                        break
                    else:
                        client_socket.sendall(b'You do not have permission to shut down the server.\n')
                else:
                    if not registered:
                        client_socket.sendall(b'Please register first using /register <nickname>\n')
                    elif ' ' not in msg:
                        client_socket.sendall(b'Invalid format. Use <recipient_nickname> <message>\n')
                    else:
                        to_nick, message = msg.split(' ', 1)
                        if to_nick in self.users:
                            self.users[to_nick].sendall(f'{nickname} says: {message}\n'.encode('utf-8'))
                            syslog.syslog(syslog.LOG_INFO, f'Message from {nickname} to {to_nick}: {message}')
                        else:
                            client_socket.sendall(b'User not found\n')
                            syslog.syslog(syslog.LOG_INFO,
                                          f'Failed to send message from {nickname} to {to_nick}: User not found')
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, f'Error: {e}')
        finally:
            if nickname and nickname in self.users:
                del self.users[nickname]
            client_socket.close()
            syslog.syslog(syslog.LOG_INFO, f'Connection closed: {addr}')

    def get_welcome_message(self):
        return """
Welcome to the chat!
Commands:
    /register <nickname>        Register with a nickname
    /change_nick <new_nickname> Change your nickname
    /quit                       Quit the chat
    /shutdown                   Shutdown the server (admin only)
To send a message, use the format: <recipient_nickname> <message>
"""


if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    server = ChatServer(config_file)
    server.start_server()
