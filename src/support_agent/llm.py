import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

load_dotenv()

MODEL = os.getenv('LLM_MODEL', 'openai:gpt-6-luna')


def chat_model() -> BaseChatModel:
    return init_chat_model(MODEL, timeout=20, max_retries=2, reasoning_effort='low')
