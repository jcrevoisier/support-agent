import json
import os

from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

DEFAULT_MODEL = 'openai:gpt-6-luna'
DEFAULT_EMBEDDING_MODEL = 'openai:text-embedding-3-small'


def chat_model() -> BaseChatModel:
    model = os.getenv('LLM_MODEL', DEFAULT_MODEL)
    default_options = '{"reasoning_effort": "low"}' if model.startswith('openai:') else '{}'
    options = json.loads(os.getenv('LLM_MODEL_OPTIONS', default_options))
    return init_chat_model(model, timeout=20, max_retries=2, **options)


def embedding_model() -> Embeddings:
    return init_embeddings(os.getenv('EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL), timeout=20, max_retries=2)
