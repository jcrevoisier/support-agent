import pytest

from support_agent import voice
from support_agent.conversation import GREETING, Conversation
from tests.fakes import fake_agent


class Microphone:
    """Returns one recording per turn, then raises ``EOFError`` like Ctrl+D to end the chat."""

    def __init__(self, turns):
        self.turns = list(turns)

    def __call__(self):
        if not self.turns:
            raise EOFError
        return self.turns.pop(0)


def run(replies, recordings, transcribe, speak):
    chat = Conversation(fake_agent(*replies))
    with pytest.raises(EOFError):
        voice.run(chat, record=Microphone(recordings), transcribe=transcribe, speak=speak)
    return chat


def test_voice_chat():
    spoken = []
    chat = run(["What's your order number?"], [b'audio'], lambda audio: 'My lamp is broken', spoken.append)
    assert spoken == [GREETING, "What's your order number?"]
    assert [message.content for message in chat.transcript] == [
        GREETING,
        'My lamp is broken',
        "What's your order number?",
    ]


def test_nothing_heard():
    spoken = []
    run([], [b'audio'], lambda audio: '', spoken.append)
    assert spoken == [GREETING, voice.DIDNT_CATCH_REPLY]


def test_transcription_failure_lets_the_customer_type(monkeypatch):
    def broken_transcribe(audio):
        raise RuntimeError('API down')

    monkeypatch.setattr('builtins.input', lambda prompt: 'My lamp is broken')
    chat = run(["What's your order number?"], [b'audio'], broken_transcribe, lambda text: None)
    assert chat.transcript[1].content == 'My lamp is broken'


def test_speech_failure_still_prints_the_reply(capsys):
    def broken_speak(text):
        raise RuntimeError('API down')

    run(["What's your order number?"], [b'audio'], lambda audio: 'My lamp is broken', broken_speak)
    assert "Bot: What's your order number?" in capsys.readouterr().out
