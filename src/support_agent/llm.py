import json
import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

DEFAULT_MODEL = 'openai:gpt-6-luna'


def chat_model() -> BaseChatModel:
    model = os.getenv('LLM_MODEL', DEFAULT_MODEL)
    default_options = '{"reasoning_effort": "low"}' if model.startswith('openai:') else '{}'
    options = json.loads(os.getenv('LLM_MODEL_OPTIONS', default_options))
    return init_chat_model(model, timeout=20, max_retries=2, **options)
