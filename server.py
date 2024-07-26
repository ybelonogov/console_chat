import asyncio
import json
import logging
import logging.handlers
import signal
import sys
from typing import Dict, Optional, Tuple

class ChatServer:
    def __init__(self, config_file: str) -> None:
        try:
            with open(config_file) as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from the configuration file {config_file}.")
            sys.exit(1)

        self.HOST: str = config.get('host', '127.0.0.1')
        self.PORT: int = config.get('port', 12345)
        self.BUFFER_SIZE: int = config.get('buffer_size', 1024)
        self.LOG_LEVEL: str = config.get('log_level', 'INFO').upper()

        self.logger = logging.getLogger('ChatServer')
        self.logger.setLevel(self.LOG_LEVEL)
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.users: Dict[str, asyncio.StreamWriter] = {}
        self.server: Optional[asyncio.AbstractServer] = None

    async def start_server(self) -> None:
        self.server = await asyncio.start_server(self.handle_client, self.HOST, self.PORT)
        self.logger.info(f'Server started on {self.HOST}:{self.PORT}')
        async with self.server:
            await self.server.serve_forever()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        addr = writer.get_extra_info('peername')
        nickname = None
        registered = False
        self.logger.info(f'Connection accepted: {addr}')
        try:
            writer.write(self.get_welcome_message().encode('utf-8'))
            await writer.drain()
            while True:
                data = await reader.read(self.BUFFER_SIZE)
                if not data:
                    break
                message = data.decode('utf-8').strip()
                if message.startswith('/register'):
                    registered, nickname = await self.register_user(writer, message, registered, nickname)
                elif message.startswith('/change_nick'):
                    nickname = await self.change_nick(writer, message, registered, nickname)
                elif message == '/quit':
                    await self.quit_chat(writer)
                    break
                elif message == '/shutdown':
                    if await self.shutdown_server_command(writer, nickname):
                        break
                else:
                    await self.send_message(writer, message, registered, nickname)
        except (asyncio.CancelledError, ConnectionResetError, ConnectionAbortedError):
            self.logger.error('Connection error with the client.')
        finally:
            if nickname and nickname in self.users:
                del self.users[nickname]
            writer.close()
            await writer.wait_closed()
            self.logger.info(f'Connection closed: {nickname}')

    async def register_user(self, writer: asyncio.StreamWriter, message: str, registered: bool, nickname: Optional[str]) -> Tuple[bool, Optional[str]]:
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            writer.write(b'Usage: /register <nickname>\n')
            await writer.drain()
            return registered, nickname

        if registered:
            writer.write(b'You are already registered. Use /change_nick <new_nickname> to change your nickname.\n')
        else:
            nickname = parts[1].strip()
            if ' ' in nickname:
                writer.write(b'Nickname cannot contain spaces.\n')
            elif nickname in self.users:
                writer.write(b'This nickname is already taken. Please choose another one.\n')
            else:
                self.users[nickname] = writer
                registered = True
                self.logger.info(f'User registered: {nickname}')
                writer.write(f'You are registered as {nickname}\n'.encode('utf-8'))
        await writer.drain()
        return registered, nickname

    async def change_nick(self, writer: asyncio.StreamWriter, message: str, registered: bool, nickname: Optional[str]) -> Optional[str]:
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            writer.write(b'Usage: /change_nick <new_nickname>\n')
            await writer.drain()
            return nickname

        if not registered:
            writer.write(b'You need to register first using /register <nickname>\n')
        else:
            new_nickname = parts[1].strip()
            if ' ' in new_nickname:
                writer.write(b'Nickname cannot contain spaces.\n')
            elif new_nickname in self.users:
                writer.write(b'This nickname is already taken.\n')
            else:
                if nickname:
                    del self.users[nickname]
                nickname = new_nickname
                self.users[nickname] = writer
                self.logger.info(f'User changed nickname to: {nickname}')
                writer.write(f'You changed your nickname to {nickname}\n'.encode('utf-8'))
        await writer.drain()
        return nickname

    async def quit_chat(self, writer: asyncio.StreamWriter) -> None:
        writer.write(b'Goodbye!\n')
        await writer.drain()

    async def shutdown_server_command(self, writer: asyncio.StreamWriter, nickname: Optional[str]) -> bool:
        if nickname == 'admin':
            writer.write(b'Shutting down server...\n')
            self.logger.info('Shutdown command received. Shutting down server...')
            for user, user_writer in self.users.items():
                user_writer.write(b'Server is shutting down...\n')
                await user_writer.drain()
                user_writer.close()
                await user_writer.wait_closed()
            self.users.clear()
            await writer.drain()
            self.server.close()
            await self.server.wait_closed()
            return True
        else:
            writer.write(b'You do not have permission to shut down the server.\n')
            await writer.drain()
        return False

    async def send_message(self, writer: asyncio.StreamWriter, message: str, registered: bool, nickname: Optional[str]) -> None:
        if not registered:
            writer.write(b'Please register first using /register <nickname>\n')
        elif ' ' not in message:
            writer.write(b'Invalid format. Use <recipient_nickname> <message>\n')
        else:
            to_nick, msg = message.split(' ', 1)
            if to_nick in self.users:
                self.users[to_nick].write(f'{nickname} says: {msg}\n'.encode('utf-8'))
                await self.users[to_nick].drain()
                writer.write(b'Message sent successfully.\n')
                self.logger.info(f'Message from {nickname} to {to_nick}: {msg}')
            else:
                writer.write(b'User not found\n')
                self.logger.info(f'Failed to send message from {nickname} to {to_nick}: User not found')
        await writer.drain()

    def get_welcome_message(self) -> str:
        return """
Welcome to the chat!
Commands:
/register <nickname>        Register with a nickname
/change_nick <new_nickname> Change your nickname
/quit                       Quit the chat
/shutdown                   Shutdown the server (admin only)
To send a message, use the format: <recipient_nickname> <message>
"""

async def shutdown(signal, loop):
    print(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    [task.cancel() for task in tasks]

    print("Cancelling outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    server = ChatServer(config_file)
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))

    await server.start_server()

if __name__ == '__main__':
    asyncio.run(main())
