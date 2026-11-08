from functools import cache
from pathlib import Path

from langchain_core.vectorstores import InMemoryVectorStore

from support_agent.llm import embedding_model

POLICIES_FILE = Path(__file__).parent / 'policies.md'


def search(question: str, count: int = 2) -> list[str]:
    """Return the policy sections closest in meaning to the question."""
    return [document.page_content for document in _store().similarity_search(question, k=count)]


@cache
def _store() -> InMemoryVectorStore:
    """Embed each section of the policies file once, on the first search."""
    sections = [section.strip() for section in POLICIES_FILE.read_text().split('## ') if section.strip()]
    return InMemoryVectorStore.from_texts(sections, embedding_model())
