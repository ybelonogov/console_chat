import asyncio
import json
import sys
import signal

class ChatClient:
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

    async def start_client(self) -> None:
        reader, writer = await asyncio.open_connection(self.HOST, self.PORT)
        try:
            await asyncio.gather(
                self.handle_client(reader),
                self.send_messages(writer)
            )
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_client(self, reader: asyncio.StreamReader) -> None:
        try:
            while True:
                data = await reader.read(self.BUFFER_SIZE)
                if not data:
                    break
                print(data.decode('utf-8').strip())
        except asyncio.IncompleteReadError:
            print("Connection closed by the server.")
        except Exception as e:
            print(f"Error: {e}")

    async def send_messages(self, writer: asyncio.StreamWriter) -> None:
        loop = asyncio.get_event_loop()
        while True:
            message = await loop.run_in_executor(None, sys.stdin.readline)
            writer.write(message.encode('utf-8'))
            await writer.drain()

async def shutdown(signal, loop):
    print(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    [task.cancel() for task in tasks]

    print("Cancelling outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    client = ChatClient(config_file)
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))

    await client.start_client()

if __name__ == '__main__':
    asyncio.run(main())
