import json
import math
import io

from flask import current_app


class AIServiceError(RuntimeError):
    """An expected local-AI configuration or processing error."""


def _ollama_client():
    try:
        from ollama import Client
    except ImportError as error:
        raise AIServiceError(
            "Ollama support is not installed. Run: python -m pip install -r requirements.txt"
        ) from error
    try:
        return Client(host=current_app.config["OLLAMA_HOST"])
    except Exception as error:
        raise AIServiceError(
            "Ollama is not available. Install Ollama and start it before using AI practice."
        ) from error


def _message_content(response):
    message = getattr(response, "message", None)
    if message is not None:
        content = getattr(message, "content", None)
        if content:
            return content
    if isinstance(response, dict):
        content = response.get("message", {}).get("content")
        if content:
            return content
    raise AIServiceError("The local AI model returned an empty response.")


def _valid_schema(value, schema):
    """Validate the small JSON-schema subset used by the local AI contracts."""
    kind = schema.get('type')
    if kind == 'object':
        properties = schema.get('properties', {})
        return (isinstance(value, dict)
                and all(key in value for key in schema.get('required', []))
                and (schema.get('additionalProperties') is not False or set(value) <= set(properties))
                and all(_valid_schema(item, properties[key]) for key, item in value.items() if key in properties))
    if kind == 'array':
        return isinstance(value, list) and all(_valid_schema(item, schema['items']) for item in value)
    if kind == 'string':
        return isinstance(value, str) and len(value) >= schema.get('minLength', 0) and len(value) <= schema.get('maxLength', math.inf)
    if kind == 'number':
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and value >= schema.get('minimum', -math.inf) and value <= schema.get('maximum', math.inf) and math.isfinite(value))
    return False


def validated_band(feedback):
    value = feedback.get('overall_band') if isinstance(feedback, dict) else None
    if not _valid_schema(value, {'type':'number','minimum':0,'maximum':9}):
        raise AIServiceError('The local AI returned an invalid band. Your response is preserved; try again.')
    return float(value)


def _json_response(name, system_prompt, user_prompt, schema):
    client = _ollama_client()
    try:
        response = client.chat(
            model=current_app.config["OLLAMA_TEXT_MODEL"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format=schema,
            options={"temperature": 0},
        )
        result = json.loads(_message_content(response))
        if not _valid_schema(result, schema):
            raise AIServiceError('The local AI returned incomplete or invalid feedback. Please try again.')
        return result
    except AIServiceError:
        raise
    except ConnectionError as error:
        raise AIServiceError(
            "Ollama is not running. Start the Ollama app or run `ollama serve`, then try again."
        ) from error
    except Exception as error:
        raise AIServiceError(
            f"The local Ollama model could not complete this request: {error}"
        ) from error


def _whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise AIServiceError(
            "faster-whisper is not installed. Run: python -m pip install -r requirements.txt"
        ) from error

    model_name = current_app.config["WHISPER_MODEL"]
    device = current_app.config["WHISPER_DEVICE"]
    compute_type = current_app.config["WHISPER_COMPUTE_TYPE"]
    cache = current_app.extensions.setdefault("whisper_models", {})
    cache_key = (model_name, device, compute_type)
    if cache_key not in cache:
        try:
            cache[cache_key] = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
            )
        except Exception as error:
            raise AIServiceError(
                "The Whisper model could not start. Check your model name and available memory."
            ) from error
    return cache[cache_key]


def _decode_speaking_audio(audio_bytes):
    """Decode browser formats to Whisper's 16 kHz mono samples across PyAV versions.

    Passing samples bypasses faster-whisper's older av.open(metadata_errors=...)
    call, which is incompatible with PyAV 19.
    """
    import av
    import numpy as np

    output = io.BytesIO()
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    limit = 16000 * 60 * 10 * 2
    with av.open(io.BytesIO(audio_bytes), mode='r') as container:
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                output.write(converted.to_ndarray().tobytes())
                if output.tell() > limit:
                    raise AIServiceError('Keep each Speaking answer under 10 minutes.')
        for converted in resampler.resample(None):
            output.write(converted.to_ndarray().tobytes())
    if not output.tell():
        raise AIServiceError('The recording contains no audio. Please record your answer again.')
    if output.tell() > limit:
        raise AIServiceError('Keep each Speaking answer under 10 minutes.')
    return np.frombuffer(output.getbuffer(), dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_audio(audio_file):
    """Transcribe one browser-recorded speaking answer locally."""
    audio_bytes = audio_file.read()
    if not audio_bytes:
        raise AIServiceError("The recording was empty. Please record your answer again.")
    if len(audio_bytes) > 15 * 1024 * 1024:
        raise AIServiceError("That recording is too large. Keep each answer under 15 MB.")

    try:
        samples = _decode_speaking_audio(audio_bytes)
        segments, _info = _whisper_model().transcribe(
            samples, beam_size=5, language="en", vad_filter=True,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
    except AIServiceError:
        raise
    except Exception as error:
        raise AIServiceError(f"The local Whisper model could not transcribe this recording: {error}") from error
    if not transcript:
        raise AIServiceError("The AI could not hear a clear answer. Please try again.")
    return transcript


def generate_next_speaking_question(current_question, next_plan, history):
    schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 1, "maxLength": 4000},
            "examiner_note": {"type": "string"},
        },
        "required": ["question", "examiner_note"],
        "additionalProperties": False,
    }
    return _json_response(
        "speaking_next_question",
        """You are a calm, professional IELTS Speaking examiner. Ask exactly one concise next question.
Follow the IELTS structure and the supplied exam plan. Do not praise, correct, or explain the candidate's answer.
Keep Part 1 questions short, keep the Part 2 cue card complete, and ask developed Part 3 discussion questions.
Return only the requested JSON.""",
        json.dumps(
            {
                "current_question": current_question,
                "next_exam_plan_item": next_plan,
                "previous_turns": history[-5:],
            },
            ensure_ascii=False,
        ),
        schema,
    )


def evaluate_writing(prompt, essay, word_count):
    schema = {
        "type": "object",
        "properties": {
            "overall_band": {"type": "number", "minimum": 0, "maximum": 9},
            "task_response_band": {"type": "number", "minimum": 0, "maximum": 9},
            "coherence_band": {"type": "number", "minimum": 0, "maximum": 9},
            "lexical_band": {"type": "number", "minimum": 0, "maximum": 9},
            "grammar_band": {"type": "number", "minimum": 0, "maximum": 9},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "improvements": {"type": "array", "items": {"type": "string"}},
            "feedback": {"type": "string", "minLength": 1},
        },
        "required": [
            "overall_band",
            "task_response_band",
            "coherence_band",
            "lexical_band",
            "grammar_band",
            "strengths",
            "improvements",
            "feedback",
        ],
        "additionalProperties": False,
    }
    return _json_response(
        "ielts_writing_feedback",
        """You are an IELTS Writing examiner providing careful practice feedback, not an official result.
Assess the essay using IELTS Academic Writing Task 2 criteria: task response, coherence and cohesion, lexical resource,
and grammatical range and accuracy. Use half-band scores where appropriate. Be specific, fair, and constructive.
Mention if the essay is substantially below 250 words. Return only the requested JSON.""",
        json.dumps(
            {"task": prompt, "word_count": word_count, "essay": essay},
            ensure_ascii=False,
        ),
        schema,
    )


def evaluate_speaking(turns):
    schema = {
        "type": "object",
        "properties": {
            "overall_band": {"type": "number", "minimum": 0, "maximum": 9},
            "fluency_band": {"type": "number", "minimum": 0, "maximum": 9},
            "lexical_band": {"type": "number", "minimum": 0, "maximum": 9},
            "grammar_band": {"type": "number", "minimum": 0, "maximum": 9},
            "pronunciation_band": {"type": "number", "minimum": 0, "maximum": 9},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "improvements": {"type": "array", "items": {"type": "string"}},
            "feedback": {"type": "string", "minLength": 1},
        },
        "required": [
            "overall_band",
            "fluency_band",
            "lexical_band",
            "grammar_band",
            "pronunciation_band",
            "strengths",
            "improvements",
            "feedback",
        ],
        "additionalProperties": False,
    }
    return _json_response(
        "ielts_speaking_feedback",
        """You are an IELTS Speaking examiner providing practice feedback, not an official result.
Assess the candidate's answers against fluency and coherence, lexical resource, grammatical range and accuracy,
and pronunciation. The audio has already been transcribed, so do not pretend to hear pronunciation details that are
not supported by the transcript; explain this limitation briefly in feedback when necessary. Use half-band scores.
Return only the requested JSON.""",
        json.dumps({"turns": turns}, ensure_ascii=False),
        schema,
    )
