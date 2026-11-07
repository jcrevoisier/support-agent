import logging

from support_agent.conversation import Conversation

LOG_FILE = 'support-agent.log'


def main() -> None:
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    chat = Conversation()
    print(f'Bot: {chat.transcript[-1].content}')
    try:
        while True:
            if text := input('You: ').strip():
                print(f'Bot: {chat.send(text)}')
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        print(f'Conversation saved to {chat.close()}')
