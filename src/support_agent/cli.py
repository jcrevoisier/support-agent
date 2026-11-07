import logging

from dotenv import load_dotenv

from support_agent.conversation import Conversation

LOG_FILE = 'support-agent.log'

logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    try:
        chat = Conversation()
    except Exception:
        logger.exception('Could not start the agent')
        raise SystemExit(
            f'Could not start the agent. Check OPENAI_API_KEY and LLM_MODEL_OPTIONS in .env. See {LOG_FILE}.'
        )
    print(f'Bot: {chat.start()}')
    try:
        while True:
            if text := input('You: ').strip():
                for reply in chat.send(text):
                    print(f'Bot: {reply}')
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        print('Saving the conversation…')
        try:
            path = chat.close()
        except KeyboardInterrupt:
            print('Stopped before the conversation was saved.')
        except OSError:
            logger.exception('Could not save conversation %s', chat.id)
            print(f'Could not save the conversation. See {LOG_FILE}.')
        else:
            print(f'Saved to {path}' if path else 'Nothing to save.')
