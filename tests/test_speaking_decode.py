"""Exercise real audio decoding, rather than mocking the dependency boundary."""
import io
import wave
from types import SimpleNamespace

import numpy as np
import pytest
from werkzeug.datastructures import FileStorage

from app.ai_service import _decode_speaking_audio, transcribe_audio, AIServiceError


def wav(rate=8000,channels=2):
    samples=(np.sin(np.arange(rate)*2*np.pi*440/rate)*12000).astype(np.int16)
    samples=np.repeat(samples[:,None],channels,axis=1)
    output=io.BytesIO()
    with wave.open(output,'wb') as file:
        file.setnchannels(channels);file.setsampwidth(2);file.setframerate(rate);file.writeframes(samples.tobytes())
    return output.getvalue()


def test_audio_decoder_resamples_stereo_for_installed_pyav():
    samples=_decode_speaking_audio(wav())
    assert samples.dtype==np.float32 and samples.shape==(16000,)
    assert np.max(np.abs(samples))>.1 and np.max(np.abs(samples))<=1


def test_transcriber_receives_samples_instead_of_incompatible_file_decode(monkeypatch):
    def transcribe(samples,**kwargs):
        assert isinstance(samples,np.ndarray) and samples.shape==(16000,)
        return [SimpleNamespace(text='A spoken answer.')],None
    monkeypatch.setattr('app.ai_service._whisper_model',lambda:SimpleNamespace(transcribe=transcribe))
    assert transcribe_audio(FileStorage(stream=io.BytesIO(wav()),filename='answer.wav'))=='A spoken answer.'


def test_corrupt_audio_reports_a_service_error():
    with pytest.raises(AIServiceError,match='could not transcribe'):
        transcribe_audio(FileStorage(stream=io.BytesIO(b'invalid audio'),filename='answer.webm'))
