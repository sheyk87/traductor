"""Transcription engine using faster-whisper with VAD filtering and timestamps."""

from pathlib import Path
from typing import List, Dict, Any
from faster_whisper import WhisperModel


class Transcriber:
    """Handles Speech-To-Text transcription with millisecond-precision timestamps."""

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )

    def transcribe(self, audio_path: Path, language: str = "en") -> List[Dict[str, Any]]:
        """Transcribes the given audio file and returns segments with start/end timestamps."""
        self._load_model()

        # vad_filter=True avoids phantom text during background music or silent pauses
        segments_gen, info = self._model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            beam_size=5,
            word_timestamps=False,
        )

        segments = []
        for idx, seg in enumerate(segments_gen):
            text = seg.text.strip()
            if not text:
                continue
            segments.append({
                "id": idx + 1,
                "start": float(seg.start),
                "end": float(seg.end),
                "text": text,
            })

        return segments
