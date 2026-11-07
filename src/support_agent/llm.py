import json
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

load_dotenv()

MODEL = os.getenv('LLM_MODEL', 'openai:gpt-6-luna')
DEFAULT_OPTIONS = '{"reasoning_effort": "low"}' if MODEL.startswith('openai:') else '{}'
MODEL_OPTIONS = json.loads(os.getenv('LLM_MODEL_OPTIONS', DEFAULT_OPTIONS))


def chat_model() -> BaseChatModel:
    return init_chat_model(MODEL, timeout=20, max_retries=2, **MODEL_OPTIONS)
