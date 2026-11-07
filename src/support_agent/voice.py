import io
import logging
import os
import wave
from collections.abc import Callable
from functools import cache

import numpy as np
import sounddevice as sd
from openai import OpenAI

from support_agent.conversation import Conversation

RECORDING_RATE = 16_000
SPEECH_RATE = 24_000
MIN_RECORDING_SECONDS = 0.3
DIDNT_CATCH_REPLY = "Sorry, I didn't catch that. Could you say it again?"

logger = logging.getLogger(__name__)


def record_audio() -> bytes:
    """Record from the microphone between two presses of Enter, after the bot has finished speaking.

    Returns WAV audio, or nothing if the recording is too short to hold any words.
    """
    sd.wait()
    input('Press Enter and speak. ')
    chunks = []
    with sd.InputStream(
        samplerate=RECORDING_RATE,
        channels=1,
        dtype='int16',
        callback=lambda data, frames, time, status: chunks.append(data.copy()),
    ):
        input('Listening… press Enter when you are done. ')
    if sum(map(len, chunks)) < RECORDING_RATE * MIN_RECORDING_SECONDS:
        return b''
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(RECORDING_RATE)
        file.writeframes(np.concatenate(chunks).tobytes())
    return buffer.getvalue()


def transcribe_audio(audio: bytes) -> str:
    model = os.getenv('STT_MODEL', 'gpt-4o-mini-transcribe')
    return _openai().audio.transcriptions.create(model=model, file=('speech.wav', audio)).text.strip()


def speak_text(text: str) -> None:
    """Start reading the text aloud once the previous message has finished, and return while it plays.

    Returning early lets the agent work on its next message during playback.
    """
    model = os.getenv('TTS_MODEL', 'gpt-4o-mini-tts')
    audio = _openai().audio.speech.create(model=model, voice='alloy', input=text, response_format='pcm').content
    sd.wait()
    sd.play(np.frombuffer(audio, dtype=np.int16), SPEECH_RATE)


def run(
    chat: Conversation,
    record: Callable[[], bytes] = record_audio,
    transcribe: Callable[[bytes], str] = transcribe_audio,
    speak: Callable[[str], None] = speak_text,
) -> None:
    """Run the voice chat until the customer presses Ctrl+C or Ctrl+D.

    ``record``, ``transcribe`` and ``speak`` default to the microphone, the speakers and OpenAI.
    """

    def say(text: str) -> None:
        print(f'Bot: {text}')
        try:
            speak(text)
        except Exception:
            logger.exception('Could not speak in conversation %s', chat.id)

    def listen() -> str:
        audio = record()
        if not audio:
            return ''
        try:
            text = transcribe(audio)
        except Exception:
            logger.exception('Could not transcribe in conversation %s', chat.id)
            return input('Sorry, I could not hear you. Please type your message: ').strip()
        print(f'You: {text}')
        return text

    try:
        say(chat.start())
        while True:
            if not (text := listen()):
                say(DIDNT_CATCH_REPLY)
                continue
            for reply in chat.send(text):
                say(reply)
    finally:
        sd.stop()


@cache
def _openai() -> OpenAI:
    return OpenAI(timeout=20, max_retries=2)
