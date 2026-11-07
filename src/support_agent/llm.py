import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

load_dotenv()

MODEL = os.getenv('LLM_MODEL', 'openai:gpt-6-luna')
REASONING_EFFORT = os.getenv('LLM_REASONING_EFFORT', 'low' if MODEL.startswith('openai:') else '')


def chat_model() -> BaseChatModel:
    options = {'reasoning_effort': REASONING_EFFORT} if REASONING_EFFORT else {}
    return init_chat_model(MODEL, timeout=20, max_retries=2, **options)
