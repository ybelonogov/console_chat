import socket
import threading
import syslog
import json
import sys

config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
with open(config_file) as f:
    config = json.load(f)

HOST = config.get('host', '127.0.0.1')
PORT = config.get('port', 12345)
MAX_USERS = config.get('max_users', 10)
BUFFER_SIZE = config.get('buffer_size', 1024)
LOG_LEVEL = config.get('log_level', 'INFO')

syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)
syslog.setlogmask(getattr(syslog, f'LOG_{LOG_LEVEL.upper()}'))

users = {}
connections = {}

def handle_client(client_socket, addr):
    nickname = None
    try:
        client_socket.sendall(b'Welcome to the chat! Please register with /register <nickname>\n')
        while True:
            msg = client_socket.recv(BUFFER_SIZE)
            if not msg:
                break
            msg = msg.decode('utf-8').strip()
            if msg.startswith('/register'):
                _, nickname = msg.split()
                users[nickname] = client_socket
                syslog.syslog(f'User registered: {nickname}')
                client_socket.sendall(f'You are registered as {nickname}\n'.encode('utf-8'))
            elif msg.startswith('/msg'):
                _, to_nick, *message = msg.split()
                message = ' '.join(message)
                if to_nick in users:
                    users[to_nick].sendall(f'{nickname} says: {message}\n'.encode('utf-8'))
                    client_socket.sendall(b'Message sent\n')
                    syslog.syslog(f'Message from {nickname} to {to_nick}: {message}')
                else:
                    client_socket.sendall(b'User not found\n')
                    syslog.syslog(f'Failed to send message from {nickname} to {to_nick}: User not found')
            else:
                client_socket.sendall(b'Unknown command\n')
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, f'Error: {e}')
    finally:
        if nickname and nickname in users:
            del users[nickname]
        client_socket.close()
        syslog.syslog(f'Connection closed: {addr}')

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(MAX_USERS)
    syslog.syslog(f'Server started on {HOST}:{PORT}')

    while True:
        client_socket, addr = server_socket.accept()
        syslog.syslog(f'Connection accepted: {addr}')
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.start()

if __name__ == '__main__':
    start_server()
