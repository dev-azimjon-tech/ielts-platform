import json
import tempfile

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
        return json.loads(_message_content(response))
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


def transcribe_audio(audio_file):
    """Transcribe one browser-recorded speaking answer locally."""
    audio_bytes = audio_file.read()
    if not audio_bytes:
        raise AIServiceError("The recording was empty. Please record your answer again.")
    if len(audio_bytes) > 15 * 1024 * 1024:
        raise AIServiceError("That recording is too large. Keep each answer under 15 MB.")

    filename = audio_file.filename or "speaking-answer.webm"
    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".webm"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix) as temporary_audio:
            temporary_audio.write(audio_bytes)
            temporary_audio.flush()
            segments, _info = _whisper_model().transcribe(
                temporary_audio.name,
                beam_size=5,
                language="en",
                vad_filter=True,
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
            "question": {"type": "string"},
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
            "feedback": {"type": "string"},
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
            "feedback": {"type": "string"},
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
