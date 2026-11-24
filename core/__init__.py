"""Core package initialization."""

from core.utils import ensure_ffmpeg
ensure_ffmpeg()

from core.config import TranslationConfig, DEFAULT_VOICES
from core.pipeline import VideoTranslationPipeline

__all__ = ["TranslationConfig", "DEFAULT_VOICES", "VideoTranslationPipeline"]
