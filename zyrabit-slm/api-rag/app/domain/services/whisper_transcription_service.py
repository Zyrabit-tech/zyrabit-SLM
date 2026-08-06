"""Service for transcribing audio/video files using local embedded Whisper."""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import BinaryIO, Dict, Any

logger = logging.getLogger("zyrabit.audio")

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    logger.warning("faster-whisper not installed. Audio transcription will not be available.")

# Default configuration from environment variables
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
# Devices can be 'cpu', 'cuda', 'auto'
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float32")


class WhisperTranscriptionService:
    """Handles audio and video transcription using local CTranslate2 Whisper implementation."""

    def __init__(
        self,
        model_name: str = WHISPER_MODEL_NAME,
        device: str = WHISPER_DEVICE,
        compute_type: str = WHISPER_COMPUTE_TYPE,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

    def _load_model(self) -> WhisperModel:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed on this system.")

        if self._model is not None:
            return self._model

        logger.info(f"Loading Whisper model '{self.model_name}' on device '{self.device}'...")
        try:
            # Load the model. It auto-downloads to ~/.cache/huggingface/hub/ by default
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            return self._model
        except Exception as exc:
            logger.error(f"Failed to load Whisper model: {exc}")
            raise RuntimeError(f"Whisper initialization failed: {exc}") from exc

    def transcribe(self, file_path_or_buffer: str | BinaryIO) -> Dict[str, Any]:
        """Transcribes the input audio or video file and returns a structured result."""
        model = self._load_model()
        
        logger.info("Starting audio transcription...")
        try:
            # transcribe returns generator for segments, and info about audio
            segments, info = model.transcribe(
                file_path_or_buffer,
                beam_size=5,
                language=None, # auto-detect
                vad_filter=True # Filter out silences automatically
            )
            
            # Consume the generator to get the full transcript
            full_text_parts = []
            segment_list = []
            
            for segment in segments:
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob
                })
                full_text_parts.append(segment.text.strip())

            full_transcript = " ".join(full_text_parts)
            
            logger.info(f"Transcription complete. Language: {info.language} (probability: {info.language_probability:.2f})")
            
            return {
                "text": full_transcript,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": segment_list
            }
            
        except Exception as exc:
            logger.error(f"Error during audio transcription: {exc}")
            raise RuntimeError(f"Transcription execution failed: {exc}") from exc
